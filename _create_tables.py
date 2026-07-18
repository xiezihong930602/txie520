# -*- coding: utf-8 -*-
"""批量创建飞书多维表格的数据表"""
import subprocess
import json
import os

BASE_TOKEN = "Z69Pb8Zpua8h3PsKiumcidJ0nEg"
WORK_DIR = os.path.dirname(os.path.abspath(__file__))

def run_lark_cmd(args):
    """执行lark-cli命令"""
    cmd = ["lark-cli", "base"] + args
    result = subprocess.run(
        cmd,
        cwd=WORK_DIR,
        capture_output=True,
        text=True
    )
    output = result.stderr or result.stdout
    try:
        return json.loads(output.strip())
    except:
        return {"ok": False, "error": {"message": output.strip()}}

def create_table(name, fields_file):
    """创建数据表"""
    cmd = ["lark-cli", "base",
           "+table-create",
           "--base-token", BASE_TOKEN,
           "--name", name,
           "--fields", f"@{fields_file}"]
    result = subprocess.run(
        cmd,
        cwd=WORK_DIR,
        capture_output=True
    )
    output = result.stderr or result.stdout
    try:
        text = output.decode("utf-8", errors="ignore")
    except:
        text = output.decode("gbk", errors="ignore")
    try:
        return json.loads(text.strip())
    except:
        return {"ok": False, "error": {"message": text.strip()}}

# 1. 创建款式库表
print("1. 创建款式库表...")
r = create_table("款式库表", "_fields_style.json")
print(json.dumps(r, ensure_ascii=False, indent=2))

# 2. 创建模板表
print("\n2. 创建模板表...")
r = create_table("模板表", "_fields_template.json")
print(json.dumps(r, ensure_ascii=False, indent=2))

# 3. 创建店铺表
print("\n3. 创建店铺表...")
r = create_table("店铺表", "_fields_shop.json")
print(json.dumps(r, ensure_ascii=False, indent=2))

# 4. 创建颜色明细表
print("\n4. 创建颜色明细表...")
r = create_table("颜色明细表", "_fields_color.json")
print(json.dumps(r, ensure_ascii=False, indent=2))

# 5. 创建商品链接表
print("\n5. 创建商品链接表...")
r = create_table("商品链接表", "_fields_product.json")
print(json.dumps(r, ensure_ascii=False, indent=2))

print("\n全部完成！")
