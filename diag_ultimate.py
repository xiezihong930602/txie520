"""终极诊断：标签页切换 + 坐标 + Vue实例 + 面板diff"""
import sys, os, time, json
ROOT = r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from executors.rpa_publisher import RpaPublisherExecutor

executor = RpaPublisherExecutor(config={"headless": False, "slow_mo": 100})
executor._init_browser()
executor._open_create_page()
page = executor.page

# === 0. 切标签页 ===
print("=== 0. 切换标签页 ===")
executor._switch_tab("类别&属性")
time.sleep(1)

# 验证
active_tab = page.evaluate("""() => {
    const active = document.querySelector('.scroll-menu-nav__item.is-active');
    return active ? active.innerText.trim() : 'none';
}""")
print(f"  当前激活标签页: {active_tab}")

# === 1. Dump 坐标 ===
print("\n=== 1. 元素坐标 ===")
shop_form = page.locator(".jx-form-item").filter(has_text="店铺")

# Cascader
try:
    cas_box = shop_form.locator(".jx-cascader").first.bounding_box()
    print(f"  cascader box: {cas_box}")
except Exception as e:
    print(f"  cascader box: ERROR {e}")

# Close button
try:
    cb_box = shop_form.locator(".jx-tag i.jx-tag__close").first.bounding_box()
    print(f"  close btn box: {cb_box}")
except Exception as e:
    print(f"  close btn box: ERROR {e}")

# Input
try:
    ib = shop_form.locator(".jx-cascader__search-input").first.bounding_box()
    print(f"  search-input box: {ib}")
except:
    pass

# === 2. 搜 Vue 实例（所有可能路径） ===
print("\n=== 2. Vue 实例搜索 ===")
vue_info = page.evaluate("""() => {
    const cas = document.querySelector('.jx-cascader');
    if (!cas) return {error: 'no cascader'};
    
    const result = {tag: cas.tagName, classes: cas.className};
    
    // 方法1: __vue__ 在 cascader 自身上
    if (cas.__vue__) {
        const v = cas.__vue__;
        result.method1 = {
            hasValue: !!v.value,
            value: JSON.stringify(v.value),
            hasOptions: !!v.options,
            optionsLen: v.options ? v.options.length : 0,
            keys: Object.keys(v).filter(k => !k.startsWith('_') && !k.startsWith('$')).slice(0, 20)
        };
    }
    
    // 方法2: 向上找 __vue__
    let el = cas;
    for (let i = 0; i < 15; i++) {
        if (el.__vue__) {
            const v = el.__vue__;
            result.method2 = {depth: i, elTag: el.tagName, 
                hasValue: !!v.value,
                value: JSON.stringify(v.value),
                hasOptions: !!v.options,
                optionsLen: v.options ? v.options.length : 0,
                keys: Object.keys(v).filter(k => !k.startsWith('_') && !k.startsWith('$')).slice(0, 30)
            };
            break;
        }
        el = el.parentElement;
        if (!el) break;
    }
    
    // 方法3: Vue 3 _vnode.component
    if (cas._vnode && cas._vnode.component) {
        const comp = cas._vnode.component;
        result.method3 = {
            hasProxy: !!comp.proxy,
            proxyKeys: comp.proxy ? Object.keys(comp.proxy).filter(k => !k.startsWith('_') && !k.startsWith('$')).slice(0, 20) : [],
            hasSetupState: !!comp.setupState,
            setupKeys: comp.setupState ? Object.keys(comp.setupState).slice(0, 20) : []
        };
    }
    
    // 方法4: __vue_app__ (Vue 3)
    const appRoot = document.querySelector('#app') || document.body;
    if (appRoot.__vue_app__) {
        result.method4 = {hasVueApp: true};
    }
    
    // 方法5: 搜 data-v- 属性上的实例
    const dvEl = cas.closest('[data-v-]');
    if (dvEl) {
        if (dvEl.__vue__) {
            result.method5 = {found: true, tag: dvEl.tagName};
        }
    }
    
    // 方法6: $parent / $children (从任何已知Vue实例)
    const allEls = document.querySelectorAll('[data-v-]');
    for (const el of allEls) {
        if (el.__vue__ && el.__vue__.$children) {
            for (const child of el.__vue__.$children) {
                if (child.$el && child.$el.classList && child.$el.classList.contains('jx-cascader')) {
                    result.method6 = {
                        found: true,
                        hasValue: !!child.value,
                        value: JSON.stringify(child.value),
                        hasOptions: !!child.options,
                        optionsLen: child.options ? child.options.length : 0
                    };
                    break;
                }
            }
        }
        if (result.method6) break;
    }
    
    return result;
}""")
print(json.dumps(vue_info, ensure_ascii=False, indent=2))

# === 3. 尝试 JS 打开面板 ===
print("\n=== 3. 尝试打开面板 ===")
# 直接用 JS 调用可能的展开方法
panel_result = page.evaluate("""() => {
    const cas = document.querySelector('.jx-cascader');
    if (!cas) return 'no_cascader';
    
    // 尝试所有可能的方法
    const methods = ['toggleDropDownVisible', 'handlePick', 'expand', 'open', 'show'];
    let el = cas;
    for (let i = 0; i < 15; i++) {
        if (el.__vue__) {
            const vue = el.__vue__;
            const tried = [];
            for (const m of methods) {
                if (typeof vue[m] === 'function') {
                    tried.push(m);
                    vue[m]();
                }
            }
            if (tried.length > 0) return 'called: ' + tried.join(', ');
            return 'no_methods, keys: ' + Object.keys(vue).filter(k => typeof vue[k] === 'function').slice(0, 20).join(', ');
        }
        el = el.parentElement;
        if (!el) break;
    }
    return 'no vue instance found';
}""")
print(f"  {panel_result}")

time.sleep(1)

# === 4. Before/After diff ===
print("\n=== 4. 面板出现前后 diff ===")
before = set(page.evaluate("""() => {
    return Array.from(document.querySelectorAll('body *')).map(el => el.className?.toString()?.slice(0, 60) || '').filter(c => c.includes('cascader') || c.includes('panel') || c.includes('dropdown') || c.includes('menu'));
}"""))
print(f"  点击前级联相关类: {len(before)}个")

# 点 cascader
cas_box = shop_form.locator(".jx-cascader").first.bounding_box()
if cas_box:
    page.mouse.click(cas_box['x'] + cas_box['width']/2, cas_box['y'] + 20)
time.sleep(1.5)

after = set(page.evaluate("""() => {
    return Array.from(document.querySelectorAll('body *')).map(el => el.className?.toString()?.slice(0, 60) || '').filter(c => c.includes('cascader') || c.includes('panel') || c.includes('dropdown') || c.includes('menu'));
}"""))
print(f"  点击后级联相关类: {len(after)}个")
new_items = after - before
print(f"  新增: {list(new_items)[:20]}")

# === 5. 截图 ===
page.screenshot(path=os.path.join(ROOT, "diag_ultimate.png"))
print(f"\n截图: {os.path.join(ROOT, 'diag_ultimate.png')}")
time.sleep(10)
executor.browser.close()
