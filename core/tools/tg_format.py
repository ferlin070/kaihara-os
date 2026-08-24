"""
Telegram Message Formatter — convert markdown to beautiful Telegram HTML.
Tables → aligned monospace, headers → emoji bold, code → pre blocks.
"""


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _format_table_block(lines: list[str]) -> str:
    """Convert markdown table lines to aligned monospace block."""
    rows = []
    max_cols = 0
    for ln in lines:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        # Skip separator rows (---|---)
        if all(set(c) <= {"-", ":", " "} for c in cells if c):
            continue
        rows.append(cells)
        max_cols = max(max_cols, len(cells))
    if not rows:
        return ""
    # Pad rows
    for r in rows:
        while len(r) < max_cols:
            r.append("")
    # Compute widths
    widths = [0] * max_cols
    for r in rows:
        for i, c in enumerate(r):
            clean = c.replace("**", "").replace("`", "")
            widths[i] = max(widths[i], len(clean))
    # Format
    out_lines = []
    for ri, r in enumerate(rows):
        line = " │ ".join(
            c.ljust(widths[i])[:widths[i]] for i, c in enumerate(r))
        out_lines.append("  " + line.rstrip())
        if ri == 0:
            sep = "─┼─".join("─" * w for w in widths)
            out_lines.append("  ┌─" + sep + "─┐" if False else "  " + "─┼─".join("─" * (w + 2) for w in widths))
    return "\n".join(out_lines)


def md_to_telegram_html(md: str, max_len: int = 3800) -> str:
    """Convert markdown to Telegram-safe HTML with pretty tables."""
    import re as _re

    text = _escape(md)
    lines = text.split("\n")
    out = []
    table_buf: list[str] = []
    in_code = False

    def flush_table():
        nonlocal table_buf
        if table_buf:
            block = _format_table_block(table_buf)
            if block:
                out.append(f"<pre>{block}</pre>")
            table_buf = []

    for ln in lines:
        stripped = ln.strip()
        # Code fences
        if stripped.startswith("```"):
            flush_table()
            if in_code:
                out.append("</pre>")
                in_code = False
            else:
                out.append("<pre>")
                in_code = True
            continue
        if in_code:
            out.append(ln.replace("&", "&amp;")
                        .replace("<", "&lt;").replace(">", "&gt;"))
            continue
        # Table rows
        if stripped.startswith("|") and "|" in stripped[1:]:
            table_buf.append(ln)
            continue
        flush_table()
        if not stripped:
            out.append("")
            continue
        # Headers: ## Title → bold caps with divider
        h = _re.match(r"^(#{1,6})\s+(.*)", stripped)
        if h:
            level = len(h.group(1))
            title = h.group(2).strip()
            if level <= 2:
                out.append(f"\n<b>━━━ {_re.sub(r'[*_`]', '', title.upper())} ━━━</b>")
            else:
                out.append(f"<b>▸ {title}</b>")
            continue
        # Blockquote
        if stripped.startswith(">"):
            out.append("💡 " + stripped.lstrip("> "))
            continue
        # Bullets: - item → • item
        bullet = _re.match(r"^[-*]\s+(.*)", stripped)
        if bullet:
            out.append("• " + _inline(bullet.group(1)))
            continue
        numbered = _re.match(r"^(\d+)\.\s+(.*)", stripped)
        if numbered:
            out.append(f"{numbered.group(1)}. " + _inline(numbered.group(2)))
            continue
        out.append(_inline(stripped))

    flush_table()
    if in_code:
        out.append("</pre>")

    html = "\n".join(out)
    html = _re.sub(r"\n{3,}", "\n\n", html)
    return html[:max_len]


def _inline(s: str) -> str:
    """Inline markdown → HTML (bold/italic/code/strikethrough)."""
    import re as _re
    s = _re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = _re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", s)
    s = _re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = _re.sub(r"~~(.+?)~~", r"<s>\1</s>", s)
    s = _re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def wrap_reply(content_html: str, agent: str = "Kaihara",
               route: str = "", provider: str = "") -> str:
    """Wrap formatted content with Kaihara-style header/footer."""
    header = f"🤖 <b>{agent.upper()}</b>"
    div = "────────────────────"
    parts = [header, div, content_html]
    meta_bits = []
    if route:
        meta_bits.append(f"route: {route}")
    if provider:
        meta_bits.append(f"via {provider}")
    if meta_bits:
        parts += [div, "<i>" + " · ".join(meta_bits) + "</i>"]
    return "\n".join(parts)
