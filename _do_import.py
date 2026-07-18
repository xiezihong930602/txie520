import subprocess
import json
import os

BASE_TOKEN = "Z69Pb8Zpua8h3PsKiumcidJ0nEg"
TABLE_ID = "tblgsBQC5kMCaDr4"
WORK_DIR = r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2"

with open(os.path.join(WORK_DIR, "style_names.txt"), "r", encoding="utf-8") as f:
    names = [line.strip() for line in f if line.strip()]

print(f"共 {len(names)} 个款式")

# 正确格式：fields + rows
payload = {
    "fields": ["款式名称"],
    "rows": [[name] for name in names]
}

tmp_file = os.path.join(WORK_DIR, "_tmp_import_all.json")
with open(tmp_file, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)

cmd = f'lark-cli base +record-batch-create --base-token {BASE_TOKEN} --table-id {TABLE_ID} --json @_tmp_import_all.json'
result = subprocess.run(cmd, cwd=WORK_DIR, capture_output=True, shell=True)
output = result.stderr or result.stdout
try:
    text = output.decode("utf-8", errors="ignore")
    resp = json.loads(text.strip())
except:
    text = output.decode("gbk", errors="ignore")
    resp = {"ok": False, "error": {"message": text.strip()}}

if resp.get("ok"):
    print(f"成功导入 {len(names)} 个款式")
else:
    print(f"失败: {resp.get('error', {}).get('message', '未知错误')}")

os.remove(tmp_file)
