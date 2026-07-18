import subprocess
import os

WORK_DIR = r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2"
cmd = 'cmd /c "lark-cli base +field-create --base-token Z69Pb8Zpua8h3PsKiumcidJ0nEg --table-id tbl8vDRirTY5Cv3Y --json @_tmp_field.json"'
result = subprocess.run(cmd, cwd=WORK_DIR, capture_output=True, shell=True)
output = result.stderr or result.stdout
try:
    text = output.decode("utf-8", errors="ignore")
except:
    text = output.decode("gbk", errors="ignore")
print(text)
