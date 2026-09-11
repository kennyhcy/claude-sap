import re
import os
import datetime

def _classify_orientation(aspect_ratio):
    if aspect_ratio >= 1.30:
        return "landscape"
    elif aspect_ratio <= 0.80:
        return "portrait"
    else:
        return "square"

def _extract_keywords(text):
    tokens = re.split(r'[\s_\-/.]+', text.lower())
    stop = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'bmp', 'image', 'img', 'photo', 'picture', 'the', 'a', 'an', 'of'}
    seen = set()
    result = []
    for t in tokens:
        if t and t not in stop and len(t) > 1 and t not in seen:
            seen.add(t)
            result.append(t)
    return result

def _try_get_dimensions(src, base_dir):
    try:
        from PIL import Image
        path = src
        if not os.path.isabs(path) and base_dir:
            path = os.path.join(base_dir, src)
        if os.path.exists(path):
            with Image.open(path) as img:
                w, h = img.size
                return w, h
    except Exception:
        pass
    return None, None

def _build_image_asset(src, alt, context_heading, base_dir, img_id):
    keywords = _extract_keywords(alt + " " + os.path.basename(src))
    w, h = _try_get_dimensions(src, base_dir)
    aspect_ratio = None
    orientation = "landscape"
    if w and h and h > 0:
        aspect_ratio = round(w / h, 2)
        orientation = _classify_orientation(aspect_ratio)
    return {
        "id": img_id,
        "src": src,
        "alt": alt,
        "width_px": w,
        "height_px": h,
        "aspect_ratio": aspect_ratio,
        "orientation": orientation,
        "context_heading": context_heading or "",
        "keywords": keywords,
        "source": "user-provided",
        "used_on_slides": []
    }

def _discover_asset_images(base_dir):
    assets = []
    if not base_dir or not os.path.isdir(base_dir):
        return assets
    image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp'}
    asset_dir = os.path.join(base_dir, "assets")
    search_dirs = [asset_dir, base_dir]
    idx = 0
    for search_dir in search_dirs:
        if not os.path.isdir(search_dir):
            continue
        for fname in sorted(os.listdir(search_dir)):
            ext = os.path.splitext(fname)[1].lower()
            if ext in image_exts:
                idx += 1
                rel_path = os.path.join("assets", fname) if search_dir == asset_dir else fname
                asset = _build_image_asset(rel_path, "", "", base_dir, f"asset-{idx:03d}")
                asset["source"] = "discovered"
                assets.append(asset)
    return assets

def _estimate_text_density(text):
    char_count = len(text)
    bullet_count = len(re.findall(r'^[\*\-]\s+', text, re.MULTILINE))
    paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
    density = char_count / 500.0 + bullet_count * 0.15 + paragraph_count * 0.2
    return round(density, 2)

def _select_image_layout(images_for_section, text_density, all_assets):
    if not images_for_section:
        return None, None

    if len(images_for_section) >= 2 and text_density < 0.5:
        if len(images_for_section) >= 4:
            return "image-grid", "grid-2x2"
        elif len(images_for_section) == 3:
            return "image-grid", "grid-3"
        else:
            return "image-comparison", None

    img = images_for_section[0]
    orientation = img.get("orientation", "landscape")

    if text_density < 0.5:
        return "image-hero", "contained-with-caption"
    elif text_density > 1.5:
        if orientation == "landscape":
            return "image-text-split", "image-top"
        else:
            return "image-text-split", "image-right-50"
    else:
        if orientation == "landscape":
            return "image-text-split", "image-top"
        elif orientation == "portrait":
            return "image-text-split", "image-right-50"
        else:
            return "image-caption-focus", None

def _format_text_content(content):
    lines = content.strip().split('\n')
    parts = []
    current_bullets = []

    def flush_bullets():
        nonlocal current_bullets
        if current_bullets:
            parts.append('<ul class="clean">\n' + '\n'.join(current_bullets) + '\n</ul>')
            current_bullets = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_bullets()
            continue
        bullet_match = re.match(r'^[\*\-]\s+(.+)$', stripped)
        if bullet_match:
            current_bullets.append(f'<li>{bullet_match.group(1)}</li>')
        else:
            flush_bullets()
            parts.append(f'<p>{stripped}</p>')

    flush_bullets()
    return '\n'.join(parts)

