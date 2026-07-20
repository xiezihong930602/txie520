"""独立测试 _select_shop — 只测店铺选择，冻结后续流程"""
import sys, os, time
ROOT = r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from executors.rpa_publisher import RpaPublisherExecutor

executor = RpaPublisherExecutor(config={"headless": False, "slow_mo": 200})
executor._init_browser()
executor._open_create_page()
executor._select_shop("Noble Boys")

print("\n=== 测试完成，30秒观察时间 ===")
time.sleep(30)
executor.browser.close()
print("关闭")
