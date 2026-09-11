import json
import re
import os
import argparse
import copy

REPAIR_CSS = """
    /* === Auto-repair compact overrides === */
    .slide-content.repair-compact {
      padding: 8px !important;
      gap: 8px !important;
    }
    .slide-content.repair-compact .panel {
      padding: 10px !important;
    }
    .slide-content.repair-compact p {
      margin: 4px 0 !important;
      line-height: 1.35 !important;
    }
    .slide-content.repair-compact ul.clean {
      margin: 4px 0 !important;
      gap: 2px !important;
    }
    .slide-content.repair-compact ul.clean li {
      margin: 1px 0 !important;
      line-height: 1.3 !important;
    }
    .slide-content.repair-tight {
      padding: 4px !important;
      gap: 4px !important;
    }
    .slide-content.repair-tight .panel {
      padding: 8px !important;
    }
    .slide-content.repair-tight p {
      margin: 2px 0 !important;
      line-height: 1.25 !important;
      font-size: 16px !important;
    }
    .slide-content.repair-tight ul.clean li {
      margin: 0 !important;
      line-height: 1.2 !important;
      font-size: 16px !important;
    }
    .slide-content.repair-tight table {
      font-size: 15px !important;
    }
    .slide-content.repair-tight td,
    .slide-content.repair-tight th {
      padding: 3px 6px !important;
    }
"""

COMPACT_LAYOUT_MAP = {
    "two-col": "panel",
    "three-col": "two-col",
    "cards": "panel",
    "number-grid": "panel",
    "chart-grid": "panel",
    "image-text-split": "image-hero",
}

def _inject_repair_css(html):
    if "repair-compact" in html:
        return html
    insert_pos = html.find("</style>")
    if insert_pos == -1:
        insert_pos = html.find("</head>")
        if insert_pos == -1:
            return html
        return html[:insert_pos] + "<style>" + REPAIR_CSS + "</style>\n" + html[insert_pos:]
    return html[:insert_pos] + REPAIR_CSS + html[insert_pos:]

def _find_slide_sections(html):
    pattern = r'(<section[^>]*class="[^"]*slide[^"]*"[^>]*>)'
    matches = list(re.finditer(pattern, html))
    return matches

def _add_class_to_slide_content(html, slide_idx, class_name):
    sections = list(re.finditer(r'<section[^>]*class="[^"]*slide[^"]*"[^>]*>(.*?)</section>', html, re.DOTALL))
    if slide_idx >= len(sections):
        return html

    match = sections[slide_idx]
    inner = match.group(1)
    content_pattern = r'(<div class=")(slide-content)("[^>]*>)'
    content_match = re.search(content_pattern, inner)
    if content_match:
        new_inner = inner[:content_match.start()] + \
                    content_match.group(1) + content_match.group(2) + f" {class_name}" + content_match.group(3) + \
                    inner[content_match.end():]
        return html[:match.start()] + match.group(0)[:match.start(1)] + new_inner + "</section>" + html[match.end():]
    return html

def apply_mechanical_repairs(html, report):
    html = _inject_repair_css(html)

    repair_log = []
    slides = report.get("slides", [])

    for slide in slides:
        idx = slide.get("index", 0)
        issues = slide.get("issues", [])
        slide_repairs = []

        has_overflow = any(i.get("type") in ("overflow_bottom", "internal_overflow") for i in issues)
        has_small_text = any(i.get("type") == "small_text" for i in issues)

        if has_overflow:
            if has_small_text:
                slide_repairs.append("repair-tight")
                slide_repairs.append("Flagged: content already at minimum font; manual split required")
            else:
                slide_repairs.append("repair-compact")
                slide_repairs.append("Applied compact CSS to reduce padding and line-height")

        if slide_repairs:
            for r in slide_repairs:
                if r.startswith("repair-"):
                    sections = list(re.finditer(r'<section[^>]*class="[^"]*slide[^"]*"[^>]*>(.*?)</section>', html, re.DOTALL))
                    if idx < len(sections):
                        match = sections[idx]
                        inner = match.group(1)
                        if 'class="slide-content' in inner and r not in inner:
                            inner = re.sub(
                                r'(class="slide-content[^"]*)(")',
                                lambda m: m.group(1) + f" {r}" + m.group(2),
                                inner,
                                count=1
                            )
                            html = html[:match.start()] + match.group(0)[:match.start(1)] + inner + "</section>" + html[match.end():]

            repair_log.append({
                "slide_index": idx,
                "applied": [r for r in slide_repairs if r.startswith("repair-")],
                "manual_actions": [r for r in slide_repairs if not r.startswith("repair-")]
            })

    return html, repair_log

