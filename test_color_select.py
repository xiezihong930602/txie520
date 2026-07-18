# 测试颜色选择 - 按文字找创建自定义颜色
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
        
        # 1. 打开产品管理页
        print("打开产品管理页...")
        page.goto("https://erp.91miaoshou.com/pddkj/item/item", wait_until="domcontentloaded")
        time.sleep(5)
        
        # 2. 创建产品
        create_btn = page.get_by_role("button", name="创建产品").first
        create_btn.wait_for(state="visible")
        print("点击创建产品...")
        create_btn.click()
        time.sleep(1)
        page.wait_for_selector(".jx-dialog", state="visible", timeout=10000)
        time.sleep(1)
        
        # 3. 引用模板
        print("引用模板...")
        trigger = page.get_by_role("button", name="引用模板").first
        trigger.click()
        time.sleep(0.8)
        menu = page.locator(".template-dropdown").first
        menu.get_by_text("男童圆领卫衣", exact=True).first.click()
        time.sleep(0.5)
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
        dialog_el.get_by_text("销售属性", exact=True).first.click()
        time.sleep(1)
        
        # 5. 添加颜色行
        print("添加颜色行...")
        page.evaluate("""
            () => {
                const all = document.querySelectorAll('.jx-dialog *');
                for (const el of all) {
                    if (el.innerText && el.innerText.includes('颜色(')) {
                        el.scrollIntoView({block: 'center'});
                        break;
                    }
                }
            }
        """)
        time.sleep(0.3)
        page.locator(":text-is('+ 新增')").first.click()
        time.sleep(1)
        
        # 6. 输入颜色名
        print("输入颜色名: 白色...")
        color_input_pos = page.evaluate("""
            () => {
                const inputs = document.querySelectorAll('.jx-dialog input');
                for (const inp of inputs) {
                    const ph = inp.placeholder || '';
                    if (ph.includes('颜色') || ph.includes('自定义')) {
                        const rect = inp.getBoundingClientRect();
                        return {x: Math.round(rect.left + 20), y: Math.round(rect.top + rect.height/2)};
                    }
                }
                return null;
            }
        """)
        
        if color_input_pos:
            page.mouse.click(color_input_pos['x'], color_input_pos['y'])
            time.sleep(0.3)
            page.keyboard.type("白色")
            time.sleep(1.2)  # 等下拉列表完全渲染
            save_screenshot(page, "img_color_list")
            
            # 按文字找"创建自定义颜色"，取坐标
            print("  查找创建自定义颜色选项...")
            custom_pos = page.evaluate("""
                () => {
                    const all = document.querySelectorAll('*');
                    let best = null;
                    for (const el of all) {
                        const text = el.innerText ? el.innerText.trim() : '';
                        if (!text || el.children.length > 0) continue;
                        // 前缀匹配：创建自定义颜色-xxx
                        if (text.startsWith('创建自定义颜色') ||
                            text.includes('创建自定义颜色-')) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 20 && rect.height > 10) {
                                // 取y最大的（最下面那个）
                                if (!best || rect.top > best.y) {
                                    best = {
                                        x: Math.round(rect.left + rect.width / 2),
                                        y: Math.round(rect.top + rect.height / 2),
                                        text: text
                                    };
                                }
                            }
                        }
                    }
                    return best;
                }
            """)
            
            if custom_pos:
                print(f"  找到: '{custom_pos['text']}' at ({custom_pos['x']}, {custom_pos['y']})")
                # 用mouse.click点击
                page.mouse.click(custom_pos['x'], custom_pos['y'])
                time.sleep(0.8)
                save_screenshot(page, "img_color_set")
                
                # 验证
                val = page.evaluate("""
                    () => {
                        const inputs = document.querySelectorAll('.jx-dialog input');
                        for (const inp of inputs) {
                            const ph = inp.placeholder || '';
                            if (ph.includes('颜色') || ph.includes('自定义')) {
                                return inp.value;
                            }
                        }
                        return '';
                    }
                """)
                print(f"  颜色值: '{val}'")
            else:
                print("  没找到创建自定义颜色选项")
                # 打印所有下拉列表文字供排查
                all_texts = page.evaluate("""
                    () => {
                        const result = [];
                        const all = document.querySelectorAll('*');
                        all.forEach(el => {
                            if (el.children.length === 0 && el.innerText && el.innerText.trim()) {
                                const rect = el.getBoundingClientRect();
                                if (rect.top > 390 && rect.top < 600 && rect.left > 80 && rect.left < 350 && rect.width > 30) {
                                    result.push(el.innerText.trim().substring(0, 20));
                                }
                            }
                        });
                        return [...new Set(result)];
                    }
                """)
                print(f"  下拉区域所有文字: {all_texts}")
        
        save_screenshot(page, "img_color_final")
        print("\n测试完成，浏览器保持开启")
        input("按回车关闭浏览器...")
        browser.close()

if __name__ == "__main__":
    main()
