import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # Use your machine's already installed Google Chrome (no download required!)
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page()

    # Load local HTML file from your exact directory
    file_path = os.path.abspath("D:/Linkdin-Automation/Job-Post-Design/Design-Template/index.html")
    page.goto(f"file:///{file_path}", wait_until="domcontentloaded")

    # Target the middle card container
    # (Update this selector with the exact class name of your card container from index.html)
    middle_card = page.locator(".bg-gradient-to-tr")

    # Capture screenshot of just that element
    middle_card.screenshot(path="middle-card.png")

    browser.close()
    print("Middle card captured successfully using local Chrome!")