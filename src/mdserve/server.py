import os
import sys
import html
import mimetypes
import urllib.parse
import json
import re
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
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500&family=Playfair+Display:ital,wght@0,400;0,500;1,400;1,500&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
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
  font-family: 'JetBrains Mono', monospace;
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
  font-family: 'Playfair Display', serif;
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
  font-family: 'Playfair Display', serif;
  font-weight: 400;
  color: var(--text);
  line-height: 1.25;
  margin-top: 1.8em;
  margin-bottom: .6em;
}}

.md-body h1 {{ font-size: 2.2rem; margin-top: 0; }}
.md-body h2 {{ font-size: 1.6rem; border-bottom: 1px solid var(--border); padding-bottom: .3em; }}
.md-body h3 {{ font-size: 1.25rem; }}
.md-body h4 {{ font-size: 1rem; font-family: 'JetBrains Mono', monospace; letter-spacing: .05em; }}

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
  font-family: 'JetBrains Mono', monospace;
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

/* ── Settings Dropdown ───────────────────────────── */
.settings-container {{
  position: relative;
  display: inline-block;
}}

.settings-dropdown {{
  position: absolute;
  top: 36px;
  right: 0;
  width: 280px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  z-index: 200;
  display: none;
  flex-direction: column;
  gap: 16px;
  animation: fadeIn 0.15s ease-out;
}}

