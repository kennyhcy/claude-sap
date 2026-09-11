# Bosch Adaptive Slides: Layout Library and Optimization Guide

> Version: 1.0.0  
> Scope: Layout selection, visual balance, safe-area usage, validation, and automatic repair  
> Intended integration: `bosch-adaptive-slides`  
> Recommended location: `references/layout_library.md`

## 1. Purpose

This library extends the slide generation skill with a reusable, content-adaptive layout system. It is designed to prevent slides that are technically valid but visually weak, including:

- large isolated whitespace regions
- unbalanced left and right columns
- oversized panels with insufficient content
- decorative icons floating without semantic purpose
- section dividers mixed with detailed content
- title hierarchy duplicated within one slide
- content concentrated in one quadrant
- layouts selected only by content type, without considering density

This library does not define a fixed deck sequence. It provides layout primitives, selection rules, quality metrics, and repair strategies that can be applied to any narrative.

---

## 2. Integration Contract

The layout library must run after semantic slide planning and before final rendering.

```text
Markdown parsing
  -> semantic document tree
  -> slide candidates
  -> layout library selection
  -> HTML rendering
  -> visual validation
  -> automatic repair
  -> export
```

For each slide candidate, the planner should provide:

```json
{
  "id": "s-006",
  "purpose": "content",
  "topic": "Device Selection & Main Controller Applicability",
  "title": "Key Components & Controller Constraints",
  "message": "The selected MCU package, clock accuracy, and voltage satisfy the controller constraints.",
  "content_blocks": [],
  "visual_intent": "technical_summary",
  "estimated_density": 0.42,
  "required_visuals": 1,
  "appendix": false
}
```

The layout engine should return:

```json
{
  "layout_id": "evidence-kpi-row",
  "variant": "balanced-60-40",
  "regions": {},
  "quality_prediction": {
    "occupancy": 0.58,
    "density_balance": 0.81,
    "visual_balance": 0.87
  }
}
```

---

## 3. Layout Design Principles

### 3.1 One slide, one primary purpose

Each slide must have one of the following purposes:

```yaml
slide_purpose:
  - cover
  - agenda
  - section_divider
  - content
  - evidence
  - decision
  - summary
  - appendix
  - closing
```

A slide must not combine a `section_divider` purpose with dense `content`, `evidence`, or `decision` blocks.

### 3.2 One slide, one dominant message

The slide title, supporting text, and visual structure must reinforce the same conclusion. If two independent conclusions are present, split the slide.

### 3.3 Layout follows density

Layout selection must consider:

- number of semantic blocks
- text volume
- number of metrics
- number and aspect ratios of visuals
- table dimensions
- hierarchy depth
- expected content occupancy
- visual weight distribution

### 3.4 Empty space must be intentional

Whitespace is valid when it separates hierarchy or emphasizes a focal message. Large accidental gaps between unrelated blocks are a validation failure.

### 3.5 Decorative elements require a role

An icon must support navigation, meaning, comparison, status, or grouping. Remove isolated decorative icons that do not improve comprehension.

---

## 4. Safe Area and Region Model

The library must use the safe content region extracted from the source template. Do not use the full slide canvas as the available content area.

```json
{
  "canvas": {
    "width_px": 1365,
    "height_px": 768
  },
  "safe_area": {
    "x": 80,
    "y": 185,
    "width": 1205,
    "height": 500
  },
  "protected_regions": [
    "topic_zone",
    "title_zone",
    "footer_zone",
    "logo_zone",
    "supergraphic_zone",
    "page_number_zone"
  ]
}
```

The exact coordinates must be extracted from the supplied template and must not be assumed globally.

---

## 5. Layout Catalog

### 5.1 `section-divider-hero`

**Purpose**

Create a clear transition between major sections.

**Use when**

- a new major section begins
- the section title is sufficient as the primary message
- a conceptual visual can establish context

**Structure**

```text
[Section number or short label]
[Large section title]
[Optional one-line orientation statement]
[Optional full-width or side visual]
```

**Constraints**

```yaml
max_body_paragraphs: 1
max_metrics: 0
max_tables: 0
max_dense_panels: 0
```

**Reject when**

- detailed controller parameters are included
- comparison content is included
- a KPI panel is required
- more than one paragraph is needed

**Repair**

Keep the divider and move the detailed content to the following slide.

---

### 5.2 `statement-support`

**Purpose**

Present one dominant conclusion with concise supporting evidence.

**Use when**

- the content is sparse
- one strong message matters more than a complex diagram
- the slide contains one conclusion and two to four supporting points

