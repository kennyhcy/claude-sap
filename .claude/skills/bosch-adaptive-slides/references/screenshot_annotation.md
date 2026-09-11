# Screenshot Cropping and Annotation Guide

Rules for handling screenshots, UI captures, and diagram images that need cropping or annotated callouts to highlight key regions. Use this guide when a slide's visual type is `annotated_image` or when the source contains screenshots requiring emphasis.

## 1. When to crop

### 1.1 Crop triggers

Crop a screenshot when:

```yaml
crop_when:
  - the screenshot contains irrelevant UI chrome (toolbars, sidebars, empty space) that dilutes the focal content
  - the focal region is < 50% of the image area
  - the image resolution is high enough that cropping still leaves ≥ 600px on the shorter side
  - the user explicitly requests focusing on a specific region
```

### 1.2 Do not crop when

```yaml
do_not_crop_when:
  - the full screenshot context is needed for understanding
  - cropping would remove < 15% of the image (not worth the complexity)
  - the image is already small (shorter side < 600px)
  - the image is a diagram (not a screenshot) where all elements matter
```

### 1.3 Crop method

Use CSS `object-fit` and `object-position` to crop visually without modifying the source file:

```yaml
crop_method:
  technique: "CSS object-position with overflow hidden container"
  container: "fixed-aspect box with overflow: hidden"
  image: "object-fit: cover; object-position: <x> <y>;"
  positions:
    top_left: "0% 0%"
    top_center: "50% 0%"
    top_right: "100% 0%"
    center_left: "0% 50%"
    center: "50% 50%"
    center_right: "100% 50%"
    bottom_left: "0% 100%"
    bottom_center: "50% 100%"
    bottom_right: "100% 100%"
```

Record the crop region in the slide manifest under `image.crop`:

```json
{
  "image": {
    "selected_src": "screenshot.png",
    "crop": {
      "applied": true,
      "position": "center",
      "focus_area": "main panel showing error state",
      "reason": "Remove toolbar and sidebar to focus on the error dialog"
    }
  }
}
```

## 2. Annotation types

### 2.1 Callout box

A labeled rectangular box overlaid on a specific region of the image.

```yaml
callout_box:
  use_when: "highlighting a UI element, error region, or specific component"
  style:
    border: "2px solid #00629B"
    background: "rgba(0, 98, 155, 0.08)"
    border_radius: "4px"
  positioning:
    method: "absolute, percentage-based within image container"
    top: "percentage from image top"
    left: "percentage from image left"
    width: "percentage of image width"
    height: "percentage of image height"
  label:
    position: "outside the box, connected by a short line"
    max_text: "20 characters"
```

### 2.2 Numbered marker

A circular numbered badge placed on the image, with a corresponding legend.

```yaml
numbered_marker:
  use_when: "3–6 distinct regions need sequential identification"
  style:
    size: "28px diameter"
    background: "#00629B"
    color: "#FFFFFF"
    font: "bold 14px"
    border: "2px solid #FFFFFF"
    box_shadow: "0 1px 4px rgba(0,0,0,0.3)"
  positioning:
    method: "absolute, percentage-based"
    offset: "place at top-left of the target region"
  legend:
    position: "below or beside the image"
    format: "[1] Label text — short explanation"
    max_per_line: 3
```

### 2.3 Arrow annotation

A directional arrow pointing from a label to a target region.

```yaml
arrow_annotation:
  use_when: "a label cannot be placed directly on the region; needs a connecting line"
  style:
    color: "#00629B"
    width: "2px"
    arrowhead: "filled triangle"
  rendering: "inline SVG path within the annotation overlay"
  label:
    position: "outside the image or in margin"
    max_text: "25 characters"
```

### 2.4 Highlight overlay

A semi-transparent colored region that draws attention without a border.

```yaml
highlight_overlay:
  use_when: "emphasizing a region without obscuring it"
  style:
    background: "rgba(255, 196, 0, 0.25)"
    border: "none"
    border_radius: "4px"
  rule: "use sparingly; maximum 2 highlight regions per image"
```

## 3. Annotation positioning rules

### 3.1 Positioning method

All annotations use percentage-based absolute positioning within the image container. This ensures annotations stay correctly placed regardless of image rendering size.

```yaml
positioning:
  coordinate_system: "percentage of image container (0% to 100%)"
  origin: "top-left corner of the image"
  required_fields:
    - top: "vertical position (0-100%)"
    - left: "horizontal position (0-100%)"
    - width: "annotation width (0-100%)"
    - height: "annotation height (0-100%)"
```

### 3.2 Layout constraints

