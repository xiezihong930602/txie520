"""尺码表诊断 - 检查创建按钮点击后发生了什么"""
import os, sys, time
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2")
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright

SIZE_CHART_URL = "https://erp.91miaoshou.com/pddkj/move_collect/template_management/sizeChart"
STATE_FILE = ROOT / "storage_state.json"

p = sync_playwright().start()
b = p.chromium.launch(headless=False, slow_mo=200)
ctx = b.new_context(storage_state=str(STATE_FILE), viewport={"width": 1920, "height": 1080})
page = ctx.new_page()
page.goto(SIZE_CHART_URL, wait_until="domcontentloaded")
time.sleep(4)

page.screenshot(path=str(ROOT / "diag_0_before.png"))

# 检查创建按钮
btn_info = page.evaluate("""() => {
    const btns = document.querySelectorAll('button');
    for (const b of btns) {
        if (b.innerText.includes('创建尺码表模板')) {
            return {text: b.innerText, visible: b.getBoundingClientRect().width > 0, disabled: b.disabled};
        }
    }
    return null;
}""")
print(f"按钮: {btn_info}")

# 点击
page.locator("button:has-text('创建尺码表模板')").first.click(force=True)
time.sleep(2)

# screenshot after
page.screenshot(path=str(ROOT / "diag_1_after_click.png"))

# dump所有弹窗
dlg_info = page.evaluate("""() => {
    const ds = document.querySelectorAll('.el-dialog__wrapper, .jx-dialog__wrapper, [role="dialog"]');
    return Array.from(ds).map((d, i) => ({
        index: i,
        visible: d.getBoundingClientRect().height > 100,
        display: d.style.display,
        h: d.getBoundingClientRect().height,
        hasInput: d.querySelectorAll('input').length,
        text: d.innerText.substring(0, 200)
    }));
}""")
print(f"弹窗: {dlg_info}")

# 检查页面是否有遮罩/loading
overlay_info = page.evaluate("""() => {
    const els = document.querySelectorAll('.jx-overlay, .el-overlay, .el-loading-mask, [class*="mask"], [class*="loading"]');
    return Array.from(els).filter(e => e.getBoundingClientRect().height > 50).map(e => ({
        class: e.className?.substring(0, 60),
        h: e.getBoundingClientRect().height,
        visible: e.style.display !== 'none'
    }));
}""")
print(f"遮罩: {overlay_info}")

print("\n=== 诊断截图已保存 ===")
b.close()
p.stop()
