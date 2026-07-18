import os
import json
import datetime

user_data = r"C:\Users\Administrator\AppData\Local\Google\Chrome\User Data"

profiles = []
for name in os.listdir(user_data):
    path = os.path.join(user_data, name)
    prefs_file = os.path.join(path, "Preferences")
    if os.path.isdir(path) and os.path.exists(prefs_file):
        mtime = os.path.getmtime(prefs_file)
        try:
            with open(prefs_file, "r", encoding="utf-8") as f:
                prefs = json.load(f)
            profile_name = prefs.get("profile", {}).get("name", "unknown")
        except:
            profile_name = "unknown"
        profiles.append((mtime, name, profile_name))

profiles.sort(reverse=True)

print("按修改时间排序（最新在前）：")
print()
for mtime, name, pname in profiles[:8]:
    t = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
    print(f"  {name:15s}  修改时间: {t}  名称: {pname}")
