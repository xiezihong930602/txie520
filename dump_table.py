# -*- coding: utf-8 -*-
"""dump尺码表格DOM结构"""
import time, json
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

# 取消全选
try:
    page.locator(".pro-virtual-table__checkbox.is-checked .jx-checkbox__inner").first.click(timeout=3000)
except:
    pass
time.sleep(0.3)

# 滚到120区域 + 勾选
page.evaluate("""() => {
    const scroller = document.querySelector('.vue-recycle-scroller');
    if (!scroller) return;
    scroller.scrollTop = 3000;
}""")
time.sleep(1)

page.evaluate("""() => {
    const scroller = document.querySelector('.vue-recycle-scroller');
    if (!scroller) return;
    const items = scroller.querySelectorAll('.vue-recycle-scroller__item-view');
    for (const item of items) {
        const txt = item.innerText.trim();
        if (txt.startsWith('120')) {
            const cb = item.querySelector('.jx-checkbox__inner');
            if (cb) cb.click();
            break;
        }
    }
}""")
time.sleep(0.5)

# dump表格结构
dump = page.evaluate("""() => {
    const items = document.querySelectorAll('.vue-recycle-scroller__item-view');
    const result = [];
    for (let i = 0; i < Math.min(items.length, 5); i++) {
        const item = items[i];
        const cells = item.querySelectorAll('[class*="table__cell"], [class*="cell"], [class*="column"]');
        const cellInfo = Array.from(cells).slice(0, 8).map(c => ({
            tag: c.tagName,
            classPrefix: c.className?.split(' ')[0]?.substring(0, 40) || '',
            text: (c.innerText || '').trim().substring(0, 20)
        }));
        result.push({
            index: i,
            cells: cellInfo,
            fullText: item.innerText.trim().substring(0, 200),
            hasInput: item.querySelectorAll('input').length,
            html_snippet: item.innerHTML.substring(0, 500)
        });
    }
    return JSON.stringify(result, null, 2);
}""")
print(dump[:5000])

b.close()
p.stop()
