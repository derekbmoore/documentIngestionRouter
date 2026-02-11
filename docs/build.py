#!/usr/bin/env python3
"""
Static site builder for Document Ingestion Router docs.
Converts Markdown files → HTML using a custom template.
No external dependencies required (uses Python stdlib markdown-like processing).
"""

import os
import re
import sys
import shutil
import html

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(DOCS_DIR, "_template")
OUT_DIR = os.path.join(DOCS_DIR, "_site")
BASE_URL = os.environ.get("BASE_URL", "/documentIngestionRouter")
SITE_URL = "https://derekbmoore.github.io"

# Page metadata extracted from YAML front matter
PAGES = []


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML front matter and body from markdown content."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            meta = {}
            for line in parts[1].strip().split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    val = val.strip().strip('"').strip("'")
                    # Handle multi-line (>-) by just taking what we have
                    meta[key.strip()] = val
            return meta, parts[2].strip()
    return {}, content


def strip_jekyll_classes(text: str) -> str:
    """Remove Jekyll/Kramdown class annotations like {: .fs-9 }."""
    return re.sub(r'\{:\s*[^}]+\}', '', text)


def md_to_html(md: str) -> str:
    """Convert markdown to HTML (lightweight, no dependencies)."""
    md = strip_jekyll_classes(md)
    lines = md.split("\n")
    out = []
    in_code = False
    code_lang = ""
    code_lines = []
    in_table = False
    table_lines = []
    in_list = False
    list_lines = []
    in_details = False

    def flush_table():
        nonlocal table_lines, in_table
        if not table_lines:
            return ""
        rows = []
        for i, row in enumerate(table_lines):
            cells = [c.strip() for c in row.strip("|").split("|")]
            # Skip separator row
            if all(re.match(r'^[-:]+$', c) for c in cells):
                continue
            tag = "th" if i == 0 else "td"
            cells_html = "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells)
            rows.append(f"<tr>{cells_html}</tr>")
        table_lines = []
        in_table = False
        return f'<div class="table-wrap"><table>{"".join(rows)}</table></div>'

    def flush_list():
        nonlocal list_lines, in_list
        if not list_lines:
            return ""
        items = "".join(f"<li>{inline(l)}</li>" for l in list_lines)
        list_lines = []
        in_list = False
        return f"<ul>{items}</ul>"

    def inline(text: str) -> str:
        """Process inline markdown."""
        # Images
        text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', text)
        # Links
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        # Bold + italic
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Italic
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        # Inline code
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        # Em dash
        text = text.replace(' — ', ' — ')
        return text

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip details/TOC blocks (Jekyll specific)
        if '<details' in line or '{:toc}' in line or '1. TOC' in line:
            i += 1
            continue
        if '</details>' in line:
            i += 1
            continue
        if line.strip().startswith('{: .text-delta'):
            i += 1
            continue
        if line.strip() == '{: .no_toc }':
            i += 1
            continue
        if '<summary>' in line:
            i += 1
            continue

        # Code blocks
        if line.strip().startswith("```"):
            if in_code:
                escaped = html.escape("\n".join(code_lines))
                lang_class = f' class="language-{code_lang}"' if code_lang else ''
                out.append(f'<pre><code{lang_class}>{escaped}</code></pre>')
                code_lines = []
                in_code = False
            else:
                # Flush any open blocks
                if in_table:
                    out.append(flush_table())
                if in_list:
                    out.append(flush_list())
                in_code = True
                code_lang = line.strip().replace("```", "").strip()
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # Table rows
        if "|" in line and line.strip().startswith("|"):
            if in_list:
                out.append(flush_list())
            in_table = True
            table_lines.append(line)
            i += 1
            continue
        elif in_table:
            out.append(flush_table())

        # List items
        if re.match(r'^\s*[-*]\s+', line):
            if in_table:
                out.append(flush_table())
            in_list = True
            list_lines.append(re.sub(r'^\s*[-*]\s+', '', line))
            i += 1
            continue
        elif in_list and line.strip() == "":
            out.append(flush_list())
            i += 1
            continue
        elif in_list and not line.startswith(" "):
            out.append(flush_list())

        # Numbered list
        if re.match(r'^\s*\d+\.\s+', line):
            content = re.sub(r'^\s*\d+\.\s+', '', line)
            out.append(f"<ol><li>{inline(content)}</li></ol>")
            i += 1
            continue

        # Headings
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            if in_list:
                out.append(flush_list())
            level = len(m.group(1))
            text = m.group(2)
            slug = re.sub(r'[^\w\s-]', '', text.lower()).strip().replace(' ', '-')
            out.append(f'<h{level} id="{slug}">{inline(text)}</h{level}>')
            i += 1
            continue

        # Horizontal rule
        if re.match(r'^---+$', line.strip()):
            i += 1
            continue

        # Empty line
        if line.strip() == "":
            i += 1
            continue

        # Paragraph
        if in_list:
            out.append(flush_list())
        out.append(f"<p>{inline(line)}</p>")
        i += 1

    # Flush remaining
    if in_table:
        out.append(flush_table())
    if in_list:
        out.append(flush_list())

    return "\n".join(out)


