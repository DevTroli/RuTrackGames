# rtlinux — Navegador de Jogos RuTracker

`rtlinux` é um navegador de jogos baseado em terminal (TUI) para o RuTracker.org, o maior tracker de torrents de jogos do mundo. Ele indexa automaticamente centenas de fóruns, cria um catálogo local em cache e oferece uma interface interativa para buscar, navegar e filtrar jogos por plataforma (Linux, Windows, Mac).

## Funcionalidades

- **Scraper assíncrono** — Fetcha múltiplas páginas em paralelo (24 conexões simultâneas)
- **Catálogo em cache** — Armazena HTML e JSON localmente para consultas rápidas
- **Busca inteligente** — Tenta substring → todas as palavras → palavras aleatórias
- **Interface TUI com Rich** — Tabelas coloridas com seeds count, tamanho, data
- **Filtros e ordenação** — Filtra por plataforma, ordena por seeds/tamanho/data
- **SSL verificado** — Conexões TLS seguras com certificados
- **Proteção contra SSRF** — Validação de URLs antes de abrir no navegador

## Instalação

### Requisitos
- Python 3.10+
- uv (recomendado) ou pip

### Com uv (recomendado)

```bash
# Clonar o repositório
git clone https://github.com/SEU_USUARIO/rtlinux.git
cd rtlinux

# Criar e ativar venv
uv venv

# Instalar dependências
uv pip install -r requirements.txt

# Executar
uv run rtlinux.py
```

### Com pip

```bash
# Criar e ativar venv
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# ou
.venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Executar
python rtlinux.py
```

## Uso

### Modo interativo (padrão)

```bash
./rtlinux.py
```

Abre uma interface terminal interativa onde você pode:
- Digitar um nome para buscar jogos
- Usar comandos como `q`, `!refresh`, `n`, `p`, `h`, etc.

### Busca direta

```bash
# Buscar jogos por nome
./rtlinux.py -g "NieR"

# Mostrar todos os resultados (sem limite de 200)
./rtlinux.py -g "NieR" -a

# Listar o catálogo completo
./rtlinux.py -c
```

### Filtrar por plataforma

```bash
# Apenas jogos Linux nativos
./rtlinux.py --forum linux

# Apenas jogos Windows
./rtlinux.py --forum windows

# Apenas jogos Mac
./rtlinux.py --forum mac

# Todos os jogos (padrão)
./rtlinux.py --forum all
```

### Forçar atualização do catálogo

```bash
# Ignorar cache e buscar novos dados do RuTracker
./rtlinux.py -r
```

## Comandos no Modo Interativo

Ao rodar `./rtlinux.py`, você vê esta tela:

```
╭─────────────────────────────────────────╮
│ RuTracker Games Browser                 │
│                                         │
│  Type a name to search · Enter = list   │
│  q = quit · !refresh = re-fetch catalog│
│  n/p = next/prev page · h = help       │
│  s <key> = sort (name/seeds/size/date) │
│  f <plat> = filter (linux/windows/mac) │
│  !info <n> = show details              │
│  !open <n> = open in browser           │
╰─────────────────────────────────────────╯
 [dim]X jogos loaded[/dim]
```

| Comando      | Descrição                                              |
|--------------|--------------------------------------------------------|
| `<texto>`    | Buscar jogos que contenham o texto                    |
| `Enter`      | Listar todos os jogos                                  |
| `q`          | Sair                                                   |
| `!refresh`   | Atualizar catálogo do site                             |
| `c` / `clear`| Limpar busca, mostrar todos                            |
| `n`          | Próxima página                                         |
| `p`          | Página anterior                                        |
| `s name`     | Ordenar por nome                                       |
| `s seeds`    | Ordenar por seeds (desc)                               |
| `s size`     | Ordenar por tamanho (desc)                             |
| `s date`     | Ordenar por data                                       |
| `f linux`    | Filtrar apenas jogos Linux                             |
| `f windows`  | Filtrar apenas jogos Windows                           |
| `f mac`      | Filtrar apenas jogos Mac                               |
| `f all`      | Mostrar todas as plataformas                           |
| `!info <n>`  | Mostrar detalhes do jogo #n                            |
| `!open <n>`  | Abre o link do torrent do jogo #n no navegador         |
| `h`          | Mostrar ajuda                                          |