@keyframes fadeIn {{
  from {{ opacity: 0; transform: translateY(-10px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

.settings-title {{
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  border-bottom: 1px solid var(--border);
  padding-bottom: 8px;
  margin-bottom: 4px;
}}

.settings-section {{
  display: flex;
  flex-direction: column;
  gap: 10px;
}}

.settings-label {{
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: var(--text2);
  font-weight: 500;
}}

.settings-row {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text);
}}

.settings-row label {{
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}}

.settings-row.indent {{
  padding-left: 20px;
}}

.settings-sublabel {{
  font-size: 11px;
  color: var(--text2);
}}

.settings-row select {{
  background: var(--bg3);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 6px;
  font-family: inherit;
  font-size: 11px;
  outline: none;
  cursor: pointer;
}}

.settings-actions {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 4px;
}}

.settings-btn {{
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  padding: 6px 8px;
  font-family: inherit;
  font-size: 11px;
  cursor: pointer;
  transition: var(--transition);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}}

.settings-btn:hover {{
  background: var(--hover);
  border-color: var(--accent);
}}

/* ── Task list / Checkbox custom styling ─────────── */
.task-checkbox {{
  margin-right: 8px;
  cursor: pointer;
  transform: translateY(1px);
}}

.task-raw-text {{
  display: none;
  font-family: 'JetBrains Mono', monospace;
  margin-right: 8px;
  color: var(--text2);
  font-weight: 500;
}}

/* When HTML checkboxes are active */
.render-checkboxes-active .task-checkbox {{
  display: inline-block;
}}
.render-checkboxes-active .task-raw-text {{
  display: none;
}}

/* When HTML checkboxes are disabled, display raw text and change bullet to dash */
.md-layout:not(.render-checkboxes-active) .task-checkbox {{
  display: none;
}}
.md-layout:not(.render-checkboxes-active) .task-raw-text {{
  display: inline;
}}

.md-layout:not(.render-checkboxes-active) li:has(.task-wrapper) {{
  list-style-type: none;
  position: relative;
  padding-left: 16px;
}}

.md-layout:not(.render-checkboxes-active) li:has(.task-wrapper)::before {{
  content: "-";
  position: absolute;
  left: 2px;
  color: var(--text2);
}}

/* Style for list items containing checked checkbox */
.crossed-ticked li:has(.task-checkbox:checked) {{
  text-decoration: line-through;
  opacity: 0.65;
}}

/* Also cross out line if raw checklist [x] is active and checkboxes are not rendered */
.crossed-ticked:not(.render-checkboxes-active) li:has(.task-checkbox[checked]) {{
  text-decoration: line-through;
  opacity: 0.65;
}}

/* ── Raw Markdown view ───────────────────────────── */
.raw-content-wrap {{
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  overflow-x: auto;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}}

.raw-content-wrap pre {{
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
  background: transparent !important;
}}

.raw-content-wrap code {{
  color: var(--text) !important;
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
}}

/* ── Wide layout settings ────────────────────────── */
.wide-layout-active {{
  max-width: 100% !important;
  width: 100% !important;
}}

.wide-layout-active .md-content-wrap {{
  max-width: 100% !important;
  padding-left: 40px !important;
  padding-right: 40px !important;
}}

.wide-layout-active .md-body {{
  max-width: 100% !important;
}}

/* ── Double page mode ────────────────────────────── */
.double-page-mode .md-content-wrap {{
  max-width: 100% !important;
  height: calc(100vh - 48px);
  padding: 24px 60px;
  overflow: hidden;
  position: relative;
}}

.double-page-mode .md-body {{
  max-width: 100% !important;
  height: calc(100vh - 160px);
  column-width: calc(50% - (var(--col-gap, 60px) / 2));
  column-gap: var(--col-gap, 60px);
  column-fill: auto;
  overflow-x: auto;
  overflow-y: hidden;
  scroll-behavior: smooth;
  padding-bottom: 20px;
  scrollbar-width: thin;
  scrollbar-color: var(--accent) var(--bg2);
}}

.double-page-mode .md-body::-webkit-scrollbar {{
  height: 8px;
}}
.double-page-mode .md-body::-webkit-scrollbar-track {{
  background: var(--bg2);
  border-radius: 4px;
}}
.double-page-mode .md-body::-webkit-scrollbar-thumb {{
  background: var(--accent);
  border-radius: 4px;
}}
.double-page-mode .md-body::-webkit-scrollbar-thumb:hover {{
  background: var(--accent-hover);
}}

.double-page-mode .md-body h1,
.double-page-mode .md-body h2,
.double-page-mode .md-body h3,
.double-page-mode .md-body h4,
.double-page-mode .md-body h5,
.double-page-mode .md-body h6,
.double-page-mode .md-body pre,
.double-page-mode .md-body blockquote,
.double-page-mode .md-body img,
.double-page-mode .md-body table,
.double-page-mode .md-body li {{
  break-inside: avoid;
}}

/* Navigation buttons for reading mode (Removed) */

/* ── Pygments (code highlight) ───────────────────── */
#pygments-style {{ display: block; }}

/* ── Reading Progress ────────────────────────────── */
.reading-progress {{
  position: fixed;
  bottom: 16px;
  right: 24px;
  left: auto;
  transform: none;
  background: transparent;
  border: none;
  color: var(--text2);
  padding: 0;
  border-radius: 0;
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  box-shadow: none;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}}
.reading-progress.visible {{
  opacity: 1;
}}

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

    // Re-render mermaid for new theme
    if (window.renderMermaid) window.renderMermaid();
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

  // --- MDserve settings & features JS ---
  let isScrolling = false;
  let lastInteractionTime = Date.now();
  const markInteraction = () => {{ lastInteractionTime = Date.now(); }};
  window.addEventListener('wheel', markInteraction, {{ passive: true }});
  window.addEventListener('keydown', markInteraction, {{ passive: true }});
  window.addEventListener('touchmove', markInteraction, {{ passive: true }});
  window.addEventListener('mousedown', markInteraction, {{ passive: true }});

  const doublePage = localStorage.getItem('mdserve-double-page') === 'true';
  const colGap = localStorage.getItem('mdserve-col-gap') || '60px';
  const mermaidEnabled = localStorage.getItem('mdserve-mermaid') === 'true';
  const crossCompleted = localStorage.getItem('mdserve-cross-completed') !== 'false';
  const renderCheckboxes = localStorage.getItem('mdserve-render-checkboxes') !== 'false';
  const wideLayout = localStorage.getItem('mdserve-wide-layout') === 'true';
  const pagePaging = localStorage.getItem('mdserve-page-paging') === 'true'; // default to false for smoother scroll
  const readingProgress = localStorage.getItem('mdserve-reading-progress') !== 'false';
  let currentZoom = parseFloat(localStorage.getItem('mdserve-zoom-level')) || 1.0;

  document.addEventListener('DOMContentLoaded', () => {{
    // Double page setup
    const dpCheckbox = document.getElementById('setting-double-page');
    if (dpCheckbox) dpCheckbox.checked = doublePage;

    const gapSelect = document.getElementById('setting-col-gap');
    if (gapSelect) gapSelect.value = colGap;

    const gapRow = document.getElementById('col-gap-row');
    if (gapRow) gapRow.style.display = doublePage ? 'flex' : 'none';

    const pagingRow = document.getElementById('page-paging-row');
    if (pagingRow) pagingRow.style.display = doublePage ? 'flex' : 'none';

    const ppCheckbox = document.getElementById('setting-page-paging');
    if (ppCheckbox) ppCheckbox.checked = pagePaging;

    const zoomSelect = document.getElementById('setting-zoom-level');
    if (zoomSelect) zoomSelect.value = currentZoom;
    applyZoom(currentZoom);

    updateDoublePageUI(doublePage, colGap);
    setTimeout(updateColumnWidth, 100);

    // Mermaid setup
    const mCheckbox = document.getElementById('setting-mermaid');
    if (mCheckbox) mCheckbox.checked = mermaidEnabled;
    if (window.renderMermaid) window.renderMermaid();

    // Cross completed setup
    const ccCheckbox = document.getElementById('setting-cross-completed');
    if (ccCheckbox) ccCheckbox.checked = crossCompleted;
    updateCrossCompletedUI(crossCompleted);

    // Checkbox rendering setup
    const rcCheckbox = document.getElementById('setting-render-checkboxes');
    if (rcCheckbox) rcCheckbox.checked = renderCheckboxes;
    updateRenderCheckboxesUI(renderCheckboxes);

    // Wide layout setup
    const wlCheckbox = document.getElementById('setting-wide-layout');
    if (wlCheckbox) wlCheckbox.checked = wideLayout;
    updateWideLayoutUI(wideLayout);

    // Reading progress setup
    const rpCheckbox = document.getElementById('setting-reading-progress');
    if (rpCheckbox) rpCheckbox.checked = readingProgress;
    const mdBody = document.querySelector('.md-body');
    if (mdBody) {{
      let scrollSnapTimer = null;
      mdBody.addEventListener('scroll', (e) => {{
        updateReadingProgress();
        
        const layout = document.querySelector('.md-layout');
        if (!layout || !layout.classList.contains('double-page-mode')) return;
        
        const pagePaging = localStorage.getItem('mdserve-page-paging') === 'true';
        const timeSinceUser = Date.now() - lastInteractionTime;
        const isBrowserDriven = timeSinceUser > 250;
        
        if (!pagePaging && !isBrowserDriven) return;

        clearTimeout(scrollSnapTimer);
        scrollSnapTimer = setTimeout(() => {{
          if (isScrolling) return;

          const gap = parseInt(getComputedStyle(mdBody).getPropertyValue('--col-gap') || '60', 10);
          const pageWidth = mdBody.clientWidth + gap;
          const currentScroll = mdBody.scrollLeft;
          
          const targetScroll = Math.round(currentScroll / pageWidth) * pageWidth;
          
          if (Math.abs(currentScroll - targetScroll) > 2) {{
            mdBody.scrollTo({{
              left: targetScroll,
              behavior: 'smooth'
            }});
          }}
        }}, 200);
      }}, {{ passive: true }});
    }}
    updateReadingProgress();

    // Raw mode setup
    const isRaw = localStorage.getItem('mdserve-raw-view') === 'true';
    updateRawViewUI(isRaw);
  }});

  // Column width calculation for accurate screen splitting
  function updateColumnWidth() {{
    const mdBody = document.querySelector('.md-body');
    const layout = document.querySelector('.md-layout');
    if (!mdBody) return;
    if (layout && layout.classList.contains('double-page-mode')) {{
      const gap = parseInt(getComputedStyle(mdBody).getPropertyValue('--col-gap') || '60', 10);
      const colWidth = Math.floor((mdBody.clientWidth - gap) / 2);
      if (colWidth > 0) {{
        mdBody.style.columnWidth = colWidth + 'px';
      }}
    }} else {{
      mdBody.style.columnWidth = '';
    }}
  }}
  window.addEventListener('resize', () => {{
    updateColumnWidth();
    updateReadingProgress();
  }});
  window.addEventListener('scroll', updateReadingProgress, {{ passive: true }});

  window.toggleReadingProgressSetting = function() {{
    const cb = document.getElementById('setting-reading-progress');
    localStorage.setItem('mdserve-reading-progress', cb.checked);
    updateReadingProgress();
  }};

  function updateReadingProgress() {{
    const showProgress = localStorage.getItem('mdserve-reading-progress') !== 'false';
    const indicator = document.getElementById('reading-progress-indicator');
    if (!indicator) return;

    if (!showProgress) {{
      indicator.classList.remove('visible');
      setTimeout(() => {{ if (!indicator.classList.contains('visible')) indicator.style.display = 'none'; }}, 300);
      return;
    }}

    const mdBody = document.querySelector('.md-body');
    const layout = document.querySelector('.md-layout');
    if (!mdBody || document.getElementById('raw-content-wrap').style.display === 'block') {{
      indicator.classList.remove('visible');
      return;
    }}

    indicator.style.display = 'flex';
    void indicator.offsetWidth; // force reflow
    indicator.classList.add('visible');

    const isDoublePage = layout && layout.classList.contains('double-page-mode');
    let percent = 0;
    let pageText = '';

    if (isDoublePage) {{
      const gap = parseInt(getComputedStyle(mdBody).getPropertyValue('--col-gap') || '60', 10);
      const pageWidth = mdBody.clientWidth + gap;
      const scrollLeft = mdBody.scrollLeft;
      const maxScroll = mdBody.scrollWidth - mdBody.clientWidth;

      if (maxScroll <= 0) percent = 100;
      else percent = Math.min(100, Math.max(0, (scrollLeft / maxScroll) * 100));

      const currentPage = Math.floor((scrollLeft + (pageWidth/2)) / pageWidth) + 1;
      const totalPages = Math.ceil((mdBody.scrollWidth + gap) / pageWidth);
      pageText = `${{currentPage}} / ${{Math.max(1, totalPages)}}`;
    }} else {{
      const scrollTop = window.scrollY || document.documentElement.scrollTop;
      const scrollHeight = document.documentElement.scrollHeight;
      const clientHeight = document.documentElement.clientHeight;
      const maxScroll = scrollHeight - clientHeight;
      
      if (maxScroll <= 0) percent = 100;
      else percent = Math.min(100, Math.max(0, (scrollTop / maxScroll) * 100));
    }}

    const pageSpan = document.getElementById('reading-page-info');
    const percentSpan = document.getElementById('reading-percent-info');
    const dotSpan = document.getElementById('reading-progress-dot');

    if (isDoublePage) {{
      pageSpan.textContent = pageText;
      pageSpan.style.display = 'inline';
      dotSpan.style.display = 'none';
      percentSpan.style.display = 'none';
    }} else {{
      pageSpan.style.display = 'none';
      dotSpan.style.display = 'none';
      percentSpan.textContent = Math.round(percent) + '%';
      percentSpan.style.display = 'inline';
    }}
  }}

  // Settings dropdown toggle
  window.toggleSettingsDropdown = function(e) {{
    if (e) e.stopPropagation();
    const dropdown = document.getElementById('settings-dropdown');
    if (!dropdown) return;
    const isVisible = dropdown.style.display === 'flex';
    dropdown.style.display = isVisible ? 'none' : 'flex';
    if (isVisible) setTimeout(updateColumnWidth, 50);
  }};

  // Close dropdown on clicking outside
  document.addEventListener('click', (e) => {{
    const dropdown = document.getElementById('settings-dropdown');
    const settingsBtn = document.getElementById('settings-btn');
    if (dropdown && dropdown.style.display === 'flex') {{
      if (!dropdown.contains(e.target) && e.target !== settingsBtn) {{
        dropdown.style.display = 'none';
      }}
    }}
  }});

  window.toggleDoublePageSetting = function() {{
    const cb = document.getElementById('setting-double-page');
    const gapRow = document.getElementById('col-gap-row');
    const pagingRow = document.getElementById('page-paging-row');
    const enabled = cb.checked;
    localStorage.setItem('mdserve-double-page', enabled);
    if (gapRow) gapRow.style.display = enabled ? 'flex' : 'none';
    if (pagingRow) pagingRow.style.display = enabled ? 'flex' : 'none';
    const colGap = localStorage.getItem('mdserve-col-gap') || '60px';
    updateDoublePageUI(enabled, colGap);
    setTimeout(updateColumnWidth, 50);
  }};

  window.changeColGapSetting = function() {{
    const select = document.getElementById('setting-col-gap');
    const val = select.value;
    localStorage.setItem('mdserve-col-gap', val);
    const enabled = localStorage.getItem('mdserve-double-page') === 'true';
    updateDoublePageUI(enabled, val);
    setTimeout(updateColumnWidth, 50);
  }};

  window.toggleMermaidSetting = function() {{
    const cb = document.getElementById('setting-mermaid');
    localStorage.setItem('mdserve-mermaid', cb.checked);
    if (window.renderMermaid) window.renderMermaid();
  }};

  window.toggleCrossCompletedSetting = function() {{
    const cb = document.getElementById('setting-cross-completed');
    localStorage.setItem('mdserve-cross-completed', cb.checked);
    updateCrossCompletedUI(cb.checked);
  }};

  window.toggleRenderCheckboxesSetting = function() {{
    const cb = document.getElementById('setting-render-checkboxes');
    localStorage.setItem('mdserve-render-checkboxes', cb.checked);
    updateRenderCheckboxesUI(cb.checked);
  }};

  window.toggleWideLayoutSetting = function() {{
    const cb = document.getElementById('setting-wide-layout');
    localStorage.setItem('mdserve-wide-layout', cb.checked);
    updateWideLayoutUI(cb.checked);
    setTimeout(updateColumnWidth, 50);
  }};

  window.togglePagePagingSetting = function() {{
    const cb = document.getElementById('setting-page-paging');
    localStorage.setItem('mdserve-page-paging', cb.checked);
  }};

  window.toggleLayoutModeQuick = function() {{
    const cb = document.getElementById('setting-double-page');
    if (cb) {{
      cb.checked = !cb.checked;
      window.toggleDoublePageSetting();
    }}
  }};

  window.changeDefaultZoomSetting = function() {{
    const select = document.getElementById('setting-zoom-level');
    currentZoom = parseFloat(select.value);
    localStorage.setItem('mdserve-zoom-level', currentZoom);
    applyZoom(currentZoom);
  }};

  window.quickZoomIn = function() {{
    currentZoom = Math.round((currentZoom + 0.1) * 10) / 10;
    localStorage.setItem('mdserve-zoom-level', currentZoom);
    const select = document.getElementById('setting-zoom-level');
    if (select) select.value = currentZoom;
    applyZoom(currentZoom);
  }};

  window.quickZoomOut = function() {{
    currentZoom = Math.max(0.5, Math.round((currentZoom - 0.1) * 10) / 10);
    localStorage.setItem('mdserve-zoom-level', currentZoom);
    const select = document.getElementById('setting-zoom-level');
    if (select) select.value = currentZoom;
    applyZoom(currentZoom);
  }};

  function applyZoom(zoom) {{
    document.body.style.zoom = zoom;
    setTimeout(updateColumnWidth, 50); // Re-calculate any layout constraints if needed
  }}

  function updateDoublePageUI(enabled, gap) {{
    const layoutBtn = document.getElementById('layout-toggle-btn');
    if (layoutBtn) {{
      layoutBtn.innerHTML = enabled ? '📄 Vertical' : '📖 Horizontal';
    }}
    const layout = document.querySelector('.md-layout');
    if (!layout) return;
    if (enabled) {{
      layout.classList.add('double-page-mode');
      layout.style.setProperty('--col-gap', gap);
    }} else {{
      layout.classList.remove('double-page-mode');
      layout.style.removeProperty('--col-gap');
    }}
  }}

  function updateCrossCompletedUI(enabled) {{
    const layout = document.querySelector('.md-layout');
    if (!layout) return;
    if (enabled) {{
      layout.classList.add('crossed-ticked');
    }} else {{
      layout.classList.remove('crossed-ticked');
    }}
  }}

  function updateRenderCheckboxesUI(enabled) {{
    const layout = document.querySelector('.md-layout');
    if (!layout) return;
    if (enabled) {{
      layout.classList.add('render-checkboxes-active');
    }} else {{
      layout.classList.remove('render-checkboxes-active');
    }}
  }}

  function updateWideLayoutUI(enabled) {{
    const layout = document.querySelector('.md-layout');
    if (!layout) return;
    if (enabled) {{
      layout.classList.add('wide-layout-active');
    }} else {{
      layout.classList.remove('wide-layout-active');
    }}
  }}

  // Raw toggle
  window.toggleRawView = function() {{
    const isRaw = localStorage.getItem('mdserve-raw-view') === 'true';
    const nextRaw = !isRaw;
    localStorage.setItem('mdserve-raw-view', nextRaw);
    updateRawViewUI(nextRaw);
  }};

  function updateRawViewUI(isRaw) {{
    const mdBody = document.querySelector('.md-body');
    const rawWrap = document.getElementById('raw-content-wrap');
    const rawBtn = document.getElementById('raw-toggle-btn');
    const layout = document.querySelector('.md-layout');

    if (isRaw) {{
      if (mdBody) mdBody.style.display = 'none';
      if (rawWrap) rawWrap.style.display = 'block';
      if (layout) layout.classList.add('raw-active');
      if (rawBtn) {{
        rawBtn.classList.add('active');
        rawBtn.innerHTML = '👁 Rendered';
      }}
    }} else {{
      if (mdBody) mdBody.style.display = 'block';
      if (rawWrap) rawWrap.style.display = 'none';
      if (layout) layout.classList.remove('raw-active');
      if (rawBtn) {{
        rawBtn.classList.remove('active');
        rawBtn.innerHTML = '📄 Raw';
      }}
    }}
  }}

  // Arrow keys paging in double page mode
  document.addEventListener('keydown', (e) => {{
    const layout = document.querySelector('.md-layout');
    if (layout && layout.classList.contains('double-page-mode')) {{
      const mdBody = document.querySelector('.md-body');
      if (!mdBody || document.getElementById('raw-content-wrap').style.display === 'block') return;

      if (e.key === 'ArrowRight') {{
        e.preventDefault();
        const gap = parseInt(getComputedStyle(mdBody).getPropertyValue('--col-gap') || '60', 10);
        mdBody.scrollBy({{ left: mdBody.clientWidth + gap, behavior: 'smooth' }});
      }} else if (e.key === 'ArrowLeft') {{
        e.preventDefault();
        const gap = parseInt(getComputedStyle(mdBody).getPropertyValue('--col-gap') || '60', 10);
        mdBody.scrollBy({{ left: -(mdBody.clientWidth + gap), behavior: 'smooth' }});
      }}
    }}
  }});

  // Wheel horizontal paging / scroll mapping
  document.addEventListener('DOMContentLoaded', () => {{
    const mdBody = document.querySelector('.md-body');
    if (mdBody) {{
      mdBody.addEventListener('wheel', (e) => {{
        const layout = document.querySelector('.md-layout');
        if (!layout || !layout.classList.contains('double-page-mode')) return;
        if (document.getElementById('raw-content-wrap').style.display === 'block') return;

        const pagePagingSetting = localStorage.getItem('mdserve-page-paging') === 'true';

        if (pagePagingSetting) {{
          if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) return; // Let trackpad horizontal scroll natively
          e.preventDefault();
          if (isScrolling) return;

          const direction = e.deltaY > 0 ? 1 : -1;
          isScrolling = true;

          const gap = parseInt(getComputedStyle(mdBody).getPropertyValue('--col-gap') || '60', 10);
          mdBody.scrollBy({{
            left: direction * (mdBody.clientWidth + gap),
            behavior: 'smooth'
          }});

          setTimeout(() => {{
            isScrolling = false;
          }}, 400);
        }} else {{
          // Continuous scroll mode mapping from vertical to horizontal
          if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {{
            e.preventDefault();
            mdBody.scrollLeft += e.deltaY;
          }}
        }}
      }}, {{ passive: false }});
    }}
  }});

  // Copy file
  window.copyEntireFile = function() {{
    const rawData = document.getElementById('raw-markdown-data').textContent;
    navigator.clipboard.writeText(rawData).then(() => {{
      const copyBtn = document.getElementById('copy-btn');
      const originalText = copyBtn.innerHTML;
      copyBtn.innerHTML = '✓ Copied!';
      copyBtn.style.borderColor = 'var(--accent)';
      setTimeout(() => {{
        copyBtn.innerHTML = originalText;
        copyBtn.style.borderColor = '';
      }}, 2000);
    }}).catch(err => {{
      console.error('Failed to copy text: ', err);
    }});
  }};

  // Checkbox toggle API calls
  document.addEventListener('click', (e) => {{
    if (e.target && e.target.classList.contains('task-checkbox')) {{
      e.preventDefault();
      const cb = e.target;
      const idx = parseInt(cb.getAttribute('data-idx'), 10);

      const currentPath = window.location.pathname;
      fetch(currentPath, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          action: 'toggle_checkbox',
          index: idx
        }})
      }})
      .then(res => res.json())
      .then(data => {{
        if (data.success) {{
          cb.checked = !cb.checked;
          window.location.reload();
        }} else {{
          alert("Error: " + data.error);
        }}
      }})
      .catch(err => {{
        console.error("Error toggling checkbox:", err);
      }});
    }}
  }});

  window.apiToggleAll = function(checkAll) {{
    const currentPath = window.location.pathname;
    fetch(currentPath, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{
        action: 'toggle_all',
        value: checkAll
      }})
    }})
    .then(res => res.json())
    .then(data => {{
      if (data.success) {{
        window.location.reload();
      }} else {{
        alert("Error: " + data.error);
      }}
    }})
    .catch(err => {{
      console.error("Error toggling all checkboxes:", err);
    }});
  }};

  // Selection toggle
  let selectedCheckboxIndices = [];

  document.addEventListener('selectionchange', () => {{
    const selection = window.getSelection();
    if (selection.isCollapsed) {{
      selectedCheckboxIndices = [];
      hideFloatingToolbar();
      return;
    }}

    const range = selection.getRangeAt(0);
    const checkboxes = document.querySelectorAll('.task-checkbox');
    const tempIndices = [];

    checkboxes.forEach(cb => {{
      if (range.intersectsNode(cb)) {{
        const idx = parseInt(cb.getAttribute('data-idx'), 10);
        if (!isNaN(idx)) {{
          tempIndices.push(idx);
        }}
      }}
    }});

    selectedCheckboxIndices = tempIndices;

    if (selectedCheckboxIndices.length > 0) {{
      showFloatingToolbar(range);
    }} else {{
      hideFloatingToolbar();
    }}
  }});

  function showFloatingToolbar(range) {{
    const toolbar = document.getElementById('floating-selection-toolbar');
    if (!toolbar) return;

    const rect = range.getBoundingClientRect();
    toolbar.style.display = 'block';
    const countSpan = document.getElementById('selection-count');
    if (countSpan) countSpan.textContent = selectedCheckboxIndices.length;

    // Position toolbar above the selection
    const top = rect.top + window.scrollY - toolbar.offsetHeight - 8;
    const left = rect.left + window.scrollX + (rect.width / 2) - (toolbar.offsetWidth / 2);

    toolbar.style.top = `${{top}}px`;
    toolbar.style.left = `${{left}}px`;
  }}

  function hideFloatingToolbar() {{
    const toolbar = document.getElementById('floating-selection-toolbar');
    if (toolbar) toolbar.style.display = 'none';
  }}

  window.apiToggleSelection = function() {{
    if (selectedCheckboxIndices.length === 0) return;

    const currentPath = window.location.pathname;
    fetch(currentPath, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{
        action: 'toggle_selection',
        indices: selectedCheckboxIndices
      }})
    }})
    .then(res => res.json())
    .then(data => {{
      if (data.success) {{
        window.location.reload();
      }} else {{
        alert("Error: " + data.error);
      }}
    }})
    .catch(err => {{
      console.error("Error toggling selection:", err);
    }});
  }};

  // Mermaid render implementation
  let mermaidInitialized = false;
  window.renderMermaid = async function() {{
    const enabled = localStorage.getItem('mdserve-mermaid') === 'true';
    const containers = document.querySelectorAll('.mermaid-container');

    if (enabled && containers.length > 0) {{
      if (!mermaidInitialized) {{
        const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'default';
        mermaid.initialize({{
          startOnLoad: false,
          theme: theme,
          securityLevel: 'loose'
        }});
        mermaidInitialized = true;
      }}

      for (let i = 0; i < containers.length; i++) {{
        const container = containers[i];
        const rawCode = container.querySelector('.mermaid-raw code').textContent;
        const renderedDiv = container.querySelector('.mermaid-rendered');
        const rawDiv = container.querySelector('.mermaid-raw');

        rawDiv.style.display = 'none';
        renderedDiv.style.display = 'block';

        if (!renderedDiv.dataset.rendered || renderedDiv.dataset.theme !== document.documentElement.getAttribute('data-theme')) {{
          try {{
            renderedDiv.innerHTML = '';
            const id = 'mermaid-svg-' + i;
            const {{ svg }} = await mermaid.render(id, rawCode);
            renderedDiv.innerHTML = svg;
            renderedDiv.dataset.rendered = 'true';
            renderedDiv.dataset.theme = document.documentElement.getAttribute('data-theme');
          }} catch (err) {{
            renderedDiv.innerHTML = `<pre class="mermaid-error" style="color: var(--accent2); background: var(--tag-bg); border: 1px solid var(--border); padding: 10px; border-radius: var(--radius); overflow-x: auto;">${{err.message}}</pre>`;
          }}
        }}
      }}
    }} else {{
      containers.forEach(container => {{
        container.querySelector('.mermaid-raw').style.display = 'block';
        container.querySelector('.mermaid-rendered').style.display = 'none';
      }});
    }}
  }};
  
  // File manager and editor APIs
  function postApi(path, data) {{
    return fetch(path, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(data)
    }}).then(res => res.json()).then(data => {{
      if (data.success) {{ window.location.reload(); }}
      else {{ alert("Error: " + data.error); }}
    }}).catch(err => alert("Request failed: " + err));
  }}
  
  window.apiCreate = function(isDir) {{
    const name = prompt("Enter " + (isDir ? "folder" : "file") + " name:");
    if (!name) return;
    const currentPath = window.location.pathname.replace(/\\/$/, '') + '/' + name;
    postApi(currentPath, {{ action: 'create', is_dir: isDir }});
  }};
  
  window.apiDelete = function(path, name) {{
    if (!confirm("Are you sure you want to delete '" + name + "'?")) return;
    postApi(path, {{ action: 'delete' }});
  }};
  
  window.apiRename = function(path, oldName) {{
    const newName = prompt("Enter new name for '" + oldName + "':", oldName);
    if (!newName || newName === oldName) return;
    postApi(path, {{ action: 'rename', new_name: newName }});
  }};
  
  window.apiDuplicate = function(path, name) {{
    const newName = prompt("Enter new name for duplicate of '" + name + "':", "copy_of_" + name);
    if (!newName || newName === name) return;
    postApi(path, {{ action: 'duplicate', new_name: newName }});
  }};
  
  window.toggleEditor = function() {{
    const mdBody = document.querySelector('.md-body');
    const rawContentWrap = document.getElementById('raw-content-wrap');
    if (!mdBody || !rawContentWrap) return;
    
    // Instead of raw view, we want an editor view
    let editorWrap = document.getElementById('editor-wrap');
    if (!editorWrap) {{
      editorWrap = document.createElement('div');
      editorWrap.id = 'editor-wrap';
      editorWrap.style.marginTop = '20px';
      
      const textarea = document.createElement('textarea');
      textarea.id = 'editor-textarea';
      textarea.style.width = '100%';
      textarea.style.height = '60vh';
      textarea.style.background = 'var(--code-bg)';
      textarea.style.color = 'var(--text)';
      textarea.style.border = '1px solid var(--border)';
      textarea.style.borderRadius = 'var(--radius)';
      textarea.style.padding = '16px';
      textarea.style.fontFamily = "'JetBrains Mono', monospace";
      textarea.style.fontSize = '13px';
      textarea.style.lineHeight = '1.6';
      
      const rawData = document.getElementById('raw-markdown-data');
      if (rawData) textarea.value = rawData.textContent;
      
      const actions = document.createElement('div');
      actions.style.marginTop = '12px';
      actions.style.display = 'flex';
      actions.style.gap = '8px';
      
      const saveBtn = document.createElement('button');
      saveBtn.className = 'theme-btn';
      saveBtn.textContent = '💾 Save';
      saveBtn.onclick = () => {{
        const path = window.location.pathname;
        postApi(path, {{ action: 'save', content: document.getElementById('editor-textarea').value }});
      }};
      
      const cancelBtn = document.createElement('button');
      cancelBtn.className = 'theme-btn';
      cancelBtn.textContent = '✕ Cancel';
      cancelBtn.onclick = window.toggleEditor;
      
      actions.appendChild(saveBtn);
      actions.appendChild(cancelBtn);
      
      editorWrap.appendChild(textarea);
      editorWrap.appendChild(actions);
      
      mdBody.parentNode.insertBefore(editorWrap, rawContentWrap);
    }}
    
    if (editorWrap.style.display === 'none' || !editorWrap.style.display) {{
      mdBody.style.display = 'none';
      if (rawContentWrap) rawContentWrap.style.display = 'none';
      editorWrap.style.display = 'block';
    }} else {{
      editorWrap.style.display = 'none';
      mdBody.style.display = 'block';
      // Restoring wide mode / raw view logic could be complex here, so just keep simple
      if (localStorage.getItem('mdserve-raw') === 'true' && rawContentWrap) {{
        rawContentWrap.style.display = 'block';
      }}
    }}
  }};
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


