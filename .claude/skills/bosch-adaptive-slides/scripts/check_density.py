import json
import re
import argparse
import os

MIN_FONT_PX = 17
SAFE_AREA_HEIGHT_PX = 500
SAFE_AREA_WIDTH_PX = 1205

def _strip_html_tags(html):
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _count_elements(html, pattern):
    return len(re.findall(pattern, html, re.IGNORECASE))

def estimate_density(content_html):
    if not content_html:
        return {
            "char_count": 0,
            "bullet_count": 0,
            "table_cell_count": 0,
            "paragraph_count": 0,
            "image_count": 0,
            "density_score": 0.0,
            "classification": "sparse"
        }

    text = _strip_html_tags(content_html)
    char_count = len(text)
    bullet_count = _count_elements(content_html, r'<li[>\s]')
    table_cell_count = _count_elements(content_html, r'<t[dh][>\s]')
    paragraph_count = _count_elements(content_html, r'<p[>\s]')
    image_count = _count_elements(content_html, r'<img[>\s]')

    density_score = (
        (char_count / 800.0)
        + (bullet_count * 0.15)
        + (table_cell_count * 0.08)
        + (paragraph_count * 0.2)
        + (image_count * 0.3)
    )

    if density_score < 0.5:
        classification = "sparse"
    elif density_score <= 1.0:
        classification = "moderate"
    elif density_score <= 1.5:
        classification = "dense"
    else:
        classification = "overflow"

    return {
        "char_count": char_count,
        "bullet_count": bullet_count,
        "table_cell_count": table_cell_count,
        "paragraph_count": paragraph_count,
        "image_count": image_count,
        "density_score": round(density_score, 3),
        "classification": classification
    }

def estimate_required_height(content_html, density):
    char_count = density["char_count"]
    bullets = density["bullet_count"]
    cells = density["table_cell_count"]
    images = density["image_count"]
    paragraphs = max(density["paragraph_count"], 1)

    text_lines = max(1, char_count / 55.0)
    bullet_height = bullets * 32
    table_height = (cells / max(1, _count_elements(content_html, r'<tr[>\s]'))) * 36 if cells > 0 else 0
    if cells > 0 and table_height == 0:
        table_height = 40
    image_height = images * 200
    paragraph_spacing = paragraphs * 16

    estimated = (text_lines * 26) + bullet_height + table_height + image_height + paragraph_spacing + 40
    return round(estimated)

def check_manifest(manifest_path, profile_path=None):
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    safe_h = SAFE_AREA_HEIGHT_PX
    safe_w = SAFE_AREA_WIDTH_PX
    if profile_path and os.path.exists(profile_path):
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)
        sa = profile.get("safe_area", {})
        safe_h = sa.get("height", safe_h)
        safe_w = sa.get("width", safe_w)

    report = {
        "safe_area": {"width": safe_w, "height": safe_h},
        "slides": [],
        "summary": {"total": 0, "pass": 0, "warn": 0, "fail": 0}
    }

    for slide in manifest.get("slides", []):
        content_html = slide.get("content_html", "")
        density = estimate_density(content_html)
        est_height = estimate_required_height(content_html, density)

        status = "pass"
        issues = []

        if density["classification"] == "overflow":
            status = "fail"
            issues.append("density_overflow: content exceeds safe area capacity; split or move to appendix")
        elif density["classification"] == "dense":
            status = "warn"
            issues.append("density_dense: content is near capacity; consider compact layout or split")

        if est_height > safe_h:
            if status != "fail":
                status = "warn"
            issues.append(f"estimated_height {est_height}px exceeds safe_area_height {safe_h}px")

        slide_report = {
            "id": slide.get("id", ""),
            "title": slide.get("title", ""),
            "density": density,
            "estimated_height_px": est_height,
            "status": status,
            "issues": issues
        }
        report["slides"].append(slide_report)
        report["summary"]["total"] += 1
        if status == "pass":
            report["summary"]["pass"] += 1
        elif status == "warn":
            report["summary"]["warn"] += 1
        else:
            report["summary"]["fail"] += 1

    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check content density of slide manifest")
    parser.add_argument("--manifest", required=True, help="Path to slide_manifest.json")
    parser.add_argument("--profile", help="Path to template_profile.json (optional, for safe area dimensions)")
    parser.add_argument("--output", help="Path to save the density report JSON")
    args = parser.parse_args()

    report = check_manifest(args.manifest, args.profile)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Density report saved to {args.output}")
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))

    s = report["summary"]
    print(f"\nDensity check: {s['pass']} pass, {s['warn']} warn, {s['fail']} fail (total {s['total']})")