```yaml
constraints:
  max_annotations_per_image: 6
  min_annotation_spacing: "8px between adjacent annotations"
  no_overlap: "annotation boxes must not overlap each other"
  within_bounds: "annotations must be within 5%–95% of image area (avoid edges)"
  label_readability: "label text must not overlap the image content it annotates"
```

### 3.3 Annotation z-index

```yaml
z_index_order:
  1: image (base layer)
  2: highlight overlays
  3: callout boxes
  4: numbered markers
  5: arrow labels (text)
```

## 4. Annotation data model

Each annotated slide records its annotations in the manifest:

```json
{
  "layout": "image-annotated",
  "image": {
    "selected_src": "dashboard.png",
    "selected_id": "img-003",
    "intent": "image_annotated",
    "crop": {
      "applied": true,
      "position": "center",
      "reason": "Focus on main dashboard panel"
    }
  },
  "annotations": [
    {
      "type": "callout_box",
      "id": "ann-1",
      "label": "Error zone",
      "position": {"top": 15, "left": 30, "width": 25, "height": 20},
      "style": "callout"
    },
    {
      "type": "numbered_marker",
      "id": "ann-2",
      "label": "Navigation bar",
      "number": 1,
      "position": {"top": 5, "left": 10, "width": 8, "height": 8},
      "style": "numbered"
    },
    {
      "type": "highlight_overlay",
      "id": "ann-3",
      "label": "KPI panel",
      "position": {"top": 60, "left": 55, "width": 30, "height": 25},
      "style": "highlight"
    }
  ],
  "annotation_legend": [
    {"number": 1, "text": "Primary navigation — all entry points start here"},
    {"number": 2, "text": "Error zone — validation failure indicator"}
  ]
}
```

## 5. Markdown directive syntax

Parse annotation directives from the source Markdown:

### 5.1 Annotation directive

```markdown
<!-- annotate: callout | label="Error zone" | top=15% left=30% width=25% height=20% -->
<!-- annotate: numbered | label="Nav bar" | number=1 | top=5% left=10% -->
<!-- annotate: highlight | label="KPI panel" | top=60% left=55% width=30% height=25% -->
```

### 5.2 Crop directive

```markdown
<!-- crop: center | reason="Focus on main dashboard panel" -->
<!-- crop: top-left | reason="Focus on error dialog in upper left" -->
```

### 5.3 Combined usage in Markdown

```markdown
## Dashboard Overview

![Dashboard screenshot](dashboard.png)

<!-- crop: center | reason="Remove sidebar to focus on main panel" -->
<!-- annotate: numbered | label="Nav bar" | number=1 | top=5% left=10% -->
<!-- annotate: callout | label="Error zone" | top=15% left=30% width=25% height=20% -->
<!-- annotate: highlight | label="KPI panel" | top=60% left=55% width=30% height=25% -->

1. Primary navigation — all entry points start here
2. Error zone — validation failure indicator
```

## 6. HTML rendering pattern

The `image-annotated` layout renders as:

```html
<div class="image-annotated">
  <div class="ia-image-wrapper">
    <img src="screenshot.png" alt="Dashboard screenshot" class="slide-img ia-img" />
    <!-- annotation overlays -->
    <div class="ia-annotation ia-callout" style="top:15%; left:30%; width:25%; height:20%;">
      <span class="ia-callout-label">Error zone</span>
    </div>
    <div class="ia-annotation ia-numbered" style="top:5%; left:10%;">
      <span class="ia-number">1</span>
    </div>
    <div class="ia-annotation ia-highlight" style="top:60%; left:55%; width:30%; height:25%;"></div>
  </div>
  <div class="ia-legend">
    <div class="ia-legend-item"><span class="ia-number-sm">1</span> Primary navigation — all entry points start here</div>
    <div class="ia-legend-item"><span class="ia-number-sm">2</span> Error zone — validation failure indicator</div>
  </div>
</div>
```

The CSS for these classes is injected by `scripts/render_html.py` when the `image-annotated` layout is detected.

## 7. Quality checks for annotated slides

```yaml
annotation_quality:
  - annotations must not obscure the focal content they describe
  - annotation labels must be legible (≥ 13px equivalent)
  - numbered markers must have corresponding legend entries
  - no more than 6 annotations per image
  - annotations must be within the image bounds (5%–95%)
  - annotation colors must have adequate contrast against the image background
  - the legend must not overflow the slide safe area
  - if cropping is applied, the focal content must remain fully visible
```

## 8. Fallback

When annotation data is incomplete or positions cannot be determined:
1. Fall back to `image-text-split` with the image and explanatory text
2. If no image is available, use `statement-support` or `evidence-kpi-row`
3. Never fabricate annotation positions for regions the source does not describe
