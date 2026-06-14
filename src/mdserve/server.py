import os
import sys
import html
import mimetypes
import urllib.parse
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.toc import TocExtension
from pygments.formatters import HtmlFormatter


# ── Pygments CSS (for both themes) ────────────────────────────────────────────
PYGMENTS_LIGHT = HtmlFormatter(style="friendly").get_style_defs(".codehilite")
PYGMENTS_DARK  = HtmlFormatter(style="dracula").get_style_defs(".codehilite")


# ── Shared page shell ──────────────────────────────────────────────────────────
PAGE_SHELL = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Geist+Mono:wght@300;400;500&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
<style>
/* ── Reset & tokens ──────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --radius: 6px;
  --transition: 0.2s ease;
}}

[data-theme="dark"] {{
  --bg:        #0e0e11;
  --bg2:       #16161b;
  --bg3:       #1e1e26;
  --border:    #2a2a38;
  --text:      #e8e8f0;
  --text2:     #888899;
  --accent:    #7c6af7;
  --accent2:   #a89cf8;
  --hover:     #1e1e2e;
  --tag-bg:    #1e1e2e;
  --link:      #a89cf8;
  --code-bg:   #12121a;
  --mark-bg:   rgba(124,106,247,.25);
}}

[data-theme="light"] {{
  --bg:        #fafaf8;
  --bg2:       #f3f3ef;
  --bg3:       #eaeae4;
  --border:    #deded6;
  --text:      #1a1a24;
  --text2:     #666677;
  --accent:    #5b48e8;
  --accent2:   #7c6af7;
  --hover:     #efefe9;
  --tag-bg:    #efefe9;
  --link:      #5b48e8;
  --code-bg:   #f0f0ea;
  --mark-bg:   rgba(91,72,232,.12);
}}

/* ── Base ────────────────────────────────────────── */
html {{ scroll-behavior: smooth; }}

body {{
  font-family: 'Geist Mono', monospace;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  font-size: 14px;
  line-height: 1.6;
}}

a {{ color: var(--link); text-decoration: none; }}
a:hover {{ text-decoration: underline; text-underline-offset: 3px; }}

/* ── Top bar ─────────────────────────────────────── */
.topbar {{
  position: sticky; top: 0; z-index: 100;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px;
  height: 48px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(12px);
}}

.topbar-left {{
  display: flex; align-items: center; gap: 16px;
  min-width: 0;
}}

.brand {{
  font-size: 13px;
  font-weight: 500;
  color: var(--accent);
  letter-spacing: .04em;
  white-space: nowrap;
  flex-shrink: 0;
}}

.breadcrumb {{
  display: flex; align-items: center; gap: 4px;
  font-size: 12px;
  color: var(--text2);
  overflow: hidden;
}}

.breadcrumb a {{ color: var(--text2); }}
.breadcrumb a:hover {{ color: var(--text); }}
.breadcrumb .sep {{ opacity: .4; flex-shrink: 0; }}
.breadcrumb .crumb {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}

.topbar-right {{ display: flex; align-items: center; gap: 8px; flex-shrink: 0; }}

/* ── Theme toggle ────────────────────────────────── */
.theme-btn {{
  cursor: pointer;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg2);
  color: var(--text2);
  padding: 4px 10px;
  font-family: inherit;
  font-size: 12px;
  transition: var(--transition);
  display: flex; align-items: center; gap: 5px;
}}
.theme-btn:hover {{ background: var(--bg3); color: var(--text); }}

/* ── Directory listing ───────────────────────────── */
.container {{
  max-width: 900px;
  margin: 0 auto;
  padding: 32px 24px 64px;
}}

.path-header {{
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 24px;
}}

.path-header h1 {{
  font-family: 'Instrument Serif', serif;
  font-size: 26px;
  font-weight: 400;
  color: var(--text);
}}

.stat-badge {{
  font-size: 11px;
  color: var(--text2);
  background: var(--tag-bg);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 2px 10px;
}}

/* ── File table ──────────────────────────────────── */
.file-table {{
  width: 100%;
  border-collapse: collapse;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}}

.file-table thead th {{
  background: var(--bg2);
  color: var(--text2);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: .06em;
  text-transform: uppercase;
  padding: 10px 16px;
  text-align: left;
  border-bottom: 1px solid var(--border);
}}