**Structure**

```text
[Conclusion title]
[Short explanation]
[2 to 4 supporting facts or callouts]
```

**Recommended occupancy**

```yaml
min: 0.40
ideal: 0.52
max: 0.68
```

---

### 5.3 `balanced-two-column`

**Purpose**

Present two content groups with comparable visual weight.

**Use when**

- left and right sections are semantically parallel
- predicted density ratio is no greater than 2.0
- both regions contain meaningful content

**Variants**

```yaml
variants:
  - 50-50
  - 55-45
  - 60-40
  - 40-60
```

**Selection rules**

```yaml
50-50: density_ratio <= 1.25
55-45: density_ratio <= 1.60
60-40: density_ratio <= 2.00
```

**Reject when**

- one column is decorative only
- one column has less than 20 percent of total visual weight
- the predicted density ratio exceeds 2.5
- a large empty central band is produced

---

### 5.4 `evidence-kpi-row`

**Purpose**

Show a technical conclusion followed by a compact row of metrics.

**Use when**

- there are two to four metrics
- metrics share a common subject
- each metric has a short label
- the narrative benefits from reading title, explanation, then evidence

**Structure**

```text
[Conclusion or technical message]
[Short explanation]
[Metric 1] [Metric 2] [Metric 3]
```

**Example content**

```text
LQFP32 | Standard package
±1.0%  | HSI16 clock precision
3.3 V  | MCU domain voltage
```

**Rules**

- use equal-height metric cells
- align values on a shared baseline
- use concise labels
- avoid wrapping a label beyond two lines
- avoid placing three metrics in one oversized empty panel

---

### 5.5 `evidence-side-panel`

**Purpose**

Pair an explanation with a dense and meaningful supporting panel.

**Use when**

- the panel contains a diagram, screenshot, annotated component, or at least four related evidence items
- the panel uses at least 65 percent of its allocated region
- the left and right visual weight ratio is no greater than 2.5

**Reject when**

- the panel contains only two or three short metrics
- the panel height greatly exceeds the content height
- the panel is used only to fill space

**Preferred fallback**

Use `evidence-kpi-row` or `statement-support`.

---

### 5.6 `comparison-split`

**Purpose**

Compare two alternatives, states, products, or solutions.

**Use when**

- both sides share comparison dimensions
- both sides have comparable data completeness
- a clear conclusion is available

**Rules**

- use synchronized row order
- keep equivalent labels aligned
- visually distinguish the recommended option only when supported by source content
- do not invent scores or rankings

---

### 5.7 `process-flow`

**Purpose**

Explain a sequence, lifecycle, or decision flow.

**Use when**

- there are three to seven ordered steps
- sequence matters
- each step can be expressed concisely

**Variants**

```yaml
variants:
  - horizontal
  - vertical
  - swimlane
  - loop
```

Choose the variant based on step count, label length, and role count.

---

### 5.8 `architecture-canvas`

**Purpose**

Display a system architecture, interface map, or layered technical model.

**Use when**

- relationships are more important than prose
- the visual requires most of the slide width
- the source contains grounded components and connections

**Rules**

- reserve the full content width for the architecture
- keep explanatory text in short callouts or speaker notes
- prevent lines from crossing labels
- keep interface names legible
- move detailed mappings to the appendix when necessary

---

### 5.9 `table-focus`

**Purpose**

Present a readable table that is essential to the slide message.

**Use when**

- the table is the primary evidence
- the table fits above minimum typography
- the highlighted rows or columns support the conclusion

**Reject when**

- the table requires body text below the minimum font size
- raw detail is not needed for the main narrative
- the table exceeds the safe width or height

**Repair**

Summarize the main finding and move the full table to the appendix.

---

### 5.10 `visual-explainer`

**Purpose**

Use one major visual with concise annotations.

**Use when**

- an image, diagram, screenshot, or illustration carries the message
- the visual can occupy at least 55 percent of the safe area
- annotations are grounded in source content

**Rules**

- preserve aspect ratio
- do not stretch visuals
- avoid duplicated hero visuals across slides
- place source information in notes or the manifest

---

### 5.11 `decision-recommendation`

**Purpose**

Present a recommendation, rationale, trade-offs, and next action.

**Structure**

```text
[Recommendation]
[Why]
[Trade-offs or conditions]
[Next action]
```

**Rules**

- do not infer a recommendation absent from the source
- distinguish facts, assumptions, and unresolved items
- mark missing required values as `TBD`

---

### 5.12 `appendix-reference`

**Purpose**

