# Slide Planning Procedure

Generate a structured per-slide plan before any HTML rendering. This procedure is mandatory: no slide may enter the rendering stage without a completed plan entry.

## Input

- Semantic document tree from `references/semantic_parser.md`
- Template profile from `scripts/inspect_template.py`
- Image asset registry from the manifest

## Step 1: Assign slide purpose

Assign exactly one purpose per slide:

| Purpose | Assign when |
|---|---|
| `cover` | First slide; deck title, author, department, date |
| `agenda` | Overview of deck structure; only when ≥3 sections exist |
| `section_divider` | Major section transition; title-only or title + one-liner |
| `content` | Primary informational slide; explanation, status, description |
| `evidence` | Data, metrics, benchmarks, test results backing a claim |
| `decision` | Recommendation, trade-off analysis, go/no-go |
| `summary` | Synthesis of preceding slides; key takeaways |
| `appendix` | Supporting detail not required for the main narrative |
| `closing` | Final slide; thank-you, Q&A, contact |

**Hard rule**: a `section_divider` must not contain dense content, evidence, or decision blocks. If the source combines a section heading with detailed content, produce two candidates: a divider followed by a content slide.

## Step 2: Define core message

Write a single sentence that captures the one takeaway the audience should remember. If two independent conclusions exist, split the slide.

The message must:
- Be a complete sentence (not a label)
- State the conclusion, not the topic
- Be falsifiable against the source (no invented claims)

## Step 3: Select visual form

Determine the best visual representation using `references/visual_selector.md`. Record `visual_type` and `rendering_method`.

If no visual adds value, set `visual_type: "none"` and use a clean typographic composition.

## Step 4: Estimate content density

Compute a density estimate for each slide:

```
char_count = total visible characters in text content
bullet_count = number of bullet/list items
table_cells = number of <td>/<th> elements
image_count = number of images
paragraph_count = number of <p> elements

density_score = (char_count / 800)
              + (bullet_count * 0.15)
              + (table_cells * 0.08)
              + (paragraph_count * 0.2)
              + (image_count * 0.3)
```

Density classification:

| Range | Classification | Action |
|---|---|---|
| < 0.5 | sparse | May merge with adjacent slide or use statement layout |
| 0.5–1.0 | moderate | Normal; proceed with selected layout |
| 1.0–1.5 | dense | Consider split or compact layout |
| > 1.5 | overflow | Must split or move content to appendix |

## Step 5: Apply split or merge

### Split when
- Density score > 1.5
- Two independent conclusions on one slide
- A table cannot fit at minimum font size
- Content combines management summary and deep technical evidence
- >2 major visuals required
- Estimated speaking time exceeds target per slide

### Merge when
- Adjacent slides repeat the same conclusion
- A metric and its interpretation are separated
- Both slides are sparse (density < 0.5) and share one message
- A figure and its explanation are split without reason

### Move to appendix when
- Large raw tables, detailed formulas, long code, extended logs
- Content is evidence but not required for the main narrative

## Step 6: Select layout candidates

For each planned slide, use `references/layout_library.md` scoring model:
1. Get compatible layouts from the compatibility matrix (section 6)
2. Score each candidate (section 7)
3. Apply hard rejection rules (section 7.1)
4. Select the highest-scoring layout that passes rejection checks

## Output: slide plan

Each slide must have a plan entry in this structure:

```json
{
  "id": "s-003",
  "purpose": "evidence",
  "topic": "Performance Benchmarks",
  "title": "Latency reduced by 20% in staging",
  "message": "Performance tests confirm a 20% latency reduction after the optimization.",
  "visual_type": "data_chart",
  "rendering_method": "html_css_svg",
  "estimated_density": 0.82,
  "density_classification": "moderate",
  "layout": "evidence-kpi-row",
  "layout_variant": "full-width-three-metrics",
  "split_from": null,
  "merged_with": null,
  "appendix": false,
  "content_blocks": ["paragraph", "metric:20%", "metric:3.3V", "metric:LQFP32"],
  "planning_notes": "Three KPIs fit a horizontal row; no split needed."
}
```

## Verification checklist

Before proceeding to rendering, verify:
- Every slide has exactly one purpose
- Every slide has a one-sentence message
- No `section_divider` contains dense content
- All density > 1.5 slides have been split or moved to appendix
- All sparse slides have been evaluated for merge
- All layouts have been scored and pass hard rejection rules
