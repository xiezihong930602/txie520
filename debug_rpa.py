# RPA分步调试脚本
# 每执行一步暂停，观察页面状态
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", 
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_drivers"))

from playwright.sync_api import sync_playwright
from config.settings import MIAOSHOU_BASE_URL
import time

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage_state.json")


def wait_enter(msg="按回车继续..."):
    input(f"\n>>> {msg}")


def main():
    style_name = "儿童拉毛卫衣"
    template_name = "男童圆领卫衣"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=200,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
        )
        
        context_kwargs = {"viewport": {"width": 1920, "height": 1080}}
        if os.path.exists(STATE_FILE):
            context_kwargs["storage_state"] = STATE_FILE
        
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        
        # ===== 第1步：打开产品管理页 =====
        print("【第1步】导航到产品管理页...")
        page.goto(f"{MIAOSHOU_BASE_URL}/pddkj/item/item")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        wait_enter("确认看到产品管理列表，按回车继续")
        
        # ===== 第2步：点击创建产品 =====
        print("【第2步】点击创建产品按钮...")
        
        # 尝试多种选择器
        clicked = False
        selectors = [
            page.get_by_role("button", name="创建产品"),
            page.locator("button:has-text('创建产品')"),
            page.locator(".jx-button--primary:has-text('创建产品')"),
        ]
        
        for i, sel in enumerate(selectors):
            try:
                btn = sel.first
                if btn.is_visible(timeout=2000):
                    print(f"  使用选择器 {i+1}")
                    btn.click()
                    clicked = True
                    break
            except:
                continue
        
        if not clicked:
            print("  没找到按钮，尝试强制点击右上角位置...")
            page.mouse.click(1700, 100)  # 右上角大概位置
        
        time.sleep(2)
        wait_enter("确认创建产品弹窗已打开，按回车继续")
        
        # ===== 第3步：点击引用模板 =====
        print("【第3步】点击引用模板下拉...")
        
        # 找左下角的引用模板按钮
        trigger_selectors = [
            page.get_by_role("button", name="引用模板"),
            page.locator(":text-is('引用模板')").locator("xpath=ancestor::button"),
            page.locator(".template-dropdown").locator("xpath=preceding-sibling::*"),
            page.locator(":text-is('引用模板')").first,
        ]
        
        clicked = False
        for i, sel in enumerate(trigger_selectors):
            try:
                el = sel.first
                if el.is_visible(timeout=2000):
                    print(f"  使用触发器选择器 {i+1}")
                    el.click()
                    clicked = True
                    break
            except:
                continue
        
        if not clicked:
            print("  没找到引用模板按钮")
        
        time.sleep(1)
        wait_enter("确认模板下拉菜单已展开，按回车继续")
        
        # ===== 第4步：选择模板 =====
        print(f"【第4步】选择模板: {template_name}")
        
        menu = page.locator(".template-dropdown").first
        if menu.is_visible():
            item = menu.get_by_text(template_name, exact=True).first
            if item.is_visible():
                item.click()
                print("  已点击模板")
            else:
                print("  模板不在列表中？")
        else:
            print("  下拉菜单没展开")
        
        time.sleep(1)
        wait_enter("确认出现引用确认弹窗，按回车继续")
        
        # ===== 第5步：点确定引用 =====
        print("【第5步】点击确定引用...")
        
        # 找确认弹窗的确定按钮
        confirm_selectors = [
            page.locator(".jx-overlay-message-box .jx-button-primary"),
            page.locator(".jx-message-box .jx-button--primary"),
            page.get_by_role("dialog").get_by_role("button", name="确定"),
            page.locator("button:has-text('确定')").last,
        ]
        
        clicked = False
        for i, sel in enumerate(confirm_selectors):
            try:
                btn = sel.first
                if btn.is_visible(timeout=2000):
                    print(f"  使用确认按钮选择器 {i+1}")
                    btn.click()
                    clicked = True
                    break
            except:
                continue
        
        if not clicked:
            print("  没找到确定按钮")
        
        time.sleep(3)
        wait_enter("确认模板已加载（弹窗还在），按回车继续")
        
        # ===== 第6步：切换到产品信息标签 =====
        print("【第6步】切换到产品信息标签...")
        
        # 清遮罩
        try:
            page.evaluate("""
                document.querySelectorAll('.jx-overlay').forEach(el => {
                    el.style.display = 'none';
                });
            """)
        except:
            pass
        time.sleep(0.5)
        
        tab = page.locator(".scroll-menu-pane__label", has_text="产品信息").first
        if tab.is_visible():
            tab.scroll_into_view_if_needed()
            time.sleep(0.3)
            tab.click()
            print("  已点击产品信息")
        else:
            print("  没找到产品信息标签")
            # 打印所有侧边标签
            labels = page.locator(".scroll-menu-pane__label").all_text_contents()
            print(f"  当前可见标签: {labels}")
        
        time.sleep(1)
        wait_enter("观察完成，按回车结束")
        
        browser.close()
    
    print("\n调试结束")


if __name__ == "__main__":
    main()