Preserve detailed technical material without interrupting the main narrative.

**Use when**

- content includes raw tables, logs, code, mappings, formulas, or secondary scenarios
- the material is useful as supporting evidence

**Rules**

- preserve Bosch branding and page numbering
- identify the related main-deck slide when possible
- retain source labels and units

---

### 5.13 `image-hero`

**Purpose**

Present a single full-width image as the primary message with minimal supporting text.

**Use when**

- one image carries the slide message
- the image is landscape orientation (aspect ratio >= 1.3)
- text content is one or two lines (title-level takeaway only)
- the image has high semantic relevance to the slide topic

**Structure**

```text
[Topic]
[Title: concise takeaway]
[Full-width image occupying >= 70% of safe area]
[Optional one-line caption or source note]
```

**Variants**

```yaml
variants:
  - full-bleed: image spans entire safe-area width, text overlaid at top
  - contained-with-caption: image in a bordered box, caption below
```

**Reject when**

- the image is portrait orientation (would leave large side gaps)
- more than two paragraphs of text are required
- the image aspect ratio would require cropping the focal subject
- the image has been used on a previous slide (unless intentionally repeated)

---

### 5.14 `image-text-split`

**Purpose**

Pair an image with explanatory text in a two-region layout.

**Use when**

- both image and text carry meaning
- the text density is moderate (1 to 4 paragraphs or bullet groups)
- an image and text reinforce the same conclusion

**Variants and split ratios**

```yaml
variants:
  image-left-50:     "image left, text right, 50-50 split"
  image-left-60:     "image left, text right, 60-40 split (image dominant)"
  image-right-50:    "text left, image right, 50-50 split"
  image-right-60:    "text left, image right, 60-40 split (text dominant)"
  image-top:         "image on top spanning full width, text below"
  image-bottom:      "text on top, image below spanning full width"
```

**Variant selection rules**

```yaml
image-left-50:  text_density_ratio <= 1.25 AND image_is_portrait_or_square
image-left-60:  text_density_ratio < 0.80 AND image_is_landscape
image-right-50: text_density_ratio <= 1.25 AND image_is_portrait_or_square
image-right-60: text_density_ratio > 1.25 AND image_is_landscape
image-top:      image_is_landscape AND text_density > 1.5 (text-heavy)
image-bottom:   image_is_landscape AND text_density < 0.7 (image-heavy, text is caption)
```

Where:
- `text_density_ratio` = estimated text region density / estimated image region density
- `image_is_landscape` = image aspect_ratio >= 1.3
- `image_is_portrait` = image aspect_ratio <= 0.8
- `image_is_square` = 0.8 < aspect_ratio < 1.3

**Reject when**

- the image region would be less than 30% of the split (image too small to read)
- the text region would be less than 25% of the split (text cramped against image)
- the image aspect ratio conflicts with the chosen split direction
- both regions contain only sparse content

---

### 5.15 `image-comparison`

**Purpose**

Show two images side by side for comparison (before/after, option A/B, two states).

**Use when**

- two images share a comparison dimension
- each image has a short label
- a conclusion or takeaway is available

**Structure**

```text
[Title: comparison conclusion]
[Image A] [Image B]
[Label A] [Label B]
[Optional one-line takeaway]
```

**Rules**

- use equal column widths
- align images on a shared top edge
- keep labels concise (one line each)
- do not invent scores or rankings not in the source
- prefer images with similar aspect ratios

---

### 5.16 `image-grid`

**Purpose**

Display two to four images in a grid layout.

**Use when**

- multiple images support the same point
- a gallery or evidence collection is the message
- each image has a short caption

**Variants**

```yaml
variants:
  grid-2: "2 images side by side"
  grid-3: "3 images in a row"
  grid-2x2: "4 images in a 2x2 grid"
```

**Rules**

- use consistent cell sizes
- align captions below each image
- keep total image count between 2 and 4
- move excess images to the appendix

---

### 5.17 `image-annotated`

**Purpose**

Present an image with explanatory callout annotations pointing to specific regions.

**Use when**

- the image requires labeled explanations
- specific areas of the image need identification
- annotations are grounded in source content

**Structure**

```text
[Title]
[Image with overlaid or adjacent callout annotations]
[Optional legend or summary]
```

**Rules**

- annotations must not obscure the focal subject
- use consistent annotation styling (Bosch blue callout boxes)
- keep annotation labels concise
- place the source image at sufficient resolution for legibility

---

### 5.18 `image-caption-focus`

**Purpose**

Present an image with a detailed caption or description below it.

**Use when**

