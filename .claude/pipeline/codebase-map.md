# Mapeamento da Codebase: rtlinux.py

**Data**: 2026-04-22  
**Fonte**: `/home/troli/Projects/rtlinux/rtlinux.py`, `/home/troli/Projects/rtlinux/requirements.txt`, `/home/troli/Projects/rtlinux/CLAUDE.md`

---

## 🎯 Resumo

rtlinux.py é um CLI/TUI Python de arquivo unico (437 linhas) para navegar jogos em torrents do forum RuTracker.org. O script faz scraping assincrono de paginas, cacheia HTML e JSON localmente, e oferece interface interativa com tabelas Rich para preview de jogos Linux, Windows e Mac.

---

## 📐 Nível Conceitual

### Domínio
- **Dominio**: Catalogo de jogos torrent de forums RuTracker (Linux, Windows, Mac)
- **Entidades principais**: Game (dict com name, link, tid, seeds, size, date, forum)
- **Fonte de dados**: RuTracker.org (HTML scraping)

### Regras de negócio
1. **Multi-forum**: Suporta 3 forums (linux=1992, windows=50, mac=51) ou "all"
2. **Paginação RuTracker**: Cada pagina tem 50 topicos
3. **Cache strategy**: HTML salvo indefinidamente em `cache/fid_page.html`, JSON deduplicado em `cache/games_fid.json`
4. **Deduplicação**: por `link` (URL canonica do topico)
5. **Ordenação default**: alfabetica por `name.lower()`
6. **Search strategy**: substring -> all-words-AND (fallback)
7. **Concorrencia**: 24 requisições simultaneas via `asyncio.Semaphore`

---

## 🧩 Nível Lógico

### Mapa de módulos (secoes logicas no arquivo unico)

```
rtlinux.py
├── Imports & Config               # Linhas 1-50
│   ├── KNOWN_FORUMS: mapeia CLI -> forum IDs
│   ├── CACHE_DIR: resolve path relativo ao script
│   └── CONCURRENCY = 24
├── HTTP/Fetch Layer               # Linhas 53-91
│   ├── fetch_url(): GET com timeout, ssl=False
│   └── get_total_pages(): detecta total de paginas via div.pg
├── Parse Layer                    # Linhas 94-183
│   ├── _extract_tid(): regex extrai topic ID
│   └── parse_html(): BeautifulSoup extrai tabela vf-tor
│       ├── Extrai: name, tid, link, seeds, size, date
│       └── Seeds: fallback chain de classes CSS
├── Cache Layer                    # Linhas 186-200
│   └── fetch_page(): le/salva HTML em disco via aiofiles
├── Catalog Service                # Linhas 203-273
│   ├── load_catalog_async(): orquestra fetch+parse
│   ├── Progress bar Rich com rate p/s
│   ├── Deduplicacao e sort alfabetico
│   └── Salva JSON cache
├── Display Layer                # Linhas 275-337
│   ├── hl(): highlight de query com Text.highlight_words
│   ├── build_table(): Rich.Table com colunas fixas
│   └── show_results(): renderiza tabela + mensagem "No games found"
├── Search Layer                 # Linhas 340-347
│   └── search(): substring OR all-words-AND fallback
├── Interactive Layer            # Linhas 350-377
│   └── interactive(): loop com Prompt.ask
│       ├── Comandos: q, !refresh, <search>
│       └── State global CURRENT_FORUMS para refresh
└── CLI Entry Point              # Linhas 380-437
    └── main(): argparse, dispatch para modos (search/catalog/interactive)
```

### Fluxo de dados

```
CLI args -> forum_ids -> load_catalog() -> [cache?] -> return lista
    |
    v
[Cache miss] -> get_total_pages() -> fetch_page(N...) -> parse_html()
    |
    v
deduplicate by link -> sort by name -> save JSON -> return
    |
    v
search() -> show_results() -> build_table() -> Rich console
```

### Patterns identificados
- **No estado compartilhado** (exceto CURRENT_FORUMS global mutavel para refresh)
- **Pipeline de dados**: fetch -> parse -> dedup -> sort -> display
- **Strategy parcial**: search() tem 2 estratégias inline (substring, AND)
- **Cache em camadas**: HTML bruto + JSON processado

---

## ⚙️ Nível Técnico

### Stack
- **Python**: 3.x (asyncio, type hints implícitos via dict)
- **HTTP**: aiohttp (async) + urllib3 (apenas para disable warnings)
- **Parsing**: beautifulsoup4 + lxml implícito
- **UI**: rich (console, table, panel, progress, prompt, text)
- **I/O async**: aiofiles

