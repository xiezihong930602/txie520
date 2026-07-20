"""
读取Excel尺码数据工具
"""
import openpyxl
from pathlib import Path

# 参数名映射：Excel表头 → 妙手系统参数名
PARAM_MAP = {
    "衣长": "衣长",
    "胸围": "胸围",
    "肩宽": "肩宽",
    "袖长": "袖长",
    "裤长": "裤长",
    "腰围": "腰围",
    "臀围": "臀围",
    "裤内长": "裤内长",
    "建议身高": "建议身高",
    "建议体重": "建议体重",
}

EXCEL_PATH = Path(r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2\款式库模板_v4_填尺码_最终版.xlsx")

def load_size_data(excel_path=EXCEL_PATH, style_name=None):
    """从Excel加载指定款式的尺码数据"""
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb.active
    headers = None
    data_rows = []
    is_top = True  # 默认上衣
    found_style = False
    
    for row in ws.iter_rows(values_only=True):
        if not row or not row[0]:
            continue
        first_cell = str(row[0]).strip()
        if first_cell == "尺码":
            headers = [str(c).strip() if c else "" for c in row]
            continue
        if headers and first_cell == style_name:
            found_style = True
            continue
        if found_style:
            size = first_cell
            # 判断是否是尺码行
            if size and (size.isdigit() or size.startswith(("1","2","3","4","5","6","7","8","9","S","M","L","X"))):
                row_data = [size]
                has_data = False
                for c in row[1:len(headers)]:
                    val = str(c).strip() if c is not None else ""
                    row_data.append(val)
                    if val:
                        has_data = True
                if has_data:
                    data_rows.append(row_data)
            else:
                # 遇到非尺码行，结束
                break
    
    # 判断是上衣还是裤子
    if headers:
        if "裤长" in headers or "腰围" in headers or "臀围" in headers:
            is_top = False
    
    wb.close()
    return headers, data_rows, is_top

def map_param_labels(headers):
    """映射Excel表头到妙手参数名"""
    labels = []
    for h in headers[1:]:
        if not h:
            labels.append("")
            continue
        mapped = PARAM_MAP.get(h, h)
        labels.append(mapped)
    return labels

def get_size_list(data_rows):
    """获取尺码列表"""
    return [r[0] for r in data_rows]

if __name__ == "__main__":
    # 测试
    headers, rows, is_top = load_size_data(style_name="儿童网眼篮球裤")
    print("headers:", headers)
    print("rows:", len(rows))
    print("is_top:", is_top)
    print("sizes:", get_size_list(rows))
