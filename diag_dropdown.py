"""探测 keyboard.type 后出现的浮层 DOM"""
import sys, os, time, json
ROOT = r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from executors.rpa_publisher import RpaPublisherExecutor

executor = RpaPublisherExecutor(config={"headless": False, "slow_mo": 100})
executor._init_browser()
executor._open_create_page()

page = executor.page

# 删 tag
print("[1] 删tag...")
try:
    page.locator(".jx-form-item").filter(has_text="店铺").locator(".jx-tag i.jx-tag__close").first.click(force=True, timeout=3000)
except:
    pass
time.sleep(0.5)

# 点击搜索框 + keyboard.type
print("[2] 输入 Noble Boys...")
search_input = page.locator(".jx-form-item").filter(has_text="店铺").locator(".jx-cascader__search-input").first
search_input.click(force=True)
time.sleep(0.5)
page.keyboard.type("Noble Boys", delay=30)

# 立即多次dump浮层
for delay in [0.5, 1.0, 1.5, 2.0]:
    time.sleep(0.5)
    info = page.evaluate("""() => {
        const r = {};
        // 搜所有可见的popup/dropdown/popper/panel元素
        const all = document.querySelectorAll('[class*="dropdown"], [class*="popper"], [class*="popup"], [class*="panel"], [class*="menu"], [class*="listbox"], [role="listbox"], [role="menu"], [role="option"]');
        r.elements = [];
        for (const el of all) {
            const rect = el.getBoundingClientRect();
            if (rect.height < 10) continue;
            const txt = (el.innerText || '').trim().slice(0, 100);
            r.elements.push({
                tag: el.tagName,
                classes: el.className?.slice(0, 120) || '',
                id: el.id || '',
                role: el.getAttribute('role') || '',
                text: txt,
                rect: {x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)}
            });
        }
        // 也搜body下新增的可见子元素
        const bodyKids = document.body.querySelectorAll(':scope > *');
        for (const kid of bodyKids) {
            const rect = kid.getBoundingClientRect();
            if (rect.height < 10 || kid.tagName === 'SCRIPT') continue;
            const txt = (kid.innerText || '').trim().slice(0, 80);
            if (kid.className && kid.className.includes('dropdown')) continue; // already captured
            r.elements.push({
                tag: kid.tagName,
                classes: kid.className?.slice(0, 120) || '',
                text: txt,
                rect: {x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)}
            });
        }
        return r;
    }""")
    print(f"\n  [t+{delay*1000:.0f}ms] 可见浮层: {len(info['elements'])}个")
    for el in info['elements']:
        print(f"    {el['tag']} {el['classes'][:60]} | text={el['text'][:50]} | rect={el['rect']}")

# 截图
page.screenshot(path=os.path.join(ROOT, "diag_dropdown.png"))
print(f"\n截图: {os.path.join(ROOT, 'diag_dropdown.png')}")
time.sleep(10)
executor.browser.close()