- the image needs textual explanation
- the caption is more than one line but less than a paragraph
- the image is the primary content, the caption is secondary

**Structure**

```text
[Title]
[Image spanning 55-75% of safe-area width]
[Caption text below image, centered or left-aligned]
[Optional source note]
```

**Rules**

- image occupies the upper region
- caption uses caption typography (smaller, muted color)
- do not let the caption exceed 3 lines
- prefer centered image when caption is short

---

## 6. Layout Compatibility Matrix

```yaml
intent_layout_compatibility:
  section_transition:
    preferred: [section-divider-hero]
    forbidden: [evidence-side-panel, table-focus, comparison-split]

  technical_summary:
    preferred: [evidence-kpi-row, statement-support, evidence-side-panel]

  comparison:
    preferred: [comparison-split, table-focus]

  process:
    preferred: [process-flow, visual-explainer]

  architecture:
    preferred: [architecture-canvas, visual-explainer]

  decision:
    preferred: [decision-recommendation, statement-support]

  sparse_message:
    preferred: [statement-support, visual-explainer]
    discouraged: [balanced-two-column, table-focus]

  detailed_reference:
    preferred: [appendix-reference, table-focus]

  image_dominant:
    preferred: [image-hero, image-caption-focus]
    discouraged: [balanced-two-column, evidence-kpi-row]

  image_text_pair:
    preferred: [image-text-split, image-caption-focus]
    discouraged: [table-focus, appendix-reference]

  image_comparison:
    preferred: [image-comparison, image-grid]
    forbidden: [image-hero, statement-support]

  image_gallery:
    preferred: [image-grid, appendix-reference]
    discouraged: [image-hero, image-text-split]

  image_annotated:
    preferred: [image-annotated, image-text-split]
    discouraged: [image-hero]
```

The matrix provides candidates only. Final selection must use density and visual-balance scoring.

---

## 7. Layout Scoring Model

Use a scoring model instead of a fixed mapping.

```text
layout_score =
  semantic_fit          * 0.22
+ readability           * 0.18
+ visual_balance        * 0.16
+ density_balance       * 0.14
+ occupancy_fit         * 0.10
+ source_component_reuse* 0.06
+ audience_fit          * 0.05
+ editability           * 0.04
+ brand_consistency     * 0.05
- overflow_penalty
- sparsity_penalty
- complexity_penalty
- purpose_conflict_penalty
```

All positive scores are normalized to the range `0.0` to `1.0`.

### 7.1 Hard rejection rules

Reject a layout candidate before scoring when any condition is true:

```yaml
hard_reject:
  - content_overlaps_protected_region
  - predicted_font_below_minimum
  - section_divider_contains_dense_content
  - required_visual_aspect_ratio_is_broken
  - table_cannot_fit_safe_area
  - predicted_density_ratio_above_3_0
  - empty_column_detected
  - image_cropped_beyond_focal_subject
  - image_resolution_below_canvas_requirement
  - image_text_split_with_empty_text_region
  - repeated_hero_image_without_intent
```

---

## 7A. Image Selection Engine

### 7A.1 Image asset model

Every image available to the deck must be registered as an asset before layout selection:

```json
{
  "image_assets": [
    {
      "id": "img-001",
      "src": "assets/architecture.png",
      "alt": "System architecture diagram",
      "width_px": 1200,
      "height_px": 800,
      "aspect_ratio": 1.50,
      "orientation": "landscape",
      "context_heading": "System Architecture",
      "keywords": ["architecture", "system", "diagram", "layers"],
      "source": "user-provided",
      "used_on_slides": []
    }
  ]
}
```

The asset registry is built from:
- Markdown image syntax `![alt](url)`
- Front matter `images:` field
- Explicit `<!-- image: path -->` directives
- Files discovered in a configured `assets/` directory

### 7A.2 Image orientation classification

```yaml
orientation:
  landscape: aspect_ratio >= 1.30
  square: 0.80 < aspect_ratio < 1.30
  portrait: aspect_ratio <= 0.80
```

### 7A.3 Image selection scoring

When a slide has an `image_*` visual intent and multiple candidate images exist, score each image:

```text
image_score =
  semantic_relevance      * 0.35
  + aspect_ratio_fit       * 0.20
  + resolution_adequacy    * 0.15
  + contextual_proximity   * 0.15
  + visual_diversity       * 0.15
  - repetition_penalty
  - low_resolution_penalty
```

#### Semantic relevance (0.35 weight)

Score how well the image matches the slide topic, title, and content:

```text
semantic_relevance =
  keyword_overlap_score
  * heading_match_boost
  * content_context_boost
```

- `keyword_overlap_score`: ratio of shared keywords between image metadata (alt text, filename tokens) and slide content
- `heading_match_boost`: 1.2 if the image's `context_heading` matches the slide topic; 1.0 otherwise
- `content_context_boost`: 1.15 if the image appears in the source Markdown under the same heading as the slide content

#### Aspect ratio fit (0.20 weight)

Score how well the image orientation matches the candidate layout:

```yaml
landscape_image:
  image-hero: 1.0
  image-text-split (image-top/bottom): 0.9
  image-text-split (image-left/right): 0.6
  image-comparison: 0.8

portrait_image:
  image-text-split (image-left/right): 1.0
  image-hero: 0.3
  image-caption-focus: 0.7

square_image:
  image-text-split: 0.85
  image-grid: 0.9
  image-caption-focus: 0.8
  image-hero: 0.5
```

#### Resolution adequacy (0.15 weight)

```yaml
resolution:
  adequate: min(width_px, height_px) >= 600
  marginal: 400 <= min(width_px, height_px) < 600
  insufficient: min(width_px, height_px) < 400
```

Map to score: adequate = 1.0, marginal = 0.6, insufficient = 0.2.

#### Contextual proximity (0.15 weight)

Score based on how close the image is to the slide content in the source document:

```yaml
proximity:
  same_section: 1.0
  adjacent_section: 0.7
  deck_global: 0.4
  external_asset: 0.3
```

#### Visual diversity (0.15 weight)

Penalize reusing the same image on multiple slides:

```yaml
diversity:
  first_use: 1.0
  second_use: 0.4
  third_plus_use: 0.0
```

#### Penalties

```yaml
repetition_penalty: 0.15 if image used on immediately preceding slide
low_resolution_penalty: 0.20 if resolution is insufficient for the chosen layout
```

### 7A.4 Image-text balance rules

After selecting the image, determine the image-text split balance:

```text
text_density =
  normalized_character_count
  + weighted_bullet_count * 2
  + paragraph_count * 3

image_weight =
  image_region_percentage_of_safe_area
  * orientation_fit_factor
```

Balance rules:

```yaml
rules:
  - if text_density > 1.5 AND image is landscape:
      prefer image-top or image-bottom (full-width image, text gets priority)
  - if text_density < 0.7 AND image is landscape:
      prefer image-hero (image dominant, text is caption)
  - if text_density is 0.7 to 1.5 AND image is portrait:
      prefer image-left or image-right with 45-55 split
  - if text_density is 0.7 to 1.5 AND image is landscape:
      prefer image-text-split with image-top or image-bottom
  - if text_density < 0.5:
      image should occupy >= 65% of safe area
  - if text_density > 2.0:
      image should occupy <= 40% of safe area, consider moving detail to notes
```

### 7A.5 Image-aware layout selection flow

```text
1. Build image asset registry from source Markdown and assets directory
2. For each slide candidate with image intent:
   a. Classify image intent (image_dominant, image_text_pair, image_comparison, image_gallery, image_annotated)
   b. Score all candidate images using image selection scoring (7A.3)
   c. Select the highest-scoring image
   d. Determine image-text balance using 7A.4
   e. Select the image-text layout variant using 5.13-5.18 variant rules
   f. Predict quality (occupancy, density_balance, visual_weight)
   g. Run standard layout scoring (section 7) with image-aware penalties
3. Record image selection reasoning in the slide manifest
```

### 7A.6 Image fallback strategy

When no suitable image is found:

```yaml
fallback_order:
  1. Generate a structured HTML/CSS/SVG visual from source content
  2. Use a clean typographic composition (statement-support or evidence-kpi-row)
  3. Use a placeholder ONLY when the source explicitly references a missing image
```

Never invent an image source URL. Never use a placeholder image when the source does not reference one.

---

## 8. Visual Quality Metrics

### 8.1 Occupancy ratio

Measure the union of visible content bounds inside the safe area.

```text
occupancy_ratio = occupied_content_area / safe_content_area
```

Recommended interpretation:

```yaml
occupancy:
  dense: "> 0.72"
  healthy: "0.45 to 0.72"
  sparse: "0.32 to 0.45"
  under_utilized: "< 0.32"
```

Low occupancy alone does not fail a valid cover, section divider, or statement slide. The threshold must depend on slide purpose.

```yaml
minimum_occupancy_by_purpose:
  cover: 0.25
  section_divider: 0.25
  statement: 0.35
  content: 0.45
  evidence: 0.48
  appendix: 0.42
```

