import html
from pathlib import Path
from pyrogram import Client, types
from .image_opt import create_webp_thumbnail


def rich_text_to_html(t) -> str:
    if t is None:
        return ""
    if isinstance(t, str):
        return html.escape(t)
    if isinstance(t, (list, types.List)):
        return "".join(rich_text_to_html(sub) for sub in t)

    cls_name = type(t).__name__
    if cls_name == "RichTextBold":
        return f"<b>{rich_text_to_html(t.text)}</b>"
    if cls_name == "RichTextItalic":
        return f"<i>{rich_text_to_html(t.text)}</i>"
    if cls_name == "RichTextUnderline":
        return f"<u>{rich_text_to_html(t.text)}</u>"
    if cls_name == "RichTextStrikethrough":
        return f"<del>{rich_text_to_html(t.text)}</del>"
    if cls_name == "RichTextCode":
        return f"<code>{rich_text_to_html(t.text)}</code>"
    if cls_name in ("RichTextUrl", "RichTextAnchorLink"):
        return f'<a href="{html.escape(t.url)}">{rich_text_to_html(t.text)}</a>'
    if cls_name == "RichTextEmailAddress":
        return f'<a href="mailto:{html.escape(t.email)}">{rich_text_to_html(t.text)}</a>'
    if cls_name == "RichTextPhoneNumber":
        return f'<a href="tel:{html.escape(t.phone)}">{rich_text_to_html(t.text)}</a>'
    if cls_name == "RichTextButton":
        btn = getattr(t, "button", None)
        if btn:
            btn_text = rich_text_to_html(getattr(btn, "text", "Button"))
            url = getattr(btn, "url", getattr(btn, "copy_text", "#"))
            if hasattr(url, "text"):
                url = url.text
            style_name = str(getattr(btn, "style", "")).split(".")[-1].lower()
            return f'<a class="rich-button {style_name}" href="{html.escape(str(url))}">{btn_text}</a>'
        return ""
    if cls_name == "RichTextMathematicalExpression":
        expr = getattr(t, "expression", "")
        return f'<code class="math">{html.escape(expr)}</code>'
    if cls_name == "RichTextCustomEmoji":
        cid = getattr(t, "custom_emoji_id", "")
        return f'<i class="custom-emoji" emoji-src="emoji/{cid}"></i>'
    if cls_name == "RichTextSpoiler":
        return f'<span class="spoiler"><span>{rich_text_to_html(t.text)}</span></span>'
    if cls_name == "RichTextSubscript":
        return f'<sub>{rich_text_to_html(t.text)}</sub>'
    if cls_name == "RichTextSuperscript":
        return f'<sup>{rich_text_to_html(t.text)}</sup>'
    if cls_name == "RichTextMarked":
        return f'<mark>{rich_text_to_html(t.text)}</mark>'

    if hasattr(t, "text"):
        return rich_text_to_html(t.text)
    return html.escape(str(t))


