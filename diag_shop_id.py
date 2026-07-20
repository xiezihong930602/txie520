"""从jx-cascader Vue组件获取Noble Boys店铺ID"""
import sys, os, time, json
ROOT = r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from playwright.sync_api import sync_playwright
from config.settings import MIAOSHOU_BASE_URL

STATE_FILE = os.path.join(ROOT, "storage_state.json")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=100)
    context = browser.new_context(
        storage_state=STATE_FILE if os.path.exists(STATE_FILE) else None,
        viewport={"width": 1920, "height": 1080}
    )
    page = context.new_page()
    page.goto(f"{MIAOSHOU_BASE_URL}/pddkj/item/item", timeout=30000)
    page.wait_for_timeout(5000)

    # 打开创建弹窗
    try:
        page.get_by_text("创建产品").first.click(timeout=5000)
    except:
        page.get_by_text("发布产品").first.click(timeout=5000)
    page.wait_for_timeout(3000)

    # 从jx-cascader的Vue实例读取所有options
    result = page.evaluate("""() => {
        const cascaders = document.querySelectorAll('.jx-cascader');
        for (const cas of cascaders) {
            // 找到Vue实例
            let el = cas;
            for (let i = 0; i < 10; i++) {
                const vue = el.__vue__ || (el._vnode?.component?.proxy);
                if (vue && vue.options) {
                    const opts = vue.options;
                    const shops = [];
                    // 递归提取
                    const extract = (list, depth) => {
                        for (const o of list) {
                            shops.push({label: o.label, value: o.value, depth: depth});
                            if (o.children) {
                                const children = Array.isArray(o.children) ? o.children : Object.values(o.children);
                                extract(children, depth + 1);
                            }
                        }
                    };
                    extract(opts, 0);
                    return {
                        method: 'vue.options',
                        shopCount: shops.length,
                        shops: shops
                    };
                }
                el = el.parentElement;
                if (!el) break;
            }
        }
        return {error: 'no vue instance found'};
    }""")

    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 备用方式：打开级联面板从DOM读
    print("\n=== 备用: 打开级联面板读DOM ===")
    try:
        shop_input = page.locator(".jx-form-item").filter(has_text="店铺").locator("input").first
        shop_input.click(force=True)
        page.wait_for_timeout(1500)
        
        items = page.evaluate("""() => {
            const result = [];
            // 找所有级联面板
            const panels = document.querySelectorAll('.jx-cascader-panel, .el-cascader-panel, .jx-cascader-menu, [class*="cascader-menu"]');
            for (const p of panels) {
                const r = p.getBoundingClientRect();
                if (r.height < 20) continue;
                const nodes = p.querySelectorAll('.el-cascader-node, .jx-cascader-node, li[class*="cascader"]');
                for (const n of nodes) {
                    const label = n.querySelector('.el-cascader-node__label, span')?.innerText?.trim() || '';
                    const val = n.getAttribute('data-value') || n.getAttribute('data-node-value') || '';
                    if (label) result.push({label, value: val});
                }
            }
            // 也搜 el-select-dropdown
            const dds = document.querySelectorAll('.jx-select-dropdown, .el-select-dropdown');
            for (const dd of dds) {
                const r = dd.getBoundingClientRect();
                if (r.height < 20) continue;
                const items = dd.querySelectorAll('li');
                for (const li of items) {
                    const txt = (li.innerText || '').trim();
                    if (txt) result.push({label: txt, from: 'dropdown'});
                }
            }
            return result;
        }""")
        print(json.dumps(items, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"备用方式失败: {e}")

    print("\n10秒后自动关闭...")
    time.sleep(10)
    browser.close()
