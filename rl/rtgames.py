#!/usr/bin/env python3
"""rutracker-games v5.0.0 — RuTracker Games Browser"""

import argparse
import asyncio
import json
import os
import re
import ssl as ssl_module
import sys
import webbrowser

import aiofiles
import aiohttp
import certifi
import urllib3
from bs4 import BeautifulSoup as bs
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (BarColumn, MofNCompleteColumn, Progress,
                           SpinnerColumn, TextColumn)
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

# ── Config & Constants ───────────────────────────────────────────────────────
# Sub-forums that contain actual games (not info/announcement topics)
FORUM_SUBFORUMS = {
    # Linux sub-forums
    1992: "Linux Native",
    2059: "Linux Wine/DOSBox",
    # Windows sub-forums - all game categories
    127: "Windows Arcade",
    2203: "Windows Fighting",
    647: "Windows FPS",
    646: "Windows TPS",
    50: "Windows Horror",
    53: "Windows Adventure",
    1008: "Windows Hidden Object",
    900: "Windows Visual Novel",
    128: "Windows Kids",
    2114: "Windows Multimedia",
    2204: "Windows Logic/Puzzle",
    278: "Windows Chess",
    52: "Windows RPG",
    54: "Windows Simulation",
    51: "Windows RTS",
    2226: "Windows TBS",
    2118: "Windows Collections",
    1310: "Windows Old Games (Action)",
    2410: "Windows Old Games (RPG)",
    2205: "Windows Old Games (Strategy)",
    2225: "Windows Old Games (Adventure)",
    2206: "Windows Old Games (Sim)",
    1007: "Windows Old Games (Arcade)",
    2228: "Windows Old PC",
    # Mac sub-forums
    537: "Mac Native",
    637: "Mac Wine/DOSBox",
}

# Group forums by platform (only sub-forums with actual games)
LINUX_FORUMS = [1992, 2059]
WINDOWS_FORUMS = [127, 2203, 647, 646, 50, 53, 1008, 900, 128, 2114, 2204, 278,
                  52, 54, 51, 2226, 2118, 1310, 2410, 2205, 2225, 2206, 1007, 2228]
MAC_FORUMS = [537, 637]
ALL_GAME_FORUMS = LINUX_FORUMS + WINDOWS_FORUMS + MAC_FORUMS

KNOWN_FORUMS = {
    "linux": (LINUX_FORUMS, "Native Linux Games"),
    "windows": (WINDOWS_FORUMS, "PC Games (Windows)"),
    "mac": (MAC_FORUMS, "Mac Games"),
    "all": (ALL_GAME_FORUMS, "All Games"),
}
MULTI_FORUMS = ALL_GAME_FORUMS
FORUM_BASE = "https://rutracker.org/forum/viewforum.php?f={fid}&start={start}"
TOPIC_BASE = "https://rutracker.org/forum/viewtopic.php?t={tid}"
VIEW_URL = "https://rutracker.org/forum/"

# Use XDG cache directory for portability
if sys.platform == "win32":
    XDG_CACHE_HOME = os.path.join(
        os.environ.get("LOCALAPPDATA", "."),
        "rtlinux"
    )
else:
    XDG_CACHE_HOME = os.environ.get(
        "XDG_CACHE_HOME",
        os.path.expanduser("~/.cache")
    )
CACHE_DIR = os.path.join(XDG_CACHE_HOME, "rtlinux")
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
CONCURRENCY = 24
PAGE_SIZE = 50

console = Console()

# Allowlist for webbrowser.open() to prevent SSRF
ALLOWED_DOMAINS = {"rutracker.org", "rutracker.net", "rutracker.nl"}

# SSL context with certificate verification enabled
SSL_CTX = ssl_module.create_default_context(cafile=certifi.where())


# ── Cache Layer ─────────────────────────────────────────────────────────────
def validate_cache_data(data):
    """Validate that cached data is a list of game dicts with required keys."""
    if not isinstance(data, list):
        return False
    if not data:  # Empty list is valid but empty
        return True
    for item in data:
        if not isinstance(item, dict):
            return False
        required_keys = {"name", "link", "tid", "seeds", "size", "date", "forum"}
        if not all(k in item for k in required_keys):
            return False
    return True


