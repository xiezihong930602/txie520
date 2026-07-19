"""尺码表模板自动创建 RPA - Codegen版本"""
import os, sys, time
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2")
sys.path.insert(0, str(ROOT))

import openpyxl
from playwright.sync_api import sync_playwright

SIZE_CHART_URL = "https://erp.91miaoshou.com/pddkj/move_collect/template_management/sizeChart"
EXCEL_PATH = Path(r"C:\Users\Administrator\Downloads\款式尺码对照表（上衣裤子分格式）.xlsx")
STATE_FILE = ROOT / "storage_state.json"
RPA_HEADLESS = False

ALL_PARAMS = [
    "领围(cm)", "肩宽(cm)", "胸围全围(cm)", "袖长(cm)", "衣长(cm)",
    "腰围全围(cm)", "臀围全围(cm)", "大腿围全围(cm)", "裤长(cm)", "裤内长(cm)", "夹圈(cm)"
]

def load_size_data(excel_path, style_name):
    wb = openpyxl.load_workbook(excel_path)
    ws = wb.active; rows = list(ws.iter_rows(values_only=True)); wb.close()
    sk = style_name.strip()
    in_block = False; headers = []; data_rows = []
    for row in rows:
        if row[0] and isinstance(row[0], str) and row[0].strip().startswith(u"\u25a0"):
            in_block = sk in str(row[0]); continue
        if not in_block or not row[0]: continue
        if isinstance(row[0], str) and u"\u5c3a\u7801" in str(row[0]):
            headers = [str(c).strip() if c else "" for c in row]; continue
        if headers and row[0] is not None:
            vals = [str(c).strip() if c is not None and str(c).strip() else "" for c in row]
            if vals and vals[0]: data_rows.append(vals)
    if not data_rows: return None, None, None
    is_top = any(u"\u80f8" in str(h) or u"\u80a9" in str(h) for h in headers)
    return headers, data_rows, is_top

def get_param_labels(headers):
    """从表头映射到页面显示的参数label"""
    return [p for h in headers if h != u"\u5c3a\u7801" for p in ALL_PARAMS if h in p or p in h]

def get_size_values(data_rows):
    return [row[0] for row in data_rows if row[0]]

def generate_paste_text(headers, data_rows):
    ph = [h for h in headers if h != u"\u5c3a\u7801"]
    lines = ["\t".join([u"\u5c3a\u7801"] + ph)]
    for row in data_rows:
        size = row[0] or ""
        vals = [row[i] if i < len(row) and row[i] else "" for i in range(1, len(headers))]
        lines.append("\t".join([size] + vals))
    return "\n".join(lines)

def get_cat_keyword(cat_path):
    """从类目路径提取搜索关键词"""
    # 取最末端的类目作为关键词
    last = cat_path.split("/")[-1].strip()
    # 去掉前缀如"男童时尚"→"帽衫"
    words = [u"帽衫", u"卫衣", u"长裤", u"短裤", u"背心", u"夹克", u"套装", u"polo", u"T恤", u"马甲"]
    for w in words:
        if w in last:
            return w
    # fallback: 取最后一个空格后的词
    parts = last.split()
    return parts[-1] if parts else last

