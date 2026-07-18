# -*- coding: utf-8 -*-
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_source.feishu import FeishuDataSource
from config.settings import FEISHU_BASE_TOKEN, LARK_CLI_PATH

print("LARK_CLI_PATH:", LARK_CLI_PATH)
print()

ds = FeishuDataSource(FEISHU_BASE_TOKEN, "tbl8vDRirTY5Cv3Y", LARK_CLI_PATH)

print("=== 调用record-list ===")
resp = ds._run_cmd(
    f'+record-list --base-token {FEISHU_BASE_TOKEN} --table-id tbl8vDRirTY5Cv3Y'
)
print("ok:", resp.get("ok"))
if not resp.get("ok"):
    print("error:", resp.get("error"))
    sys.exit(1)

data = resp.get("data", {})
items = data.get("data", [])
fields = data.get("fields", [])
record_ids = data.get("record_id_list", [])

print(f"\n记录数: {len(items)}")
print(f"字段列表: {fields}")
print()

for i, row in enumerate(items):
    print(f"--- 记录 {i+1} ---")
    print(f"record_id: {record_ids[i] if i < len(record_ids) else 'N/A'}")
    for j, field in enumerate(fields):
        val = row[j]
        print(f"  {field}: {repr(val)} (type: {type(val).__name__})")
    
    # 判断是否待上架
    status = row[fields.index("上架状态")] if "上架状态" in fields else None
    print(f"  -> 上架状态判断: status={repr(status)}")
    is_pending = False
    if isinstance(status, list) and "待上架" in status:
        is_pending = True
        print("  -> 匹配: list包含待上架")
    elif status == "待上架":
        is_pending = True
        print("  -> 匹配: 字符串等于待上架")
    print(f"  -> 是否待上架: {is_pending}")
    print()
