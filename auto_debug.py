import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_drivers")

from playwright.sync_api import sync_playwright
import time

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage_state.json")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

def save_screenshot(page, name):
    path = os.path.join(OUT_DIR, f"{name}.png")
    page.screenshot(path=path, full_page=True)
    print(f"  截图: {name}.png")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            storage_state=STATE_FILE,
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        
        # ===== 第1步：产品列表页 =====
        print("【第1步】打开产品管理页...")
        page.goto("https://erp.91miaoshou.com/pddkj/item/item", wait_until="domcontentloaded")
        time.sleep(5)
        save_screenshot(page, "debug_1_list")
        
        # ===== 第2步：点击创建产品 =====
        print("【第2步】点击创建产品...")
        try:
            btn = page.locator("button:has-text('创建产品')").first
            btn.wait_for(state="visible", timeout=10000)
            btn.click()
            time.sleep(2)
            save_screenshot(page, "debug_2_dialog")
            print("  创建产品弹窗已打开")
        except Exception as e:
            print(f"  失败: {e}")
            save_screenshot(page, "debug_2_error")
            browser.close()
            return
        
        # ===== 第3步：点击引用模板 =====
        print("【第3步】点击引用模板...")
        try:
            # 找引用模板按钮
            trigger = page.locator(":text-is('引用模板')").locator("xpath=ancestor::button").first
            if not trigger.is_visible(timeout=2000):
                trigger = page.get_by_role("button", name="引用模板").first
            trigger.wait_for(state="visible", timeout=5000)
            trigger.click()
            time.sleep(1)
            save_screenshot(page, "debug_3_template_dropdown")
            print("  模板下拉已展开")
        except Exception as e:
            print(f"  失败: {e}")
            save_screenshot(page, "debug_3_error")
            browser.close()
            return
        
        # ===== 第4步：选择模板 =====
        print("【第4步】选择模板: 男童圆领卫衣...")
        try:
            menu = page.locator(".template-dropdown").first
            menu.wait_for(state="visible", timeout=3000)
            item = menu.get_by_text("男童圆领卫衣", exact=True).first
            item.wait_for(state="visible", timeout=3000)
            item.click()
            time.sleep(1)
            save_screenshot(page, "debug_4_template_selected")
            print("  模板已选中")
        except Exception as e:
            print(f"  失败: {e}")
            save_screenshot(page, "debug_4_error")
            browser.close()
            return
        
        # ===== 第5步：确认引用 =====
        print("【第5步】确认引用模板...")
        try:
            dialog = page.get_by_role("dialog", name="提示")
            dialog.wait_for(state="visible", timeout=5000)
            confirm_btn = dialog.get_by_role("button", name="确定")
            confirm_btn.wait_for(state="visible", timeout=3000)
            confirm_btn.click()
            # 等待模板数据加载完成，弹窗重新渲染
            time.sleep(7)
            save_screenshot(page, "debug_5_applied")
            print("  模板已引用")
        except Exception as e:
            print(f"  失败: {e}")
            save_screenshot(page, "debug_5_error")
            browser.close()
            return
        
        # ===== 第6步：切换产品信息标签 =====
        print("【第6步】切换到产品信息标签...")
        try:
            dialog = page.locator(".jx-dialog").last
            tab = dialog.get_by_text("产品信息", exact=True).first
            tab.wait_for(state="visible", timeout=10000)
            tab.click()
            time.sleep(1)
            save_screenshot(page, "debug_6_product_info")
            print("  已切换到产品信息")
        except Exception as e:
            print(f"  失败: {e}")
            save_screenshot(page, "debug_6_error")
        
        # ===== 第7步：切换销售属性标签 =====
        print("【第7步】切换到销售属性标签...")
        try:
            dialog = page.locator(".jx-dialog").last
            tab = dialog.get_by_text("销售属性", exact=True).first
            tab.wait_for(state="visible", timeout=5000)
            tab.click()
            time.sleep(1)
            save_screenshot(page, "debug_7_sku_info")
            print("  已切换到销售属性")
        except Exception as e:
            print(f"  失败: {e}")
            save_screenshot(page, "debug_7_error")
        
        # ===== 第8步：切回产品信息，填标题测试 =====
        print("【第8步】切回产品信息，测试填标题...")
        try:
            dialog = page.locator(".jx-dialog").last
            tab = dialog.get_by_text("产品信息", exact=True).first
            tab.click()
            time.sleep(0.8)
            
            # 找产品标题输入框
            title_input = page.locator("input[placeholder*='产品标题'], textarea[placeholder*='产品标题'], input[placeholder*='英语标题']").first
            title_input.wait_for(state="visible", timeout=5000)
            title_input.click()
            title_input.fill("Test Boys Hoodie Sweatshirt Pullover")
            time.sleep(0.5)
            save_screenshot(page, "debug_8_title_filled")
            print("  标题已填入")
        except Exception as e:
            print(f"  失败: {e}")
            save_screenshot(page, "debug_8_error")
        
        # ===== 第9步：切回销售属性，测试勾选尺码 =====
        print("【第9步】切回销售属性，测试勾选尺码...")
        try:
            dialog = page.locator(".jx-dialog").last
            tab = dialog.get_by_text("销售属性", exact=True).first
            tab.click()
            time.sleep(0.8)
            
            # 切换到全部尺码标签
            all_tab = page.locator(".size-area :text('全部'), .size-tab :text('全部')").first
            if all_tab.is_visible(timeout=2000):
                all_tab.click()
                time.sleep(0.3)
            
            # 勾选几个尺码（用JS直接找）
            for size in ["110", "120", "130"]:
                found = page.evaluate(f"""
                    (sizeText) => {{
                        const els = document.querySelectorAll('.jx-checkbox, input[type=checkbox]');
                        for (const el of els) {{
                            const label = el.closest('label') || el.parentElement;
                            if (label && label.textContent.trim() === sizeText) {{
                                if (!el.checked) el.click();
                                return true;
                            }}
                        }}
                        // 再试试找包含尺码文字的元素
                        const all = document.querySelectorAll('*');
                        for (const el of all) {{
                            if (el.children.length === 0 && el.textContent.trim() === sizeText) {{
                                const checkbox = el.previousElementSibling?.querySelector('input');
                                if (checkbox && !checkbox.checked) {{
                                    checkbox.click();
                                    return true;
                                }}
                            }}
                        }}
                        return false;
                    }}
                """, size)
                if found:
                    print(f"  已勾选 {size}")
                else:
                    print(f"  未找到 {size}")
            
            time.sleep(1)
            save_screenshot(page, "debug_9_sizes_selected")
            print("  尺码勾选完成")
        except Exception as e:
            print(f"  失败: {e}")
            save_screenshot(page, "debug_9_error")
        
        # ===== 第10步：切换其他信息标签，找重量字段 =====
        print("【第10步】切换其他信息标签，找重量字段...")
        try:
            dialog = page.locator(".jx-dialog").last
            tab = dialog.get_by_text("其他信息", exact=True).first
            tab.wait_for(state="visible", timeout=5000)
            tab.click()
            time.sleep(1)
            save_screenshot(page, "debug_10_other_info")
            print("  已切换到其他信息")
        except Exception as e:
            print(f"  失败: {e}")
            save_screenshot(page, "debug_10_error")
        
        # ===== 第11步：切回类别&属性，测试设置季节 =====
        print("【第11步】切回类别&属性，测试设置季节...")
        try:
            dialog = page.locator(".jx-dialog").last
            tab = dialog.get_by_text("类别&属性", exact=True).first
            tab.click()
            time.sleep(0.8)
            
            # 找到季节下拉框
            season_label = page.locator(":text-is('季节')").first
            season_label.wait_for(state="visible", timeout=5000)
            
            # 找旁边的下拉框
            season_select = season_label.locator("xpath=following-sibling::*//*[contains(@class,'select') or @role='combobox']").first
            if season_select.count() == 0:
                # 试试父元素的下一个兄弟
                season_select = season_label.locator("xpath=../following-sibling::*//*[contains(@class,'select') or @role='combobox']").first
            
            season_select.wait_for(state="visible", timeout=3000)
            season_select.click()
            time.sleep(0.5)
            
            # 下拉列表往下滚动找更多选项
            dropdown = page.locator(".jx-select-dropdown, .select-dropdown").first
            if dropdown.is_visible():
                for _ in range(3):
                    dropdown.hover()
                    page.mouse.wheel(0, 300)
                    time.sleep(0.2)
            
            time.sleep(0.3)
            save_screenshot(page, "debug_11_season_dropdown")
            print("  季节下拉已展开并滚动")
            
            # 选择"春/秋"
            option = page.locator(".jx-select-dropdown li:has-text('春/秋'), .select-dropdown li:has-text('春/秋')").first
            if option.is_visible(timeout=2000):
                option.click()
                print("  已选春/秋")
            else:
                print("  没找到春/秋选项，先关闭")
                page.keyboard.press("Escape")
            
            time.sleep(0.5)
            save_screenshot(page, "debug_11_season_selected")
        except Exception as e:
            print(f"  失败: {e}")
            save_screenshot(page, "debug_11_error")
        
        # ===== 第12步：切换产品描述，测试外包装形状 =====
        print("【第12步】切换产品描述，测试外包装形状...")
        try:
            dialog = page.locator(".jx-dialog").last
            tab = dialog.get_by_text("产品描述", exact=True).first
            tab.click()
            time.sleep(0.8)
            
            # 找到外包装形状下拉
            shape_label = page.locator(":text-is('外包装形状')").first
            shape_label.wait_for(state="visible", timeout=5000)
            
            # 找旁边的下拉框
            shape_select = shape_label.locator("xpath=../following-sibling::*//*[contains(@class,'select') or @role='combobox']").first
            shape_select.wait_for(state="visible", timeout=3000)
            shape_select.click()
            time.sleep(0.5)
            
            save_screenshot(page, "debug_12_shape_dropdown")
            print("  外包装形状下拉已展开")
            
            # 选"长方体"
            option = page.locator(".jx-select-dropdown li:has-text('长方体'), .select-dropdown li:has-text('长方体')").first
            if option.is_visible(timeout=2000):
                option.click()
                print("  已选长方体")
            else:
                print("  没找到长方体，关闭")
                page.keyboard.press("Escape")
            
            time.sleep(0.5)
            save_screenshot(page, "debug_12_shape_selected")
        except Exception as e:
            print(f"  失败: {e}")
            save_screenshot(page, "debug_12_error")
        
        # ===== 第13步：切回销售属性，找添加颜色按钮 =====
        print("【第13步】切回销售属性，查找添加颜色按钮...")
        try:
            dialog = page.locator(".jx-dialog").last
            tab = dialog.get_by_text("销售属性", exact=True).first
            tab.click()
            time.sleep(0.8)
            
            # 滚动到颜色区
            page.evaluate("""
                () => {
                    const tables = document.querySelectorAll('.jx-dialog .ant-table, .jx-dialog table');
                    for (const t of tables) {
                        if (t.innerText && t.innerText.includes('颜色')) {
                            t.scrollIntoView({block: 'center'});
                            const container = t.closest('.ant-table-body, .table-container, [class*="scroll"]');
                            if (container) {
                                container.scrollLeft = 0;
                            }
                            break;
                        }
                    }
                }
            """)
            time.sleep(0.5)
            
            # 找颜色区所有可点击元素（包括无文字图标）
            info = page.evaluate("""
                () => {
                    const result = [];
                    // 找颜色表格所在的容器
                    let container = null;
                    const allDivs = document.querySelectorAll('.jx-dialog [class*="table"]');
                    for (const d of allDivs) {
                        if (d.innerText && d.innerText.includes('颜色(')) {
                            container = d;
                            break;
                        }
                    }
                    if (!container) return {found: false};
                    
                    // 找容器内所有可点击元素
                    const clickables = container.querySelectorAll('button, [role="button"], [class*="add"], [class*="plus"]');
                    clickables.forEach((el, i) => {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            result.push({
                                text: el.innerText.trim().substring(0, 10),
                                class: el.className.substring(0, 50),
                                tag: el.tagName,
                                html: el.outerHTML.substring(0, 100)
                            });
                        }
                    });
                    return {found: true, count: clickables.length, items: result};
                }
            """)
            
            print(f"  找到颜色容器: {info['found']}")
            if info['found']:
                print(f"  可点击元素数: {info['count']}")
                for item in info['items']:
                    print(f"    [{item['tag']}] text='{item['text']}' class={item['class']}")
            
            save_screenshot(page, "debug_13_color_detail")
        except Exception as e:
            print(f"  失败: {e}")
            import traceback
            traceback.print_exc()
            save_screenshot(page, "debug_13_error")
        
        browser.close()
        print("\n调试完成")

if __name__ == "__main__":
    main()