def create_one(page, style_name, cat_path, size_category):
    print(f"\n===== {style_name} =====")
    headers, data_rows, is_top = load_size_data(EXCEL_PATH, style_name)
    if not data_rows: print(f"  [SKIP] 未找到数据"); return False
    params = get_param_labels(headers)
    sizes = get_size_values(data_rows)
    paste_text = generate_paste_text(headers, data_rows)
    cat_kw = get_cat_keyword(cat_path)
    print(f"  类型: {'上衣' if is_top else '裤子'}, 参数: {params}, 尺码: {len(sizes)}, 类目关键词: {cat_kw}")

    # 1. 创建
    page.get_by_role("button", name=u"创建尺码表模板").click()
    time.sleep(2)

    # 2. 模板名称
    page.get_by_role("textbox", name=u"*模板名称").click()
    page.get_by_role("textbox", name=u"*模板名称").fill(style_name)
    time.sleep(0.3)
    print("  [OK] 名称")

    # 3. 类目 - 搜索关键词 → 点击匹配项
    page.get_by_role("textbox", name=u"*类目").click()
    time.sleep(0.3)
    page.get_by_role("textbox", name=u"*类目").fill(cat_kw)
    time.sleep(2)
    # 找匹配的级联选项
    try:
        page.get_by_role("listitem").filter(has_text=cat_path).first.click(timeout=5000)
        print("  [OK] 类目")
    except:
        # fallback: 用关键词模糊匹配
        page.get_by_role("listitem").filter(has_text=cat_kw).first.click(timeout=5000)
        print(f"  [OK] 类目(fallback: {cat_kw})")
    time.sleep(0.5)

    # 4. 勾选尺码参数 - 用label的checkbox点内圈
    for param in params:
        try:
            page.locator(f"label:has-text('{param}') .jx-checkbox__inner").click(timeout=2000)
            time.sleep(0.1)
        except: pass
    print(f"  [OK] 参数勾选")

    # 5. 尺码全选→取消
    try:
        # 点击表头checkbox
        page.locator("th .jx-checkbox__inner").first.click(timeout=2000)
        time.sleep(0.2)
        page.locator("th .jx-checkbox__inner").first.click(timeout=2000)
        time.sleep(0.3)
    except: pass

    # 6. 逐个勾选尺码 - 虚拟滚动，需要点击可见的checkbox
    for size in sizes:
        try:
            # 找包含该尺码的行
            row = page.locator(f"td:has-text('{size}')").first
            if row.is_visible():
                # 滚动到可见
                row.scroll_into_view_if_needed()
                time.sleep(0.1)
            # 点该行的checkbox
            page.locator(f"tr:has(td:text-is('{size}')) .jx-checkbox__inner").first.click(timeout=2000)
            time.sleep(0.1)
        except:
            continue
    print(f"  [OK] 尺码勾选: {len(sizes)}")

    # 7. 粘贴导入
    try:
        page.get_by_role("button", name=u"Excel快速编辑").click()
        time.sleep(0.5)
        page.get_by_role("menuitem", name=u"第二步：粘贴导入").click()
        time.sleep(1)
        # 粘贴到textarea
        page.locator("textarea").first.click()
        page.locator("textarea").first.fill(paste_text)
        time.sleep(0.5)
        page.get_by_role("button", name=u"导入").click()
        time.sleep(2)
        print("  [OK] 粘贴导入")
    except Exception as e:
        print(f"  粘贴导入失败: {e}")

    # 8. 保存
    try:
        page.get_by_role("button", name=u"保存").click()
        time.sleep(3)
        ok = style_name in page.inner_text("body")
        print(f"  [{'SAVED' if ok else 'WARN'}] {style_name}")
        return True
    except:
        print(f"  [FAIL] 保存")
        return False

def main():
    styles = [
        {"name": u"儿童拉毛卫衣", "cat": u"服装、鞋靴和珠宝饰品/男童时尚/男童服装/男童时尚帽衫和卫衣/男童时尚帽衫", "sc": u"男童装"},
        {"name": u"儿童拉毛卫裤", "cat": u"服装、鞋靴和珠宝饰品/男童时尚/男童服装/男童时尚套装/男童长裤套装", "sc": u"男童装"},
    ]
    p = sync_playwright().start()
    b = p.chromium.launch(headless=RPA_HEADLESS, slow_mo=200)
    ctx = b.new_context(storage_state=str(STATE_FILE), viewport={"width": 1920, "height": 1080})
    page = ctx.new_page()
    page.goto(SIZE_CHART_URL, wait_until="domcontentloaded"); time.sleep(4)
    for s in styles:
        if not create_one(page, s["name"], s["cat"], s["sc"]): break
    print("\n=== DONE ===")
    b.close(); p.stop()

if __name__ == "__main__":
    main()