def parse_markdown_to_manifest(md_text, base_dir=None):
    """
    Heuristically parses raw Markdown into a slide_manifest.json structure.
    Extracts images, builds an image asset registry, and selects image-text layouts.
    This provides a fallback for autonomous CLI usage without an LLM.
    """
    manifest = {
        "deck_metadata": {
            "title": "Generated Presentation",
            "author": "Auto-Generator",
            "department": "Bosch",
            "date": datetime.date.today().isoformat()
        },
        "image_assets": [],
        "slides": []
    }

    frontmatter_match = re.match(r'^---\n(.*?)\n---', md_text, re.DOTALL)
    if frontmatter_match:
        fm = frontmatter_match.group(1)
        for line in fm.split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                manifest["deck_metadata"][k.strip()] = v.strip()
        md_text = md_text[frontmatter_match.end():]

    image_assets = _discover_asset_images(base_dir)

    cover_section = md_text.strip()
    title_match = re.search(r'^#\s+(.+)', cover_section, re.MULTILINE)
    if title_match:
        manifest["deck_metadata"]["title"] = title_match.group(1).strip()

    manifest["slides"].append({
        "id": "slide-cover",
        "topic": "",
        "title": manifest["deck_metadata"].get("title", ""),
        "layout": "cover-simple",
        "content_html": ""
    })

    sections = re.split(r'\n##\s+', '\n' + md_text)
    img_counter = 0

    for i, sec in enumerate(sections[1:], 1):
        lines = sec.strip().split('\n')
        heading = lines[0].strip()
        content_lines = lines[1:]
        content = '\n'.join(content_lines).strip()

        img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        img_directive_pattern = re.compile(r'<!--\s*image:\s*(\S+)\s*-->')

        images_in_section = []
        for m in img_pattern.finditer(content):
            img_counter += 1
            asset = _build_image_asset(m.group(2), m.group(1), heading, base_dir, f"img-{img_counter:03d}")
            images_in_section.append(asset)
            image_assets.append(asset)
            content = content.replace(m.group(0), '', 1)

        for m in img_directive_pattern.finditer(content):
            img_counter += 1
            asset = _build_image_asset(m.group(1), "", heading, base_dir, f"img-{img_counter:03d}")
            images_in_section.append(asset)
            image_assets.append(asset)
            content = content.replace(m.group(0), '', 1)

        text_density = _estimate_text_density(content)
        selected_layout, selected_variant = _select_image_layout(images_in_section, text_density, image_assets)

        html_content = ""
        layout = "panel"

        if selected_layout:
            layout = selected_layout
            img_html = images_in_section[0]
            img_tag = f'<img src="{img_html["src"]}" alt="{img_html["alt"]}" class="slide-img" />'

            text_content = _format_text_content(content)

            if selected_layout == "image-hero":
                html_content = f'<div class="image-hero">\n  <div class="image-hero-box">{img_tag}</div>\n  <p class="image-caption">{img_html["alt"]}</p>\n</div>'
            elif selected_layout == "image-text-split":
                if selected_variant and selected_variant.startswith("image-top"):
                    html_content = f'<div class="image-text-split image-text-top">\n  <div class="its-image">{img_tag}</div>\n  <div class="its-text">{text_content}</div>\n</div>'
                elif selected_variant and selected_variant.startswith("image-bottom"):
                    html_content = f'<div class="image-text-split image-text-bottom">\n  <div class="its-text">{text_content}</div>\n  <div class="its-image">{img_tag}</div>\n</div>'
                elif selected_variant and "right" in selected_variant:
                    html_content = f'<div class="image-text-split image-text-right">\n  <div class="its-text">{text_content}</div>\n  <div class="its-image">{img_tag}</div>\n</div>'
                else:
                    html_content = f'<div class="image-text-split image-text-left">\n  <div class="its-image">{img_tag}</div>\n  <div class="its-text">{text_content}</div>\n</div>'
            elif selected_layout == "image-caption-focus":
                html_content = f'<div class="image-caption-focus">\n  <div class="icf-image">{img_tag}</div>\n  <p class="icf-caption">{img_html["alt"]}</p>\n  <div class="icf-text">{text_content}</div>\n</div>'
            elif selected_layout == "image-comparison":
                img_b_tag = ""
                if len(images_in_section) >= 2:
                    img_b = images_in_section[1]
                    img_b_tag = f'<img src="{img_b["src"]}" alt="{img_b["alt"]}" class="slide-img" />'
                html_content = f'<div class="image-comparison">\n  <div class="ic-cell"><div class="ic-img">{img_tag}</div><p class="ic-label">{images_in_section[0]["alt"]}</p></div>\n  <div class="ic-cell"><div class="ic-img">{img_b_tag}</div><p class="ic-label">{images_in_section[1]["alt"] if len(images_in_section) > 1 else ""}</p></div>\n</div>'
            elif selected_layout == "image-grid":
                cells = ""
                for gimg in images_in_section[:4]:
                    gtag = f'<img src="{gimg["src"]}" alt="{gimg["alt"]}" class="slide-img" />'
                    cells += f'<div class="ig-cell"><div class="ig-img">{gtag}</div><p class="ig-label">{gimg["alt"]}</p></div>\n'
                grid_class = f"image-grid ig-{len(images_in_section[:4])}"
                html_content = f'<div class="{grid_class}">\n{cells}</div>'
        else:
            if content:
                html_content = f'<div class="panel">\n{_format_text_content(content)}\n</div>'

        slide_entry = {
            "id": f"slide-{i}",
            "topic": "Section",
            "title": heading,
            "layout": layout,
            "content_html": html_content
        }
        if selected_layout:
            slide_entry["layout_variant"] = selected_variant or ""
            slide_entry["image"] = {
                "selected_id": images_in_section[0]["id"] if images_in_section else None,
                "selected_src": images_in_section[0]["src"] if images_in_section else None,
                "intent": selected_layout,
                "balance": selected_variant or "",
                "image_count": len(images_in_section)
            }
            for ia in images_in_section:
                ia["used_on_slides"].append(slide_entry["id"])

        manifest["slides"].append(slide_entry)

    manifest["image_assets"] = image_assets
    return manifest

if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Parse Markdown to slide manifest")
    parser.add_argument("--markdown", required=True, help="Path to source Markdown file")
    parser.add_argument("--output", help="Path to save the manifest JSON")
    args = parser.parse_args()

    with open(args.markdown, 'r', encoding='utf-8') as f:
        md_text = f.read()

    base_dir = os.path.dirname(os.path.abspath(args.markdown))
    manifest = parse_markdown_to_manifest(md_text, base_dir)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"Manifest saved to {args.output}")
    else:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
