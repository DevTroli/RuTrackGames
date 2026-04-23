# rtlinux — Navegador de Jogos RuTracker

Navegador TUI em Python para o [RuTracker.org](https://rutracker.org/forum/), com catálogo local em cache, busca inteligente e interface interativa com Rich.

**Autor:** troli · **Licença:** MIT · **Versão:** 5.0 (2026-04-23)

---

## Requisitos

- Python 3.10+
- `uv` (recomendado) ou `pip`

## Instalação rápida

```bash
git clone https://github.com/SEU_USUARIO/rtlinux.git && cd rtlinux
uv venv && uv pip install -r requirements.txt
uv run rtlinux.py
```

## Uso

```bash
./rtlinux.py                    # Modo interativo
./rtlinux.py -g "NieR"          # Busca direta
./rtlinux.py --forum linux      # Filtrar por plataforma (linux/windows/mac/all)
./rtlinux.py -r                 # Forçar atualização do catálogo
./rtlinux.py -g "NieR" -a       # Todos os resultados (sem limite)
```

## Comandos no modo interativo

| Comando       | Ação                                  |
|---------------|---------------------------------------|
| `<texto>`     | Buscar por nome                       |
| `Enter`       | Listar todos os jogos                 |
| `s seeds`     | Ordenar por seeds / size / date / name|
| `f linux`     | Filtrar por plataforma                |
| `n` / `p`     | Próxima / página anterior             |
| `!info <n>`   | Detalhes do jogo #n                   |
| `!open <n>`   | Abrir torrent no navegador            |
| `!refresh`    | Atualizar catálogo                    |
| `h`           | Ajuda · `q` = sair                    |

## Funcionalidades

- Scraper assíncrono com 24 conexões paralelas (aiohttp)
- Cache XDG em `~/.cache/rtlinux/` (HTML + JSON)
- Busca: substring → AND → palavras parciais
- SSL/TLS verificado com `certifi`
- Proteção contra SSRF (allowlist de domínios)
- Escape automático de Rich markup

## Dependências

`aiohttp` · `beautifulsoup4` · `rich` · `aiofiles` · `certifi`

---

> Este projeto não é afiliado ao RuTracker.org. Use conforme os termos de serviço do site.