# ── HTTP ─────────────────────────────────────────────────────────────────────
async def fetch_url(session, url, sem):
    """Fetch a URL with rate-limiting via semaphore. Returns bytes or None on failure."""
    async with sem:
        try:
            async with session.get(
                url,
                headers={"User-Agent": UA},
                ssl=SSL_CTX,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as r:
                return await r.read()
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
            return None


# ── Page count ───────────────────────────────────────────────────────────────
async def get_total_pages(session, sem, fid):
    """Detect the total number of pages for a forum by parsing pagination links.

    Uses a cached max_page value if available, otherwise fetches the first page
    and extracts the highest page number from the pagination div.
    Falls back to 47 pages if detection fails.
    """
    max_file = os.path.join(CACHE_DIR, f"max_page_{fid}.txt")
    if os.path.exists(max_file):
        try:
            with open(max_file) as f:
                return int(f.read().strip())
        except (ValueError, OSError):
            return None
    raw = await fetch_url(session, FORUM_BASE.format(fid=fid, start=0), sem)
    if raw:
        # RuTracker uses Windows-1251 encoding
        content = raw.decode("cp1251", errors="ignore")
        soup = bs(content, "html.parser")
        # try pagination div
        pg = soup.find("div", class_="pg")
        if pg:
            nums = [int(a.text) for a in pg.find_all("a") if a.text.strip().isdigit()]
            if nums:
                pages = max(nums)
                os.makedirs(CACHE_DIR, exist_ok=True)
                with open(max_file, "w") as f:
                    f.write(str(pages))
                return pages
        console.print(
            f"[yellow] Could not detect pages for f={fid}, defaulting to 1[/yellow]"
        )
        return 1


# ── Parse one HTML page ───────────────────────────────────────────────────────
def _extract_tid(href: str) -> str:
    """Pull topic id from any href variant."""
    m = re.search(r"[?&]t=(\d+)", href)
    return m.group(1) if m else ""


def parse_html(content: str, fid: int) -> list:
    """Parse a single RuTracker forum page HTML into a list of game dicts.

    RuTracker forum rows contain:
    - Title:   td.vf-col-t-title > a.torTopic
    - Seeds:   td.vf-col-tor > div > span.seedmed > b
    - Size:    td.vf-col-tor > div > a.f-dl  (e.g. "574.9\\xa0MB")
    - Date:    td.vf-col-last-post > p:first-child  (e.g. "2026-04-22 13:58")

    Returns list of dicts with keys: name, link, tid, seeds, size, date, forum.
    Seeds and size are stored as raw extracted strings; formatting happens at display time.
    """
    soup = bs(content, "html.parser")
    games = []

    pc = soup.find("div", id="page_content")
    if not pc:
        return games

    # try strict class first, then any table with vf-tor in class string
    table = pc.find("table", class_="vf-table vf-tor forumline forum") or pc.find(
        "table", class_=lambda c: c and "vf-tor" in c
    )
    if not table:
        return games

    for row in table.find_all("tr", class_="hl-tr"):
        try:
            # ── title ──
            tc = row.find("td", class_=lambda c: c and "vf-col-t-title" in c)
            if not tc:
                continue
            a = tc.find("a", class_=lambda c: c and "torTopic" in c)
            if not a:
                continue

            name = a.get_text(" ", strip=True)
            href = a.get("href", "")
            tid = _extract_tid(href)

            # build canonical link
            if tid:
                link = TOPIC_BASE.format(tid=tid)
            elif href.startswith("http"):
                link = href
            elif href.startswith("/"):
                link = "https://rutracker.org" + href
            else:
                link = VIEW_URL + href

            # ── seeds & size: structured extraction from vf-col-tor ──
            # HTML structure:
            #   <td class="vf-col-tor">
            #     <div><span class="seedmed"><b>50</b></span> | <span class="leechmed">...</span></div>
            #     <div><a class="f-dl">574.9&nbsp;MB</a></div>
            #   </td>
            seeds = "-"
            size = "-"
            tor_col = row.find("td", class_=lambda c: c and "vf-col-tor" in c)
            if tor_col:
                # Extract seeds from span.seedmed > b
                seed_span = tor_col.find("span", class_="seedmed")
                if seed_span and seed_span.find("b"):
                    seeds = seed_span.find("b").get_text(strip=True)

                # Extract size from a.f-dl (download link text)
                size_link = tor_col.find("a", class_=lambda c: c and "f-dl" in c)
                if size_link:
                    size = size_link.get_text(strip=True).replace("\xa0", " ")

                # Fallback: if structured extraction failed, try text split
                if seeds == "-" or size == "-":
                    tor_text = tor_col.get_text(strip=True)
                    if "|" in tor_text:
                        parts = tor_text.split("|")
                        if len(parts) >= 2 and seeds == "-":
                            seeds = parts[0].strip()
                        if len(parts) >= 2 and size == "-":
                            size = parts[1].strip()
                    elif tor_text and seeds == "-":
                        seeds = tor_text

            # ── date: extract from vf-col-last-post ──
            # HTML: <td class="vf-col-last-post"><p>2026-04-22 13:58</p>...
            date = "-"
            last_post = row.find("td", class_=lambda c: c and "vf-col-last-post" in c)
            if last_post:
                first_p = last_post.find("p")
                if first_p:
                    date_text = first_p.get_text(strip=True)
                    # Format: "YYYY-MM-DD HH:MM" -- take just the date part
                    if len(date_text) >= 10:
                        date = date_text[:10]

            games.append(
                {
                    "name": name,
                    "link": link,
                    "tid": tid,
                    "seeds": seeds,
                    "size": size,
                    "date": date,
                    "forum": fid,
                }
            )
        except Exception as e:
            if os.environ.get("RTLINUX_DEBUG"):
                console.print(f"[dim]Row parse error: {e}[/dim]")
            continue
    return games


# ── Fetch one page (with disk cache) ─────────────────────────────────────────
async def fetch_page(session, sem, fid, page_idx, refresh):
    """Fetch and parse a single forum page, using disk cache when available.

    If the page HTML is cached and refresh=False, reads from disk.
    Otherwise fetches from RuTracker, caches the HTML, and parses it.
    Returns a list of game dicts.
    """
    cf = os.path.join(CACHE_DIR, f"{fid}_{page_idx}.html")
    if os.path.exists(cf) and not refresh:
        async with aiofiles.open(cf, encoding="cp1251", errors="ignore") as f:
            content = await f.read()
    else:
        url = FORUM_BASE.format(fid=fid, start=page_idx * 50)
        raw = await fetch_url(session, url, sem)
        if not raw:
            return []
        # RuTracker uses Windows-1251 (cp1251) encoding
        content = raw.decode("cp1251", errors="ignore")
        async with aiofiles.open(cf, "w", encoding="cp1251") as f:
            await f.write(content)
    return parse_html(content, fid)


# ── Load full catalog ────────────────────────────────────────────────────────
async def load_catalog_async(forum_ids, refresh):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_key = "_".join(str(f) for f in sorted(forum_ids))
    games_json = os.path.join(CACHE_DIR, f"games_{cache_key}.json")

    if os.path.exists(games_json) and not refresh:
        try:
            with open(games_json, encoding="utf-8") as f:
                data = json.load(f)
            if validate_cache_data(data):
                return data
            else:
                console.print(
                    f"[yellow] Cache file corrupted, re-fetching...[/yellow]"
                )
        except Exception as e:
            console.print(f"[yellow] Cache read error: {e}, re-fetching...[/yellow]")

    sem = asyncio.Semaphore(CONCURRENCY)
    conn = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=SSL_CTX)

    async with aiohttp.ClientSession(connector=conn) as session:
        page_counts = await asyncio.gather(
            *(get_total_pages(session, sem, fid) for fid in forum_ids)
        )
        total = sum(page_counts)
        all_games = []
        done = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("[dim]{task.fields[rate]} p/s[/dim]"),
            console=console,
        ) as prog:
            loop = asyncio.get_running_loop()
            task = prog.add_task("Fetching catalog...", total=total, rate="-")
            t0 = loop.time()

            async def go(fid, idx):
                nonlocal done
                gs = await fetch_page(session, sem, fid, idx, refresh)
                all_games.extend(gs)
                done += 1
                elapsed = loop.time() - t0
                prog.update(
                    task,
                    advance=1,
                    rate=f"{done/elapsed:.1f}" if elapsed > 0.1 else "-",
                )

            await asyncio.gather(
                *[
                    go(fid, idx)
                    for fid, pages in zip(forum_ids, page_counts)
                    for idx in range(pages)
                ]
            )

        # deduplicate + sort
        seen = set()
        unique = []
        for g in all_games:
            if g["link"] not in seen:
                seen.add(g["link"])
                unique.append(g)
        unique.sort(key=lambda g: g["name"].lower())

        with open(games_json, "w", encoding="utf-8") as f:
            json.dump(unique, f, ensure_ascii=False, indent=2)
        return unique


