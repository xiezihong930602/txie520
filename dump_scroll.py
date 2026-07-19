# -*- coding: utf-8 -*-
"""诊断虚拟滚动容器属性"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2")
STATE_FILE = ROOT / "storage_state.json"

p = sync_playwright().start()
b = p.chromium.launch(headless=False, slow_mo=200)
ctx = b.new_context(storage_state=str(STATE_FILE), viewport={"width": 1920, "height": 1080})
page = ctx.new_page()
page.goto("https://erp.91miaoshou.com/pddkj/move_collect/template_management/sizeChart", wait_until="domcontentloaded")
time.sleep(4)

page.get_by_role("button", name="创建尺码表模板").click()
time.sleep(2)
page.get_by_role("textbox", name="*模板名称").fill("儿童拉毛卫衣")
page.get_by_role("textbox", name="*类目").fill("男童时尚帽衫")
time.sleep(2)
page.locator("li:has-text('男童时尚帽衫')").first.click(timeout=5000)
time.sleep(1.5)

for param in ["胸围全围(cm)", "衣长(cm)", "袖长(cm)", "肩宽(cm)"]:
    try:
        page.locator(f"label:has-text('{param}') .jx-checkbox__inner").click(timeout=2000)
        time.sleep(0.15)
    except:
        pass
time.sleep(1)

# dump所有可滚动容器
info = page.evaluate("""() => {
    const result = [];
    const all = document.querySelectorAll('*');
    for (const el of all) {
        const cs = getComputedStyle(el);
        if (cs.overflowY === 'auto' || cs.overflowY === 'scroll' || el.className?.includes('scroll')) {
            const r = el.getBoundingClientRect();
            result.push({
                tag: el.tagName,
                class: el.className?.substring(0, 100),
                height: r.height,
                scrollHeight: el.scrollHeight,
                scrollTop: el.scrollTop,
                clientHeight: el.clientHeight,
                childCount: el.children.length
            });
        }
    }
    return JSON.stringify(result, null, 2);
}""")
print(info[:5000])

b.close()
p.stop()
