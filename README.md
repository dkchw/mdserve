# mdserve

A beautiful local file server with Markdown rendering. Like `python -m http.server` but with style.

## Install

```bash
uv tool install .
```

## Usage

```bash
# Serve current directory on port 2112
mdserve

# Custom port
mdserve 8080

# Custom bind address
mdserve 2112 --bind 127.0.0.1
```

## Features

- 📁 **File browser** — clean directory listing with file icons, sizes, and dates
- 📄 **Markdown rendering** — beautiful typography with syntax-highlighted code blocks
- ☀/☽ **Light & dark mode** — toggle in the top bar, preference saved to localStorage
- 🗂 **Table of contents** — auto-generated sidebar for Markdown files with headings
- 📖 **Double Page Mode** — Firefox Reader-style double column layout that scrolls vertically (configurable column gap)
- 🖥 **Wide Layout Mode** — stretches the document width to fill the screen edges, removing wide side gaps
- 📄 **Raw MD Display & Copy** — view raw markdown source in a single click and copy the entire file instantly
- ☑ **Interactive Checklists** — click checkboxes to write updates (`- [ ]` / `- [x]`) back to disk, check/uncheck all, tick selected ranges, and toggle line-through style for completed tasks
- 🧜 **Mermaid Diagrams** — dynamic diagram rendering (responsive to light/dark themes)
- 🔒 **Safe** — path traversal protection, stays within the served directory
- **No configuration** — just run it

## License
Apache License 2.0. See LICENSE file for details.
