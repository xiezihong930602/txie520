"""
尺码表模板自动创建 RPA v2 - 修复弹窗内input定位
"""
import os, sys, time, re
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
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    style_key = style_name.strip()
    in_block = False; headers = []; data_rows = []
    for row in rows:
        if row[0] and isinstance(row[0], str) and row[0].strip().startswith(u"\u25a0"):
            in_block = style_key in str(row[0])
            continue
        if not in_block or not row[0]:
            continue
        if isinstance(row[0], str) and u"\u5c3a\u7801" in str(row[0]):
            headers = [str(c).strip() if c else "" for c in row]
            continue
        if headers and row[0] is not None:
            vals = [str(c).strip() if c is not None and str(c).strip() else "" for c in row]
            if vals and vals[0]:
                data_rows.append(vals)
    if not data_rows:
        return None, None, None
    is_top = any(u"\u80f8" in str(h) or u"\u80a9" in str(h) for h in headers)
    return headers, data_rows, is_top

def get_params_from_headers(headers):
    params = []
    for h in headers:
        if not h or h == u"\u5c3a\u7801":
            continue
        for p in ALL_PARAMS:
            if h in p or p in h:
                params.append(p)
                break
    return params

def get_size_values(data_rows):
    return [row[0] for row in data_rows if row[0]]

def generate_paste_text(headers, data_rows):
    param_headers = [h for h in headers if h and h != u"\u5c3a\u7801"]
    lines = ["\t".join([u"\u5c3a\u7801"] + param_headers)]
    for row in data_rows:
        size = row[0] if row[0] else ""
        vals = [row[i] if i < len(row) and row[i] else "" for i in range(1, len(headers))]
        lines.append("\t".join([size] + vals))
    return "\n".join(lines)