### 8.2 Density balance

For layouts with multiple primary regions:

```text
density_balance = min(region_density) / max(region_density)
```

```yaml
interpretation:
  good: ">= 0.60"
  acceptable: "0.40 to 0.60"
  warning: "0.33 to 0.40"
  fail: "< 0.33"
```

A `density_balance` below `0.33` represents an imbalance greater than approximately `3:1`.

### 8.3 Visual weight balance

Suggested base weights:

```yaml
visual_weight:
  title: 5
  subtitle: 2
  body_paragraph: 3
  bullet_group: 4
  metric: 4
  kpi_card: 5
  table: 7
  chart: 8
  diagram: 8
  image: 8
  icon: 1
```

Adjust the base weight using rendered area, color contrast, and typographic emphasis.

```text
adjusted_weight =
base_weight
* normalized_rendered_area
* contrast_factor
* emphasis_factor
```

Fail when one primary region has more than four times the visual weight of another primary region, unless the layout intentionally defines one dominant hero visual.

### 8.4 Quadrant heatmap

Divide the safe area into four quadrants and calculate the proportion of visual weight in each region.

```text
+-------------+-------------+
| Q1          | Q2          |
+-------------+-------------+
| Q3          | Q4          |
+-------------+-------------+
```

Trigger review when:

```yaml
quadrant_warning:
  - max_quadrant_weight > 0.50
  - max_quadrant_weight > 2.2 * average_quadrant_weight
```

Do not apply this rule mechanically to intentional hero layouts.

### 8.5 Empty region detection

Detect contiguous empty rectangles after subtracting content bounds from the safe area.

Trigger repair when a non-intentional empty region:

```yaml
large_empty_region:
  width_ratio: "> 0.25"
  height_ratio: "> 0.45"
  isolated_between_content_groups: true
```

### 8.6 Alignment quality

Validate:

- shared left edges
- shared top edges
- common baselines for KPI values
- consistent gutters
- consistent card padding
- stable title-to-content spacing

Reject one-off offsets that are not required by hierarchy.

### 8.7 Panel utilization

```text
panel_utilization = panel_content_bounds / panel_inner_area
```

```yaml
panel_utilization:
  healthy: ">= 0.55"
  warning: "0.35 to 0.55"
  fail: "< 0.35"
```

A tall side panel containing only three short KPI rows should normally be replaced by a horizontal KPI row or a smaller panel.

---

## 9. Section Divider Guard

Detect section divider intent using title semantics and content structure.

```yaml
section_divider_signals:
  - explicit_section_heading
  - chapter_number
  - short_section_subtitle
  - no_evidence_required
  - narrative_transition
```

When the score exceeds the configured threshold:

```yaml
slide_purpose: section_divider
allowed_content:
  - section_number
  - section_title
  - one_line_orientation
  - one_conceptual_visual
forbidden_content:
  - dense_paragraph
  - metric_panel
  - table
  - architecture
  - comparison
  - detailed_evidence
```

If forbidden content exists, automatically produce two slide candidates:

```text
Slide N: section divider
Slide N+1: detailed content
```

---

## 10. Automatic Repair Strategy

Apply repairs in the following order.

### 10.1 Purpose repair

1. Detect mixed slide purposes.
2. Separate section transition from detailed content.
3. Separate executive conclusion from technical evidence when both are dense.

### 10.2 Layout repair

1. Remove unsupported decorative elements.
2. Select a better layout family.
3. Adjust column ratio using predicted density.
4. Convert a tall sparse side panel into a horizontal KPI row.
5. Expand a meaningful visual when source fidelity permits.

### 10.3 Content repair

1. Remove accidental duplication.
2. Shorten wording without changing meaning.
3. Convert prose into structured points.
4. Move secondary detail to notes or appendix.
5. Split the slide when one message cannot be maintained.

### 10.4 Spacing repair

1. Normalize region gaps.
2. Reduce excessive panel padding.
3. Restore aligned edges and baselines.
4. Keep minimum readable typography.

### 10.5 Last-resort typography repair

Reduce font size only after all structural repairs fail. Never go below the configured minimum.

```yaml
typography_minimums:
  topic_px: 34
  title_px: 22
  body_px: 17
  caption_px: 13
```

---

## 11. Validation Pipeline Extension

Add the following validation stage after the existing structural and overflow checks.

### Stage F.2: Layout Quality Validation

Required checks:

```yaml
checks:
  - slide_purpose_consistency
  - occupancy_ratio
  - density_balance
  - visual_weight_balance
  - quadrant_heatmap
  - empty_region_detection
  - panel_utilization
  - alignment_quality
  - decorative_element_relevance
  - title_hierarchy_consistency
```

### Failure conditions

```yaml
fail_when:
  content_slide_occupancy_below: 0.45
  primary_region_density_balance_below: 0.33
  unintended_visual_weight_ratio_above: 4.0
  unintended_quadrant_weight_above: 0.50
  sparse_panel_utilization_below: 0.35
  section_divider_contains_dense_content: true
  isolated_decorative_element: true
  duplicated_title_hierarchy: true
```

### Validation exceptions

Purpose-aware exceptions are allowed for:

- cover slides
- section dividers
- intentional statement slides
- hero visual slides
- closing slides

Every exception must include a reason in the slide manifest.

---

## 12. Manifest Extension

Add layout reasoning and measured quality results to each slide record.

```json
{
  "index": 6,
  "id": "s-006",
  "purpose": "evidence",
  "layout": {
    "id": "evidence-kpi-row",
    "variant": "full-width-three-metrics",
    "alternatives_rejected": [
      {
        "id": "evidence-side-panel",
        "reason": "Predicted panel utilization was below 0.35."
      }
    ]
  },
  "image": {
    "selected_id": "img-003",
    "selected_src": "assets/architecture.png",
    "selection_score": 0.82,
    "intent": "image_text_pair",
    "balance": "image-right-50",
    "alternatives_rejected": [
      {
        "id": "img-001",
        "reason": "Lower semantic relevance (0.45). Image context heading did not match slide topic."
      },
      {
        "id": "img-005",
        "reason": "Repetition penalty: used on preceding slide s-005."
      }
    ]
  },
  "quality": {
    "occupancy_ratio": 0.57,
    "density_balance": 0.78,
    "visual_weight_ratio": 1.42,
    "max_quadrant_weight": 0.34,
    "panel_utilization": null,
    "purpose_consistency": true
  },
  "repairs": [
    "Separated section divider from technical content.",
    "Converted sparse vertical KPI panel into a horizontal metric row.",
    "Removed isolated decorative icon."
  ],
  "validation": {
    "overflow": false,
    "overlap": false,
    "brand_pass": true,
    "layout_quality_pass": true
  }
}
```

---

## 13. Optimization Directions

### Priority 1: Make validation purpose-aware

Current geometric checks should not treat all slides equally. A section divider can be sparse by design, while a technical content slide should normally use more of the safe area.

**Implementation direction**

- add `slide_purpose` to every candidate
- define occupancy thresholds per purpose
- record every validation exception and its reason

### Priority 2: Add underflow detection, not only overflow detection

A slide can have no clipping and still look unfinished. Detect unused space, empty columns, sparse panels, and extremely low occupancy.

**Implementation direction**

- calculate rendered content bounds
- calculate safe-area occupancy
- detect contiguous empty regions
- trigger re-layout before adjusting font size

### Priority 3: Replace fixed columns with density-driven regions

A fixed `50-50` layout often produces a dense panel beside a sparse text block.

**Implementation direction**

- estimate region density before rendering
- test `50-50`, `55-45`, `60-40`, and reverse variants
- reject layouts with predicted imbalance above `3:1`
- render the top two candidates and compare actual measurements when confidence is low

### Priority 4: Separate section transitions from content slides

A section heading and detailed content on the same canvas create competing title hierarchies.

**Implementation direction**

- classify explicit section headings as narrative transitions
- use a `section-divider` guard
- automatically split when detailed evidence is detected

### Priority 5: Validate panel utilization

Large cards and side panels should be proportional to the amount of content inside them.

**Implementation direction**

- measure content bounds inside each panel
- re-size or replace panels below the utilization threshold
- prefer a KPI row for two to four short technical metrics

### Priority 6: Remove semantically weak decoration

A floating magnifier or similar icon adds visual noise when it does not label a function or explain a relationship.

**Implementation direction**

- require every non-background icon to have a semantic role
- remove icons that are isolated, unlabeled, and unrelated to navigation
- do not use decoration to patch empty space

### Priority 7: Use render-measure-repair loops

Predicted density is useful but cannot detect every CSS and font-rendering effect.

**Implementation direction**

```text
Plan candidate layouts
  -> render preview
  -> measure actual DOM bounds
  -> capture slide image
  -> run geometric validation
  -> perform visual review
  -> repair
  -> re-render
```

Use no more than three repair iterations per slide. If a slide still fails, split it and report the repair in the manifest.