def parse_and_modify_markdown(fs_path: Path, action_fn) -> tuple[bool, str]:
    try:
        text = fs_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return False, str(e)

    lines = text.splitlines(keepends=True)
    in_code_block = False
    checkbox_idx = 0
    modified = False

    cb_pattern = re.compile(r'^(\s*[-*+]\s+|\s*\d+\.\s+)\[([ xX])\]')

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue

        if not in_code_block:
            match = cb_pattern.match(line)
            if match:
                prefix = match.group(1)
                val = match.group(2)
                
                new_val, line_modified = action_fn(checkbox_idx, val)
                if line_modified:
                    start_idx = len(prefix) + 1
                    line = line[:start_idx] + new_val + line[start_idx+1:]
                    modified = True
                checkbox_idx += 1
        
        new_lines.append(line)

    if modified:
        try:
            fs_path.write_text("".join(new_lines), encoding="utf-8")
            return True, ""
        except Exception as e:
            return False, str(e)
    
    return True, ""


def toggle_markdown_checkbox(fs_path: Path, target_idx: int) -> tuple[bool, str]:
    def action(current_idx, val):
        if current_idx == target_idx:
            new_val = " " if val.lower() == "x" else "x"
            return new_val, True
        return val, False
    return parse_and_modify_markdown(fs_path, action)


