# Changelog

Todos as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e este projeto aderir ao [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<sub><a href="README.md">🇺🇸 English</a> | <a href="README_pt.md">🇧🇷 Português</a></sub>

---

## [5.0.0](https://github.com/DevTroli/RuTrackGames/compare/v4.0.0...v5.0.0) - 2026-04-23

### 📦 PyPI Distribution

- **Reestruturação para pacote Python**
  - Código movido para package `rl/` (`rl/__init__.py`, `rl/rtgames.py`)
  - Entry point para comando global: `rutracker-games`
  - `pyproject.toml` configurado para build com hatchling

- **Disponível via PyPI/TestPyPI**
  - `pip install rutracker-games`
  - Build: `uv build` → produz `.whl` e `.tar.gz`
  - Upload: `twine upload dist/*.whl`

### 📄 Documentação

- **README multilíngue**
  - `README.md` — inglês (padrão, compatível com PyPI/GitHub)
  - `README_pt.md` — português brasileiro
  - Links cruzados em ambos os arquivos

### 🔒 Segurança

- **Habilitar verificação SSL/TLS** em todas as conexões HTTP com certificado do `certifi`
  - Removeu `ssl=False` de todas as requisições
  - Removeu `urllib3.disable_warnings()`

- **Prevenir SSRF/Scheme injection** ao abrir links no navegador
  - Validar esquema da URL (apenas http/https)
  - Manter allowlist de domínios permitidos (`rutracker.org`, `rutracker.net`, `rutracker.nl`)

- **Prevenir Rich markup injection**
  - Usar `rich.text.Text` para escapar nomes de jogos e queries do usuário
  - Aplica-se a todas as saídas com texto dinâmico

### ✨ Melhorias

- **Reorganização de cache para XDG**
  - Move de `./cache/` para `~/.cache/rl/` (Linux/macOS) ou `%LOCALAPPDATA%/rtlinux/` (Windows)
  - Mais portável e não conflita com diretório do script

- **Otimizar busca** (single-pass vs triple-pass)
  - Antiga: 3 iterações sobre o catálogo (substring, all-words, any-word)
  - Nova: 1 itação única que classifica em 3 buckets
  - ~3x mais rápido para catálogos grandes

- **Unificar dispatcher de comandos**
  - Removida duplicação da lógica `!refresh`
  - Adicionado `PREFIX_COMMANDS` para comandos com argumentos (`s `, `f `, `!info `, `!open `)

- **Melhorar mensagens de erro**
  - `search_with_strategies()`: informa estratégia usada ("Exact", "Fuzzy (all words)", etc.)
  - `!open`: mensagens claras para URL inválida ou domínio não permitido
  - `!refresh`: mensagem se nenhum fórum configurado

- **Melhor help do modo interativo**
  - Painel inicial agora lista todos os comandos disponíveis
  - Mais informações sobre filtros e ordenação

### 🐛 Correções

- **Corrigir `asyncio.get_event_loop()` deprecado**
  - Agora usa `asyncio.get_running_loop()` (compatível com Python ≥3.10)

- **File handles sem contexto `with`**
  - Linhas 140-141 e 155-156 agora usam `with open()...`
  - Garante fechamento adequado do descriptor

- **Remover exceção `except Exception: pass` genérica**
  - Especifica tipos de exceção: `(ValueError, OSError)` em cache
  - Mantém `except Exception` apenas em parsing onde é esperado (com debug log)

- **Remover global mutável `CURRENT_FORUMS`**
  - Agora `forum_ids` vive no estado `state` do TUI
  - Mais testável e sem efeitos colaterais globais

- **Mudança de fallback de 47 páginas para 1**
  - 47 era um número arbitrário sem justificativa
  - 1 é conservador — sempre funciona, avisa o usuário se precisar ser ajustado manualmente

### 🔧 Interna

- Adicionada função `size_to_mb()` para evitar duplicação com `cmd_sort`
- Adicionada constante global `SSL_CTX` com contexto SSL configurado

---

## [4.0.0](https://github.com/DevTroli/RuTrackGames/compare/v3.0.0...v4.0.0) - 2026-04-22

### ✨ Features

- Busca fuzzy como fallback (tenta substring → AND → fuzzy)
- Paginação manual (`n` / `p` no modo interativo)
- Comandos avançados: `s` (sort), `f` (filter), `!info`, `!open`
- Status bar com contagem e filtros

### 🐛 Bug Fixes

- Mensagem amigável quando busca retorna vazio (em vez de "No games found")
- Validação básica de cache JSON

### 🔧 Refatoração

- Organizado em seções com comentários `# ── Nome ──`
- Funções auxiliárias: `search_substring()`, `search_all_words()`, `search_fuzzy()`

---

## [3.0.0] - 2026-04-21

### ✨ Features

- Scraper assíncrono básico
- Cache simples em disco
- Modo interativo com busca

---

## [2.0.0] - 2026-04-20

### ✨ Features

- Parsing HTML inicial
- Suporte a múltiplos fóruns
- Formatação de saída com Rich

---

## [1.0.0] - 2026-04-19

### ✨ Feature

- Primeira versão funcional
- Busca básica
- Catálogo Linux nativo