### Priority 8: Add cross-slide rhythm checks

A single slide may look acceptable while the full deck feels inconsistent.

**Implementation direction**

- compare title positions and line counts
- compare card radii, padding, and gutters
- compare visual density across neighboring slides
- detect repeated identical layouts when narrative variety is needed
- preserve consistent section naming and page numbering

### Priority 9: Build regression tests from failure examples

Store problematic slides as test fixtures and assert that the same layout failure does not return.

**Recommended fixture categories**

```yaml
fixtures:
  - sparse_side_panel
  - mixed_section_divider_and_content
  - empty_middle_column
  - oversized_metric_card
  - duplicate_title_hierarchy
  - isolated_decorative_icon
  - unbalanced_two_column
  - content_below_safe_area
  - image_too_small_for_layout
  - image_text_split_empty_text_region
  - repeated_hero_image
  - portrait_image_in_full_width_layout
  - image_grid_with_mismatched_aspect_ratios
  - image_caption_overflow
```

### Priority 10: Distinguish predicted and measured quality

The planning layer predicts visual quality. The rendered output provides the final truth.

**Implementation direction**

```yaml
quality:
  predicted:
    occupancy: 0.55
    density_balance: 0.70
  measured:
    occupancy: 0.48
    density_balance: 0.61
```

Use measured values for final validation and manifest status.

---

## 14. Example Repair for the Observed Failure Pattern

### Detected problems

```yaml
slide_purpose_conflict:
  section_divider: true
  detailed_content: true

layout_problems:
  oversized_right_panel: true
  low_panel_utilization: true
  isolated_middle_icon: true
  large_empty_center_region: true
  duplicated_title_hierarchy: true
```

### Recommended transformation

```text
Before
  One slide combines:
  - Section 2 heading
  - section subtitle
  - chapter label
  - detailed content title
  - explanatory paragraph
  - large right KPI panel
  - isolated decorative icon

After
  Slide A: Section divider
  - Section 2
  - Device Selection & Main Controller Applicability
  - optional relevant visual

  Slide B: Technical content
  - Key Components & Controller Constraints
  - concise technical explanation
  - full-width three-metric evidence row
```

### Recommended layout for Slide B

```text
[Topic]
[Title: Key Components & Controller Constraints]

[One or two-line takeaway]

[LQFP32]          [±1.0%]               [3.3 V]
Standard package  HSI16 clock precision MCU domain voltage
```

This transformation removes competing title levels, improves occupancy, strengthens reading order, and gives each slide one clear purpose.

---

## 15. Suggested Skill Package Structure

```text
bosch-adaptive-slides/
├── SKILL.md
├── references/
│   └── layout_library.md
├── scripts/
│   ├── score_layouts.py
│   ├── measure_layout.py
│   ├── validate_visual_balance.py
│   └── repair_layout.py
├── schemas/
│   └── layout_quality.schema.json
└── tests/
    ├── fixtures/
    └── test_layout_quality.py
```

The main `SKILL.md` should reference this library from the layout selection, validation, repair, and acceptance-criteria sections.

---

## 16. Acceptance Criteria

The layout library is accepted when:

- section divider slides do not contain dense evidence blocks
- content slides do not contain accidental empty columns
- two-column layouts reject density imbalance above `3:1`
- sparse side panels are resized or replaced automatically
- unsupported decorative icons are removed
- occupancy is measured against the extracted safe area
- measured layout quality is recorded in the manifest
- failed layouts are repaired and re-rendered
- the final deck receives a second cross-slide consistency check
- no repair hides source content or reduces text below the minimum typography

---

## 17. Recommended Additions to the Main Skill

Add the following references to `SKILL.md`:

```md
### Layout library

Use `references/layout_library.md` as the source of truth for:

- layout candidates and compatibility
- purpose-aware occupancy thresholds
- density and visual-weight scoring
- section-divider guards
- panel-utilization checks
- layout-quality validation
- automatic repair order

A slide must pass both structural validation and layout-quality validation before export.
```

Add this requirement to the rendering workflow:

```md
#### Stage F.2: Layout Quality Validation

After structural and overflow validation, measure actual rendered occupancy,
region density balance, visual-weight balance, panel utilization, empty regions,
and alignment quality. Apply purpose-aware thresholds. Repair and re-render any
failed slide, then perform a second cross-slide consistency check.
```

Add this requirement to acceptance criteria:

```md
The deck must not contain mixed-purpose section dividers, accidental empty
columns, sparse oversized panels, unsupported decorative icons, or multi-region
density imbalance greater than 3:1.
```