def generate_manual_repair_instructions(report):
    instructions = []

    for slide in report.get("slides", []):
        idx = slide.get("index", 0)
        issues = slide.get("issues", [])

        for issue in issues:
            itype = issue.get("type", "")

            if itype == "overflow_bottom":
                instructions.append({
                    "slide_index": idx,
                    "action": "split_or_simplify",
                    "reason": f"Content overflows by {issue.get('overflow_px', 0)}px",
                    "options": [
                        "Split slide into two slides with one message each",
                        "Convert prose paragraphs to concise bullet points",
                        "Move secondary detail to speaker notes or appendix",
                        "Switch to a full-width layout (e.g., panel instead of two-col)"
                    ]
                })

            elif itype == "internal_overflow":
                instructions.append({
                    "slide_index": idx,
                    "action": "reduce_content",
                    "reason": f"Internal scroll overflow of {issue.get('overflow_px', 0)}px",
                    "options": [
                        "Shorten wording without changing meaning",
                        "Remove redundant paragraphs",
                        "Reduce bullet count by merging related items",
                        "Move detailed evidence to appendix"
                    ]
                })

            elif itype == "small_text":
                elements = issue.get("elements", [])
                instructions.append({
                    "slide_index": idx,
                    "action": "fix_small_text",
                    "reason": f"{len(elements)} element(s) below minimum font size",
                    "options": [
                        "Split slide to reduce content density",
                        "Remove non-essential text to allow larger fonts",
                        "Switch to a simpler layout with fewer regions"
                    ]
                })

            elif itype == "overlap":
                instructions.append({
                    "slide_index": idx,
                    "action": "fix_overlap",
                    "reason": issue.get("message", "Overlapping elements detected"),
                    "options": [
                        "Adjust layout to use grid/flex with explicit areas",
                        "Increase gap between regions",
                        "Switch to a single-column layout"
                    ]
                })

            elif itype == "content_in_footer_zone":
                instructions.append({
                    "slide_index": idx,
                    "action": "move_content_up",
                    "reason": "Content extends into footer protected zone",
                    "options": [
                        "Reduce content height by splitting or simplifying",
                        "Remove top padding/margin from content area",
                        "Switch to a more compact layout"
                    ]
                })

    return instructions

def repair_html(html_path, report_path, output_path=None):
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)

    repaired_html, repair_log = apply_mechanical_repairs(html, report)
    manual_instructions = generate_manual_repair_instructions(report)

    out_path = output_path or html_path
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(repaired_html)

    print(f"Repaired HTML saved to {out_path}")
    print(f"Mechanical repairs applied: {sum(len(r.get('applied', [])) for r in repair_log)}")
    print(f"Manual repair instructions: {len(manual_instructions)}")

    if manual_instructions:
        print("\nManual repair instructions:")
        for inst in manual_instructions:
            print(f"  Slide {inst['slide_index']}: {inst['action']} — {inst['reason']}")
            for opt in inst.get("options", []):
                print(f"    - {opt}")

    return {
        "repaired_html_path": out_path,
        "mechanical_repairs": repair_log,
        "manual_instructions": manual_instructions
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Repair rendered HTML slides based on inspection report")
    parser.add_argument("--html", required=True, help="Path to rendered HTML deck")
    parser.add_argument("--report", required=True, help="Path to inspection report JSON from inspect_render.py")
    parser.add_argument("--output", help="Path to save repaired HTML (defaults to overwriting input)")
    args = parser.parse_args()

    repair_html(args.html, args.report, args.output)