.file-table tbody tr {{
  border-bottom: 1px solid var(--border);
  transition: background var(--transition);
}}
.file-table tbody tr:last-child {{ border-bottom: none; }}
.file-table tbody tr:hover {{ background: var(--hover); }}

.file-table td {{
  padding: 10px 16px;
  font-size: 13px;
  vertical-align: middle;
}}

.file-table td.name-cell {{
  display: flex; align-items: center; gap: 10px;
}}

.icon {{
  font-size: 16px;
  flex-shrink: 0;
  width: 22px;
  text-align: center;
}}

.file-name {{ color: var(--text); }}
.file-name.is-dir {{ color: var(--accent2); font-weight: 500; }}
.file-name.is-md  {{ color: var(--accent); }}

.size-cell, .date-cell {{
  color: var(--text2);
  font-size: 12px;
  white-space: nowrap;
}}

.md-badge {{
  font-size: 10px;
  background: var(--mark-bg);
  color: var(--accent2);
  border-radius: 4px;
  padding: 1px 6px;
  letter-spacing: .03em;
}}

/* ── Markdown viewer ─────────────────────────────── */
.md-layout {{
  display: grid;
  grid-template-columns: var(--sidebar-width, 220px) 1fr;
  gap: 0;
  max-width: 1200px;
  margin: 0 auto;
  min-height: calc(100vh - 48px);
  position: relative;
  transition: grid-template-columns 0.2s ease;
}}

.md-layout.is-dragging {{
  transition: none !important;
}}

/* States */
.md-layout[data-sidebar-state="collapsed"] {{
  --sidebar-width: 0px;
}}
.md-layout[data-sidebar-state="collapsed"] .toc-sidebar {{
  display: none;
}}
.md-layout[data-sidebar-state="collapsed"] .sidebar-resizer {{
  display: none;
}}
.md-layout[data-sidebar-state="collapsed"] .md-content-wrap {{
  grid-column: 1 / span 2;
}}
.md-layout[data-sidebar-state="collapsed"] .md-body {{
  margin: 0 auto;
}}

.md-layout[data-sidebar-state="partial"] {{
  --sidebar-width: 220px;
}}

.md-layout[data-sidebar-state="expanded"] {{
  --sidebar-width: 360px;
}}

/* Resizer */
.sidebar-resizer {{
  position: absolute;
  top: 0;
  left: var(--sidebar-width, 220px);
  transform: translateX(-50%);
  width: 6px;
  height: 100%;
  cursor: col-resize;
  background: transparent;
  transition: background var(--transition);
  z-index: 10;
}}
.sidebar-resizer::after {{
  content: '';
  position: absolute;
  top: 0;
  left: 2px;
  width: 2px;
  height: 100%;
  background: var(--border);
  transition: background var(--transition);
}}
.sidebar-resizer:hover::after, .sidebar-resizer.is-dragging::after {{
  background: var(--accent);
}}

/* TOC sidebar */
.toc-sidebar {{
  grid-column: 1;
  position: sticky; top: 48px;
  height: calc(100vh - 48px);
  overflow-y: auto;
  padding: 28px 20px;
  border-right: 1px solid var(--border);
  background: var(--bg2);
  width: 100%;
  box-sizing: border-box;
  transition: width var(--transition);
}}

.md-layout.is-dragging .toc-sidebar {{
  transition: none !important;
}}

.toc-sidebar::-webkit-scrollbar {{ width: 4px; }}
.toc-sidebar::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 4px; }}

.toc-label {{
  font-size: 10px;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--text2);
  margin-bottom: 12px;
  font-weight: 500;
}}

.toc-sidebar .toc ul {{
  list-style: none;
  padding: 0;
  margin: 0;
}}

.toc-sidebar .toc li {{
  margin: 0;
}}

.toc-sidebar .toc a {{
  display: block;
  padding: 4px 8px;
  font-size: 12px;
  color: var(--text2);
  border-radius: 4px;
  line-height: 1.4;
  transition: var(--transition);
}}

.toc-sidebar .toc a:hover {{
  color: var(--text);
  background: var(--hover);
  text-decoration: none;
}}

