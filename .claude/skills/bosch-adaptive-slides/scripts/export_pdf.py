import os
import sys

def export_html_to_pdf(html_path, pdf_path):
    """
    Automates HTML-to-PDF compilation using Playwright if available.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("\n[INFO] Playwright is not installed in your Python environment.")
        print("To generate PDF directly from the CLI, please install Playwright:")
        print("  pip install playwright")
        print("  playwright install")
        print("\nAlternative (No installation required):")
        print("  Open the generated HTML in Chrome/Edge, press Ctrl+P, and select 'Save as PDF'.")
        print("  The slides will format perfectly to standard pages automatically!\n")
        return False

    print(f"Exporting {html_path} to PDF via Playwright (headless Chromium)...")
    abs_html_path = os.path.abspath(html_path)
    abs_pdf_path = os.path.abspath(pdf_path)
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            # Navigate to local file
            page.goto(f"file:///{abs_html_path}")
            # Emulate screen media type so standard styles show correctly, or print styles
            page.emulate_media(media="print")
            # Wait for any rendering/scripts
            page.wait_for_timeout(1000)
            
            # Print to PDF using slide dimensions (1365px x 768px)
            page.pdf(
                path=abs_pdf_path,
                width="1365px",
                height="768px",
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"}
            )
            browser.close()
        print(f"PDF successfully exported to: {abs_pdf_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to generate PDF via Playwright: {e}")
        return False
