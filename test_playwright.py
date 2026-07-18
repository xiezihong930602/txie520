# Playwright冒烟测试
# 验证浏览器能否正常启动并打开妙手后台
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 指定浏览器驱动路径
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", 
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_drivers"))

from playwright.sync_api import sync_playwright


def test_launch():
    """测试浏览器启动"""
    print("启动浏览器...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        page = browser.new_page()
        print("打开妙手后台...")
        page.goto("https://erp.91miaoshou.com/pddkj/item/item")
        page.wait_for_load_state("networkidle")
        print(f"页面标题: {page.title()}")
        print("页面URL:", page.url)
        
        # 截图
        page.screenshot(path="test_screenshot.png", full_page=True)
        print("已截图: test_screenshot.png")
        
        input("按回车关闭浏览器...")
        browser.close()
    print("测试完成")


def test_with_user_data():
    """使用Chrome用户数据目录启动（复用登录态）"""
    import os
    user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
    
    print(f"使用用户数据目录: {user_data_dir}")
    print("启动浏览器（复用Chrome登录态）...")
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            channel="chrome"
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://erp.91miaoshou.com/pddkj/item/item")
        page.wait_for_load_state("networkidle")
        print(f"页面标题: {page.title()}")
        
        input("按回车关闭浏览器...")
        context.close()
    print("测试完成")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "basic"
    if mode == "userdata":
        test_with_user_data()
    else:
        test_launch()