def load_catalog(forum_ids, refresh=False):
    """Synchronous wrapper for load_catalog_async. Loads or fetches the full game catalog."""
    return asyncio.run(load_catalog_async(forum_ids, refresh))


# ── Display ──────────────────────────────────────────────────────────────────
def size_to_mb(raw: str) -> float:
    """Convert a size string to megabytes. Returns 0 if unparseable."""
    if not raw or raw == "-":
        return 0.0
    cleaned = raw.replace("\xa0", " ").replace(",", ".").strip()
    m = re.match(r"(\d+\.?\d*)\s*(MB|GB|TB)", cleaned, re.IGNORECASE)
    if not m:
        return 0.0
    value = float(m.group(1))
    unit = m.group(2).upper()
    return value * {"MB": 1, "GB": 1024, "TB": 1024 * 1024}[unit]


def format_size(raw: str) -> str:
    """Format a size string from RuTracker into a clean, semantic representation.

    RuTracker returns sizes like "0454.6 MB", "1111.5 GB", "7.97 GB".
    This function:
    - Strips leading zeros from the numeric part
    - Converts to the most appropriate unit (< 1 GB -> MB, >= 1024 GB -> TB)
    - Produces output like "454.6 MB", "1.08 TB", "13.17 GB"

    Args:
        raw: Size string from RuTracker, e.g. "0454.6 MB" or "7.97 GB"

    Returns:
        Cleanly formatted size string, or the original string if parsing fails.
    """
    mb_value = size_to_mb(raw)
    if mb_value == 0.0 and (not raw or raw == "-"):
        return "-"
    if mb_value >= 1024 * 1024:
        return f"{mb_value / (1024 * 1024):.2f} TB"
    elif mb_value >= 1000:
        return f"{mb_value / 1024:.2f} GB"
    else:
        return f"{mb_value:.1f} MB"