.toc-sidebar .toc ul ul a {{ padding-left: 20px; font-size: 11.5px; }}
.toc-sidebar .toc ul ul ul a {{ padding-left: 32px; font-size: 11px; }}
.toc-sidebar .toc ul ul ul ul a {{ padding-left: 44px; font-size: 11px; }}
.toc-sidebar .toc ul ul ul ul ul a {{ padding-left: 56px; font-size: 11px; }}
.toc-sidebar .toc ul ul ul ul ul ul a {{ padding-left: 68px; font-size: 11px; }}

/* Sidebar Control Group in Topbar */
.sidebar-ctrl-group {{
  display: inline-flex;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg2);
  overflow: hidden;
  margin-right: 8px;
}}

.sidebar-btn {{
  cursor: pointer;
  border: none;
  background: transparent;
  color: var(--text2);
  padding: 4px 10px;
  font-family: inherit;
  font-size: 12px;
  transition: var(--transition);
  border-right: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
}}

.sidebar-btn:last-child {{
  border-right: none;
}}

.sidebar-btn:hover {{
  background: var(--bg3);
  color: var(--text);
}}

.sidebar-btn.active {{
  background: var(--accent);
  color: #ffffff;
}}

/* MD content */
.md-content-wrap {{
  grid-column: 2;
  padding: 40px 56px 80px;
  min-width: 0;
}}

.md-filename {{
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 12px;
  color: var(--text2);
  margin-bottom: 28px;
}}

.md-filename .dot {{ color: var(--accent); }}

/* ── Markdown typography ─────────────────────────── */
.md-body {{
  max-width: 720px;
}}

.md-body h1,
.md-body h2,
.md-body h3,
.md-body h4,
.md-body h5,
.md-body h6 {{
  font-family: 'Instrument Serif', serif;
  font-weight: 400;
  color: var(--text);
  line-height: 1.25;
  margin-top: 1.8em;
  margin-bottom: .6em;
}}

.md-body h1 {{ font-size: 2.2rem; margin-top: 0; }}
.md-body h2 {{ font-size: 1.6rem; border-bottom: 1px solid var(--border); padding-bottom: .3em; }}
.md-body h3 {{ font-size: 1.25rem; }}
.md-body h4 {{ font-size: 1rem; font-family: 'Geist Mono', monospace; letter-spacing: .05em; }}

.md-body p {{ margin-bottom: 1.1em; color: var(--text); line-height: 1.8; }}

.md-body a {{ color: var(--link); }}
.md-body a:hover {{ text-decoration: underline; }}

.md-body strong {{ color: var(--text); font-weight: 600; }}
.md-body em {{ font-style: italic; }}

.md-body ul, .md-body ol {{
  padding-left: 1.4em;
  margin-bottom: 1em;
}}
.md-body li {{ margin-bottom: .35em; line-height: 1.7; }}

.md-body blockquote {{
  border-left: 3px solid var(--accent);
  margin: 1.4em 0;
  padding: .6em 1.2em;
  background: var(--mark-bg);
  border-radius: 0 var(--radius) var(--radius) 0;
  color: var(--text2);
  font-style: italic;
}}

.md-body code {{
  font-family: 'Geist Mono', monospace;
  font-size: .85em;
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: .1em .4em;
  color: var(--accent2);
}}

.md-body pre {{
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.2em 1.4em;
  overflow-x: auto;
  margin: 1.4em 0;
  line-height: 1.6;
}}

.md-body pre code {{
  background: none;
  border: none;
  padding: 0;
  color: var(--text);
  font-size: .88em;
}}

.md-body table {{
  width: 100%;
  border-collapse: collapse;
  margin: 1.4em 0;
  font-size: 13px;
}}

.md-body th {{
  background: var(--bg2);
  color: var(--text2);
  text-align: left;
  padding: 8px 14px;
  border: 1px solid var(--border);
  font-size: 11px;
  letter-spacing: .06em;
  text-transform: uppercase;
}}

.md-body td {{
  padding: 8px 14px;
  border: 1px solid var(--border);
}}

.md-body td:first-child, .md-body th:first-child {{ border-left: none; }}
.md-body td:last-child, .md-body th:last-child {{ border-right: none; }}

.md-body tr:hover td {{ background: var(--hover); }}

.md-body hr {{
  border: none;
  border-top: 1px solid var(--border);
  margin: 2em 0;
}}

.md-body img {{
  max-width: 100%;
  border-radius: var(--radius);
  border: 1px solid var(--border);
}}

