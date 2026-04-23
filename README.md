# RuTrackGames — Navegador de Jogos RuTracker

TUI interativa para navegar e buscar torrents no [RuTracker.org](https://rutracker.org/forum/).

**Autor:** DevTroli · **Licença:** MIT · **Versão:** 5.0

[![PyPI](https://img.shields.io/pypi/v/rutracker-games.svg)](https://pypi.org/project/rutracker-games)
[![Python](https://img.shields.io/pypi/pyversions/rutracker-games)](https://pypi.org/project/rutracker-games)

---

## Instalação

**Global (recomendado):**
```bash
pip install rutracker-games
rutracker-games
```

**Desenvolvimento:**
```bash
git clone https://github.com/DevTroli/RuTrackGames.git && cd RuTrackGames
uv venv && uv pip install -r requirements.txt
uv run rl/rtgames.py
```

## Uso

```bash
rutracker-games                    # Modo interativo
rutracker-games -g "NieR"          # Busca direta
rutracker-games --forum linux      # Apenas Linux-native
rutracker-games -c                 # Catálogo completo
rutracker-games -r                 # Forçar atualização
```

## Comandos (TUI)

| Comando | Ação |
|---------|------|
| `<texto>` | Buscar por jogo |
| `Enter` | Listar catálogo |
| `s seeds|size|date|name` | Ordenar |
| `f linux|windows|mac` | Filtrar plataforma |
| `n` / `p` | Próxima / anterior |
| `!info <n>` | Detalhes |
| `!open <n>` | Abrir torrent |
| `!refresh` | Atualizar cache |
| `h` | Ajuda · `q` | Sair |

## Recursos

- ⚡ Assíncrono: 24 conexões paralelas
- 📦 Cache XDG em `~/.cache/rl/`
- 🔒 SSL/TLS + SSRF protection
- 🎨 Interface Rich colorida
- 🔍 Busca inteligente substring/AND

---

> Não afiliado ao RuTracker.org. Use conforme os [termos de serviço](https://rutracker.org/forum/rules.php).