## Estrutura do Projeto

```
rtlinux/
├── rtlinux.py        # Script principal (single-file)
├── requirements.txt  # Dependências Python
├── README.md         # Este arquivo
├── .gitignore        # Arquivos ignorados pelo git
└── cache/            # Diretório de cache (gerado automaticamente)
    ├── *.html        # Páginas HTML cacheadas (encoding cp1251)
    ├── max_page_*.txt# Contagem de páginas por fórum
    └── games_*.json  # Catálogo deduplicado em JSON
```

### Cache

O cache é armazenado no diretório padrão:
- **Linux/macOS**: `~/.cache/rtlinux/`
- **Windows**: `%LOCALAPPDATA%/rtlinux/`

Para limpar todo o cache:
```bash
rm -rf ~/.cache/rtlinux/  # Linux/macOS
# ou
rmdir /s %LOCALAPPDATA%\rtlinux  # Windows
```

## Segurança

### SSL/TLS Verificação
Desde v5, as conexões HTTP usam **SSL/TLS verificado** com certificados do `certifi`. O código anterior desabilitava verificações (ssl=False) — esta versão corrige essa vulnerabilidade de Man-in-the-Middle.

### Validação de URLs
Ao abrir um link com `!open <n>`, o script valida:
- Esquema deve ser `http` ou `https`
- Domínio deve estar na allowlist (`rutracker.org`, `rutracker.net`, `rutracker.nl`)

Isso previne ataques de **SSRF** (Server-Side Request Forgery) e injeção de URLs maliciosas.

### Rich Markup Escaping
Nomes de jogos e queries do usuário são **escapados automaticamente** pelo Rich `Text` object, prevenindo injeção de markup.

## Desenvolvimento

### Executar testes (futuro)
```bash
uv run pytest  # quando houver testes
```

### Formatação
```bash
uv run ruff format rtlinux.py
uv run ruff check rtlinux.py
```

### Tipo checking (futuro)
```bash
uv run mypy rtlinux.py
```

## Licença

Este projeto é distribuído sob a **Licença MIT**.

```
MIT License

Copyright (c) 2026 rtlinux contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Créditos

- **Autor**: troli
- **Base de dados**: [RuTracker.org](https://rutracker.org/forum/) — O maior tracker de jogos digitais
- **Frameworks**:
  - [aiohttp](https://docs.aiohttp.org/) — HTTP assíncrono
  - [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) — Parsing HTML
  - [Rich](https://rich.readthedocs.io/) — Interface terminal moderna
  - [aiofiles](https://github.com/Gottox/aiofiles) — I/O assíncrono em disco
  - [certifi](https://github.com/certifi/python-certifi) — Certificados SSL

## Contribuindo

Pull requests são bem-vindos! Para mudanças significativas:

1. Abra um issue descrevendo a mudança proposta
2. Fork o repositório
3. Crie uma branch para sua feature (`git checkout -b feature/ua-feature`)
4. Commit suas mudanças (`git commit -m 'Adicionar nova feature'`)
5. Push para a branch (`git push origin feature/ua-feature`)
6. Abra um Pull Request

### Diretrizes
- Mantenha o estilo single-file do código
- Siga o padrão de comentários `# ── Seção ──` para separar módulos
- Adicione docstrings minimalistas quando útil
- Teste manualmente antes de enviar PR

## Changelog

### v5.0 (2026-04-23)
- **Segurança**: Habilitar SSL verification com certifi
- **Segurança**: Validação de URLs antes de abrir no navegador (SSRF protection)
- **Segurança**: Escapar Rich markup em nomes de jogos (`Text` object)
- **Correção**: File handles com `with` statement
- **Melhoria**: `size_to_mb()` compartilhada entre formatação e ordenação
- **Melhoria**: Otimizar busca para passagem única
- **Melhoria**: Unificar dispatcher de comandos (prefixos)
- **Melhoria**: Cache no padrão XDG (`~/.cache/rtlinux/`)
- **Correção**: `asyncio.get_running_loop()` (deprecado `get_event_loop()`)
- **Melhoria**: Melhor help inicial do modo interativo

### v4.0 (anterior)
- Versão inicial com busca substring + AND

---

**Nota**: Este projeto não é afiliado ao RuTracker.org. Use responsibly conforme os termos de serviço do site.