/* ── Pygments (code highlight) ───────────────────── */
#pygments-style {{ display: block; }}

/* ── No TOC fallback ─────────────────────────────── */
.md-layout.no-toc {{
  grid-template-columns: 1fr;
}}
.md-layout.no-toc .toc-sidebar {{ display: none; }}
.md-layout.no-toc .md-content-wrap {{ padding: 40px 10%; }}

/* ── Responsive ──────────────────────────────────── */
@media (max-width: 768px) {{
  .md-layout {{
    grid-template-columns: 1fr !important;
  }}
  .toc-sidebar {{ display: none !important; }}
  .sidebar-resizer {{ display: none !important; }}
  .sidebar-ctrl-group {{ display: none !important; }}
  .md-content-wrap {{ padding: 28px 20px 60px; grid-column: 1 / span 2 !important; }}
  .container {{ padding: 20px 16px 48px; }}
}}
</style>
<!-- Pygments styles (swapped on theme toggle) -->
<style id="pygments-style">{pygments_css}</style>
</head>
<body>
{body}
<script>
(function() {{
  const html = document.documentElement;

  // Restore saved theme
  const saved = localStorage.getItem('mdserve-theme') || 'dark';
  html.setAttribute('data-theme', saved);
  updateThemeBtn(saved);

  function updateThemeBtn(theme) {{
    const btn = document.getElementById('theme-btn');
    if (!btn) return;
    btn.textContent = theme === 'dark' ? '☀ Light' : '☽ Dark';
  }}

  window.toggleTheme = function() {{
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('mdserve-theme', next);
    updateThemeBtn(next);

    // swap pygments stylesheet
    const style = document.getElementById('pygments-style');
    if (style) {{
      style.textContent = next === 'dark'
        ? {dark_css_json}
        : {light_css_json};
    }}
  }};

  // Sidebar controls
  const layout = document.querySelector('.md-layout');
  const resizer = document.querySelector('.sidebar-resizer');

  if (layout) {{
    const savedState = localStorage.getItem('mdserve-sidebar-state') || 'partial';
    const savedWidth = localStorage.getItem('mdserve-sidebar-width') || '220px';

    window.setSidebarState = function(state, width) {{
      layout.setAttribute('data-sidebar-state', state);

      document.querySelectorAll('.sidebar-btn').forEach(btn => {{
        btn.classList.remove('active');
      }});

      const activeBtn = document.getElementById('sidebar-btn-' + state);
      if (activeBtn) {{
        activeBtn.classList.add('active');
      }}

      if (state === 'custom' && width) {{
        layout.style.setProperty('--sidebar-width', width);
        localStorage.setItem('mdserve-sidebar-width', width);
      }} else {{
        layout.style.removeProperty('--sidebar-width');
      }}

      localStorage.setItem('mdserve-sidebar-state', state);
    }};

    // Initialize sidebar
    if (savedState === 'custom') {{
      setSidebarState('custom', savedWidth);
    }} else {{
      setSidebarState(savedState);
    }}

    if (resizer) {{
      let startX, startWidth;

      resizer.addEventListener('mousedown', function(e) {{
        e.preventDefault();
        startX = e.clientX;
        const rect = document.querySelector('.toc-sidebar').getBoundingClientRect();
        startWidth = rect.width;

        layout.classList.add('is-dragging');
        resizer.classList.add('is-dragging');

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
      }});

      function handleMouseMove(e) {{
        const deltaX = e.clientX - startX;
        let newWidth = startWidth + deltaX;

        if (newWidth < 120) {{
          setSidebarState('collapsed');
        }} else {{
          if (newWidth > 600) newWidth = 600;
          setSidebarState('custom', newWidth + 'px');
        }}
      }}

      function handleMouseUp() {{
        layout.classList.remove('is-dragging');
        resizer.classList.remove('is-dragging');
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      }}
    }}
  }}
}})();
</script>
</body>
</html>"""


def _topbar(breadcrumb_html: str, sidebar_controls: str = "") -> str:
    return f"""
<header class="topbar">
  <div class="topbar-left">
    <span class="brand">⬡ mdserve</span>
    <nav class="breadcrumb">{breadcrumb_html}</nav>
  </div>
  <div class="topbar-right">
    {sidebar_controls}
    <button class="theme-btn" id="theme-btn" onclick="toggleTheme()">☀ Light</button>
  </div>
