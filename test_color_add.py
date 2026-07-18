# 测试添加颜色行
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
import time

# 指定浏览器驱动路径
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
        
        # 1. 打开产品管理页
        print("打开产品管理页...")
        page.goto("https://erp.91miaoshou.com/pddkj/item/item", wait_until="domcontentloaded")
        time.sleep(5)
        
        # 2. 点击创建产品
        print("点击创建产品...")
        create_btn = page.get_by_role("button", name="创建产品").first
        create_btn.wait_for(state="visible", timeout=10000)
        create_btn.click()
        time.sleep(1)
        page.wait_for_selector(".jx-dialog", state="visible", timeout=10000)
        time.sleep(1)
        
        # 3. 引用模板
        print("引用模板...")
        trigger = page.get_by_role("button", name="引用模板").first
        trigger.wait_for(state="visible")
        trigger.click()
        time.sleep(0.8)
        
        menu = page.locator(".template-dropdown").first
        menu.wait_for(state="visible")
        template_item = menu.get_by_text("男童圆领卫衣", exact=True).first
        template_item.click()
        time.sleep(0.5)
        
        # 确认弹窗
        try:
            dialog = page.get_by_role("dialog", name="提示")
            dialog.wait_for(state="visible", timeout=5000)
            dialog.get_by_role("button", name="确定").click()
            time.sleep(7)
        except:
            pass
        
        # 4. 切到销售属性
        print("切到销售属性...")
        dialog_el = page.locator(".jx-dialog").last
        tab = dialog_el.get_by_text("销售属性", exact=True).first
        tab.click()
        time.sleep(1)
        save_screenshot(page, "color_test_1_sku_tab")
        
        # 5. 滚动到颜色区，点击+新增
        print("点击颜色区+新增...")
        
        # 滚动到颜色区
        page.evaluate("""
            () => {
                const all = document.querySelectorAll('.jx-dialog *');
                for (const el of all) {
                    if (el.innerText && el.innerText.includes('颜色(0)')) {
                        el.scrollIntoView({block: 'center'});
                        break;
                    }
                }
            }
        """)
        time.sleep(0.5)
        
        # 找颜色区的+新增（第一个就是颜色区的）
        add_links = page.locator(":text-is('+ 新增')").all()
        print(f"  找到 {len(add_links)} 个+新增")
        
        if add_links:
            add_links[0].click()
            time.sleep(1.5)
            save_screenshot(page, "color_test_2_after_add")
            print("  已点击第一个+新增")
            
            # 看看颜色行的结构
            color_rows = page.evaluate("""
                () => {
                    const rows = document.querySelectorAll('.jx-dialog .ant-table-tbody tr, .jx-dialog table tbody tr');
                    const result = [];
                    rows.forEach((r, i) => {
                        if (r.innerText && r.innerText.length < 200) {
                            result.push({index: i, text: r.innerText.substring(0, 100)});
                        }
                    });
                    return result;
                }
            """)
            print(f"  表格行数: {len(color_rows)}")
            for row in color_rows[:3]:
                print(f"    行{row['index']}: {row['text'][:80]}")
        else:
            print("  没找到+新增")
        
        browser.close()
        print("\n测试完成")

if __name__ == "__main__":
    main()
