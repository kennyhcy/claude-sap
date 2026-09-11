# Visual Type Selection Guide

Determine the best visual representation for each slide's content. Use this guide during Step 3 of the slide planning procedure (`references/slide_planner.md`).

## Visual type catalog

### 1. Flowchart / Process diagram
**Use when**: 3–7 ordered steps where sequence matters (lifecycle, decision flow, pipeline, state machine)
**Don't use when**: <3 steps (use bullets), >7 steps (split or use timeline), steps are unordered (use cards)
**Rendering**: HTML/CSS/SVG with flex/grid layout, or Mermaid `flowchart`

### 2. Architecture diagram
**Use when**: system layers, component relationships, interface map, data flow topology
**Don't use when**: only 2 components (use comparison), no connections between components (use cards)
**Rendering**: HTML/CSS/SVG layered grid, or Mermaid `graph`

### 3. Comparison table / Matrix
**Use when**: 2+ options evaluated against shared dimensions; side-by-side feature comparison
**Don't use when**: only 1 option (use statement), >6 rows at min font (split or move to appendix)
**Rendering**: HTML table with Bosch styling

### 4. Data chart (bar / line / pie / donut / radar)
**Use when**: numeric trends, distributions, proportions, before/after measurements, multi-dimensional comparisons
**Don't use when**: <3 data points (use KPI cards), data is categorical without quantities (use table)
**Rendering**: SVG generated from explicit numeric data in the source. Never synthesize data.

### 5. KPI cards / metric row
**Use when**: 2–4 key metrics sharing a common subject; each metric has a short label and value
**Don't use when**: >4 metrics (use table), metrics are unrelated (split the slide)
**Rendering**: HTML/CSS grid of equal-height cells

### 6. Timeline / roadmap
**Use when**: chronological events, project phases, milestone sequence with dates
**Don't use when**: <3 milestones (use bullets), events are not time-ordered (use cards)
**Rendering**: HTML/CSS horizontal or vertical timeline with phase markers

### 7. Annotated image / screenshot
**Use when**: a screenshot, photo, or diagram requires labeled callouts pointing to specific regions
**Don't use when**: image is self-explanatory (use image-hero), no annotations needed (use image-text-split)
**Rendering**: HTML/CSS with positioned overlay callouts on `<img>`. See `references/screenshot_annotation.md` for cropping and annotation rules.

### 8. Typographic composition (no visual)
**Use when**: the message is best conveyed by text alone; no visual adds explanatory value
**Don't use when**: content has inherent visual structure (process, architecture, comparison, data)
**Rendering**: Clean text layout with Bosch typography

---

## Chart type decision tree

When the visual type is `data_chart`, select the specific chart subtype using this decision tree. Evaluate in order; stop at the first match.

### Step 1: Determine data structure

```
Is the data a single proportion (parts of a whole, summing to 100%)?
  YES → Go to Pie/Donut rules
  NO → Continue

Is the data a trend over time or ordered sequence?
  YES → Go to Line/Area rules
  NO → Continue

Is the data a comparison of categories (no inherent order)?
  YES → Go to Bar rules
  NO → Continue

Is the data multi-dimensional (3+ axes/variables per item)?
  YES → Go to Radar/Spider rules
  NO → Continue

Is the data a distribution/histogram?
  YES → Use bar chart (vertical, no gaps between bars)
  NO → Default to bar chart
```

### Step 2: Chart subtype rules

#### Bar chart (vertical or horizontal)

```yaml
bar_chart:
  use_when: "comparing 2–8 categorical items with a shared numeric scale"
  min_data_points: 2
  max_data_points: 8
  vertical_bar:
    when: "category labels are short (≤12 chars) OR items are ≤5"
    advantage: "compact, easy to read value labels"
  horizontal_bar:
    when: "category labels are long (>12 chars) OR items >5"
    advantage: "labels are readable without rotation"
  grouped_bar:
    when: "2–3 series compared across the same categories"
    max_series: 3
    rule: "use distinct Bosch palette colors per series; add legend"
  stacked_bar:
    when: "showing composition within categories AND total comparison"
    rule: "ensure segments are distinguishable; add legend"
  reject_when:
    - ">8 categories (split or use table)"
    - "single data point (use KPI card)"
    - "values are percentages summing to 100% with ≤4 parts (use donut)"
```

#### Line chart

```yaml
line_chart:
  use_when: "showing trend over time, ordered sequence, or continuous variable"
  min_data_points: 3
  max_series: 4
  single_line:
    when: "one metric tracked over time"
    example: "monthly latency from Jan to Jun"
  multi_line:
    when: "2–4 metrics tracked over the same time axis"
    rule: "distinct colors per line; legend required; lines must not overlap obscuring values"
  area_chart:
    when: "emphasizing cumulative volume or proportion over time"
    rule: "use for single series only; avoid with multiple overlapping areas"
  reject_when:
    - "<3 data points (use KPI cards)"
    - ">4 series (use table or small multiples)"
    - "x-axis is categorical without order (use bar chart)"
    - "values are discrete, non-continuous (use bar chart)"
```

#### Pie / Donut chart

