# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import FEISHU_BASE_TOKEN, STYLE_LIBRARY_PATH, LARK_CLI_PATH
from data_source.product_loader import FeishuProductLoader

print("LARK_CLI_PATH:", LARK_CLI_PATH)
print()

loader = FeishuProductLoader(
    base_token=FEISHU_BASE_TOKEN,
    excel_path=STYLE_LIBRARY_PATH,
    lark_cli=LARK_CLI_PATH
)

print("=== 测试直接调用record-list ===")
resp = loader.product_ds._run_cmd(
    f'+record-list --base-token {FEISHU_BASE_TOKEN} --table-id tbl8vDRirTY5Cv3Y'
)
print("ok:", resp.get("ok"))
print("data keys:", list(resp.get("data", {}).keys()) if resp.get("data") else "None")

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
        print(f"  {field}: {val} (type: {type(val).__name__})")
    print()

print("\n=== 测试load_pending_products ===")
products = loader.load_pending_products()
print(f"待上架数量: {len(products)}")
for p in products:
    print(f"  - {p.get('title')}: {p.get('style_name')}, 颜色数: {len(p.get('colors', []))}")
