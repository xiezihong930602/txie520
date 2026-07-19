"""
尺码表模板自动创建 RPA - 完整版
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
RPA_HEADLESS = False  # 有头模式调试

# 所有可能的尺码参数复选框
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
    in_block = False
    headers = []
    data_rows = []
    
    for row in rows:
        if row[0] and isinstance(row[0], str) and row[0].strip().startswith(u"\u25a0"):
            in_block = style_key in str(row[0])
            continue
        if not in_block:
            continue
        if not row[0]:
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
    """从表头确定需要勾选的尺码参数"""
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
    """提取尺码值列表"""
    return [row[0] for row in data_rows if row[0]]


def generate_paste_text(headers, data_rows):
    """生成粘贴导入用的Tab分隔文本"""
    param_headers = [h for h in headers if h and h != u"\u5c3a\u7801"]
    lines = ["\t".join([u"\u5c3a\u7801"] + param_headers)]
    for row in data_rows:
        size = row[0] if row[0] else ""
        vals = []
        for i in range(1, len(headers)):
            v = row[i] if i < len(row) else ""
            vals.append(v if v else "")
        lines.append("\t".join([size] + vals))
    return "\n".join(lines)


def navigate_category(page, cat_path):
    """用键盘搜索方式选择类目"""
    try:
        inp = page.locator(".jx-dialog__wrapper input[placeholder*=\"\u8bf7\u9009\u62e9\"], .el-dialog__wrapper input[placeholder*=\"\u8bf7\u9009\u62e9\"]").first
        inp.click()
        time.sleep(0.5)
        inp.press("Control+a")
        # 取类目路径最后一段作为搜索关键词
        keyword = cat_path.split("/")[-1].strip()
        inp.type(keyword, delay=100)
        time.sleep(2)
        page.keyboard.press("ArrowDown")
        time.sleep(0.3)
        page.keyboard.press("Enter")
        time.sleep(0.5)
        return True
    except Exception as e:
        print(f"  选择类目失败: {e}")
        return False


def check_params(page, params):
    """勾选尺码参数复选框"""
    # 先确保面板可见
    try:
        param_els = page.locator(".el-checkbox").all()
        for el in param_els:
            try:
                label = el.locator(".el-checkbox__label").inner_text().strip()
                for p in params:
                    if label == p:
                        cb = el.locator(".el-checkbox__input")
                        cb.click(timeout=1000)
                        time.sleep(0.2)
                        break
            except:
                continue
    except Exception as e:
        print(f"  勾选参数失败: {e}")


def uncheck_all_sizes(page):
    """取消所有尺码勾选"""
    try:
        # 点击全选复选框取消（如果已勾选）
        header_cb = page.locator("th .el-checkbox").first
        header_cb.click()
        time.sleep(0.3)
        header_cb.click()  # 两次=先取消
        time.sleep(0.3)
    except:
        pass


def check_sizes(page, size_values):
    """勾选款式对应的尺码"""
    # 尺码列表在表格的td里
    try:
        rows = page.locator("tbody tr").all()
        for row in rows:
            try:
                label = row.locator("td").first.inner_text().strip()
                if label in size_values:
                    row.locator(".el-checkbox").first.click(timeout=1000)
                    time.sleep(0.1)
            except:
                continue
    except Exception as e:
        print(f"  勾选尺码失败: {e}")


def paste_import(page, paste_text):
    """粘贴导入尺码数据"""
    try:
        # 悬停Excel快速编辑
        excel_btn = page.locator("span:has-text('Excel\u5feb\u901f\u7f16\u8f91')").first
        excel_btn.hover()
        time.sleep(0.5)
        
        # 点击粘贴导入
        paste_opt = page.locator("text=\u7c98\u8d34\u5bfc\u5165").first
        paste_opt.click()
        time.sleep(1)
        
        # 在导入弹窗的文本框中粘贴
        textarea = page.locator("textarea").first
        textarea.click()
        time.sleep(0.3)
        textarea.fill(paste_text)
        time.sleep(0.5)
        
        # 点击导入按钮
        import_btn = page.locator("button:has-text('\u5bfc\u5165')").first
        import_btn.click()
        time.sleep(1.5)
        return True
    except Exception as e:
        print(f"  粘贴导入失败: {e}")
        return False


def save_template(page):
    """点击保存按钮"""
    try:
        save_btn = page.locator(".jx-dialog__wrapper button:has-text('\u4fdd\u5b58'), .el-dialog__wrapper button:has-text('\u4fdd\u5b58')").first
        save_btn.click()
        time.sleep(2)
        return True
    except:
        return False


def create_one_sizetable(page, style_name, cat_path, size_category):
    """创建一个尺码表模板"""
    print(f"\n===== {style_name} =====")
    
    # 读数据
    headers, data_rows, is_top = load_size_data(EXCEL_PATH, style_name)
    if not data_rows:
        print(f"  [SKIP] 未找到款式数据")
        return False
    
    params = get_params_from_headers(headers)
    sizes = get_size_values(data_rows)
    paste_text = generate_paste_text(headers, data_rows)
    
    print(f"  类型: {'上衣' if is_top else '裤子'}")
    print(f"  参数: {params}")
    print(f"  尺码数: {len(sizes)}")
    
    # 1. 点击创建按钮
    try:
        page.locator("button:has-text('\u521b\u5efa\u5c3a\u7801\u8868\u6a21\u677f')").first.click(timeout=5000)
    except:
        # 可能在弹窗内，先关闭
        try:
            page.locator(".jx-dialog__close").first.click()
            time.sleep(0.5)
        except: pass
        page.locator("button:has-text('\u521b\u5efa\u5c3a\u7801\u8868\u6a21\u677f')").first.click(timeout=5000)
    time.sleep(2)
    
    # 2. 模板名称
    try:
        # 找弹窗内的第一个input（模板名称）
        inputs = page.locator(".jx-dialog__wrapper input:not([type=\"hidden\"]), .el-dialog__wrapper input:not([type=\"hidden\"])").all()
        for inp in inputs:
            val = inp.input_value() if hasattr(inp, 'input_value') else ''
            if not val or len(val) == 0:
                try:
                    placeholder = inp.get_attribute("placeholder") or ""
                    if "模板名称" in placeholder or "名称" in placeholder:
                        continue
                except:
                    pass
        # 弹窗里第一个input通常是模板名称（类目cascader的input内部不直接可见）
        name_inp = page.locator(".jx-dialog__wrapper input, .el-dialog__wrapper input").first
        name_inp.click()
        name_inp.fill(style_name)
        time.sleep(0.3)
    
        page.screenshot(path=str(ROOT / f"size_step1_{style_name}.png"))
    except Exception as e:
        print(f"  填写名称失败: {e}")
        return False
    
    # 3. 类目
    navigate_category(page, cat_path)
    time.sleep(0.5)
    page.screenshot(path=str(ROOT / f"size_step2_{style_name}.png"))
    
    # 4. 尺码表分类
    try:
        # 类目选择后页面可能刷新，重新定位分类下拉框
        selects = page.locator(".jx-dialog__wrapper .el-select, .el-dialog__wrapper .el-select").all()
        # 找包含"分类"字样的
        for sel in selects:
            try:
                txt = sel.inner_text()
                if u"\u5206\u7c7b" in txt or u"\u7537\u7ae5" in txt or u"\u5973\u7ae5" in txt:
                    sel.click()
                    time.sleep(0.5)
                    break
            except:
                continue
        # 选分类
        if size_category:
            option = page.locator(f"li:has-text('{size_category}')").first
            option.click(timeout=3000)
            time.sleep(0.3)
    except Exception as e:
        print(f"  选择分类失败: {e}")
    
    # 5. 勾选尺码参数
    check_params(page, params)
    time.sleep(0.5)
    page.screenshot(path=str(ROOT / f"size_step3_{style_name}.png"))
    
    # 6. 取消全选 → 勾选对应尺码
    uncheck_all_sizes(page)
    time.sleep(0.3)
    check_sizes(page, sizes)
    time.sleep(0.5)
    page.screenshot(path=str(ROOT / f"size_step4_{style_name}.png"))
    
    # 7. 粘贴导入
    paste_import(page, paste_text)
    page.screenshot(path=str(ROOT / f"size_step5_{style_name}.png"))
    
    # 8. 保存
    ok = save_template(page)
    print(f"  {'[OK]' if ok else '[FAIL]'} 保存")
    
    # 等待保存完成
    time.sleep(2)
    return ok


def main():
    # 测试三个款式
    test_styles = [
        {
            "name": u"\u513f\u7ae5\u62c9\u6bdb\u536b\u8863",  # 儿童拉毛卫衣 ST-001
            "cat": u"\u670d\u88c5\u3001\u978b\u9774\u548c\u73e0\u5b9d\u9970\u54c1/\u7537\u7ae5\u65f6\u5c1a/\u7537\u7ae5\u670d\u88c5/\u7537\u7ae5\u65f6\u5c1a\u5e3d\u886b\u548c\u536b\u8863/\u7537\u7ae5\u65f6\u5c1a\u5e3d\u886b",
            "size_cat": u"\u7537\u7ae5\u88c5"  # 男童装
        },
        {
            "name": u"\u513f\u7ae5\u62c9\u6bdb\u536b\u88e4",  # 儿童拉毛卫裤 ST-003
            "cat": u"\u670d\u88c5\u3001\u978b\u9774\u548c\u73e0\u5b9d\u9970\u54c1/\u7537\u7ae5\u65f6\u5c1a/\u7537\u7ae5\u670d\u88c5/\u7537\u7ae5\u65f6\u5c1a\u5957\u88c5/\u7537\u7ae5\u957f\u88e4\u5957\u88c5",
            "size_cat": u"\u7537\u7ae5\u88c5"
        },
    ]
    
    p = sync_playwright().start()
    b = p.chromium.launch(headless=RPA_HEADLESS, slow_mo=200)
    ctx = b.new_context(
        storage_state=str(STATE_FILE) if STATE_FILE.exists() else None,
        viewport={"width": 1920, "height": 1080}
    )
    page = ctx.new_page()
    page.goto(SIZE_CHART_URL, wait_until="domcontentloaded")
    time.sleep(4)
    
    for style in test_styles:
        ok = create_one_sizetable(page, style["name"], style["cat"], style["size_cat"])
        if not ok:
            print(f"  [FAIL] {style['name']} - 停止测试")
            break
    
    print("\n=== 完成 ===")
    b.close()
    p.stop()

if __name__ == "__main__":
    main()
