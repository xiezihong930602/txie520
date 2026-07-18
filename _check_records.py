import subprocess
import json

lark_cli = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\sandbox_envs_dir\envs\9eac7d70-8fe7-4deb-a1bd-2616c56c7020\override_dlcs\lark-cli.exe"
cmd = f'"{lark_cli}" base +record-list --base-token Z69Pb8Zpua8h3PsKiumcidJ0nEg --table-id tbl8vDRirTY5Cv3Y'

result = subprocess.run(cmd, capture_output=True, shell=True)
output = result.stderr or result.stdout
text = output.decode("utf-8", errors="ignore")
print(text)