### Dependências (requirements.txt)
```
aiohttp>=3.9.0
aiofiles>=23.2.0
beautifulsoup4>=4.12.0
rich>=13.7.0
urllib3>=2.0.0
```

### Build/Test/Config
- **Build**: Nenhum - single-file executável
- **Testes**: Nenhum presente
- **Config**: Nenhum arquivo externo - tudo hardcoded em CONSTANTES no topo do arquivo
- **CI/CD**: Nenhum
- **Lint/Type Check**: Nenhum configurado

### Estrutura de arquivos
```
/home/troli/Projects/rtlinux/
├── rtlinux.py       # Arquivo unico com toda a logica (437 linhas)
├── requirements.txt # 6 dependencias
├── cache/           # Diretorio criado em runtime (nao versionado)
│   ├── {fid}_{page}.html
│   ├── max_page_{fid}.txt
│   └── games_{fid_list}.json
└── CLAUDE.md        # Guia de uso para Claude Code
```

---

## 📍 Onde Implementar

Com base no plano de arquitetura, localizacoes especificas para cada melhoria:

### P1: Reorganizar secoes + Coluna Forum
- **Onde**: `build_table()` (linhas 284-321) e `parse_html()` (linhas 101-183)
- **Racional**: 
  - `parse_html()` ja captura `fid` e salva em `game["forum"]`
  - Criar mapeamento fid->label (reverse de KNOWN_FORUMS)
  - Substituir coluna "Link" por "Forum" em `tbl.add_column()`

### P2: Search Strategy Chain + Fuzzy
- **Onde**: Nova seção apos linha 347 (depois do search atual)
- **Racional**:
  - Extrair `search()` em funcoes separadas: `search_substring()`, `search_all_words()`, `search_fuzzy()`
  - `search()` novo retorna `(results, strategy_name)`
  - `fuzzy` implementado como razão de caracteres: `len(set(q) & set(name)) / len(set(q))`

### P3: Paginação no modo interativo
- **Onde**: `interactive()` (linhas 351-377) e `show_results()` (linhas 324-337)
- **Racional**:
  - Adicionar `state = {"page": 0, "page_size": 50}` no loop
  - Modificar `show_results()` para receber `page` e calcular slice `[start:end]`
  - Adicionar `paginate()` helper function

### P4: Command Dispatcher
- **Onde**: Nova seção apos `interactive()` ou substituindo o loop interno
- **Racional**:
  - Dict `COMMANDS = {"n": cmd_next, "p": cmd_prev, "h": cmd_help, ...}`
  - Cada handler recebe `state, catalog`
  - Modificar loop para `cmd = COMMANDS.get(query.lower())`

### P5: Sort e Filter
- **Onde**: handlers no dispatcher + UI em `build_table()`
- **Racional**:
  - `cmd_sort(state, catalog, key)`: ordena `catalog[:]` in-place
  - `cmd_filter_forum(state, catalog, forum)`: filtra por fid
  - `build_table()`: destacar header da coluna ativa

### P6: Game Info (!info N)
- **Onde**: novo handler `cmd_info()`
- **Racional**:
  - Receber numero N da tabela atual
  - Buscar game na pagina/resultado atual
  - Mostrar `Panel` com detalhes completos (link clicavel, seeds coloridos)

### P7: Robustez de cache
- **Onde**: `load_catalog_async()` (linhas 204-268) e `main()` (linhas 380-437)
- **Racional**:
  - Validar JSON carregado: é lista? contém dicts? tem chaves obrigatórias?
  - Se invalido: warn e re-fetch automaticamente (nao exit)
  - Se fetch parcial: continuar com o que conseguiu
  - `main()`: nunca `sys.exit(1)` sem mensagem orientadora

### P8: UI Polish
- **Onde**: `build_table()` para cores de seeds
- **Racional**:
  - Mapear seeds para cores: >10 verde, 1-10 amarelo, 0 vermelho, "-" dim

---

## 🔧 Como Implementar (Conventions)

### Estilo de código existente
- **Docstrings**: minimalistas ou ausentes
- **Comentarios de seção**: `# ── Nome ──` (em dash unicode)
- **Nomes**: snake_case para funcoes/variaveis, CONSTANTES em maiusculas
- **Tipos**: nao usa type hints (exceto em `_extract_tid(href: str)`)
- **Rich styling**: `[bold cyan]`, `[dim]`, `[yellow]`, `[green]`, `[red]`

