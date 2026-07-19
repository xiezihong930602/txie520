from playwright.sync_api import sync_playwright
import time

p = sync_playwright().start()
b = p.chromium.launch(headless=False, slow_mo=200)
ctx = b.new_context(storage_state="storage_state.json", viewport={"width": 1920, "height": 1080})
page = ctx.new_page()
page.goto("https://erp.91miaoshou.com/pddkj/move_collect/template_management/sizeChart", wait_until="domcontentloaded")
time.sleep(5)
page.screenshot(path="size_template_page.png", full_page=True)
print("=== DONE ===")
b.close()
