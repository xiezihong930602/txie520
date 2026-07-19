"""尺码表模板自动创建 RPA - 修复版
修复: 1)虚拟滚动尺码勾选 2)导入弹窗关闭后保存 3)分类选择
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
    last = cat_path.split("/")[-1].strip()
    keywords = [u"帽衫", u"卫衣", u"长裤", u"短裤", u"背心", u"夹克", u"套装", u"polo", u"T恤", u"马甲"]
    for kw in keywords:
        if kw in last or kw.lower() in last.lower():
            return kw
    parts = last.split()
    return parts[-1] if parts else last

def create_one(page, style_name, cat_path, size_category):
    print(f"\n===== {style_name} =====")
    headers, data_rows, is_top = load_size_data(EXCEL_PATH, style_name)
    if not data_rows: print(f"  [SKIP]"); return False
    param_labels = get_param_labels(headers)
    sizes = get_size_values(data_rows)
    paste_text = generate_paste_text(headers, data_rows)
    cat_kw = get_cat_keyword(cat_path)
    print(f"  参数: {param_labels}, 尺码({len(sizes)}): {sizes}")

    # 1. 创建
    page.get_by_role("button", name=u"创建尺码表模板").click()
    time.sleep(2)

    # 2. 模板名称
    page.get_by_role("textbox", name=u"*模板名称").click()
    page.get_by_role("textbox", name=u"*模板名称").fill(style_name)
    time.sleep(0.3)

    # 3. 类目 - 直接粘贴完整路径
    page.get_by_role("textbox", name=u"*类目").click()
    time.sleep(0.3)
    page.get_by_role("textbox", name=u"*类目").fill(cat_path)
    time.sleep(0.5)
    # 等级联菜单弹出后选匹配项
    try:
        page.locator(f"li:has-text('{cat_path}')").first.click(timeout=5000)
    except:
        # fallback: 用最后一段关键词
        page.get_by_role("listitem").filter(has_text=cat_path.split("/")[-1].strip()).first.click(timeout=5000)
    time.sleep(0.5)
    print(f"  [OK] 类目")

    # 4. 分类 - 用JS点Vue下拉
    try:
        page.evaluate("""(cat) => {
            const dlg = document.querySelector('.el-dialog__wrapper');
            if (!dlg) return;
            const selects = dlg.querySelectorAll('.el-select');
            let target = null;
            for (const s of selects) {
                // 找renderType=1(分类选择)的select
                const vue = s.__vue__;
                if (vue && vue.renderType === 1) { target = s; break; }
                if (s.innerText.includes('分类') || s.innerText.includes('童装')) { target = s; break; }
            }
            if (target) target.click();
        }""", size_category)
        time.sleep(0.5)
        page.get_by_role("listitem").filter(has_text=size_category).first.click(timeout=3000)
        time.sleep(0.3)
        print(f"  [OK] 分类")
    except:
        print(f"  [WARN] 分类跳过")

    # 5. 参数勾选
    for pl in param_labels:
        try:
            page.locator(f"label:has-text('{pl}') .jx-checkbox__inner").click(timeout=2000)
            time.sleep(0.15)
        except: pass
    print(f"  [OK] 参数勾选: {len(param_labels)}")

    # 6. 取消全选
    try:
        page.locator("th .jx-checkbox__inner").first.click(timeout=2000)
        time.sleep(0.2)
        page.locator("th .jx-checkbox__inner").first.click(timeout=2000)
        time.sleep(0.3)
    except: pass

    # 7. 勾选尺码 - 先虚拟滚动到第一个可见，再依次选中
    for size in sizes:
        try:
            # 聚焦该尺码的td让它出现
            td = page.locator(f"td:text-is('{size}')").first
            td.scroll_into_view_if_needed()
            time.sleep(0.2)
            # 等虚拟滚动渲染完后勾选
            cb = page.locator(f"tr:has(td:text-is('{size}')) .jx-checkbox__inner").first
            cb.click(timeout=3000)
            time.sleep(0.15)
        except Exception as e:
            print(f"    尺码 {size} 勾选失败: {e}")
    print(f"  [OK] 尺码勾选")

    # 8. 粘贴导入
    try:
        page.locator("span:has-text('Excel快速编辑')").first.click()
        time.sleep(0.5)
        page.locator("text=第二步：粘贴导入").first.click()
        time.sleep(1)
        # 用剪贴板写入 → Ctrl+V 原生物理粘贴
        page.evaluate("""(text) => {
            const ta = document.querySelector('textarea');
            if (ta) {
                ta.focus();
                ta.value = text;
                ta.dispatchEvent(new Event('input', {bubbles: true}));
                ta.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }""", paste_text)
        time.sleep(0.3)
        # 再Ctrl+V确保
        page.locator("textarea").first.click()
        page.keyboard.press("Control+a")
        page.keyboard.press("Control+v")
        time.sleep(0.5)
        page.get_by_role("button", name=u"导入").click()
        time.sleep(2)
        print(f"  [OK] 粘贴导入")
    except Exception as e:
        print(f"  [FAIL] 粘贴导入: {e}")
        return False

    # 9. 保存
    try:
        page.get_by_role("button", name=u"保存").click(force=True)
        time.sleep(3)
        body = page.inner_text("body")
        ok = style_name in body
        print(f"  [{'SAVED' if ok else 'WARN'}] {style_name} {'(列表中已存在)' if ok else '(未找到)'}")
        return True
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
    page.goto(SIZE_CHART_URL, wait_until="domcontentloaded"); time.sleep(4)
    for s in styles:
        if not create_one(page, s["name"], s["cat"], s["sc"]): break
    print("\n=== DONE ===")
    b.close(); p.stop()

if __name__ == "__main__":
    main()
