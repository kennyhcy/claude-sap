import json
import os
import argparse

INSPECT_JS = r"""
() => {
  const MIN_FONT_PX = 13;
  const SAFE_TOP = 185;
  const SAFE_BOTTOM = 685;
  const SAFE_LEFT = 80;
  const SAFE_RIGHT = 1285;

  const slides = document.querySelectorAll('.slide');
  const results = [];

  slides.forEach((slide, idx) => {
    const slideRect = slide.getBoundingClientRect();
    const content = slide.querySelector('.slide-content');
    const issues = [];

    if (!content) {
      results.push({index: idx, issues: ["no .slide-content element found"]});
      return;
    }

    const contentRect = content.getBoundingClientRect();

    // Overflow: content extends beyond safe area
    if (contentRect.bottom > SAFE_BOTTOM + 2) {
      issues.push({
        type: "overflow_bottom",
        message: `Content bottom ${Math.round(contentRect.bottom)}px exceeds safe area bottom ${SAFE_BOTTOM}px`,
        overflow_px: Math.round(contentRect.bottom - SAFE_BOTTOM)
      });
    }
    if (contentRect.right > SAFE_RIGHT + 2) {
      issues.push({
        type: "overflow_right",
        message: `Content right ${Math.round(contentRect.right)}px exceeds safe area right ${SAFE_RIGHT}px`,
        overflow_px: Math.round(contentRect.right - SAFE_RIGHT)
      });
    }

    // ScrollHeight overflow (content clipped internally)
    if (content.scrollHeight > content.clientHeight + 2) {
      issues.push({
        type: "internal_overflow",
        message: `Content scrollHeight ${content.scrollHeight}px exceeds clientHeight ${content.clientHeight}px`,
        overflow_px: content.scrollHeight - content.clientHeight
      });
    }

    // Small text detection
    const textSelectors = 'p, li, td, th, span, h1, h2, h3, h4, h5, h6, div';
    const textElements = content.querySelectorAll(textSelectors);
    const smallTexts = [];
    textElements.forEach(el => {
      const style = window.getComputedStyle(el);
      const fontSize = parseFloat(style.fontSize);
      if (fontSize > 0 && fontSize < MIN_FONT_PX) {
        const text = el.textContent.trim().substring(0, 60);
        if (text) {
          smallTexts.push({
            tag: el.tagName.toLowerCase(),
            font_size: fontSize,
            text_preview: text
          });
        }
      }
    });
    if (smallTexts.length > 0) {
      issues.push({
        type: "small_text",
        message: `${smallTexts.length} text element(s) below minimum ${MIN_FONT_PX}px`,
        elements: smallTexts.slice(0, 5)
      });
    }

    // Overlap detection: check child blocks within content
    const blocks = content.querySelectorAll('div, table, ul, ol, p, img, figure');
    const blockRects = [];
    blocks.forEach(b => {
      const r = b.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) {
        blockRects.push({el: b, rect: r});
      }
    });
    const overlaps = [];
    for (let i = 0; i < blockRects.length; i++) {
      for (let j = i + 1; j < blockRects.length; j++) {
        const a = blockRects[i].rect;
        const b = blockRects[j].rect;
        const aContainsB = a.left <= b.left && a.right >= b.right && a.top <= b.top && a.bottom >= b.bottom;
        const bContainsA = b.left <= a.left && b.right >= a.right && b.top <= a.top && b.bottom >= a.bottom;
        if (aContainsB || bContainsA) continue;

        const ix = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
        const iy = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
        if (ix > 5 && iy > 5) {
          const overlapArea = ix * iy;
          const minArea = Math.min(
            (a.right - a.left) * (a.bottom - a.top),
            (b.right - b.left) * (b.bottom - b.top)
          );
          if (overlapArea > minArea * 0.1) {
            overlaps.push({
              a: blockRects[i].el.tagName.toLowerCase() + (blockRects[i].el.className ? '.' + blockRects[i].el.className.split(' ')[0] : ''),
              b: blockRects[j].el.tagName.toLowerCase() + (blockRects[j].el.className ? '.' + blockRects[j].el.className.split(' ')[0] : ''),
              overlap_px: Math.round(overlapArea)
            });
          }
        }
      }
    }
    if (overlaps.length > 0) {
      issues.push({
        type: "overlap",
        message: `${overlaps.length} overlapping element pair(s) detected`,
        pairs: overlaps.slice(0, 5)
      });
    }

    // Content in protected zones
    const footer = slide.querySelector('.slide-footer');
    const logo = slide.querySelector('.slide-logo');
    const supergraphic = slide.querySelector('.slide-supergraphic');
    if (footer) {
      const fr = footer.getBoundingClientRect();
      const cr = content.getBoundingClientRect();
      if (cr.bottom > fr.top - 2) {
        issues.push({
          type: "content_in_footer_zone",
          message: `Content bottom ${Math.round(cr.bottom)}px overlaps footer zone starting at ${Math.round(fr.top)}px`
        });
      }
    }

    // Measure occupancy
    const safeWidth = SAFE_RIGHT - SAFE_LEFT;
    const safeHeight = SAFE_BOTTOM - SAFE_TOP;
    const contentArea = Math.min(contentRect.width, safeWidth) * Math.min(contentRect.height, safeHeight);
    const safeArea = safeWidth * safeHeight;
    const occupancy = safeArea > 0 ? Math.round((contentArea / safeArea) * 100) / 100 : 0;

    // Count text elements for density info
    const allText = content.textContent || '';
    const charCount = allText.replace(/\s+/g, ' ').trim().length;

    results.push({
      index: idx,
      content_bounds: {
        top: Math.round(contentRect.top),
        bottom: Math.round(contentRect.bottom),
        left: Math.round(contentRect.left),
        right: Math.round(contentRect.right),
        width: Math.round(contentRect.width),
        height: Math.round(contentRect.height)
      },
      scroll_height: content.scrollHeight,
      client_height: content.clientHeight,
      occupancy_ratio: occupancy,
      char_count: charCount,
      issue_count: issues.length,
      issues: issues,
      status: issues.length === 0 ? "pass" : "fail"
    });
  });

  return results;
}
"""

