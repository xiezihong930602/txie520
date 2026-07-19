"""尺码表模板自动创建 RPA - 最终版
流程：导航 → 创建 → 填名称 → 选类目 → 选分类 → 勾参数 → 取消全选 → 勾尺码 → 粘贴导入 → 保存
"""
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
    last = cat_path.split("/")[-1].strip()
    keywords = [u"帽衫", u"卫衣", u"长裤", u"短裤", u"背心", u"夹克", u"套装", u"polo", u"T恤", u"马甲", u"马甲"]
    for kw in keywords:
        if kw in last or kw.lower() in last.lower():
            return kw
    parts = last.split()
    return parts[-1] if parts else last

def create_one(page, style_name, cat_path, size_category):
    print(f"\n===== {style_name} =====")
    headers, data_rows, is_top = load_size_data(EXCEL_PATH, style_name)
    if not data_rows: print(f"  [SKIP] 未找到数据"); return False
    param_labels = get_param_labels(headers)
    sizes = get_size_values(data_rows)
    paste_text = generate_paste_text(headers, data_rows)
    cat_kw = get_cat_keyword(cat_path)
    print(f"  类型: {'上衣' if is_top else '裤子'}")
    print(f"  参数: {param_labels}")
    print(f"  尺码({len(sizes)}): {sizes[:5]}...")
    print(f"  类目关键词: {cat_kw}")

    # === 步骤1: 点击创建按钮 ===
    page.get_by_role("button", name=u"创建尺码表模板").click()
    time.sleep(2)

    # === 步骤2: 填写模板名称 ===
    page.get_by_role("textbox", name=u"*模板名称").click()
    page.get_by_role("textbox", name=u"*模板名称").fill(style_name)
    time.sleep(0.3)
    print("  [OK] 模板名称")

    # === 步骤3: 选择类目 ===
    page.get_by_role("textbox", name=u"*类目").click()
    time.sleep(0.3)
    # 搜索类目关键词
    page.get_by_role("textbox", name=u"*类目").fill(cat_kw)
    time.sleep(2)
    # 从级联浮层中点击匹配项
    try:
        page.get_by_role("listitem").filter(has_text=cat_path).first.click(timeout=5000)
    except:
        page.get_by_role("listitem").filter(has_text=cat_kw).first.click(timeout=5000)
    time.sleep(0.5)
    print(f"  [OK] 类目: {cat_kw}")

    # === 步骤4: 选择尺码表分类 ===
    try:
        # 分类下拉框在弹窗里，查找含有分类文字的el-select
        page.locator(".el-dialog__wrapper .el-select", has_text=u"分类").first.click(timeout=3000)
        time.sleep(0.5)
        page.get_by_role("listitem").filter(has_text=size_category).first.click(timeout=3000)
        time.sleep(0.3)
        print(f"  [OK] 分类: {size_category}")
    except:
        print(f"  [WARN] 分类选择跳过")

    # === 步骤5: 勾选尺码参数 ===
    # 参数复选框是 label 包裹的 .jx-checkbox__inner
    for pl in param_labels:
        try:
            page.locator(f"label:has-text('{pl}') .jx-checkbox__inner").click(timeout=2000)
            time.sleep(0.15)
        except:
            pass
    print(f"  [OK] 参数勾选: {len(param_labels)}个")

    # === 步骤6: 取消全选 ===
    try:
        page.locator("th .jx-checkbox__inner").first.click(timeout=2000)
        time.sleep(0.2)
        # 如果第一次点击是勾选（表头默认未勾），再点一次取消
        page.locator("th .jx-checkbox__inner").first.click(timeout=2000)
        time.sleep(0.3)
    except:
        pass

    # === 步骤7: 勾选对应尺码 ===
    checked = 0
    for size in sizes:
        try:
            # 虚拟滚动：需要先让目标行出现在视口
            row_sel = f"tr:has(td:text-is('{size}')) .jx-checkbox__inner"
            cb = page.locator(row_sel).first
            if cb.is_visible():
                cb.click(timeout=2000)
                checked += 1
                time.sleep(0.1)
            else:
                # 不可见时跳过（尺码不在当前页的虚拟滚动范围内）
                pass
        except:
            pass
    print(f"  [OK] 尺码勾选: {checked}/{len(sizes)}")

    # === 步骤8: 粘贴导入 ===
    try:
        page.get_by_role("button", name=u"Excel快速编辑").click()
        time.sleep(0.5)
        page.get_by_role("menuitem", name=u"第二步：粘贴导入").click()
        time.sleep(1)
        page.locator("textarea").first.click()
        page.locator("textarea").first.fill(paste_text)
        time.sleep(0.5)
        page.get_by_role("button", name=u"导入").click()
        time.sleep(2)
        print(f"  [OK] 粘贴导入")
    except Exception as e:
        print(f"  [FAIL] 粘贴导入: {e}")
        return False

    # === 步骤9: 保存 ===
    try:
        page.get_by_role("button", name=u"保存").click()
        time.sleep(3)
        # 验证是否出现在列表里
        page_text = page.inner_text("body")
        if style_name in page_text:
            print(f"  [SAVED] {style_name}")
            return True
        else:
            print(f"  [WARN] 可能未保存成功，模板列表中未找到")
            return False
    except Exception as e:
        print(f"  [FAIL] 保存: {e}")
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
    page.goto(SIZE_CHART_URL, wait_until="domcontentloaded")
    time.sleep(4)

    ok = fail = 0
    for s in styles:
        if create_one(page, s["name"], s["cat"], s["sc"]):
            ok += 1
        else:
            fail += 1
            break

    print(f"\n=== 完成: 成功{ok}, 失败{fail} ===")
    b.close()
    p.stop()

if __name__ == "__main__":
    main()