</header>"""


def _breadcrumb(urlpath: str) -> str:
    parts = [p for p in urlpath.strip("/").split("/") if p]
    crumbs = ['<a href="/" class="crumb">~</a>']
    accumulated = ""
    for i, part in enumerate(parts):
        accumulated += f"/{part}"
        crumbs.append('<span class="sep">/</span>')
        if i < len(parts) - 1:
            crumbs.append(f'<a href="{accumulated}/" class="crumb">{html.escape(part)}</a>')
        else:
            crumbs.append(f'<span class="crumb">{html.escape(part)}</span>')
    return "".join(crumbs)


def _file_icon(name: str, is_dir: bool) -> str:
    if is_dir:
        return "📁"
    ext = Path(name).suffix.lower()
    icons = {
        ".md": "📄", ".markdown": "📄",
        ".py": "🐍", ".js": "🟨", ".ts": "🔷",
        ".json": "📋", ".yaml": "📋", ".yml": "📋", ".toml": "📋",
        ".html": "🌐", ".css": "🎨",
        ".sh": "⚙", ".bash": "⚙",
        ".png": "🖼", ".jpg": "🖼", ".jpeg": "🖼", ".gif": "🖼", ".svg": "🖼", ".webp": "🖼",
        ".pdf": "📕",
        ".zip": "📦", ".tar": "📦", ".gz": "📦",
        ".txt": "📝",
        ".mp4": "🎬", ".mov": "🎬",
        ".mp3": "🎵", ".wav": "🎵",
    }
    return icons.get(ext, "·")


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 ** 2:
        return f"{size/1024:.1f} KB"
    elif size < 1024 ** 3:
        return f"{size/1024**2:.1f} MB"
    else:
        return f"{size/1024**3:.1f} GB"


def _fmt_date(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%b %d, %Y")


def render_directory(fs_path: Path, urlpath: str) -> str:
    entries = []
    try:
        items = sorted(fs_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        items = []

    # Parent dir link
    if urlpath.strip("/"):
        parent = "/" + "/".join(urlpath.strip("/").split("/")[:-1])
        if parent != "/":
            parent += "/"
        entries.append(("dir", "..", parent, None, None))

    for item in items:
        if item.name.startswith("."):
            continue
        try:
            stat = item.stat()
        except OSError:
            continue
        if item.is_dir():
            link = urlpath.rstrip("/") + "/" + urllib.parse.quote(item.name) + "/"
            entries.append(("dir", item.name, link, None, stat.st_mtime))
        else:
            link = urlpath.rstrip("/") + "/" + urllib.parse.quote(item.name)
            ext = item.suffix.lower()
            entries.append(("file", item.name, link, stat.st_size, stat.st_mtime, ext))

    rows = []
    for entry in entries:
        kind = entry[0]
        name = entry[1]
        link = entry[2]

        if name == "..":
            rows.append(f"""<tr>
              <td><div class="name-cell">
                <span class="icon">↑</span>
                <a href="{link}" class="file-name is-dir">../</a>
              </div></td>
              <td class="size-cell">—</td>
              <td class="date-cell">—</td>
            </tr>""")
            continue

        icon = _file_icon(name, kind == "dir")
        size_str = "—" if kind == "dir" else _fmt_size(entry[3])
        date_str = _fmt_date(entry[4]) if entry[4] else "—"
        ext = entry[5] if kind == "file" else ""
        is_md = ext in (".md", ".markdown")

        name_class = "is-dir" if kind == "dir" else ("is-md" if is_md else "")
        display_name = html.escape(name) + ("/" if kind == "dir" else "")
        badge = ' <span class="md-badge">md</span>' if is_md else ""

        rows.append(f"""<tr>
          <td><div class="name-cell">
            <span class="icon">{icon}</span>
            <a href="{link}" class="file-name {name_class}">{display_name}{badge}</a>
          </div></td>
          <td class="size-cell">{size_str}</td>
          <td class="date-cell">{date_str}</td>
        </tr>""")

    count = len([e for e in entries if e[1] != ".."])
    folder_name = fs_path.name or "/"

    body = f"""
{_topbar(_breadcrumb(urlpath))}
<main class="container">
  <div class="path-header">
    <h1>{html.escape(folder_name)}</h1>
    <span class="stat-badge">{count} items</span>
  </div>
  <table class="file-table">
    <thead>
      <tr>
        <th>Name</th>
        <th>Size</th>
        <th>Modified</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</main>"""

    import json
    return PAGE_SHELL.format(
        title=f"{folder_name} — mdserve",
        pygments_css=PYGMENTS_DARK,
        dark_css_json=json.dumps(PYGMENTS_DARK),
        light_css_json=json.dumps(PYGMENTS_LIGHT),
        body=body,
    )


def render_markdown(fs_path: Path, urlpath: str) -> str:
    import json
    text = fs_path.read_text(encoding="utf-8", errors="replace")

    md = markdown.Markdown(
        extensions=[
            FencedCodeExtension(),
            CodeHiliteExtension(linenums=False, guess_lang=True),
            TableExtension(),
            TocExtension(permalink=True),
            "nl2br",
            "sane_lists",
            "smarty",
            "attr_list",
            "def_list",
        ]
    )
    content_html = md.convert(text)
    toc_html = getattr(md, "toc", "")
    has_toc = bool(toc_html.strip()) and "<li>" in toc_html

    sidebar_controls = ""
    sidebar = ""
    layout_class = "md-layout"
    if has_toc:
        sidebar_controls = """<div class="sidebar-ctrl-group">
      <button class="sidebar-btn" id="sidebar-btn-collapsed" onclick="setSidebarState('collapsed')" title="Collapse sidebar">🗙</button>
      <button class="sidebar-btn" id="sidebar-btn-partial" onclick="setSidebarState('partial')" title="Standard width">◧</button>
      <button class="sidebar-btn" id="sidebar-btn-expanded" onclick="setSidebarState('expanded')" title="Expanded width">◨</button>
    </div>"""
        sidebar = f"""<aside class="toc-sidebar">
  <div class="toc-label">Contents</div>
  <nav class="toc">{toc_html}</nav>