def seeds_style(seeds_str: str) -> Text:
    """Return a styled Text object for the seeds count.

    Color coding:
    - Green:  > 10 seeders (healthy torrent)
    - Yellow: 1-10 seeders (few seeders)
    - Red:    0 seeders (dead torrent)
    - Dim:    unknown ("-")

    High-seed games (>50) also get a bright marker.
    """
    if seeds_str == "-" or not seeds_str:
        return Text(seeds_str, style="dim")
    try:
        count = int(seeds_str)
    except ValueError:
        return Text(seeds_str, style="dim")
    if count == 0:
        return Text("0", style="bold red")
    elif count <= 10:
        return Text(seeds_str, style="yellow")
    else:
        marker = " *" if count > 50 else ""
        return Text(seeds_str + marker, style="bold green")


def hl(text: str, query: str) -> Text:
    """Return a Text object with query highlighted."""
    t = Text(text, no_wrap=True, overflow="ellipsis")
    if query:
        t.highlight_words([query], style="bold cyan on navy_blue", case_sensitive=False)
    return t


def get_forum_name(fid):
    """Get forum name from forum ID."""
    return FORUM_SUBFORUMS.get(fid, f"Forum-{fid}")


def get_platform_name(fid):
    """Get platform (Linux/Windows/Mac) from forum ID."""
    if fid in LINUX_FORUMS:
        return "Linux"
    elif fid in WINDOWS_FORUMS:
        return "Windows"
    elif fid in MAC_FORUMS:
        return "Mac"
    return "Unknown"


