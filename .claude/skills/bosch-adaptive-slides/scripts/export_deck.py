import argparse
import json
import os
import sys

from inspect_template import inspect_template
from parse_markdown import parse_markdown_to_manifest
from render_html import render_deck
from export_pdf import export_html_to_pdf

def main():
    parser = argparse.ArgumentParser(description="Bosch Adaptive Slides Generator")
    parser.add_argument("--template", required=True, help="Path to the source Bosch HTML template")
    parser.add_argument("--output", help="Path to save the generated HTML deck")
    parser.add_argument("--pdf", help="Path to save the generated PDF deck")
    parser.add_argument("--format", choices=["html", "pdf", "both"], help="Specify format: html, pdf, or both")
    parser.add_argument("--department", help="Department string (e.g., PT-GT/ETD32). Overrides front matter and skips interactive prompt.")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--markdown", help="Path to source Markdown file (triggers autonomous heuristic parsing)")
    group.add_argument("--manifest", help="Path to pre-planned slide_manifest.json (LLM agent mode)")
    
    args = parser.parse_args()
    
    # Deduce base name from input for default outputs
    input_base = "deck"
    if args.markdown:
        input_base = os.path.splitext(args.markdown)[0]
    elif args.manifest:
        input_base = os.path.splitext(args.manifest)[0]
        
    print(f"Inspecting template: {args.template}")
    profile = inspect_template(args.template)
    
    if args.manifest:
        print(f"Loading slide manifest: {args.manifest}")
        with open(args.manifest, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    elif args.markdown:
        print(f"Parsing markdown: {args.markdown}")
        with open(args.markdown, 'r', encoding='utf-8') as f:
            md_text = f.read()
        manifest = parse_markdown_to_manifest(md_text)
        
    # 1. Resolve department: CLI arg > front matter > interactive prompt
    deck_metadata = manifest.get("deck_metadata", {})
    dept = deck_metadata.get("department", "").strip()

    if args.department:
        dept = args.department.strip()
    elif not dept or dept == "Bosch" or dept == "Auto-Generator":
        try:
            user_dept = input("Please enter your department (e.g., PT-GT/ETD32) [PT-GT/ETD32]: ").strip()
            dept = user_dept if user_dept else "PT-GT/ETD32"
        except (IOError, EOFError):
            dept = "PT-GT/ETD32"

    deck_metadata["department"] = dept
    
    # Default year to 2026
    if "year" not in deck_metadata:
        deck_metadata["year"] = "2026"
        
    manifest["deck_metadata"] = deck_metadata
    
    # 2. Interactive query for format if not explicitly specified
    fmt = args.format
    if not fmt:
        try:
            print("\nPlease choose output format / 请选择输出格式:")
            print("  1. HTML slide deck only (for presentations) / 仅生成 HTML 网页版")
            print("  2. PDF slide document only (for printing) / 仅生成 PDF 报告版")
            print("  3. Both HTML and PDF / HTML 和 PDF 均生成")
            choice = input("Enter choice (1/2/3) [1]: ").strip()
            if choice == "2":
                fmt = "pdf"
            elif choice == "3":
                fmt = "both"
            else:
                fmt = "html"
        except (IOError, EOFError):
            fmt = "html"
            
    # Resolve output paths based on format selection
    output_html = args.output if args.output else f"{input_base}_deck.html"
    output_pdf = args.pdf if args.pdf else f"{input_base}_deck.pdf"
    
    # If PDF only, we still need to render HTML temporarily to build the PDF
    temp_html_path = None
    if fmt == "pdf" and not args.output:
        temp_html_path = f"{input_base}_temp_deck.html"
        output_html = temp_html_path

    print(f"\nRendering {len(manifest.get('slides', []))} slides for department {dept} and year {deck_metadata['year']}...")
    html_output = render_deck(profile, manifest)
    
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_output)
        
    if fmt in ["html", "both"] or temp_html_path:
        print(f"Success! HTML deck saved to: {output_html}")
        
    if fmt in ["pdf", "both"]:
        # Run Playwright HTML -> PDF export
        export_success = export_html_to_pdf(output_html, output_pdf)
        
        # Cleanup temporary HTML if user didn't ask for HTML
        if temp_html_path and os.path.exists(temp_html_path):
            try:
                os.remove(temp_html_path)
                print("(Cleaned up temporary HTML asset)")
            except OSError:
                pass

if __name__ == "__main__":
    main()