def toggle_all_checkboxes(fs_path: Path, check_all: bool) -> tuple[bool, str]:
    target_val = "x" if check_all else " "
    def action(current_idx, val):
        if val != target_val:
            return target_val, True
        return val, False
    return parse_and_modify_markdown(fs_path, action)


def toggle_checkboxes_by_indices(fs_path: Path, indices: list[int]) -> tuple[bool, str]:
    indices_set = set(indices)
    def action(current_idx, val):
        if current_idx in indices_set:
            new_val = " " if val.lower() == "x" else "x"
            return new_val, True
        return val, False
    return parse_and_modify_markdown(fs_path, action)


li_cb_pattern = re.compile(r'(<li>(?:<p>)?)\[([ xX])\]')

def replace_checkboxes_in_html(html_content: str) -> str:
    count = [0]
    
    def repl(match):
        prefix = match.group(1)
        val = match.group(2)
        checked = "checked" if val.lower() == "x" else ""
        idx = count[0]
        count[0] += 1
        char = "x" if val.lower() == "x" else " "
        return f'{prefix}<span class="task-wrapper" data-idx="{idx}"><input type="checkbox" class="task-checkbox" data-idx="{idx}" {checked}><span class="task-raw-text">[{char}]</span></span>'
        
    return li_cb_pattern.sub(repl, html_content)


