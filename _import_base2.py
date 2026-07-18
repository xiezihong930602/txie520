import subprocess
import json
import os

BASE_TOKEN = "Z69Pb8Zpua8h3PsKiumcidJ0nEg"
WORK_DIR = r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2"

def import_data(table_id, fields, rows):
    payload = {"fields": fields, "rows": rows}
    tmp_file = os.path.join(WORK_DIR, "_tmp_data.json")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    
    cmd = f'lark-cli base +record-batch-create --base-token {BASE_TOKEN} --table-id {table_id} --json @_tmp_data.json'
    result = subprocess.run(cmd, cwd=WORK_DIR, capture_output=True, shell=True)
    output = result.stderr or result.stdout
    try:
        text = output.decode("utf-8", errors="ignore")
        resp = json.loads(text.strip())
    except:
        text = output.decode("gbk", errors="ignore")
        resp = {"ok": False, "error": {"message": text.strip()}}
    
    os.remove(tmp_file)
    return resp

# 1. 导入模板表
print("导入模板表...")
r = import_data("tbl8MDtm0cijDycp", ["模板名称"], [
    ["男童圆领卫衣"], ["女童套装"], ["女童T恤"], 
    ["女童短裤"], ["女童背心"], ["男童帽衫"]
])
print("成功" if r.get("ok") else f"失败: {r.get('error', {}).get('message')}")

# 2. 导入店铺表
print("\n导入店铺表...")
r = import_data("tblcstU6w77Klawo", ["店铺名称", "平台", "店铺ID"], [
    ["Noble Boys", "TEMU全托管", "14255939"]
])
print("成功" if r.get("ok") else f"失败: {r.get('error', {}).get('message')}")

print("\n完成！")