def build():
    """Build the static site."""
    # Clean output
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR, exist_ok=True)

    # Read template
    template_path = os.path.join(TEMPLATE_DIR, "template.html")
    with open(template_path, "r") as f:
        template = f.read()

    # Copy CSS
    css_src = os.path.join(TEMPLATE_DIR, "style.css")
    css_dst = os.path.join(OUT_DIR, "style.css")
    shutil.copy2(css_src, css_dst)

    # Copy assets
    assets_src = os.path.join(DOCS_DIR, "assets")
    assets_dst = os.path.join(OUT_DIR, "assets")
    if os.path.exists(assets_src):
        if os.path.exists(assets_dst):
            shutil.rmtree(assets_dst)
        shutil.copytree(assets_src, assets_dst)

    # Collect pages
    pages = []
    for fname in os.listdir(DOCS_DIR):
        if not fname.endswith(".md"):
            continue
        filepath = os.path.join(DOCS_DIR, fname)
        with open(filepath, "r") as f:
            content = f.read()
        meta, body = parse_frontmatter(content)
        slug = fname.replace(".md", "")
        if slug == "index":
            slug = ""
        pages.append({
            "title": meta.get("title", fname.replace(".md", "").replace("-", " ").title()),
            "nav_order": int(meta.get("nav_order", 99)),
            "slug": slug,
            "body": body,
            "filename": fname,
        })

    pages.sort(key=lambda p: p["nav_order"])

    # Build nav HTML
    nav_items = []
    for p in pages:
        href = f'{BASE_URL}/' if p["slug"] == "" else f'{BASE_URL}/{p["slug"]}.html'
        nav_items.append(
            f'<a href="{href}" class="nav-link" data-page="{p["slug"]}">'
            f'{p["title"]}</a>'
        )
    nav_html = "\n".join(nav_items)

    # Build each page
    for p in pages:
        body_html = md_to_html(p["body"])

        page_html = template.replace("{{TITLE}}", p["title"])
        page_html = page_html.replace("{{NAV}}", nav_html)
        page_html = page_html.replace("{{CONTENT}}", body_html)
        page_html = page_html.replace("{{CONTENT}}", body_html)
        page_html = page_html.replace("{{BASE_URL}}", BASE_URL)
        page_html = page_html.replace("{{SITE_URL}}", SITE_URL)
        page_html = page_html.replace("{{CURRENT_PAGE}}", p["slug"])

        out_name = "index.html" if p["slug"] == "" else f'{p["slug"]}.html'
        out_path = os.path.join(OUT_DIR, out_name)
        with open(out_path, "w") as f:
            f.write(page_html)
        print(f"  ✓ {out_name}")

    print(f"\nBuilt {len(pages)} pages → {OUT_DIR}")


if __name__ == "__main__":
    build()