def build_table(games, query):
    """Build a Rich Table displaying a page of game results.

    Columns: # (reference number for !info/!open), Nome, Seeds (color-coded),
    Tamanho (semantic size formatting), Data, Plataforma.
    """
    table = Table(
        show_header=True,
        header_style="bold magenta",
        box=box.MINIMAL_DOUBLE_HEAD,
        title_justify="left",
    )
    table.add_column("#", style="bold yellow", width=4, justify="right")
    table.add_column("Nome", style="cyan", min_width=35)
    table.add_column("Seeds", justify="right", width=7)
    table.add_column("Tamanho", style="blue", justify="right", width=11)
    table.add_column("Data", style="dim", justify="right", width=10)
    table.add_column("Plataforma", style="dim", justify="left", width=8)

    for i, game in enumerate(games):
        table.add_row(
            str(i + 1),
            hl(game["name"], query),
            seeds_style(game["seeds"]),
            format_size(game["size"]),
            game["date"],
            get_platform_name(game["forum"]),
        )
    return table


def show_results(results, query="", limit=200):
    """Display search results as a paginated table.

    Args:
        results: List of game dicts to display.
        query: Search query for highlighting matches.
        limit: Maximum number of results to show.
    """
    if not results:
        query_text = Text(query)
        console.print(
            f"[yellow]Nenhum resultado encontrado para[/yellow] [bold]{query_text}[/bold]"
        )
        return

    console.print(build_table(results[:limit], query))
    if len(results) > limit:
        console.print(f"[dim]Mostrando os primeiros {limit} resultados...[/dim]")
    console.print(f"[dim]Total: {len(results)} jogos[/dim]\n")


# ── Search ───────────────────────────────────────────────────────────────────
def search_with_strategies(catalog, query):
    """
    Search games with multiple strategies in a single pass.
    Returns: (results, strategy_name)
    """
    query_lower = query.lower().strip()
    query_words = query_lower.split()

    exact, all_words, any_word = [], [], []

    for g in catalog:
        name_lower = g["name"].lower()
        if query_lower in name_lower:
            exact.append(g)
        elif len(query_words) > 1 and all(w in name_lower for w in query_words):
            all_words.append(g)
        elif len(query_words) > 1 and any(w in name_lower for w in query_words):
            any_word.append(g)

    if exact:
        return exact, "Exact"
    if all_words:
        return all_words, "Fuzzy (all words)"
    if any_word:
        return any_word, "Fuzzy (any word)"
    return [], "None"


# ── Pagination ───────────────────────────────────────────────────────────────
def paginate(results, page_number, page_size):
    """Return a slice of results for the given page number and page size."""
    start_index = page_number * page_size
    end_index = start_index + page_size
    return results[start_index:end_index], len(results)


# ── Commands ─────────────────────────────────────────────────────────────────
def cmd_quit(state, catalog):
    """Exit the application."""
    sys.exit(0)


def cmd_clear(state, catalog):
    """Clear search and show all games."""
    state["results"] = catalog[:]
    state["page"] = 0
    state["current_query"] = ""
    console.print(f"[dim]Busca limpa. Mostrando todos os {len(catalog)} jogos[/dim]")


def cmd_refresh(state, catalog):
    """Re-fetch the catalog from RuTracker and update the session state."""
    console.print("[dim]Atualizando catálogo...[/dim]")
    forum_ids = state.get("forum_ids", [])
    if not forum_ids:
        console.print("[red]Erro: Nenhum fórum configurado[/red]")
        return
    new_catalog = load_catalog(forum_ids, refresh=True)
    catalog[:] = new_catalog  # Update the original catalog list
    state["results"] = catalog[:]
    state["page"] = 0
    state["current_query"] = ""
    console.print(f"[green]✓[/green] [dim]{len(catalog)} jogos carregados[/dim]\n")


