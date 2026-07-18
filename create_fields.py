# 批量创建多维表格字段
import subprocess
import json
import os

BASE_TOKEN = "Z69Pb8Zpua8h3PsKiumcidJ0nEg"
TABLE_ID = "tblgZesB3dnXUgqj"

LARK_CLI = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\sandbox_envs_dir\envs\084fee42-5307-4ea4-9732-9d2e322248ff\override_dlcs\lark-cli.exe"

fields = [
    {"type": "text", "name": "商品编号"},
    {"type": "text", "name": "款式名称"},
    {"type": "select", "name": "分类", "options": [{"name": "儿童"}, {"name": "成人"}]},
    {"type": "text", "name": "模板名称"},
    {"type": "text", "name": "产品标题"},
    {"type": "number", "name": "成本价"},
    {"type": "number", "name": "供货价"},
    {"type": "text", "name": "尺码列表"},
    {"type": "text", "name": "SKU分类"},
    {"type": "text", "name": "颜色名称"},
    {"type": "attachment", "name": "商品主图"},
    {"type": "select", "name": "上架状态", "options": [
        {"name": "待上架"}, {"name": "上架中"}, {"name": "已上架"}, {"name": "上架失败"}
    ]},
    {"type": "text", "name": "SKC ID"},
    {"type": "text", "name": "错误信息"},
    {"type": "text", "name": "备注"},
]

os.chdir(os.path.dirname(os.path.abspath(__file__)))

for field in fields:
    # 写临时JSON文件
    with open("_tmp_field.json", "w", encoding="utf-8") as f:
        json.dump(field, f, ensure_ascii=False)
    
    # 调用lark-cli（用cmd避免PowerShell @问题）
    cmd = f'cmd /c ""{LARK_CLI}" base +field-create --base-token {BASE_TOKEN} --table-id {TABLE_ID} --json @_tmp_field.json"'
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    
    try:
        resp = json.loads(result.stdout)
        if resp.get("ok"):
            print(f"✅ 创建字段: {field['name']}")
        else:
            print(f"❌ 创建失败: {field['name']} - {resp.get('error', {}).get('message')}")
    except Exception as e:
        print(f"❌ 解析失败: {field['name']} - {e}")
        print("STDOUT:", repr(result.stdout[:300]))
        print("STDERR:", repr(result.stderr[:300]))

# 清理临时文件
if os.path.exists("_tmp_field.json"):
    os.remove("_tmp_field.json")

print("\n完成!")
