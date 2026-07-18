# 专门探测尺码区结构
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
import time

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", 
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_drivers"))

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage_state.json")

def save_screenshot(page, name):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{name}.png")
    page.screenshot(path=path, full_page=True)
    print(f"  截图: {name}.png")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=200,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
        )
        
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            storage_state=STATE_FILE if os.path.exists(STATE_FILE) else None
        )
        page = context.new_page()
        
        print("打开产品管理页...")
        page.goto("https://erp.91miaoshou.com/pddkj/item/item", wait_until="domcontentloaded")
        time.sleep(5)
        
        print("点击创建产品...")
        page.get_by_role("button", name="创建产品").first.click()
        time.sleep(1)
        page.wait_for_selector(".jx-dialog", state="visible", timeout=10000)
        time.sleep(1)
        
        print("引用模板...")
        page.get_by_role("button", name="引用模板").first.click()
        time.sleep(0.8)
        page.locator(".template-dropdown").first.get_by_text("男童圆领卫衣", exact=True).first.click()
        time.sleep(0.5)
        try:
            d = page.get_by_role("dialog", name="提示")
            d.wait_for(state="visible", timeout=5000)
            d.get_by_role("button", name="确定").click()
            time.sleep(7)
        except:
            pass
        
        print("切到销售属性...")
        page.locator(".jx-dialog").last.get_by_text("销售属性", exact=True).first.click()
        time.sleep(1)
        
        # 滚动到尺码区
        page.evaluate("""
            () => {
                const all = document.querySelectorAll('.jx-dialog *');
                for (const el of all) {
                    if (el.innerText && el.innerText.includes('常用尺码')) {
                        el.scrollIntoView({block: 'center'});
                        break;
                    }
                }
            }
        """)
        time.sleep(0.5)
        save_screenshot(page, "img_size_area")
        
        # 探测尺码区结构
        print("\n探测尺码区结构:")
        size_area_info = page.evaluate("""
            () => {
                const result = {tabs: [], checkboxes: []};
                
                // 找子标签（常用尺码/全部）
                const tabs = document.querySelectorAll('.jx-dialog .jx-tabs__item, .jx-dialog [role="tab"]');
                tabs.forEach(t => {
                    const rect = t.getBoundingClientRect();
                    if (rect.width > 20) {
                        result.tabs.push({
                            text: t.innerText.trim(),
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            active: t.className.includes('active') || t.className.includes('is-active')
                        });
                    }
                });
                
                // 找所有尺码checkbox
                const cbs = document.querySelectorAll('.jx-dialog input[type="checkbox"]');
                cbs.forEach(cb => {
                    const rect = cb.getBoundingClientRect();
                    // 尺码区大概在y=700~950
                    if (rect.top > 650 && rect.top < 950) {
                        const label = cb.closest('label') || cb.parentElement;
                        result.checkboxes.push({
                            text: label ? label.textContent.trim().substring(0, 10) : '?',
                            checked: cb.checked,
                            y: Math.round(rect.top)
                        });
                    }
                });
                
                return result;
            }
        """)
        
        print(f"  子标签: {size_area_info['tabs']}")
        print(f"  尺码checkbox ({len(size_area_info['checkboxes'])}个):")
        for cb in size_area_info['checkboxes'][:10]:
            print(f"    '{cb['text']}' checked={cb['checked']} y={cb['y']}")
        
        # 尝试点击"全部"标签
        all_tab = None
        for t in size_area_info['tabs']:
            if '全部' in t['text']:
                all_tab = t
                break
        
        if all_tab and not all_tab['active']:
            print(f"\n  点击'全部'标签...")
            page.mouse.click(all_tab['x'] + 20, all_tab['y'] + 15)
            time.sleep(0.5)
            save_screenshot(page, "img_size_all_tab")
        
        # 再探测一次checkbox
        print("\n  再次探测尺码checkbox:")
        cbs2 = page.evaluate("""
            () => {
                const result = [];
                const cbs = document.querySelectorAll('.jx-dialog input[type="checkbox"]');
                cbs.forEach(cb => {
                    const rect = cb.getBoundingClientRect();
                    if (rect.top > 650 && rect.top < 950) {
                        const label = cb.closest('label') || cb.parentElement;
                        result.push({
                            text: label ? label.textContent.trim().substring(0, 10) : '?',
                            checked: cb.checked,
                            x: Math.round(rect.left),
                            y: Math.round(rect.top)
                        });
                    }
                });
                return result;
            }
        """)
        for cb in cbs2[:15]:
            print(f"    '{cb['text']}' checked={cb['checked']} at ({cb['x']},{cb['y']})")
        
        # 尝试点击110尺码
        print("\n  尝试点击110尺码...")
        clicked = page.evaluate("""
            () => {
                const cbs = document.querySelectorAll('.jx-dialog input[type="checkbox"]');
                for (const cb of cbs) {
                    const rect = cb.getBoundingClientRect();
                    if (rect.top > 650 && rect.top < 950) {
                        const label = cb.closest('label') || cb.parentElement;
                        if (label && label.textContent.trim().startsWith('110')) {
                            const r = cb.getBoundingClientRect();
                            // 返回坐标，用mouse点
                            return {x: Math.round(r.left + 5), y: Math.round(r.top + 5)};
                        }
                    }
                }
                return null;
            }
        """)
        if clicked:
            page.mouse.click(clicked['x'], clicked['y'])
            time.sleep(0.3)
            print(f"  已点击坐标 ({clicked['x']}, {clicked['y']})")
        else:
            print("  没找到110尺码")
        
        save_screenshot(page, "img_size_final")
        print("\n测试完成，浏览器保持开启")
        input("按回车关闭浏览器...")
        browser.close()

if __name__ == "__main__":
    main()