def cmd_next_page(state, catalog):
    """Advance to the next page of results."""
    total_pages = (len(state["results"]) + PAGE_SIZE - 1) // PAGE_SIZE or 1
    if state["page"] < total_pages - 1:
        state["page"] += 1
    else:
        console.print("[yellow]Já está na última página.[/yellow]")


def cmd_prev_page(state, catalog):
    """Go back to the previous page of results."""
    if state["page"] > 0:
        state["page"] -= 1
    else:
        console.print("[yellow]Já está na primeira página.[/yellow]")


def cmd_help(state, catalog):
    help_text = """
[bold]Comandos disponíveis:[/bold]
 [bold]q[/bold] = sair
 [bold]!refresh[/bold] = atualizar catálogo
 [bold]c[/bold] / [bold]clear[/bold] = limpar busca (mostrar todos)
 [bold]n[/bold] = próxima página
 [bold]p[/bold] = página anterior
 [bold]s <chave>[/bold] = ordenar por 'name', 'seeds', 'size', 'date'
 [bold]f <fórum>[/bold] = filtrar por 'linux', 'windows', 'mac', 'all'
 [bold]!info <número>[/bold] = mostrar detalhes (ex: !info 1)
 [bold]!open <número>[/bold] = abrir jogo no navegador
 [bold]h[/bold] = mostrar esta ajuda

[bold]Pesquisa:[/bold]
 Digite um nome para buscar. Todos os termos devem estar no nome.

[bold]Links:[/bold]
 Para abrir: use !open <número> ou clique no link com Ctrl
"""
    console.print(Panel(help_text, title="Ajuda", border_style="green"))


def cmd_sort(state, catalog, sort_key):
    """Sort results by name, seeds, size, or date."""
    valid_sort_keys = ["name", "seeds", "size", "date"]
    if sort_key in valid_sort_keys:
        if sort_key == "seeds":
            state["results"].sort(
                key=lambda g: int(g["seeds"]) if g["seeds"].isdigit() else -1,
                reverse=True,
            )
        elif sort_key == "size":
            state["results"].sort(key=lambda g: size_to_mb(g["size"]), reverse=True)
        else:
            state["results"].sort(
                key=lambda g: (
                    g[sort_key].lower() if isinstance(g[sort_key], str) else g[sort_key]
                )
            )
        state["sort_key"] = sort_key
        state["page"] = 0
        console.print(f"[dim]Ordenado por {sort_key}[/dim]")
    else:
        console.print(f"[red]Chave de ordenação inválida: {sort_key}[/red]")


def cmd_filter_forum(state, catalog, forum_name):
    """Filter results by platform."""
    platform_forums = {
        "linux": LINUX_FORUMS,
        "windows": WINDOWS_FORUMS,
        "mac": MAC_FORUMS,
        "all": None,
    }
    if forum_name in platform_forums:
        forums = platform_forums[forum_name]
        if forums is None:
            # Show all
            state["results"] = catalog[:]
        else:
            state["results"] = [g for g in catalog if g["forum"] in forums]
        state["filter_forum"] = forum_name
        state["page"] = 0
        console.print(
            f"[dim]Filtrado por {forum_name} ({len(state['results'])} jogos)[/dim]"
        )
    else:
        console.print(f"[red]Fórum inválido: {forum_name}[/red]")


