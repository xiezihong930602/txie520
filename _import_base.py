# -*- coding: utf-8 -*-
"""导入基础数据：模板表、店铺表"""
import subprocess
import json
import os

BASE_TOKEN = "Z69Pb8Zpua8h3PsKiumcidJ0nEg"
WORK_DIR = os.path.dirname(os.path.abspath(__file__))


def batch_create(table_id, records):
    """批量创建记录"""
    payload = {"records": records}
    tmp_file = os.path.join(WORK_DIR, "_tmp_base.json")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    
    cmd = f'cmd /c "lark-cli base +record-batch-create --base-token {BASE_TOKEN} --table-id {table_id} --json @_tmp_base.json"'
    
    result = subprocess.run(cmd, cwd=WORK_DIR, capture_output=True, shell=True)
    output = result.stderr or result.stdout
    try:
        text = output.decode("utf-8", errors="ignore")
        resp = json.loads(text.strip())
    except:
        resp = {"ok": False, "error": {"message": output.decode("gbk", errors="ignore").strip()}}
    
    if os.path.exists(tmp_file):
        os.remove(tmp_file)
    return resp


def main():
    # 1. 导入模板表
    print("导入模板表...")
    templates = [
        {"模板名称": "男童圆领卫衣"},
        {"模板名称": "女童套装"},
        {"模板名称": "女童T恤"},
        {"模板名称": "女童短裤"},
        {"模板名称": "女童背心"},
        {"模板名称": "男童帽衫"},
    ]
    r = batch_create("tbl8MDtm0cijDycp", templates)
    print("成功" if r.get("ok") else f"失败: {r.get('error', {}).get('message')}")
    
    # 2. 导入店铺表
    print("\n导入店铺表...")
    shops = [
        {"店铺名称": "Noble Boys", "平台": "TEMU全托管", "店铺ID": "14255939"}
    ]
    r = batch_create("tblcstU6w77Klawo", shops)
    print("成功" if r.get("ok") else f"失败: {r.get('error', {}).get('message')}")
    
    print("\n基础数据导入完成！")


if __name__ == "__main__":
    main()
