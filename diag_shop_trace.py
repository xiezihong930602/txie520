"""实时跟踪店铺选择操作 — 用户手动操作时记录DOM变化、Vue状态、可用选择器"""
import sys, os, time, json
ROOT = r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from playwright.sync_api import sync_playwright
from config.settings import MIAOSHOU_BASE_URL

STATE_FILE = os.path.join(ROOT, "storage_state.json")
LOG = []

def snap(page, label):
    """快照：记录店铺级联区域关键信息"""
    info = page.evaluate("""() => {
        const r = {};
        
        // 1. 店铺form-item内的cascader
        const fis = document.querySelectorAll('.jx-form-item, .el-form-item');
        for (const fi of fis) {
            const lb = fi.querySelector('label, .el-form-item__label');
            if (!lb || !lb.innerText.includes('店铺')) continue;
            
            const tag = fi.querySelector('.jx-tag.is-closable, .jx-tag[class*="closable"]');
            r.hasTag = !!tag;
            r.tagText = tag ? (tag.innerText || '').trim() : '';
            r.tagHTML = tag ? tag.outerHTML.substring(0, 300) : '';
            
            // 关闭按钮
            const closeI = tag ? tag.querySelector('i') : null;
            r.closeHTML = closeI ? closeI.outerHTML.substring(0, 200) : '';
            r.closeClasses = closeI ? (closeI.className || '') : '';
            
            // 输入框
            const inp = fi.querySelector('input');
            r.inputValue = inp ? inp.value : '';
            r.inputPlaceholder = inp ? inp.placeholder : '';
            r.inputReadonly = inp ? inp.readOnly : null;
            r.inputClasses = inp ? inp.className : '';
            
            // cascader容器
            const cas = fi.querySelector('.jx-cascader, [class*="cascader"]');
            r.cascaderClasses = cas ? cas.className : '';
            
            // Vue实例
            if (cas) {
                let el = cas;
                for (let i = 0; i < 10; i++) {
                    const vue = el.__vue__ || (el._vnode?.component?.proxy);
                    if (vue) {
                        r.hasVue = true;
                        r.vueValue = JSON.stringify(vue.value || vue.modelValue || '');
                        r.vueKeys = Object.keys(vue).filter(k => !k.startsWith('_') && !k.startsWith('$')).slice(0, 30);
                        // 检查关键方法
                        r.hasOptions = !!vue.options;
                        r.optionsLen = vue.options ? vue.options.length : 0;
                        if (vue.options && vue.options.length > 0) {
                            r.option0 = {label: vue.options[0].label, value: vue.options[0].value};
                            if (vue.options[0].children) {
                                const kids = Array.isArray(vue.options[0].children) ? vue.options[0].children : Object.values(vue.options[0].children);
                                r.option0_childCount = kids.length;
                                r.option0_children = kids.slice(0, 5).map(c => ({label: c.label, value: c.value}));
                            }
                        }
                        break;
                    }
                    el = el.parentElement;
                    if (!el) break;
                }
            }
            if (!r.hasVue) r.hasVue = false;
            
            // 级联面板
            const panels = document.querySelectorAll('.jx-cascader-panel, .el-cascader-panel, [class*="cascader-panel"], .jx-cascader-menu__wrap');
            r.panelCount = 0;
            r.panelItems = [];
            for (const p of panels) {
                const rect = p.getBoundingClientRect();
                if (rect.height < 20) continue;
                r.panelCount++;
                r.panelRect = {x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)};
                const items = p.querySelectorAll('li, .el-cascader-node, [class*="cascader-node"]');
                for (const it of items) {
                    const txt = (it.innerText || '').trim();
                    if (txt) r.panelItems.push(txt.slice(0, 50));
                }
            }
            
            // 下拉浮层 (jx-select-dropdown)
            const dds = document.querySelectorAll('.jx-select-dropdown, .el-select-dropdown');
            r.dropdownVisible = false;
            r.dropdownItems = [];
            for (const dd of dds) {
                const rect = dd.getBoundingClientRect();
                if (rect.height < 20) continue;
                r.dropdownVisible = true;
                r.dropdownRect = {x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)};
                const lis = dd.querySelectorAll('li');
                for (const li of lis) {
                    const txt = (li.innerText || '').trim();
                    const classes = li.className;
                    if (txt) r.dropdownItems.push({text: txt, classes: classes});
                }
            }
            break;
        }
        return r;
    }""")
    LOG.append({"step": label, "info": info})
    print(f"\n{'='*60}")
    print(f"  [{label}]")
    print(f"  tag={info.get('tagText','')} | input={info.get('inputValue','')}")
    print(f"  closeBtn: {info.get('closeClasses','')}")
    if info.get('hasVue'):
        print(f"  vue.value={info.get('vueValue','')}")
    if info.get('panelCount', 0) > 0:
        print(f"  面板: {info['panelCount']}个, items={info.get('panelItems','')[:10]}")
    if info.get('dropdownVisible'):
        print(f"  下拉浮层: items={info.get('dropdownItems','')}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=100)
    context = browser.new_context(
        storage_state=STATE_FILE if os.path.exists(STATE_FILE) else None,
        viewport={"width": 1920, "height": 1080}
    )
    page = context.new_page()
    page.goto(f"{MIAOSHOU_BASE_URL}/pddkj/item/item", timeout=30000)
    page.wait_for_timeout(5000)

    print("打开创建弹窗...")
    try:
        page.get_by_text("创建产品").first.click(timeout=5000)
    except:
        page.get_by_text("发布产品").first.click(timeout=5000)
    page.wait_for_timeout(3000)

    snap(page, "0-初始状态")

    print("\n" + "="*60)
    print("请在浏览器中依次操作：")
    print("  1) 点击店铺tag的×关闭按钮 → 完成后在终端按 Enter")
    print("  2) 在搜索框输入 Noble Boys → 完成后按 Enter")
    print("  3) 点击下拉结果中的 Noble Boys → 完成后按 Enter")
    print("  4) 点击空白区域确认 → 完成后按 Enter")
    print("="*60)

    for i, desc in enumerate(["1-删tag后", "2-输入后", "3-选结果后", "4-确认后"]):
        input(f"\n>>> 操作「{desc[2:]}」完成后按 Enter...")
        snap(page, desc)

    # 最终输出
    print("\n\n========== 完整日志 (JSON) ==========")
    print(json.dumps(LOG, ensure_ascii=False, indent=2))

    # 截图
    page.screenshot(path=os.path.join(ROOT, "diag_shop_trace.png"))
    print(f"\n截图: {os.path.join(ROOT, 'diag_shop_trace.png')}")
    print("完成，浏览器保持打开10秒...")
    time.sleep(10)
    browser.close()
