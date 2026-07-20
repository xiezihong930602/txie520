"""诊断店铺选择区域DOM — 运行后等浏览器打开，你手动点「创建产品」"""
from playwright.sync_api import sync_playwright
import time, json

state = r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2\storage_state.json"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        r"C:\Users\Administrator\.doubao\chats\temp_playwright_diag",
        channel="chrome", headless=False,
        args=["--start-maximized"]
    )
    page = ctx.new_page()
    page.goto("https://erp.91miaoshou.com/pddkj/item/item")
    print("浏览器已打开，请手动点击「创建产品」，然后回来按 Enter 继续...")
    input("按 Enter 继续...")

    time.sleep(3)

    # Dump 店铺选择区域所有标签和×按钮
    info = page.evaluate("""() => {
        const result = {};
        
        // 1. 找所有tag（标签）
        const tags = [];
        document.querySelectorAll('.jx-tag, .el-tag, [class*="tag"]').forEach(t => {
            const r = t.getBoundingClientRect();
            if (r.height > 5) {
                const html = t.outerHTML.substring(0, 500);
                const icons = [];
                t.querySelectorAll('.jx-icon, .el-icon, svg, path, [class*="close"]').forEach(i => {
                    icons.push({cls: i.className?.baseVal||i.className||'', tag: i.tagName, html: i.outerHTML.substring(0,200)});
                });
                tags.push({text: (t.innerText||'').substring(0,50), top: r.top, left: r.left, w: r.width, h: r.height, html, icons});
            }
        });
        result.tags = tags;
        
        // 2. 找所有cascader
        const cascaders = [];
        document.querySelectorAll('.jx-cascader, .el-cascader, [class*="cascader"]').forEach(c => {
            const r = c.getBoundingClientRect();
            if (r.height > 5 && r.top < 300) {
                const inputs = [];
                c.querySelectorAll('input').forEach(i => {
                    inputs.push({placeholder: i.placeholder, readonly: i.readOnly, value: i.value || ''});
                });
                cascaders.push({top: r.top, w: r.width, html: c.outerHTML.substring(0,300), inputs});
            }
        });
        result.cascaders = cascaders;
        
        return result;
    }""")

    print(json.dumps(info, ensure_ascii=False, indent=2))
    ctx.close()