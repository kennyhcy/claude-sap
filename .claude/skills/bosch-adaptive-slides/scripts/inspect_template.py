import re
import json
import os

def extract_block(html, start_tag, end_tag):
    start_idx = html.find(start_tag)
    if start_idx == -1:
        return ""
    end_idx = html.find(end_tag, start_idx)
    if end_idx == -1:
        return ""
    return html[start_idx:end_idx + len(end_tag)]

def extract_content(html, regex_pattern):
    match = re.search(regex_pattern, html, re.DOTALL)
    if match:
        return match.group(0)
    return ""

def inspect_template(template_path):
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")
        
    with open(template_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Extract major layout fragments
    style_block = extract_block(html, "<style>", "</style>")
    script_block = extract_block(html, "<script>", "</script>")
    
    # Extract protected brand zones
    footer_match = extract_content(html, r'<footer class="slide-footer">.*?</footer>')
    logo_match = extract_content(html, r'<div class="slide-logo"[^>]*>.*?</div>')
    supergraphic_match = extract_content(html, r'<div class="slide-supergraphic"[^>]*>.*?</div>')
    
    # Extract slide viewer controls
    viewer_match = extract_content(html, r'<div class="slide-viewer"[^>]*>.*?</div>')
    
    profile = {
        "style_block": style_block,
        "script_block": script_block,
        "footer_html": footer_match,
        "logo_html": logo_match,
        "supergraphic_html": supergraphic_match,
        "viewer_html": viewer_match,
        "available_layouts": [
            "cover-simple", "section-banner", "two-col", "three-col", "panel",
            "cards", "number-grid", "timeline", "matrix-wrap", "arch", "flow",
            "chart-grid", "checklist", "roadmap", "end-page", "default",
            "image-hero", "image-text-split", "image-comparison",
            "image-grid", "image-caption-focus", "image-annotated"
        ]
    }
    return profile

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Inspect Bosch HTML template")
    parser.add_argument("--template", required=True, help="Path to the HTML template")
    parser.add_argument("--output", help="Path to save the profile JSON")
    args = parser.parse_args()
    
    profile = inspect_template(args.template)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2)
    else:
        print(json.dumps(profile, indent=2))
