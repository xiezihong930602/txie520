"""尺码表模板自动创建 RPA v5 - 修复弹窗定位"""
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

DIALOG_BASE = '.el-dialog__wrapper:visible, .jx-dialog__wrapper:visible'
DIALOG_VISIBLE = '.el-dialog__wrapper'

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

def get_params_from_headers(headers):
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

def get_visible_dialog(page):
    """找到当前可见的弹窗"""
    dialogs = page.locator(DIALOG_VISIBLE).all()
    for d in dialogs:
        if d.is_visible():
            return d
    # fallback: 用JS找
    vid = page.evaluate("""() => {
        const ds = document.querySelectorAll('.el-dialog__wrapper, .jx-dialog__wrapper');
        for (let i = ds.length - 1; i >= 0; i--) {
            if (ds[i].getBoundingClientRect().height > 100 && ds[i].style.display !== 'none') return i;
        }
        return -1;
    }""")
    if vid >= 0:
        return dialogs[vid]
    return None

def create_one(page, style_name, cat_path, size_category):
    print(f"\n===== {style_name} =====")
    headers, data_rows, is_top = load_size_data(EXCEL_PATH, style_name)
    if not data_rows: print(f"  [SKIP] 未找到数据"); return False
    params = get_params_from_headers(headers)
    sizes = get_size_values(data_rows)
    paste_text = generate_paste_text(headers, data_rows)
    print(f"  类型: {'上衣' if is_top else '裤子'}, 参数: {params}, 尺码: {len(sizes)}")

    # 1. 创建
    page.locator("button:has-text('创建尺码表模板')").first.click(force=True)
    time.sleep(2)

    dialog = get_visible_dialog(page)
    if not dialog:
        print(f"  [FAIL] 找不到弹窗")
        page.screenshot(path=str(ROOT / f"size_err_nodlg_{style_name}.png"))
        return False
    print(f"  弹窗可见: True")

    # 2. 填名称
    try:
        name_inp = dialog.locator('input[placeholder*="模板名称"]')
        if name_inp.count() == 0:
            # 第一个input（排除cascader的）
            name_inp = dialog.locator('input:not([placeholder*="搜索"]):not([placeholder*="选择"])').first
        name_inp.click(force=True)
        name_inp.fill(style_name)
        time.sleep(0.3)
        print(f"  [OK] 名称")
    except Exception as e:
        print(f"  名称失败: {e}")
        page.screenshot(path=str(ROOT / f"size_err_name_{style_name}.png"))
        return False

    # 3. 类目
    try:
        cat_inp = dialog.locator('input[placeholder*="请选择或输入搜索"]')
        cat_inp.click(force=True)
        time.sleep(0.5)
        cat_inp.press("Control+a")
        keyword = cat_path.split("/")[-1].strip()
        cat_inp.type(keyword, delay=100)
        time.sleep(2)
        page.keyboard.press("ArrowDown"); time.sleep(0.3)
        page.keyboard.press("Enter"); time.sleep(0.5)
        print(f"  [OK] 类目: {keyword}")
    except Exception as e:
        print(f"  类目失败: {e}")
        page.screenshot(path=str(ROOT / f"size_err_cat_{style_name}.png"))
        return False

    # 4. 分类
    try:
        sel = dialog.locator('.el-select', has_text='分类')
        if sel.count() == 0: sel = dialog.locator('.el-select').nth(1)
        sel.click(force=True); time.sleep(0.5)
        page.locator(f"li:has-text('{size_category}')").first.click(timeout=3000)
        time.sleep(0.3)
        print(f"  [OK] 分类: {size_category}")
    except:
        print(f"  [WARN] 分类跳过")

    # 5. 勾选参数
    cbs = dialog.locator(".el-checkbox__label").all()
    for cb in cbs:
        try:
            label = cb.inner_text().strip()
            if label in params:
                cb.click(force=True); time.sleep(0.1)
        except: continue
    print(f"  [OK] 参数勾选")

    # 6. 尺码勾选
    try:
        ac = dialog.locator("th .el-checkbox").first
        ac.click(force=True); time.sleep(0.2)
        ac.click(force=True); time.sleep(0.2)
        rows = dialog.locator("tbody tr").all()
        for row in rows:
            try:
                label = row.locator("td").first.inner_text().strip()
                if label in sizes:
                    row.locator(".el-checkbox").first.click(force=True); time.sleep(0.1)
            except: continue
        print(f"  [OK] 尺码勾选: {len(sizes)}")
    except Exception as e:
        print(f"  尺码勾选失败: {e}")

    # 7. 粘贴导入
    try:
        eb = dialog.locator("span:has-text('Excel快速编辑')")
        eb.hover(); time.sleep(0.5)
        page.locator("text=粘贴导入").first.click(); time.sleep(1)
        ta = page.locator("textarea").first
        ta.click(); time.sleep(0.3)
        ta.fill(paste_text); time.sleep(0.5)
        page.locator("button:has-text('导入')").first.click(); time.sleep(1.5)
        print(f"  [OK] 粘贴导入")
    except Exception as e:
        print(f"  粘贴导入失败: {e}")

    # 8. 保存
    try:
        dialog.locator("button:has-text('保存')").click(force=True)
        time.sleep(2)
        print(f"  [SAVED] {style_name}")
        return True
    except:
        print(f"  [FAIL] 保存")
        page.screenshot(path=str(ROOT / f"size_err_save_{style_name}.png"))
        return False

def main():
    styles = [
        {"name": "儿童拉毛卫衣", "cat": "服装、鞋靴和珠宝饰品/男童时尚/男童服装/男童时尚帽衫和卫衣/男童时尚帽衫", "sc": "男童装"},
        {"name": "儿童拉毛卫裤", "cat": "服装、鞋靴和珠宝饰品/男童时尚/男童服装/男童时尚套装/男童长裤套装", "sc": "男童装"},
    ]
    p = sync_playwright().start()
    b = p.chromium.launch(headless=RPA_HEADLESS, slow_mo=200)
    ctx = b.new_context(storage_state=str(STATE_FILE) if STATE_FILE.exists() else None, viewport={"width": 1920, "height": 1080})
    page = ctx.new_page()
    page.goto(SIZE_CHART_URL, wait_until="domcontentloaded"); time.sleep(4)
    for s in styles:
        if not create_one(page, s["name"], s["cat"], s["sc"]): break
    print("\n=== DONE ===")
    b.close(); p.stop()

if __name__ == "__main__":
    main()