def create_one_sizetable(page, bp, style_name, cat_path, size_category):
    print(f"\n===== {style_name} =====")
    headers, data_rows, is_top = load_size_data(EXCEL_PATH, style_name)
    if not data_rows:
        print(f"  [SKIP] 未找到数据")
        return False
    params = get_params_from_headers(headers)
    sizes = get_size_values(data_rows)
    paste_text = generate_paste_text(headers, data_rows)
    print(f"  类型: {'上衣' if is_top else '裤子'}, 参数: {params}, 尺码: {len(sizes)}个")

    # 1. 点击创建按钮
    page.locator("button:has-text('创建尺码表模板')").first.click(timeout=5000)
    time.sleep(2)

    # --- 诊断：dump弹窗内所有input ---
    diag = page.evaluate("""() => {
        const dialogs = document.querySelectorAll('.el-dialog__wrapper, .jx-dialog__wrapper, [role="dialog"]');
        const result = [];
        for (const dlg of dialogs) {
            if (dlg.getBoundingClientRect().height < 100) continue;
            const inputs = dlg.querySelectorAll('input:not([type=hidden])');
            for (const inp of inputs) {
                result.push({
                    placeholder: inp.placeholder || '',
                    value: inp.value || '',
                    maxlength: inp.maxLength || '',
                    name: inp.name || '',
                    class: inp.className?.substring(0, 80) || '',
                    visible: inp.getBoundingClientRect().width > 0
                });
            }
        }
        return result;
    }""")
    print(f"  [诊断] 弹窗input: {diag}")

    # 2. 填模板名称 - 找placeholder含"请输入模板名称"的input
    try:
        name_inp = page.locator('input[placeholder*="请输入模板名称"]').first
        if name_inp.count() == 0:
            name_inp = page.locator('input[maxlength="60"]').first
        name_inp.click()
        name_inp.fill(style_name)
        time.sleep(0.3)
        page.screenshot(path=str(ROOT / f"size_s1_{style_name}.png"))
    except Exception as e:
        print(f"  填写名称失败: {e}")
        page.screenshot(path=str(ROOT / f"size_err_naming_{style_name}.png"))
        return False

    # 3. 选类目 - 键盘搜索
    try:
        cat_inp = page.locator('.el-cascader input, [class*="cascader"] input').first
        cat_inp.click()
        time.sleep(0.5)
        cat_inp.press("Control+a")
        keyword = cat_path.split("/")[-1].strip()
        cat_inp.type(keyword, delay=100)
        time.sleep(2)
        page.keyboard.press("ArrowDown")
        time.sleep(0.3)
        page.keyboard.press("Enter")
        time.sleep(0.5)
    except Exception as e:
        print(f"  选类目失败: {e}")

    # 4. 选尺码表分类
    try:
        sel = page.locator('.el-select', has_text='分类').first
        if sel.count() == 0:
            sel = page.locator('.el-select').nth(1)  # 第二个select通常是分类
        sel.click()
        time.sleep(0.5)
        page.locator(f"li:has-text('{size_category}')").first.click(timeout=3000)
        time.sleep(0.3)
    except Exception as e:
        print(f"  选分类失败: {e}")
    page.screenshot(path=str(ROOT / f"size_s4_{style_name}.png"))

    # 5. 勾选尺码参数
    try:
        cbs = page.locator(".el-checkbox__label").all()
        for cb in cbs:
            try:
                label = cb.inner_text().strip()
                if label in params:
                    cb.click(timeout=1000)
                    time.sleep(0.15)
            except:
                continue
    except Exception as e:
        print(f"  勾选参数失败: {e}")
    time.sleep(0.3)
    page.screenshot(path=str(ROOT / f"size_s5_{style_name}.png"))

    # 6. 取消全选 -> 勾选尺码
    try:
        # 先取消全选
        all_cb = page.locator("th .el-checkbox").first
        all_cb.click(); time.sleep(0.2)
        all_cb.click(); time.sleep(0.2)
        # 勾选对应尺码
        rows = page.locator("tbody tr").all()
        for row in rows:
            try:
                label = row.locator("td").first.inner_text().strip()
                if label in sizes:
                    row.locator(".el-checkbox").first.click(timeout=1000)
                    time.sleep(0.1)
            except:
                continue
    except Exception as e:
        print(f"  勾选尺码失败: {e}")
    time.sleep(0.3)
    page.screenshot(path=str(ROOT / f"size_s6_{style_name}.png"))

    # 7. 粘贴导入
    try:
        excel_btn = page.locator("span:has-text('Excel快速编辑')").first
        excel_btn.hover()
        time.sleep(0.5)
        page.locator("text=粘贴导入").first.click()
        time.sleep(1)
        textarea = page.locator("textarea").first
        textarea.click()
        time.sleep(0.3)
        textarea.fill(paste_text)
        time.sleep(0.5)
        page.locator("button:has-text('导入')").first.click()
        time.sleep(1.5)
    except Exception as e:
        print(f"  粘贴导入失败: {e}")
    page.screenshot(path=str(ROOT / f"size_s7_{style_name}.png"))

    # 8. 保存
    try:
        page.locator("button:has-text('保存')").first.click()
        time.sleep(2)
        print(f"  [OK] 保存")
    except:
        print(f"  [FAIL] 保存")
        page.screenshot(path=str(ROOT / f"size_err_save_{style_name}.png"))
        return False

    print(f"  [OK] {style_name}")
    return True


def main():
    test_styles = [
        {"name": "儿童拉毛卫衣", "cat": "服装、鞋靴和珠宝饰品/男童时尚/男童服装/男童时尚帽衫和卫衣/男童时尚帽衫", "size_cat": "男童装"},
        {"name": "儿童拉毛卫裤", "cat": "服装、鞋靴和珠宝饰品/男童时尚/男童服装/男童时尚套装/男童长裤套装", "size_cat": "男童装"},
    ]

    p = sync_playwright().start()
    b = p.chromium.launch(headless=RPA_HEADLESS, slow_mo=200)
    ctx = b.new_context(storage_state=str(STATE_FILE) if STATE_FILE.exists() else None, viewport={"width": 1920, "height": 1080})
    page = ctx.new_page()
    page.goto(SIZE_CHART_URL, wait_until="domcontentloaded")
    time.sleep(4)

    for style in test_styles:
        ok = create_one_sizetable(page, None, style["name"], style["cat"], style["size_cat"])
        if not ok:
            print(f"[FAIL] {style['name']} - 停止")
            break

    print("\n=== DONE ===")
    b.close()
    p.stop()

if __name__ == "__main__":
    main()