### Exemplo de pattern para novas funcoes
```python
# ── Search Strategies ─────────────────────────────────────────────

def search_substring(catalog: list, query: str) -> list:
    q = query.lower()
    return [g for g in catalog if q in g["name"].lower()]

def search_all_words(catalog: list, query: str) -> list:
    words = query.lower().split()
    return [g for g in catalog if all(w in g["name"].lower() for w in words)]

def search_fuzzy(catalog: list, query: str, threshold: float = 0.7) -> list:
    qset = set(query.lower())
    matches = []
    for g in catalog:
        ratio = len(qset & set(g["name"].lower())) / len(qset)
        if ratio >= threshold:
            matches.append((ratio, g))
    return [g for _, g in sorted(matches, reverse=True)]

STRATEGIES = [search_substring, search_all_words, search_fuzzy]

def search(catalog, query):
    for strategy in STRATEGIES:
        results = strategy(catalog, query)
        if results:
            return results, strategy.__name__
    return [], None
```

### Pattern para comando dispatcher
```python
# ── Interactive Commands ──────────────────────────────────────────

def cmd_quit(state, catalog):
    raise SystemExit

def cmd_next_page(state, catalog):
    state["page"] = min(state["page"] + 1, state["total_pages"] - 1)

def cmd_prev_page(state, catalog):
    state["page"] = max(state["page"] - 1, 0)

def cmd_help(state, catalog):
    console.print(Panel("n=next, p=prev, s=name/seeds/size/date, f=forum..."))

COMMANDS = {
    "q": cmd_quit,
    "n": cmd_next_page,
    "p": cmd_prev_page,
    "h": cmd_help,
}

# No loop interativo:
query = Prompt.ask("...").strip()
cmd = COMMANDS.get(query.lower())
if cmd:
    cmd(state, catalog)
else:
    # é busca
    pass
```

### Status bar pattern
```python
# Footer da tabela ou panel separado
console.print(
    f"[dim]{len(catalog)} jogos | "
    f"Forum: {state['forum']} | "
    f"Sort: {state['sort_key']} | "
    f"Pag {state['page']+1}/{state['total_pages']}[/dim]"
)
```

---

## ✅ Prontidão

| Item | Status | Nota |
|------|--------|------|
| Entendimento do domínio | [x] | RuTracker scraping, Multi-forum |
| Entendimento do fluxo de dados | [x] | Fetch -> Parse -> Cache -> Display |
| Stack identificada | [x] | aiohttp, bs4, rich, aiofiles |
| Dependencias mapeadas | [x] | 6 pacotes, todas compatíveis |
| Pontos de inserção identificados | [x] | Linhas específicas para cada feature |
| Patterns existentes documentados | [x] | Secoes únicodes, snake_case |
| Criterios de aceitação claros | [x] | No plano de arquitetura |
| Testes existentes | [ ] | Não há - considerar testes manuais |
| CI/CD configurado | [ ] | Não aplicável para script single-file |

### Blockers
- **Nenhum blocker técnico identificado**
- Risco baixo: todas as dependencias já estão presentes e funcionando
- Risco médio: parsing de HTML pode quebrar se RuTracker mudar estrutura (não é bloqueio para refactor)

---

## 🚧 Lacunas e Próximos Passos Priorizados

### Prioridade Alta (Passos 1, 2, 5 - Independentes)
1. **Reorganizar secoes do arquivo** (esforço P)
   - Adicionar comentários de seção claros seguindo padrão existente
   - Trocar coluna "Link" por "Forum" em `build_table()`

2. **Implementar Search Strategy Chain** (esforço M)
   - Extrair `search_substring()`, `search_all_words()`, `search_fuzzy()`
   - Modificar `search()` para retornar `(results, strategy_name)`
   - Atualizar `show_results()` para informar qual estratégia foi usada

3. **Robustez de cache** (esforço P)
   - Validar JSON antes de usar
   - Re-fetch automático em vez de `sys.exit(1)`

### Prioridade Média (Passos 3, 4 - Dependem de estrutura)
4. **Paginação interativa** (esforço M)
   - Implementar `paginate()` helper
   - Adicionar estado `page` ao loop interativo
   - Comandos `n`/`p`

5. **Command Dispatcher + features** (esforço G)
   - Dict `COMMANDS` com handlers
   - `h` help, `s` sort, `f` filter, `!info N` detalhes

### Prioridade Baixa (Passo 6 - Polimento)
6. **UI Final Polish** (esforço P)
   - Status bar com contagem/fórum/sort/pagina
   - Cores semanticas para seeds
   - Remover limite de 200 no modo interativo

### Decisões arquiteturais pendentes
- **None** - todas as decisões já foram tomadas no plano.md
- A manutenção como single-file foi explicitamente decidida
- Strategy pattern escolhido para busca
- Fuzzy search será implementação própria (ratio de caracteres)
- Paginação será via comandos, não scroll infinito
