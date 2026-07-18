# 浏览器登录脚本
# 第一次手动登录后保存登录状态（storage_state.json），后续自动加载
# 用法: python login_browser.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 指定浏览器驱动路径
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", 
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_drivers"))

from playwright.sync_api import sync_playwright
from config.settings import MIAOSHOU_BASE_URL

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage_state.json")


def main():
    print("启动浏览器...")
    print()
    print("=== 操作说明 ===")
    print("1. 在弹出的浏览器中登录妙手后台")
    print("2. 登录成功后确认能看到产品管理页面")
    print("3. 回到命令行按回车键保存登录状态")
    print("================")
    print()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        page.goto(f"{MIAOSHOU_BASE_URL}/pddkj/item/item")
        
        input("\n登录成功后，按回车键保存状态...")
        
        # 保存登录状态（cookie + localStorage）
        context.storage_state(path=STATE_FILE)
        print(f"\n登录状态已保存到: {STATE_FILE}")
        
        browser.close()
    
    print("完成，后续运行RPA会自动加载登录状态")


if __name__ == "__main__":
    main()