def cmd_show_info(state, catalog, game_number):
    """Show detailed information about a game."""
    from urllib.parse import urlparse
    try:
        game_idx = int(game_number) - 1  # Convert to 0-based index
        if 0 <= game_idx < len(state["results"]):
            game = state["results"][game_idx]
            # Create a panel with game details using Text to escape markup
            details = Text()
            details.append("Nome: ", style="bold")
            details.append(Text(game["name"]))  # Escapes automatically
            details.append("\nLink: ", style="bold")
            details.append(Text(game["link"]))
            details.append("\nSeeds: ", style="bold")
            details.append(Text(game["seeds"]))
            details.append("\nTamanho: ", style="bold")
            details.append(Text(format_size(game["size"])))
            details.append("\nData: ", style="bold")
            details.append(Text(game["date"]))
            details.append("\nPlataforma: ", style="bold")
            details.append(Text(get_platform_name(game["forum"])))
            details.append("\nFórum: ", style="bold")
            details.append(Text(get_forum_name(game["forum"])))
            console.print(Panel(details, title="Detalhes do Jogo", border_style="cyan"))
        else:
            console.print("[red]Número inválido — use o # da tabela (1-{len(state['results'])})[/red]")
    except ValueError:
        console.print("[red]Comando inválido — use: !info <número> (ex: !info 1)[/red]")


def cmd_open_game(state, catalog, game_number):
    """Open game link in browser."""
    from urllib.parse import urlparse
    try:
        game_idx = int(game_number) - 1
        if 0 <= game_idx < len(state["results"]):
            game = state["results"][game_idx]
            link = game["link"]
            # Validate URL to prevent SSRF
            parsed = urlparse(link)
            if parsed.scheme not in ("http", "https"):
                console.print("[red]Esquema de URL invalida[/red]")
                return
            if parsed.hostname and parsed.hostname not in ALLOWED_DOMAINS:
                console.print(f"[red]Dominio na o permitido: {parsed.hostname}[/red]")
                return
            console.print(f"[dim]Abrindo: {link}[/dim]")
            webbrowser.open(link)
        else:
            console.print("[red]Número inválido — use o # da tabela (1-{len(state['results'])})[/red]")
    except ValueError:
        console.print("[red]Comando inválido — use: !open <número> (ex: !open 1)[/red]")


COMMANDS = {
    "q": cmd_quit,
    "!refresh": cmd_refresh,
    "c": cmd_clear,
    "clear": cmd_clear,
    "n": cmd_next_page,
    "p": cmd_prev_page,
    "h": cmd_help,
}


# ── Interactive ──────────────────────────────────────────────────────────────
PREFIX_COMMANDS = {
    "s ": lambda state, catalog, arg: cmd_sort(state, catalog, arg),
    "f ": lambda state, catalog, arg: cmd_filter_forum(state, catalog, arg),
    "!info ": lambda state, catalog, arg: cmd_show_info(state, catalog, arg),
    "!open ": lambda state, catalog, arg: cmd_open_game(state, catalog, arg),
}


