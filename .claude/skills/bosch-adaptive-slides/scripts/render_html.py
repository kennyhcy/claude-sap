import json

IMAGE_LAYOUT_CSS = """
    /* === Image-aware layout styles === */
    .slide-img {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      border-radius: 8px;
      display: block;
    }

    .image-hero .image-hero-box,
    .image-text-split .its-image,
    .image-caption-focus .icf-image,
    .image-comparison .ic-img,
    .image-grid .ig-img {
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #F7F7F7 0%, #EEF5FA 100%);
      border: 1px solid var(--bosch-border);
      border-radius: 12px;
      padding: 12px;
      overflow: hidden;
    }

    /* image-hero */
    .image-hero {
      display: flex;
      flex-direction: column;
      align-items: center;
      height: 100%;
      gap: 12px;
    }
    .image-hero .image-hero-box {
      flex: 1 1 0;
      width: 100%;
      min-height: 0;
    }
    .image-hero .image-caption {
      font-size: 14px;
      color: var(--bosch-mid-gray);
      text-align: center;
      margin: 0;
    }

    /* image-text-split */
    .image-text-split {
      display: grid;
      height: 100%;
      gap: 22px;
      align-items: stretch;
    }
    .image-text-split.image-text-left,
    .image-text-split.image-text-right {
      grid-template-columns: 1fr 1fr;
    }
    .image-text-split.image-text-top {
      grid-template-columns: 1fr;
      grid-template-rows: 1fr auto;
    }
    .image-text-split.image-text-bottom {
      grid-template-columns: 1fr;
      grid-template-rows: auto 1fr;
    }
    .image-text-split .its-image {
      min-height: 180px;
    }
    .image-text-split .its-text {
      display: flex;
      flex-direction: column;
      justify-content: center;
      padding: 8px 4px;
      font-size: 18px;
      line-height: 1.5;
      color: #303030;
    }
    .image-text-split .its-text ul.clean {
      font-size: 18px;
    }

    /* image-caption-focus */
    .image-caption-focus {
      display: flex;
      flex-direction: column;
      align-items: center;
      height: 100%;
      gap: 10px;
    }
    .image-caption-focus .icf-image {
      flex: 1 1 0;
      width: 75%;
      min-height: 0;
    }
    .image-caption-focus .icf-caption {
      font-size: 15px;
      color: var(--bosch-mid-gray);
      text-align: center;
      margin: 0;
    }
    .image-caption-focus .icf-text {
      font-size: 17px;
      line-height: 1.45;
      color: #303030;
      text-align: center;
      max-width: 90%;
    }

    /* image-comparison */
    .image-comparison {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 22px;
      height: 100%;
      align-items: stretch;
    }
    .image-comparison .ic-cell {
      display: flex;
      flex-direction: column;
      gap: 10px;
      min-height: 0;
    }
    .image-comparison .ic-img {
      flex: 1 1 0;
      min-height: 200px;
    }
    .image-comparison .ic-label {
      font-size: 16px;
      font-weight: 600;
      color: var(--bosch-blue-dark);
      text-align: center;
      margin: 0;
    }

    /* image-grid */
    .image-grid {
      display: grid;
      gap: 18px;
      height: 100%;
    }
    .image-grid.ig-2 { grid-template-columns: 1fr 1fr; }
    .image-grid.ig-3 { grid-template-columns: 1fr 1fr 1fr; }
    .image-grid.ig-2x2 { grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; }
    .image-grid .ig-cell {
      display: flex;
      flex-direction: column;
      gap: 8px;
      min-height: 0;
    }
    .image-grid .ig-img {
      flex: 1 1 0;
      border-radius: 10px;
      padding: 10px;
      min-height: 140px;
    }
    .image-grid .ig-label {
      font-size: 14px;
      color: var(--bosch-mid-gray);
      text-align: center;
      margin: 0;
    }
"""

def _needs_image_css(slides):
    image_layouts = {
        "image-hero", "image-text-split", "image-comparison",
        "image-grid", "image-caption-focus", "image-annotated"
    }
    for slide in slides:
        if slide.get("layout") in image_layouts:
            return True
        if slide.get("image"):
            return True
    return False

