# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`rtlinux.py` (v5) is a single-file Python CLI/TUI for browsing RuTracker.org game torrents. It asynchronously scrapes forum pages, caches HTML and JSON locally, and provides an interactive interface with Rich tables to preview games across Linux, Windows, and Mac platforms.

## Commands

### Run the application

```bash
./rtlinux.py                    # Interactive mode, all games
./rtlinux.py --forum linux      # Interactive mode, Linux games only
./rtlinux.py --forum windows    # Interactive mode, Windows games only
./rtlinux.py --forum mac        # Interactive mode, Mac games only
```

### Direct search

```bash
./rtlinux.py -g "NieR"          # Search for "NieR"
./rtlinux.py -g "NieR" -a       # Show all results (no 200 cap)
```

### Catalog mode

```bash
./rtlinux.py -c                 # List full catalog
./rtlinux.py -c --forum linux   # List Linux catalog only
```

### Refresh cache

```bash
./rtlinux.py -r                 # Force re-fetch from RuTracker
```

### Dependencies

```bash
pip install -r requirements.txt
```

### Install as CLI (optional)

```bash
pip install -e .                # If setup.py exists
# or
cp rtlinux.py /usr/local/bin/rtlinux
```

## Code Architecture

### Single-file structure

The entire application is in `rtlinux.py` (~900 lines), organized into logical sections:

```
rtlinux.py
├── Imports ────────────────────────────────────────────────────
├── Config & Constants ─────────────────────────────────────────
│   ├── FORUM_SUBFORUMS: Forum ID → platform label mapping
│   ├── LINUX/WINDOWS/MAC_FORUMS: Forum ID lists by platform
│   ├── KNOWN_FORUMS: CLI flags → (forum_ids, label)
│   ├── FORUM_BASE, TOPIC_BASE: URL templates
│   ├── CACHE_DIR: Local cache path
│   ├── UA: User-Agent string
│   ├── CONCURRENCY: 24 (async semaphore limit)
│   └── PAGE_SIZE: 50 (RuTracker pagination)
├── Cache Layer ────────────────────────────────────────────────
│   └── validate_cache_data(): JSON integrity check
├── HTTP Layer ─────────────────────────────────────────────────
│   └── fetch_url(): async GET with semaphore, timeout, ssl=False
├── Page Count Detection ───────────────────────────────────────
│   └── get_total_pages(): Detect RuTracker pages via div.pg
├── HTML Parsing ───────────────────────────────────────────────
│   ├── _extract_tid(): Regex extract topic ID from href
│   └── parse_html(): BeautifulSoup extract game dicts
│       ├── name, link, tid from title cells
│       ├── seeds from span.seedmed > b
│       ├── size from a.f-dl
│       └── date from vf-col-last-post
├── Page Fetch & Cache ─────────────────────────────────────────
│   └── fetch_page(): Load HTML from disk or fetch+cache
├── Catalog Service ────────────────────────────────────────────
│   ├── load_catalog_async(): Orchestrate fetch+parse+dedup
│   ├── Progress bar via Rich
│   ├── Deduplicate by link, sort alphabetically
│   └── Save JSON cache
│   └── load_catalog(): Sync wrapper (asyncio.run)
├── Display Helpers ────────────────────────────────────────────
│   ├── format_size(): Normalize size strings (MB/GB/TB)
│   ├── seeds_style(): Color-coded seed count (green/yellow/red)
│   ├── hl(): Highlight query matches in table cells
│   ├── get_forum_name(), get_platform_name(): ID → label
│   ├── build_table(): Rich.Table constructer
│   └── show_results(): Paginated table display
├── Search ─────────────────────────────────────────────────────
│   └── search_with_strategies(): substring → AND words → any word
├── Pagination ─────────────────────────────────────────────────
│   └── paginate(): Slice results by page_number, page_size
├── Commands ───────────────────────────────────────────────────
│   ├── cmd_quit(), cmd_clear()
│   ├── cmd_refresh(), cmd_next_page(), cmd_prev_page()
│   ├── cmd_help(), cmd_sort(), cmd_filter_forum()
│   ├── cmd_show_info(), cmd_open_game()
│   └── COMMANDS dict for dispatcher
├── Interactive Mode ───────────────────────────────────────────
│   └── interactive(): Async TUI loop with Prompt.ask
└── CLI Entry Point ────────────────────────────────────────────
    └── main(): argparse, route to modes (search/catalog/interactive)
```