```yaml
pie_chart:
  use_when: "showing proportions of a whole; 3–5 parts"
  min_parts: 3
  max_parts: 5
  donut_preferred: true   # donut is visually cleaner; use by default
  rules:
    - "parts must sum to 100% (or close with a visible qualifier)"
    - "label each segment directly or with a legend"
    - "sort segments by value, largest first, starting at 12 o'clock"
    - "use Bosch palette; avoid more than 5 distinct colors"
  reject_when:
    - ">5 parts (use bar chart or treemap)"
    - "<3 parts (use KPI cards)"
    - "parts do not sum to a meaningful whole (use bar chart)"
    - "comparison between pies is needed (use grouped bar)"
```

#### Radar / Spider chart

```yaml
radar_chart:
  use_when: "comparing 2–3 entities across 4–8 qualitative dimensions"
  min_dimensions: 4
  max_dimensions: 8
  max_entities: 3
  rules:
    - "all dimensions must share a common scale (0 to max)"
    - "use translucent fills to distinguish overlapping entities"
    - "label each axis clearly"
  reject_when:
    - "<4 dimensions (use grouped bar)"
    - ">3 entities (use table)"
    - "dimensions are not comparable on the same scale (use table)"
```

### Step 3: Rendering method for charts

```yaml
chart_rendering:
  html_css_svg:
    when: "default; preferred for all generated charts"
    advantage: "full control over styling, no external dependencies, print-safe"
    data_source: "explicit numeric data from the source Markdown"
  
  inline_svg:
    when: "chart needs precise positioning or custom shapes"
    advantage: "scalable, styleable with CSS"
  
  mermaid:
    when: "source already contains a Mermaid code block for charts"
    note: "Mermaid is limited to basic bar and pie; prefer HTML/CSS/SVG for richer charts"
  
  external_library:
    when: "never — do not introduce Chart.js, ECharts, or similar runtime dependencies"
```

### Step 4: Chart data requirements

```yaml
data_requirements:
  min_data_points:
    bar: 2
    line: 3
    pie: 3
    radar: 4   # 4 dimensions minimum
  
  must_be_explicit:
    - "all numeric values must originate from user-provided source content"
    - "never interpolate, extrapolate, or synthesize missing data points"
    - "if data is insufficient for any chart type, fall back to KPI cards or a table"
  
  labeling:
    - "every axis must have a label"
    - "every data series must have a legend entry or direct label"
    - "units must be visible (%, ms, MB, count, etc.)"
    - "baseline (zero) must be visible on bar charts unless a qualifier is shown"
  
  color:
    - "use Bosch brand palette tokens from the template"
    - "maximum 5 distinct colors per chart"
    - "use color to distinguish series, not decoration"
    - "ensure adequate contrast between adjacent segments"
```

### Step 5: Chart sizing rules

```yaml
chart_sizing:
  min_chart_height_px: 200
  max_chart_height_px: 380
  min_chart_width_px: 400
  full_width_chart:
    when: "chart is the primary content of the slide"
    layout: "architecture-canvas or table-focus"
  half_width_chart:
    when: "chart is paired with text explanation"
    layout: "image-text-split or evidence-side-panel"
  chart_with_table:
    when: "chart and supporting table both needed"
    rule: "stack vertically (chart-top, table-bottom) OR side-by-side with 60-40 split"
    reject: "if both cannot fit at minimum font, move table to appendix"
```

---

## Decision matrix

Map content intent (from `references/semantic_parser.md`) to visual type:

| Content intent | Primary visual type | Fallback |
|---|---|---|
| process | flowchart | timeline (if date-ordered) |
| architecture | architecture diagram | annotated image |
| comparison | comparison table | cards |
| metrics / kpi | KPI cards | data chart |
| trend | data chart (line) | KPI cards |
| timeline / roadmap | timeline | flowchart |
| status update | KPI cards | typographic |
| decision | comparison table | typographic |
| risk | matrix (4-quadrant) | table |
| summary | typographic | KPI cards |
| context / background | typographic | annotated image |
| problem statement | typographic | flowchart |
| findings | data chart | table |
| benchmark | KPI cards | data chart |
| distribution | data chart (bar) | table |
| proportion | data chart (donut) | KPI cards |

## Rendering method selection

| Method | Use when | Data source |
|---|---|---|
| HTML/CSS/SVG | Default for all generated visuals | Content blocks in manifest |
| Mermaid | Complex graph/flowchart with many nodes | Mermaid code block in Markdown |
| Inline SVG | Custom diagrams needing precise positioning | Generated from component list |
| Image reference | User-provided screenshot/photo | Image asset registry |

**Priority**: User-provided image > HTML/CSS/SVG from source data > Mermaid > chart from numeric data > typographic.

## Data integrity rules

1. Generate charts only from data explicitly provided by the user
2. Never synthesize, extrapolate, or interpolate missing data points
3. Preserve original units, labels, ranges, and comparison baselines
4. Mark approximate or incomplete data with a visible qualifier (e.g., "~", "approx.")
5. Add a `source` note in speaker notes or the slide manifest for every generated visual
6. If data is insufficient for a chart, fall back to KPI cards or typographic layout
7. When multiple chart types are viable, prefer the one that communicates the conclusion most directly (e.g., donut for proportions, line for trends, bar for comparisons)