def render_deck(profile, manifest):
    """
    Renders the final HTML slide deck from the template profile and the slide manifest.
    Supports image-aware layouts with automatic CSS injection.
    """

    html_out = []
    html_out.append('<!DOCTYPE html>\n<html lang="en">\n<head>')
    html_out.append('  <meta charset="UTF-8" />')
    html_out.append('  <meta name="viewport" content="width=device-width, initial-scale=1.0" />')

    deck_metadata = manifest.get("deck_metadata", {})
    deck_title = deck_metadata.get("title", "Bosch Presentation")
    html_out.append(f'  <title>{deck_title}</title>')

    html_out.append(profile.get("style_block", ""))

    slides = manifest.get("slides", [])
    if _needs_image_css(slides):
        html_out.append('<style>' + IMAGE_LAYOUT_CSS + '</style>')

    html_out.append('</head>\n<body>')

    html_out.append('  <main class="deck">')

    department = deck_metadata.get("department", "PT-GT/ETD32")
    year = deck_metadata.get("year", "2026")

    orig_footer = profile.get("footer_html", "")
    footer_html = orig_footer
    if footer_html:
        footer_html = footer_html.replace("PT-GT/ETD32", department)
        footer_html = footer_html.replace("2025", year).replace("2026", year)

    for idx, slide in enumerate(slides):
        layout = slide.get("layout", "default")

        slide_classes = "slide"
        if layout == "cover-simple":
            slide_classes += " cover-bg-slide"

        html_out.append(f'    <section class="{slide_classes}" data-slide-index="{idx}">')

        if layout == "cover-simple":
            html_out.append('      <div class="cover-simple">')
            html_out.append(f'        <h1 class="cover-simple-title">{slide.get("title", "")}</h1>')
            html_out.append('        <div class="cover-title-bar"></div>')
            html_out.append('        <div class="cover-simple-meta">')

            author = deck_metadata.get("author", "")
            if author:
                html_out.append(f'          <div class="item"><div class="label">汇报人</div><div class="value">{author}</div></div>')

            if department:
                html_out.append(f'          <div class="item"><div class="label">汇报人部门</div><div class="value">{department}</div></div>')

            date = deck_metadata.get("date", "")
            if date:
                html_out.append(f'          <div class="item"><div class="label">时间</div><div class="value">{date}</div></div>')

            html_out.append('        </div>')
            html_out.append('      </div>')
        else:
            topic = slide.get("topic", "")
            title = slide.get("title", "")
            content_html = slide.get("content_html", "")

            html_out.append(f'      <h2 class="slide-topic">{topic}</h2>')
            html_out.append(f'      <div class="slide-title-wrap"><h1 class="slide-title">{title}</h1></div>')
            html_out.append(f'      <div class="slide-content">\n{content_html}\n      </div>')

            html_out.append('      <div class="page-number" aria-label="slide number"></div>')
            html_out.append('      ' + (footer_html if footer_html else ""))
            html_out.append('      ' + profile.get("logo_html", ""))
            html_out.append('      ' + profile.get("supergraphic_html", ""))

        html_out.append('    </section>')

    html_out.append('  </main>')

    html_out.append(profile.get("viewer_html", ""))
    html_out.append('  <div class="print-host" id="printHost" aria-hidden="true"></div>')

    html_out.append(profile.get("script_block", ""))
    html_out.append('</body>\n</html>')

    return "\n".join(html_out)

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Render HTML Deck")
    parser.add_argument("--profile", required=True, help="Path to profile JSON")
    parser.add_argument("--manifest", required=True, help="Path to slide manifest JSON")
    parser.add_argument("--output", required=True, help="Path to save HTML")
    args = parser.parse_args()

    with open(args.profile, 'r', encoding='utf-8') as f:
        profile = json.load(f)

    with open(args.manifest, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    html_content = render_deck(profile, manifest)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Deck saved to {args.output}")
