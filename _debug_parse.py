# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

lark_cli = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\sandbox_envs_dir\envs\9eac7d70-8fe7-4deb-a1bd-2616c56c7020\override_dlcs\lark-cli.exe"

print("=== 1. 执行record-list ===")
args = [lark_cli, "base", "+record-list",
        "--base-token", "Z69Pb8Zpua8h3PsKiumcidJ0nEg",
        "--table-id", "tbl8vDRirTY5Cv3Y"]
result = subprocess.run(args, capture_output=True)
output = result.stderr or result.stdout
text = output.decode("utf-8", errors="ignore")
print(text)
print()

print("=== 2. 解析表格 ===")
lines = text.strip().split("\n")
header_idx = None
for i, line in enumerate(lines):
    if line.startswith("| _record_id"):
        header_idx = i
        print(f"找到表头在第{i}行")
        break

if header_idx is None:
    print("没找到表头行")
    sys.exit(1)

headers = [h.strip() for h in lines[header_idx].split("|") if h.strip()]
print(f"字段列表: {headers}")
print()

data_rows = []
for line in lines[header_idx + 2:]:
    if not line.startswith("|") or "---" in line or line.strip() == "":
        continue
    cells = [c.strip() for c in line.split("|") if c.strip()]
    print(f"行数据 ({len(cells)}列): {cells}")
    data_rows.append(cells)

print(f"\n共解析到 {len(data_rows)} 行数据")
print()

print("=== 3. 上架状态字段判断 ===")
status_idx = headers.index("上架状态") - 1 if "上架状态" in headers else -1
print(f"上架状态列索引: {status_idx}")

for i, row in enumerate(data_rows):
    status_val = row[status_idx] if status_idx < len(row) else "N/A"
    print(f"记录{i+1} 上架状态原始值: {repr(status_val)}, 类型: {type(status_val).__name__}")
    
    # 尝试JSON解析
    parsed = status_val
    if isinstance(status_val, str) and status_val.startswith("["):
        try:
            parsed = json.loads(status_val)
            print(f"  JSON解析后: {parsed}, 类型: {type(parsed).__name__}")
        except Exception as e:
            print(f"  JSON解析失败: {e}")
    
    # 判断是否待上架
    is_pending = False
    if isinstance(parsed, list) and "待上架" in parsed:
        is_pending = True
        print(f"  -> 判定为待上架: 是 (list包含)")
    elif parsed == "待上架":
        is_pending = True
        print(f"  -> 判定为待上架: 是 (字符串相等)")
    else:
        print(f"  -> 判定为待上架: 否")
