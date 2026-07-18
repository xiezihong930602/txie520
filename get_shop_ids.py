"""获取所有店铺ID——用于硬编码"""
import sys, os, time, json
ROOT = r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from playwright.sync_api import sync_playwright
from config.settings import MIAOSHOU_BASE_URL

STATE_FILE = os.path.join(ROOT, "storage_state.json")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        storage_state=STATE_FILE if os.path.exists(STATE_FILE) else None,
        viewport={"width": 1920, "height": 1080}
    )
    page = context.new_page()
    page.goto(f"{MIAOSHOU_BASE_URL}/pddkj/item/item", timeout=30000)
    page.wait_for_timeout(3000)

    # 打开创建弹窗：通过点击页面上第一个可用的创建按钮
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button, a');
        for (const b of btns) {
            if (b.innerText && b.innerText.includes('发布产品')) {
                b.click();
                return;
            }
        }
        // fallback: click 创建发布
        const all = document.body.innerText;
    }""")
    page.wait_for_timeout(2000)

    # 打开店铺级联面板
    page.evaluate("""() => {
        const inputs = document.querySelectorAll('input');
        for (const inp of inputs) {
            if ((inp.placeholder||'').includes('请选择或输入搜索')) {
                inp.click();
                break;
            }
        }
    }""")
    page.wait_for_timeout(1000)

    # 点击"店铺"展开子列表
    page.evaluate("""() => {
        const nodes = document.querySelectorAll('.el-cascader-node');
        for (const nd of nodes) {
            const lb = nd.querySelector('.el-cascader-node__label');
            if (lb && (lb.innerText||'').trim() === '店铺') {
                lb.click();
                break;
            }
        }
    }""")
    page.wait_for_timeout(1500)

    # 获取所有子节点
    shops = page.evaluate("""() => {
        const nodes = document.querySelectorAll('.el-cascader-node');
        const result = [];
        for (const nd of nodes) {
            const lb = nd.querySelector('.el-cascader-node__label');
            const txt = (lb?.innerText||'').trim();
            if (!txt || txt === '店铺' || txt === '店铺分组') continue;
            // 尝试从Vue component获取value
            let val = '';
            const cascader = document.querySelector('.jx-pro-cascader');
            if (cascader) {
                let el = cascader, vue = null;
                for (let i = 0; i < 10; i++) {
                    vue = el.__vue__ || (el._vnode?.component?.proxy);
                    if (vue) break;
                    el = el.parentElement;
                    if (!el) break;
                }
                if (vue && vue.cachedOptions) {
                    // 搜索children
                    const search = (opts) => {
                        if (!opts) return;
                        for (const o of opts) {
                            if (o.label === txt) { val = o.value; return; }
                            if (o.children) search(o.children);
                        }
                    };
                    search(vue.cachedOptions);
                }
            }
            if (!val) {
                // fallback: from DOM
                val = nd.getAttribute('data-value') || '';
            }
            result.push({label: txt, value: val});
        }
        return result;
    }""")

    print("\n=== 店铺ID列表 ===")
    for s in shops:
        print(f"  {s['label']}: {s['value']}")

    print(f"\n共 {len(shops)} 个店铺")
    print("\n使用方式：在 _select_shop 中把 '14255039' 替换为目标店铺的 value")

    browser.close()
