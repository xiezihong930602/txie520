# -*- coding: utf-8 -*-
""" Step-1: 从Excel读取款式尺码数据并打印验证 """
import openpyxl
from pathlib import Path

EXCEL_PATH = Path(r"C:\Users\Administrator\Downloads\款式尺码对照表（上衣裤子分格式）.xlsx")

ALL_PARAMS = [
    "领围(cm)", "肩宽(cm)", "胸围全围(cm)", "袖长(cm)", "衣长(cm)",
    "腰围全围(cm)", "臀围全围(cm)", "大腿围全围(cm)", "裤长(cm)", "裤内长(cm)", "夹圈(cm)"
]


def load_size_data(excel_path, style_name):
    """加载指定款式的尺码数据"""
    wb = openpyxl.load_workbook(excel_path)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    style_key = style_name.strip()
    in_block = False
    headers = []
    data_rows = []

    for row in rows:
        # 检测款式标题行：■ ST-xxx - 款式名称 [类型]
        cell0 = row[0]
        if cell0 and isinstance(cell0, str) and cell0.strip().startswith("■"):
            in_block = style_key in str(cell0)
            continue
        if not in_block or not cell0:
            continue
        # 表头行：包含"尺码"
        if isinstance(cell0, str) and "尺码" in str(cell0):
            headers = [str(c).strip() if c else "" for c in row]
            continue
        # 数据行
        if headers:
            vals = []
            for c in row:
                if c is not None and str(c).strip():
                    vals.append(str(c).strip())
                else:
                    vals.append("")
            if vals and vals[0]:
                data_rows.append(vals)

    if not data_rows:
        return None, None, None

    # 判断上衣/裤子：headers中含"胸"或"肩"为上装
    is_top = any("胸" in h or "肩" in h for h in headers)
    return headers, data_rows, is_top


def map_param_labels(headers):
    """表头列 → 页面参数label"""
    result = []
    for h in headers:
        if not h or h == "尺码":
            continue
        for p in ALL_PARAMS:
            if h in p or p in h:
                result.append(p)
                break
    return result


def get_size_list(data_rows):
    """提取尺码值列表"""
    return [r[0] for r in data_rows if r[0]]


def gen_paste_text(headers, data_rows):
    """生成粘贴导入文本"""
    ph = [h for h in headers if h and h != "尺码"]
    lines = ["\t".join(["尺码"] + ph)]
    for row in data_rows:
        size = row[0] or ""
        vals = []
        for i in range(1, len(headers)):
            v = row[i] if i < len(row) else ""
            vals.append(v if v else "")
        lines.append("\t".join([size] + vals))
    return "\n".join(lines)


# ---- 测试 ----
if __name__ == "__main__":
    tests = ["儿童拉毛卫衣", "儿童拉毛卫裤", "儿童牛奶丝圆领短袖"]
    
    for name in tests:
        headers, data_rows, is_top = load_size_data(EXCEL_PATH, name)
        if not data_rows:
            print(f"\n{'='*50}\n  {name}: 未找到数据\n{'='*50}")
            continue
        
        params = map_param_labels(headers)
        sizes = get_size_list(data_rows)
        paste = gen_paste_text(headers, data_rows)

        print(f"\n{'='*50}")
        print(f"  款式: {name}")
        print(f"  类型: {'上衣' if is_top else '裤子'}")
        print(f"  表头: {headers}")
        print(f"  页面参数label: {params}")
        print(f"  尺码({len(sizes)}个): {sizes}")
        print(f"  数据行数: {len(data_rows)}")
        print(f"\n  --- 粘贴文本前3行 ---")
        for line in paste.split("\n")[:4]:
            print(f"  {line}")