### Data flow

```
CLI args → forum_ids → load_catalog() → [check JSON cache?]
    ↓ (cache miss)
get_total_pages() → fetch_page(N...) → parse_html()
    ↓
deduplicate by link → sort by name → save JSON → return list
    ↓
search_with_strategies() → show_results() → build_table() → Rich console
```

### Forum structure

**Linux forums:**
- 1992: Linux Native
- 2059: Linux Wine/DOSBox

**Windows forums (24 categories):**
- Arcade, Fighting, FPS, TPS, Horror, Adventure, Hidden Object, Visual Novel
- Kids, Multimedia, Logic/Puzzle, Chess, RPG, Simulation, RTS, TBS
- Collections, Old Games (six subcategories), Old PC

**Mac forums:**
- 537: Mac Native
- 637: Mac Wine/DOSBox

### Cache behavior

- HTML pages cached as `{fid}_{page}.html` (Windows-1251 encoding)
- Page count cached as `max_page_{fid}.txt`
- Deduplicated catalog cached as `games_{fid_list}.json`
- Cache is validated on load; corrupt JSON triggers re-fetch
- HTML cache reused unless `--refresh` flag is set

## Interactive Mode Commands

When running `./rtlinux.py` (no flags):

| Command | Description |
|---------|-------------|
| `<query>` | Search games (substring → AND → any word fallback) |
| `Enter` | Show all games |
| `q` | Quit |
| `!refresh` | Re-fetch catalog from RuTracker |
| `c` or `clear` | Clear search, show all |
| `n` | Next page |
| `p` | Previous page |
| `s <key>` | Sort by `name`, `seeds`, `size`, or `date` |
| `f <platform>` | Filter by `linux`, `windows`, `mac`, or `all` |
| `!info <N>` | Show detailed info about game #N |
| `!open <N>` | Open game torrent link in browser |
| `h` | Show help |

## Search Strategies

The search function tries multiple strategies in order:

1. **Substring match** (exact case-insensitive containment)
2. **All-words AND** (all query words must appear, in any order)
3. **Any-word match** (at least one query word match)

Each search reports the strategy used and result count.

## Key Code Locations

| Feature | Location |
|---------|----------|
| Forum mappings | Lines 34-80 |
| Cache validation | Lines 98-110 |
| HTML parsing | Lines 170-277 |
| Catalog async fetch | Lines 305-381 |
| Size formatting | Lines 385-417 |
| Seed color coding | Lines 420-443 |
| Search strategies | Lines 522-558 |
| Interactive commands | Lines 570-725 |
| CLI entry point | Lines 840-903 |

## Development Notes

### File organization

Maintain the single-file structure. If the file exceeds ~800 lines significantly, consider moving to a package (`rtlinux/`) with separate modules for:
- `catalog.py` (fetch, cache, parse)
- `search.py` (strategies, ranking)
- `ui.py` (tables, commands, interactive loop)
- `cli.py` (argparse, entry point)

### Encoding

RuTracker returns HTML in Windows-1251 (cp1251). Always decode with:
```python
content.decode("cp1251", errors="ignore")
```

### Async patterns

- Semaphore limit = 24 concurrent requests
- Use `aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)`
- Catch all exceptions in `fetch_url()` and return `None`

### UI patterns

- Use Rich `Text` object for highlighting: `highlight_words([query], style="bold cyan on navy_blue")`
- Seeds coloring: `>10` green, `1-10` yellow, `0` red, `-` dim
- Size formatting converts to best unit (MB/GB/TB)

## Common Issues

### "Nenhum resultado encontrado"

Either no games match or cache is empty/corrupt. Try:
```bash
./rtlinux.py -r         # Force re-fetch
./rtlinux.py -g "partial" -a   # Show all with partial match
```

### Cache corrupt

Delete cache directory (`rm -rf cache/`) and re-run. Next fetch rebuilds cache.

### Forum-specific errors

Try a smaller forum:
```bash
./rtlinux.py --forum linux     # Only 2 sub-forums
```

## References

- Full architecture plan: `.claude/pipeline/plan.md`
- Codebase mapping: `.claude/pipeline/codebase-map.md`