LAYOUT_FAMILY_PREFIXES = [
    "image-", "evidence-", "table-", "statement-", "process-",
    "architecture-", "comparison-", "section-divider-", "decision-"
]

EXEMPT_LAYOUTS = {"cover-simple", "section-divider-hero", "end-page", "appendix-reference"}

def _get_layout_family(layout_name):
    for prefix in LAYOUT_FAMILY_PREFIXES:
        if layout_name.startswith(prefix):
            return prefix.rstrip("-")
    return layout_name

def _check_layout_diversity(slide_results):
    if len(slide_results) < 3:
        return None

    layouts = []
    for s in slide_results:
        idx = s.get("index", 0)
        section_el = None
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            pass

    return None

def check_layout_diversity_from_manifest(manifest_slides):
    issues = []
    if len(manifest_slides) < 3:
        return issues

    layouts = [s.get("layout", "default") for s in manifest_slides]

    max_consecutive = 1
    current_consecutive = 1
    for i in range(1, len(layouts)):
        if layouts[i] == layouts[i-1] and layouts[i] not in EXEMPT_LAYOUTS:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 1

    if max_consecutive > 2:
        issues.append({
            "type": "consecutive_layout_repetition",
            "message": f"{max_consecutive} consecutive slides use the same layout '{layouts[i-1]}' (max allowed: 2)",
            "severity": "warn"
        })

    families = [_get_layout_family(l) for l in layouts]
    max_family_consecutive = 1
    current_family_consecutive = 1
    for i in range(1, len(families)):
        if families[i] == families[i-1]:
            current_family_consecutive += 1
            max_family_consecutive = max(max_family_consecutive, current_family_consecutive)
        else:
            current_family_consecutive = 1

    if max_family_consecutive > 3:
        issues.append({
            "type": "consecutive_family_repetition",
            "message": f"{max_family_consecutive} consecutive slides use the same layout family '{families[i-1]}' (max allowed: 3)",
            "severity": "warn"
        })

    from collections import Counter
    layout_counts = Counter(layouts)
    total = len(layouts)
    for layout_name, count in layout_counts.items():
        if layout_name in EXEMPT_LAYOUTS:
            continue
        share = count / total
        if share > 0.40 and total > 4:
            issues.append({
                "type": "layout_share_exceeded",
                "message": f"Layout '{layout_name}' used on {count}/{total} slides ({share:.0%}, max 40%)",
                "severity": "warn"
            })

    family_counts = Counter(families)
    exempt_families = {_get_layout_family(l) for l in EXEMPT_LAYOUTS}
    for family_name, count in family_counts.items():
        if family_name in exempt_families:
            continue
        share = count / total
        if share > 0.55 and total > 4:
            issues.append({
                "type": "family_share_exceeded",
                "message": f"Layout family '{family_name}' used on {count}/{total} slides ({share:.0%}, max 55%)",
                "severity": "warn"
            })

    distinct_layouts = len(set(layouts))
    if distinct_layouts < 3 and total > 4:
        issues.append({
            "type": "insufficient_layout_variety",
            "message": f"Deck uses only {distinct_layouts} distinct layouts across {total} slides (min 3 recommended)",
            "severity": "warn"
        })

    return issues

def inspect_html(html_path, output_path=None):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] Playwright is not installed. Install with: pip install playwright && playwright install")
        return None

    abs_html = os.path.abspath(html_path)
    if not os.path.exists(abs_html):
        print(f"[ERROR] HTML file not found: {abs_html}")
        return None

    results = None

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1365, "height": 768})
        page.goto(f"file:///{abs_html}")
        page.wait_for_timeout(1500)

        results = page.evaluate(INSPECT_JS)

        browser.close()

    report = {
        "html_path": abs_html,
        "slide_count": len(results),
        "slides": results,
        "summary": {
            "total": len(results),
            "pass": sum(1 for r in results if r.get("status") == "pass"),
            "fail": sum(1 for r in results if r.get("status") == "fail")
        }
    }

    diversity_issues = _check_layout_diversity(results)
    if diversity_issues:
        report["layout_diversity"] = diversity_issues

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Inspection report saved to {output_path}")

    s = report["summary"]
    print(f"Render inspection: {s['pass']} pass, {s['fail']} fail (total {s['total']})")

    for r in results:
        if r.get("status") == "fail":
            print(f"  Slide {r['index']}: {r['issue_count']} issue(s)")
            for issue in r.get("issues", []):
                print(f"    - {issue.get('type')}: {issue.get('message', '')}")

    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect rendered HTML slides for visual issues")
    parser.add_argument("--html", required=True, help="Path to rendered HTML deck")
    parser.add_argument("--output", help="Path to save inspection report JSON")
    args = parser.parse_args()

    inspect_html(args.html, args.output)
