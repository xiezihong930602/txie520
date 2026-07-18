# -*- coding: utf-8 -*-
import subprocess
import json
import sys

lark_cli = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\sandbox_envs_dir\envs\9eac7d70-8fe7-4deb-a1bd-2616c56c7020\override_dlcs\lark-cli.exe"

args = [lark_cli, "base", "+record-list", 
        "--base-token", "Z69Pb8Zpua8h3PsKiumcidJ0nEg", 
        "--table-id", "tbl8vDRirTY5Cv3Y",
        "--json"]

result = subprocess.run(args, capture_output=True)
output = result.stderr or result.stdout
text = output.decode("utf-8", errors="ignore")

print("=== 原始输出前500字符 ===")
print(text[:500])
print()

try:
    data = json.loads(text.strip())
    print("=== JSON解析成功 ===")
    print("ok:", data.get("ok"))
    if data.get("ok"):
        d = data.get("data", {})
        print("data keys:", list(d.keys()))
        print("fields:", d.get("fields"))
        print("record_count:", len(d.get("data", [])))
        if d.get("data"):
            print("first row:", d.get("data")[0])
except json.JSONDecodeError as e:
    print("JSON解析失败:", e)
    print("尝试直接解析表格...")
