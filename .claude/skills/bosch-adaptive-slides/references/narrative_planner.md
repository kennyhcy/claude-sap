# Narrative Planner & Layout Selector Prompt

Your task is to take a semantic array of slide candidates and select the most appropriate visual layout for each slide based on the Bosch template components.

## Available Layouts

### Standard Layouts
- `cover-simple`: First slide.
- `section-banner`: Big title divider.
- `two-col`: Side-by-side text/tables.
- `three-col`: Three columns.
- `panel`: Simple bordered box.
- `cards`: Grid of cards.
- `number-grid`: KPI dashboard.
- `timeline`: For project phases.
- `matrix-wrap`: 4-quadrant risk matrix.
- `arch`: Architectural layers.
- `flow`: Step-by-step process.
- `chart-grid`: Side-by-side charts.
- `checklist`: Action items.
- `roadmap`: Long-term phase plan.
- `end-page`: Thank you / Q&A.

### Image-Aware Layouts
- `image-hero`: Full-width image as primary message, minimal text.
  - Variants: `full-bleed`, `contained-with-caption`
- `image-text-split`: Image on one side, text on the other.
  - Variants: `image-left-50`, `image-left-60`, `image-right-50`, `image-right-60`, `image-top`, `image-bottom`
- `image-comparison`: Two images side by side for comparison.
- `image-grid`: 2-4 images in a grid.
  - Variants: `grid-2`, `grid-3`, `grid-2x2`
- `image-annotated`: Image with explanatory callout annotations.
- `image-caption-focus`: Image with detailed caption/description below.

## Image-Text Layout Selection

When a slide candidate has an image intent, apply these rules:

### Step 1: Determine image intent
- If text is minimal (caption only) and image is landscape → `image_dominant`
- If text and image both carry meaning → `image_text_pair`
- If two images compare states/options → `image_comparison`
- If 3-4 images support one point → `image_gallery`
- If image needs labeled annotations → `image_annotated`

### Step 2: Select the best image (if multiple candidates)
Score each image by:
- **Semantic relevance (35%)**: keyword overlap between image metadata and slide content
- **Aspect ratio fit (20%)**: does the image orientation match the candidate layout?
- **Resolution adequacy (15%)**: is the image large enough for the canvas?
- **Contextual proximity (15%)**: does the image appear under the same heading in source?
- **Visual diversity (15%)**: avoid repeating the same image across slides

Select the highest-scoring image. Record rejected alternatives with reasons.

### Step 3: Determine image-text balance
- Landscape image + low text → image occupies >= 70% of safe area → `image-hero`
- Landscape image + high text → `image-text-split` with `image-top` variant
- Portrait image + medium text → `image-text-split` with `image-right-50` or `image-left-50`
- Square image + medium text → `image-caption-focus` or `image-text-split`
- Two images → `image-comparison`
- 3-4 images → `image-grid`

### Step 4: Generate content HTML
- Wrap content inside the appropriate layout tags (e.g. `<div class="image-text-split image-text-right">...</div>`)
- Use `<img src="..." alt="..." class="slide-img" />` for images
- Add image to the `content_html` property in the `slide_manifest.json`

## Rules
1. Match the content density to the layout structure. Use CSS grid classes provided by the template.
2. Never stretch or distort images. Always preserve aspect ratio with `object-fit: contain`.
3. Do not reuse the same image on more than 2 slides unless intentionally repeated.
4. If no suitable image is found for an image-intent slide, fall back to a structured HTML/CSS visual or a clean typographic layout.
5. Record the selected image ID and rejected alternatives in the slide manifest.