def extract_mermaid_blocks(text: str) -> tuple[str, list[str]]:
    pattern = re.compile(r'^```mermaid\s*\n(.*?)\n```', re.DOTALL | re.MULTILINE)
    placeholders = []
    def replace(match):
        code = match.group(1)
        idx = len(placeholders)
        placeholders.append(code)
        return f"<!-- MERMAID_PLACEHOLDER_{idx} -->"
        
    processed_text = pattern.sub(replace, text)
    return processed_text, placeholders


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
              <td></td>
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
          <td style="display: flex; gap: 4px;">
            <button class="theme-btn" style="padding: 2px 6px; font-size: 10px;" onclick="apiRename('{link.rstrip("/")}', '{html.escape(name)}')">Ren</button>
            <button class="theme-btn" style="padding: 2px 6px; font-size: 10px;" onclick="apiDuplicate('{link.rstrip("/")}', '{html.escape(name)}')">Dup</button>
            <button class="theme-btn" style="padding: 2px 6px; font-size: 10px;" onclick="apiDelete('{link.rstrip("/")}', '{html.escape(name)}')">Del</button>
          </td>
        </tr>""")

    count = len([e for e in entries if e[1] != ".."])
    folder_name = fs_path.name or "/"

    body = f"""
{_topbar(_breadcrumb(urlpath))}
<main class="container">
  <div class="path-header">
    <h1>{html.escape(folder_name)}</h1>
    <span class="stat-badge">{count} items</span>
    <div style="flex-grow: 1;"></div>
    <button class="theme-btn" onclick="apiCreate(false)">+ File</button>
    <button class="theme-btn" onclick="apiCreate(true)">+ Folder</button>
  </div>
  <table class="file-table">
    <thead>
      <tr>
        <th>Name</th>
        <th>Size</th>
        <th>Modified</th>
        <th>Actions</th>
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

    # 1. Preprocess raw markdown to extract Mermaid blocks
    processed_text, mermaid_blocks = extract_mermaid_blocks(text)

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
    content_html = md.convert(processed_text)
    
    # 2. Render task checkboxes in HTML
    content_html = replace_checkboxes_in_html(content_html)

    # 3. Restore Mermaid blocks
    for idx, code in enumerate(mermaid_blocks):
        placeholder = f"<!-- MERMAID_PLACEHOLDER_{idx} -->"
        escaped_code = html.escape(code)
        container = f"""<div class="mermaid-container" data-idx="{idx}">
          <pre class="mermaid-raw"><code>{escaped_code}</code></pre>
          <div class="mermaid-rendered" style="display: none;"></div>
        </div>"""
        if f"<p>{placeholder}</p>" in content_html:
            content_html = content_html.replace(f"<p>{placeholder}</p>", container)
        else:
            content_html = content_html.replace(placeholder, container)

    toc_html = getattr(md, "toc", "")
    has_toc = bool(toc_html.strip()) and "<li>" in toc_html

    # Settings dropdown HTML
    settings_dropdown = """<div class="settings-dropdown" id="settings-dropdown">
      <div class="settings-title">Viewer Settings</div>
      
      <div class="settings-section">
        <div class="settings-label">General</div>
        <div class="settings-row">
          <label for="setting-double-page">
            <input type="checkbox" id="setting-double-page" onchange="toggleDoublePageSetting()">
            Double Page Mode
          </label>
        </div>
        <div class="settings-row indent" id="col-gap-row" style="display: none;">
          <span class="settings-sublabel">Column Gap</span>
          <select id="setting-col-gap" onchange="changeColGapSetting()">
            <option value="40px">Narrow (40px)</option>
            <option value="60px" selected>Normal (60px)</option>
            <option value="80px">Wide (80px)</option>
          </select>
        </div>
        <div class="settings-row indent" id="page-paging-row" style="display: none;">
          <label for="setting-page-paging">
            <input type="checkbox" id="setting-page-paging" onchange="togglePagePagingSetting()">
            Page-by-page scrolling
          </label>
        </div>
        <div class="settings-row">
          <span class="settings-sublabel">Default Zoom</span>
          <select id="setting-zoom-level" onchange="changeDefaultZoomSetting()">
            <option value="0.5">50%</option>
            <option value="0.6">60%</option>
            <option value="0.7">70%</option>
            <option value="0.8">80%</option>
            <option value="0.9">90%</option>
            <option value="1" selected>100%</option>
            <option value="1.1">110%</option>
            <option value="1.2">120%</option>
            <option value="1.3">130%</option>
            <option value="1.4">140%</option>
            <option value="1.5">150%</option>
            <option value="1.6">160%</option>
            <option value="1.7">170%</option>
            <option value="1.8">180%</option>
            <option value="1.9">190%</option>
            <option value="2">200%</option>
          </select>
        </div>
        <div class="settings-row">
          <label for="setting-wide-layout">
            <input type="checkbox" id="setting-wide-layout" onchange="toggleWideLayoutSetting()">
            Wide Layout (Fit Screen)
          </label>
        </div>
        <div class="settings-row">
          <label for="setting-reading-progress">
            <input type="checkbox" id="setting-reading-progress" onchange="toggleReadingProgressSetting()">
            Reading progress HUD
          </label>
        </div>
        <div class="settings-row">
          <label for="setting-mermaid">
            <input type="checkbox" id="setting-mermaid" onchange="toggleMermaidSetting()">
            Render Mermaid
          </label>
        </div>
      </div>

      <div class="settings-section">
        <div class="settings-label">Tasks / Checklist</div>
        <div class="settings-row">
          <label for="setting-render-checkboxes">
            <input type="checkbox" id="setting-render-checkboxes" onchange="toggleRenderCheckboxesSetting()">
            Render checkboxes
          </label>
        </div>
        <div class="settings-row">
          <label for="setting-cross-completed">
            <input type="checkbox" id="setting-cross-completed" onchange="toggleCrossCompletedSetting()">
            Cross completed tasks
          </label>
        </div>
        <div class="settings-actions">
          <button class="settings-btn" onclick="apiToggleAll(true)">☑ Tick All</button>
          <button class="settings-btn" onclick="apiToggleAll(false)">☐ Untick All</button>
        </div>
      </div>
    </div>"""

    toc_controls = ""
    sidebar = ""
    layout_class = "md-layout"
    if has_toc:
        toc_controls = """<div class="sidebar-ctrl-group">
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

    sidebar_controls = f"""{toc_controls}
    <button class="theme-btn" id="zoom-out-btn" onclick="quickZoomOut()" title="Zoom Out">🔍-</button>
    <button class="theme-btn" id="zoom-in-btn" onclick="quickZoomIn()" title="Zoom In">🔍+</button>
    <button class="theme-btn" id="copy-btn" onclick="copyEntireFile()" title="Copy raw markdown to clipboard">📋 Copy</button>
    <button class="theme-btn" id="layout-toggle-btn" onclick="toggleLayoutModeQuick()" title="Toggle layout mode">📖 Horizontal</button>
    <button class="theme-btn" id="raw-toggle-btn" onclick="toggleRawView()" title="Toggle raw markdown view">📄 Raw</button>
    <button class="theme-btn" onclick="toggleEditor()" title="Edit markdown file">✏️ Edit</button>
    <div class="settings-container">
      <button class="theme-btn" id="settings-btn" onclick="toggleSettingsDropdown(event)" title="Viewer Settings">⚙ Settings</button>
      {settings_dropdown}
    </div>"""

    parent = "/" + "/".join(urlpath.strip("/").split("/")[:-1])
    if parent != "/":
        parent += "/"

    raw_markdown_escaped = html.escape(text)

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
    <div class="raw-content-wrap" id="raw-content-wrap" style="display: none;">
      <pre><code class="language-markdown">{raw_markdown_escaped}</code></pre>
    </div>
  </div>
</div>
<div id="reading-progress-indicator" class="reading-progress" style="display: none;">
  <span id="reading-page-info"></span>
  <span class="dot" id="reading-progress-dot">·</span>
  <span id="reading-percent-info"></span>
</div>
<div id="floating-selection-toolbar" style="display: none; position: absolute; z-index: 1000; background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.25);">
  <button class="theme-btn" onclick="apiToggleSelection()" style="border: none; background: transparent; padding: 4px 8px; font-size: 11px;">
    ☑ Tick Selection (<span id="selection-count">0</span>)
  </button>
</div>
<script type="text/plain" id="raw-markdown-data">{raw_markdown_escaped}</script>
"""

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

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        urlpath = urllib.parse.unquote(parsed.path)
        fs_path = self.base_dir / urlpath.lstrip("/")

        try:
            fs_path = fs_path.resolve()
            fs_path.relative_to(self.base_dir.resolve())
        except (ValueError, OSError):
            self._404()
            return

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        import json
        try:
            req = json.loads(post_data.decode('utf-8'))
        except Exception:
            self._send_json({"error": "Invalid JSON"}, status=400)
            return

        action = req.get("action")
        
        if action == "create":
            is_dir = req.get("is_dir", False)
            try:
                if is_dir:
                    fs_path.mkdir(parents=True, exist_ok=True)
                else:
                    fs_path.parent.mkdir(parents=True, exist_ok=True)
                    fs_path.touch(exist_ok=True)
                self._send_json({"success": True})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return
            
        elif action == "delete":
            import shutil
            try:
                if fs_path.is_dir():
                    shutil.rmtree(fs_path)
                elif fs_path.exists():
                    fs_path.unlink()
                self._send_json({"success": True})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return
            
        elif action == "rename":
            new_name = req.get("new_name")
            if not new_name:
                self._send_json({"error": "Missing new_name"}, status=400)
                return
            new_path = fs_path.parent / new_name
            try:
                new_path.resolve().relative_to(self.base_dir.resolve())
                fs_path.rename(new_path)
                self._send_json({"success": True})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return
            
        elif action == "duplicate":
            import shutil
            new_name = req.get("new_name")
            if not new_name:
                self._send_json({"error": "Missing new_name"}, status=400)
                return
            new_path = fs_path.parent / new_name
            try:
                new_path.resolve().relative_to(self.base_dir.resolve())
                if fs_path.is_dir():
                    shutil.copytree(fs_path, new_path)
                else:
                    shutil.copy2(fs_path, new_path)
                self._send_json({"success": True})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return
            
        elif action == "save":
            content = req.get("content")
            if content is None:
                self._send_json({"error": "Missing content"}, status=400)
                return
            try:
                fs_path.write_text(content, encoding="utf-8")
                self._send_json({"success": True})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        # Legacy actions (toggle checkboxes) require existing md file
        if not fs_path.is_file() or fs_path.suffix.lower() not in (".md", ".markdown"):
            self._404()
            return

        if action == "toggle_checkbox":
            idx = req.get("index")
            if idx is None:
                self._send_json({"error": "Missing index"}, status=400)
                return
            success, msg = toggle_markdown_checkbox(fs_path, idx)
            if success:
                self._send_json({"success": True})
            else:
                self._send_json({"error": msg}, status=500)
        elif action == "toggle_all":
            value = req.get("value")
            success, msg = toggle_all_checkboxes(fs_path, value)
            if success:
                self._send_json({"success": True})
            else:
                self._send_json({"error": msg}, status=500)
        elif action == "toggle_selection":
            indices = req.get("indices")
            if not isinstance(indices, list):
                self._send_json({"error": "Indices must be a list"}, status=400)
                return
            success, msg = toggle_checkboxes_by_indices(fs_path, indices)
            if success:
                self._send_json({"success": True})
            else:
                self._send_json({"error": msg}, status=500)
        else:
            self._send_json({"error": f"Unknown action: {action}"}, status=400)

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
