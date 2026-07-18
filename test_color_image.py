# 测试颜色行多图上传 - 网络图片方式
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
import time

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", 
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_drivers"))

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage_state.json")

# 5张测试图URL，按顺序
IMAGE_URLS = [
    "https://aka.doubaocdn.com/s/5wyU1wuoJ8",
    "https://aka.doubaocdn.com/s/QfQp1wuoJ8",
    "https://aka.doubaocdn.com/s/AFm31wuoJ5",
    "https://aka.doubaocdn.com/s/sQUv1wuoJ6",
    "https://aka.doubaocdn.com/s/UqTC1wuoJ6",
]

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
        
        # 2. 找创建产品按钮
        create_btn = None
        for retry in range(3):
            try:
                create_btn = page.get_by_role("button", name="创建产品").first
                create_btn.wait_for(state="visible", timeout=5000)
                break
            except:
                print(f"  第{retry+1}次刷新...")
                page.reload(wait_until="domcontentloaded")
                time.sleep(5)
        
        if not create_btn or not create_btn.is_visible():
            save_screenshot(page, "img_test_error_no_btn")
            print("  找不到创建产品按钮")
            input("按回车关闭...")
            browser.close()
            return
        
        print("点击创建产品...")
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
        time.sleep(0.5)
        
        add_link = page.locator(":text-is('+ 新增')").first
        add_link.click()
        time.sleep(1.5)
        
        # 6. 找图片框并点击
        print("找图片上传框...")
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
        time.sleep(0.5)
        
        candidates = page.evaluate("""
            () => {
                const dialog = document.querySelector('.jx-dialog');
                if (!dialog) return [];
                const result = [];
                const all = dialog.querySelectorAll('div, span, a, button');
                all.forEach((el, i) => {
                    const rect = el.getBoundingClientRect();
                    if (rect.top >= 250 && rect.top <= 450 && 
                        rect.left >= 100 && rect.left <= 500 &&
                        rect.width >= 30 && rect.width <= 150 &&
                        rect.height >= 30 && rect.height <= 150 &&
                        el.children.length <= 3) {
                        result.push({
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            w: Math.round(rect.width),
                            h: Math.round(rect.height),
                            text: el.innerText.substring(0, 8)
                        });
                    }
                });
                const unique = [];
                const seen = new Set();
                result.forEach(r => {
                    const key = r.x + ',' + r.y;
                    if (!seen.has(key)) {
                        seen.add(key);
                        unique.push(r);
                    }
                });
                return unique.slice(0, 10);
            }
        """)
        
        img_box = None
        for c in candidates:
            if c['w'] >= 100 and c['h'] >= 100 and c['text'].strip() == '':
                img_box = c
                break
        if not img_box and len(candidates) > 0:
            candidates.sort(key=lambda x: x['w'] * x['h'], reverse=True)
            img_box = candidates[0]
        
        if img_box:
            cx = img_box['x'] + img_box['w'] // 2
            cy = img_box['y'] + img_box['h'] // 2
            print(f"  图片框: ({cx}, {cy})")
            
            page.mouse.click(cx, cy)
            time.sleep(0.6)
            
            # 点击使用网络图片
            page.evaluate("""
                () => {
                    const all = document.querySelectorAll('*');
                    for (const el of all) {
                        if (el.children.length === 0 && el.innerText && el.innerText.trim() === '使用网络图片') {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0) { el.click(); return; }
                        }
                    }
                }
            """)
            time.sleep(1)
            save_screenshot(page, "img_test_url_dialog")
            
            # 找到URL弹窗
            print("  处理URL弹窗...")
            
            # 1. 取消"同时保存图片到妙手图片空间"的勾选
            print("  取消保存到妙手空间的勾选...")
            unchecked = page.evaluate("""
                () => {
                    const dialogs = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
                    for (const d of dialogs) {
                        const rect = d.getBoundingClientRect();
                        if (rect.width > 400 && rect.height > 200 && 
                            d.innerText && d.innerText.includes('使用网络图片')) {
                            // 找checkbox
                            const checkboxes = d.querySelectorAll('input[type="checkbox"]');
                            for (const cb of checkboxes) {
                                if (cb.checked) {
                                    cb.click();
                                    return true;
                                }
                            }
                            return false;
                        }
                    }
                    return false;
                }
            """)
            print(f"  已取消勾选: {unchecked}")
            
            # 2. 找textarea并填入5个URL（换行分隔）
            print("  填入5张图片URL...")
            textarea_info = page.evaluate("""
                () => {
                    const dialogs = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
                    for (const d of dialogs) {
                        const rect = d.getBoundingClientRect();
                        if (rect.width > 400 && rect.height > 200 && 
                            d.innerText && d.innerText.includes('使用网络图片')) {
                            const ta = d.querySelector('textarea');
                            if (ta) {
                                const r = ta.getBoundingClientRect();
                                return {
                                    found: true,
                                    x: Math.round(r.left),
                                    y: Math.round(r.top),
                                    w: Math.round(r.width),
                                    h: Math.round(r.height)
                                };
                            }
                        }
                    }
                    return {found: false};
                }
            """)
            
            if textarea_info['found']:
                # 点击输入框，全选清空，然后粘贴5个URL
                tx = textarea_info['x'] + 10
                ty = textarea_info['y'] + 10
                page.mouse.click(tx, ty)
                time.sleep(0.2)
                
                # 全选清空
                page.keyboard.press("Control+A")
                time.sleep(0.1)
                page.keyboard.press("Backspace")
                time.sleep(0.1)
                
                # 输入5个URL，换行分隔
                urls_text = "\n".join(IMAGE_URLS)
                page.keyboard.type(urls_text)
                time.sleep(0.5)
                
                save_screenshot(page, "img_test_urls_filled")
                print(f"  已填入 {len(IMAGE_URLS)} 个URL")
                
                # 3. 点击确定
                print("  点击确定...")
                page.evaluate("""
                    () => {
                        const dialogs = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
                        for (const d of dialogs) {
                            const rect = d.getBoundingClientRect();
                            if (rect.width > 400 && rect.height > 200 && 
                                d.innerText && d.innerText.includes('使用网络图片')) {
                                const btns = d.querySelectorAll('button');
                                for (const btn of btns) {
                                    if (btn.innerText.trim() === '确定') {
                                        btn.click();
                                        return true;
                                    }
                                }
                            }
                        }
                        return false;
                    }
                """)
                time.sleep(8)  # 多图上传等久一点
                save_screenshot(page, "img_test_multi_upload_done")
                print("  上传完成（查看截图确认是否5张都上去了）")
            else:
                print("  没找到textarea")
        
        save_screenshot(page, "img_test_final")
        
        print("\n测试完成，浏览器保持开启")
        input("按回车关闭浏览器...")
        browser.close()

if __name__ == "__main__":
    main()