async def rich_blocks_to_html(blocks: list, app: Client, msg_id: int, base_path: Path, media_path: Path) -> str:
    html_parts = []
    for b in blocks:
        cls_name = type(b).__name__
        if cls_name == "RichBlockParagraph":
            t = rich_text_to_html(getattr(b, "text", None))
            if t.strip():
                html_parts.append(f"<p>{t}</p>")
        elif cls_name == "RichBlockSectionHeading":
            size = getattr(b, "size", 1)
            tag = "h2" if size == 1 else "h3"
            html_parts.append(f"<{tag}>{rich_text_to_html(b.text)}</{tag}>")
        elif cls_name in ("RichBlockBlockQuotation", "RichBlockPullQuotation", "RichBlockExpandableBlockQuotation"):
            cls_attr = ""
            if cls_name == "RichBlockPullQuotation":
                cls_attr = ' class="pullquote"'
            elif cls_name == "RichBlockExpandableBlockQuotation":
                cls_attr = ' class="expandable" expandable'
            if hasattr(b, "blocks") and b.blocks:
                t = await rich_blocks_to_html(b.blocks, app, msg_id, base_path, media_path)
            else:
                t = rich_text_to_html(getattr(b, "text", ""))
            credit = rich_text_to_html(getattr(b, "credit", None))
            cite = f"<cite>{credit}</cite>" if credit else ""
            html_parts.append(f"<blockquote{cls_attr}>{t}{cite}</blockquote>")
        elif cls_name == "RichBlockList":
            items = []
            is_check = any(getattr(item, "has_checkbox", False) for item in b.items)
            is_ordered = False
            for item in b.items:
                if getattr(item, "type", "") == "1" or str(getattr(item, "label", "")).isdigit():
                    is_ordered = True
                inner = await rich_blocks_to_html(item.blocks, app, msg_id, base_path, media_path) if hasattr(item, "blocks") else ""
                if getattr(item, "has_checkbox", False):
                    checked = "checked" if getattr(item, "is_checked", False) else ""
                    items.append(f'<li class="check-item"><input type="checkbox" {checked} disabled> {inner}</li>')
                else:
                    items.append(f"<li>{inner}</li>")
            tag = "ol" if is_ordered else "ul"
            cls = ' class="checklist"' if is_check else ""
            html_parts.append(f"<{tag}{cls}>{''.join(items)}</{tag}>")
        elif cls_name == "RichBlockDetails":
            summary = rich_text_to_html(getattr(b, "summary", "Details"))
            inner = await rich_blocks_to_html(b.blocks, app, msg_id, base_path, media_path) if hasattr(b, "blocks") else ""
            open_attr = " open" if getattr(b, "is_open", False) else ""
            html_parts.append(f"<details{open_attr}><summary>{summary}</summary>{inner}</details>")
        elif cls_name == "RichBlockDivider":
            html_parts.append("<hr>")
        elif cls_name == "RichBlockPreformatted":
            lang = getattr(b, "language", "")
            attr = f' language="{html.escape(lang)}"' if lang else ""
            html_parts.append(f"<pre{attr}><code>{rich_text_to_html(b.text)}</code></pre>")
        elif cls_name == "RichBlockFooter":
            html_parts.append(f'<footer class="rich-footer">{rich_text_to_html(b.text)}</footer>')
        elif cls_name == "RichBlockButtons":
            btns = []
            align = getattr(b, "align", "left") or "left"
            for btn in getattr(b, "buttons", []):
                btn_text = rich_text_to_html(getattr(btn, "text", "Button"))
                url = getattr(btn, "url", getattr(btn, "copy_text", "#"))
                if hasattr(url, "text"):
                    url = url.text
                style_name = str(getattr(btn, "style", "")).split(".")[-1].lower()
                btns.append(f'<a class="rich-button {style_name}" href="{html.escape(str(url))}">{btn_text}</a>')
            html_parts.append(f'<div class="rich-button-row align-{align}">{"".join(btns)}</div>')
        elif cls_name == "RichBlockThinking":
            html_parts.append(f'<div class="rich-thinking">{rich_text_to_html(getattr(b, "text", ""))}</div>')
        elif cls_name == "RichBlockTable":
            cap = f"<caption>{rich_text_to_html(b.caption)}</caption>" if getattr(b, "caption", None) else ""
            rows = []
            for r in getattr(b, "cells", []):
                cells = []
                for c in r:
                    tag = "th" if getattr(c, "is_header", False) else "td"
                    c_text = rich_text_to_html(c.text)
                    attrs = []
                    if getattr(c, "colspan", 1) > 1:
                        attrs.append(f'colspan="{c.colspan}"')
                    if getattr(c, "rowspan", 1) > 1:
                        attrs.append(f'rowspan="{c.rowspan}"')
                    attr_str = (" " + " ".join(attrs)) if attrs else ""
                    cells.append(f"<{tag}{attr_str}>{c_text}</{tag}>")
                rows.append(f"<tr>{''.join(cells)}</tr>")
            cls = ' class="rich-table' + (' bordered' if getattr(b, 'is_bordered', False) else '') + '"'
            html_parts.append(f"<table{cls}>{cap}{''.join(rows)}</table>")
        elif cls_name == "RichBlockPhoto":
            photo = getattr(b, "photo", None)
            if photo:
                try:
                    fname = f"{msg_id}_photo_{photo.file_unique_id}.jpg"
                    fp = media_path / fname
                    if not fp.is_file():
                        await app.download_media(photo.file_id, file_name=str(fp))
                    create_webp_thumbnail(fp)
                    rel_url = str(fp.relative_to(base_path))
                    thumb_fp = fp.with_name(f"{fp.stem}_thumb.webp")
                    img_src = str(thumb_fp.relative_to(base_path)) if thumb_fp.is_file() else rel_url
                    caption = rich_text_to_html(getattr(b, "caption", None))
                    cap_html = f"<figcaption>{caption}</figcaption>" if caption else ""
                    html_parts.append(f'<figure class="rich-photo"><img data-src="{img_src}" data-full="{rel_url}" src="{img_src}" alt="" loading="lazy"/>{cap_html}</figure>')
                except Exception as e:
                    print(f"Warning: Failed to download rich photo: {e}")
    return "\n".join(html_parts)