def interactive(catalog, forum_ids):
    """Run the interactive TUI loop with search, pagination, and commands.

    forum_ids: list of forum IDs to use for refresh
    """
    console.print(
        Panel(
            "[bold cyan]RuTracker Games Browser[/bold cyan]\n\n"
            " Type a name to search · Enter = list all\n"
            " [bold]q[/bold] = quit [bold]!refresh[/bold] = re-fetch catalog\n"
            " [bold]n/p[/bold] = next/prev page [bold]h[/bold] = help\n"
            " [bold]s <key>[/bold] = sort (name/seeds/size/date) [bold]f <plat>[/bold] = filter\n"
            " [bold]!info <n>[/bold] = show details [bold]!open <n>[/bold] = open in browser",
            box=box.DOUBLE_EDGE,
            expand=False,
        )
    )
    console.print(f" [dim]{len(catalog)} games loaded[/dim]\n")

    # Initialize state
    state = {
        "page": 0,
        "results": catalog[:],
        "sort_key": "name",
        "filter_forum": "all",
        "current_query": "",
        "forum_ids": forum_ids,
    }

    while True:
        try:
            query = Prompt.ask("[bold cyan]Search[/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold red]Bye![/bold red]")
            break

        # Check for commands
        if query.lower() in COMMANDS:
            try:
                COMMANDS[query.lower()](state, catalog)
                continue
            except SystemExit:
                break
        elif any(query.startswith(prefix) for prefix in PREFIX_COMMANDS):
            prefix = next(p for p in PREFIX_COMMANDS if query.startswith(p))
            arg = query[len(prefix):].strip()
            try:
                PREFIX_COMMANDS[prefix](state, catalog, arg)
                continue
            except SystemExit:
                break
        elif query == "!refresh":
            cmd_refresh(state, catalog)
            continue

        # Handle search or list all
        if query:
            # Search with strategies - ALWAYS on full catalog
            results, strategy = search_with_strategies(catalog, query)
            state["results"] = results
            state["page"] = 0
            state["current_query"] = query
            if not results:
                console.print(
                    f"[yellow]Nenhum resultado encontrado para '[bold]{query}[/bold]'[/yellow]\n"
                )
                continue
            else:
                console.print(f"[dim]Estratégia: {strategy} | {len(results)} resultados[/dim]")
        else:
            # List all
            state["results"] = catalog[:]
            state["page"] = 0
            state["current_query"] = ""

        # Show paginated results
        page_results, total_items = paginate(state["results"], state["page"], PAGE_SIZE)
        total_pages = (len(state["results"]) + PAGE_SIZE - 1) // PAGE_SIZE or 1

        if page_results:
            console.print(build_table(page_results, state["current_query"]))
            console.print(
                f"[dim]Página {state['page'] + 1}/{total_pages} — Use 'n' próxima, 'p' anterior, 'h' ajuda[/dim]\n"
            )
        else:
            console.print("[bold red]Nenhum jogo encontrado[/bold red]\n")

        # Show status bar
        console.print(
            f"[dim]{len(state['results'])} jogos | Forum: {state['filter_forum']} | Sort: {state['sort_key']} | Pag {state['page']+1}/{total_pages}[/dim]"
        )


# ── CLI ──────────────────────────────────────────────────────────────────────
def main():
    """CLI entry point. Parses arguments, loads catalog, and runs search/list/TUI."""
    ap = argparse.ArgumentParser(
        prog="rtlinux",
        description="RuTracker Games Browser — async TUI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
--forum choices:
  all      linux + windows + mac (default)
  linux    Native Linux Games only
  windows  PC / Windows Games only
  mac      Mac Games only

Examples:
  ./rtlinux.py                    interactive, all games
  ./rtlinux.py -g "NieR"          direct search
  ./rtlinux.py -g "NieR" -a       show all results (no cap)
  ./rtlinux.py --forum linux      only Linux-native games
  ./rtlinux.py -c                 full catalog
  ./rtlinux.py -r                 force re-fetch from site
""",
    )
    ap.add_argument("-g", "--game", metavar="QUERY", help="Search query")
    ap.add_argument(
        "-a", "--all", action="store_true", help="Show all results (no 200 cap)"
    )
    ap.add_argument("-c", "--catalog", action="store_true", help="List full catalog")
    ap.add_argument(
        "-r", "--refresh", action="store_true", help="Force re-fetch from RuTracker"
    )
    ap.add_argument("--forum", default="all", choices=list(KNOWN_FORUMS))
    args = ap.parse_args()

    forums, label = KNOWN_FORUMS[args.forum]

    console.rule(f"[bold cyan]rtlinux[/bold cyan] [dim]{label}[/dim]")
    catalog = load_catalog(forums, refresh=args.refresh)

    if not catalog:
        console.print(
            "[yellow]Nenhum jogo carregado. Possiveis causas:[/yellow]\n"
            "  [dim]- Sem conexao com RuTracker.org[/dim]\n"
            "  [dim]- Cache vazio ou corrompido (tente -r para re-buscar)[/dim]\n"
            "  [dim]- Forum sem jogos (tente --forum linux para um forum menor)[/dim]"
        )
        # Don't exit, continue with empty catalog
        catalog = []

    console.print(f"[green]✓[/green] [dim]{len(catalog)} games in catalog[/dim]\n")
    limit = 999_999 if args.all else 200

    if args.game:
        results, strategy = search_with_strategies(catalog, args.game)
        show_results(results, args.game, limit)
    elif args.catalog:
        show_results(catalog, limit=limit)
    else:
        interactive(catalog, forums)


if __name__ == "__main__":
    main()
