# _fix_sync.py - 修复sync_images.py的工具脚本
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(ROOT, "sync_images.py")

# 读取文件，去BOM和null bytes
with open(path, "rb") as f:
    data = f.read()

# 移除BOM和null bytes
data = data.replace(b"\xef\xbb\xbf", b"")
data = data.replace(b"\x00", b"")

with open(path, "wb") as f:
    f.write(data)

print("cleaned:", path)

# 验证
import ast
with open(path, "r", encoding="utf-8") as f:
    ast.parse(f.read())
print("syntax OK")
