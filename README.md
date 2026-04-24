# RuTrackGames — RuTracker Games Browser

Interactive TUI for browsing and searching torrents on [RuTracker.org](https://rutracker.org/forum/).

[![License](https://img.shields.io/pypi/l/rutracker-games)](LICENSE)
[![Downloads](https://static.pepy.tech/badge/rutracker-games)](https://pepy.tech/project/rutracker-games)

**Author:** DevTroli · **License:** MIT · **Version:** 5.0

<sub><a href="README.md">🇺🇸 English</a> | <a href="README_pt.md">🇧🇷 Português</a></sub>

---

## Installation

**Global (recommended):**
```bash
pip install rutracker-games
rutracker-games
```

**Development:**
```bash
git clone https://github.com/DevTroli/RuTrackGames.git && cd RuTrackGames
uv venv && uv pip install -r requirements.txt
uv run rl/rtgames.py
```

## Usage

```bash
rutracker-games                    # Interactive mode
rutracker-games -g "NieR"          # Direct search
rutracker-games --forum linux      # Linux-native only
rutracker-games -c                 # Full catalog
rutracker-games -r                 # Force refresh
```

## TUI Commands

| Command | Action |
|---------|--------|
| `<text>` | Search by name |
| `Enter` | List catalog |
| `s seeds|size|date|name` | Sort |
| `f linux|windows|mac` | Filter by platform |
| `n` / `p` | Next / previous page |
| `!info <n>` | Game details |
| `!open <n>` | Open torrent |
| `!refresh` | Refresh cache |
| `h` | Help · `q` | Quit |

## Features

- ⚡ Async: 24 concurrent connections (aiohttp)
- 📦 XDG cache in `~/.cache/rl/`
- 🔒 SSL/TLS + SSRF protection
- 🎨 Rich-colored TUI interface
- 🔍 Smart search: substring/AND matching

---

> Not affiliated with RuTracker.org. Use subject to [ToS](https://rutracker.org/forum/rules.php).
