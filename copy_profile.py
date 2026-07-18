import shutil
import os

src = r"C:\Users\Administrator\AppData\Local\Google\Chrome\User Data\Profile 26"
dst = r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2\chrome_rpa\Default"

print(f"复制Chrome Profile到项目目录...")
print(f"源: {src}")
print(f"目标: {dst}")

# 确保目标父目录存在
os.makedirs(os.path.dirname(dst), exist_ok=True)

# 复制
shutil.copytree(src, dst, dirs_exist_ok=True)

print("复制完成")
print(f"大小: {sum(os.path.getsize(os.path.join(root, f)) for root, _, files in os.walk(dst) for f in files) / 1024 / 1024:.1f} MB")
