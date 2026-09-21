from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # 1. Launch your local system Chrome (bypasses browser download blocks)
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page()

    # 2. Set viewport size wide and tall enough for the canvas
    page.set_viewport_size({"width": 1280, "height": 1000})

    # 3. Securely format the local Windows file path into a file:// URI
    html_path = Path("D:/Linkdin-Automation/Job-Post-Design/Design-Template/index.html").resolve()
    page.goto(html_path.as_uri(), wait_until="domcontentloaded")

    # 4. Target the main card container by its ID
    job_card = page.locator("#job-post-card")
    job_card.wait_for(state="visible", timeout=15000)

    # 5. Capture a clean, precise screenshot of the entire job post card
    job_card.screenshot(path="full-job-post.png")

    browser.close()
    print("Full job post card captured successfully as 'full-job-post.png'!")