</aside>
<div class="sidebar-resizer"></div>"""
    else:
        layout_class += " no-toc"

    parent = "/" + "/".join(urlpath.strip("/").split("/")[:-1])
    if parent != "/":
        parent += "/"

    body = f"""
{_topbar(_breadcrumb(urlpath), sidebar_controls)}
<div class="{layout_class}">
  {sidebar}
  <div class="md-content-wrap">
    <p class="md-filename">
      <a href="{parent}">← back</a>
      <span class="dot">·</span>
      {html.escape(fs_path.name)}
    </p>
    <article class="md-body">{content_html}</article>
  </div>
</div>"""

    return PAGE_SHELL.format(
        title=f"{fs_path.name} — mdserve",
        pygments_css=PYGMENTS_DARK,
        dark_css_json=json.dumps(PYGMENTS_DARK),
        light_css_json=json.dumps(PYGMENTS_LIGHT),
        body=body,
    )


# ── Request handler ────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    base_dir: Path = Path.cwd()

    def log_message(self, fmt, *args):
        sys.stdout.write(f"  {self.address_string()} → {fmt % args}\n")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        urlpath = urllib.parse.unquote(parsed.path)
        fs_path = self.base_dir / urlpath.lstrip("/")

        try:
            fs_path = fs_path.resolve()
            # Security: stay within base_dir
            fs_path.relative_to(self.base_dir.resolve())
        except (ValueError, OSError):
            self._404()
            return

        if fs_path.is_dir():
            self._send_html(render_directory(fs_path, urlpath))
        elif fs_path.is_file():
            ext = fs_path.suffix.lower()
            if ext in (".md", ".markdown"):
                self._send_html(render_markdown(fs_path, urlpath))
            else:
                self._send_file(fs_path)
        else:
            self._404()

    def _send_html(self, content: str):
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path):
        mime, _ = mimetypes.guess_type(str(path))
        mime = mime or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _404(self):
        body = b"<h1>404 Not Found</h1>"
        self.send_response(404)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ── Entry point ────────────────────────────────────────────────────────────────
def run(port: int = 2112, bind: str = ""):
    Handler.base_dir = Path.cwd()
    server = HTTPServer((bind, port), Handler)
    addr = bind or "0.0.0.0"
    print(f"\n  ⬡ mdserve  http://localhost:{port}  (serving {Path.cwd()})\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Goodbye.\n")
