# -*- coding: utf-8 -*-
""" Step-2: 打开妙手创建弹窗, 只填表不保存, 每步截图 """
import os, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright
from step1_read_data import load_size_data, map_param_labels, get_size_list, gen_paste_text

SIZE_CHART_URL = "https://erp.91miaoshou.com/pddkj/move_collect/template_management/sizeChart"
EXCEL_PATH = Path(r"C:\Users\Administrator\Downloads\款式尺码对照表（上衣裤子分格式）.xlsx")
STATE_FILE = ROOT / "storage_state.json"
OUT_DIR = ROOT / "step2_screenshots"

def fill_one(page, style_name, cat_path, size_category):
    """只填表, 不保存"""
    os.makedirs(str(OUT_DIR), exist_ok=True)
    s = lambda n: page.screenshot(path=str(OUT_DIR / f"{style_name}_{n}.png"))

    headers, data_rows, is_top = load_size_data(EXCEL_PATH, style_name)
    if not data_rows:
        print(f"  [SKIP] 未找到数据")
        return False

    param_labels = map_param_labels(headers)
    sizes = get_size_list(data_rows)
    paste_text = gen_paste_text(headers, data_rows)

    print(f"  类型: {'上衣' if is_top else '裤子'}")
    print(f"  参数: {param_labels}")
    print(f"  尺码({len(sizes)}): {sizes}")

    # --- 0. 打开创建弹窗 ---
    page.get_by_role("button", name="创建尺码表模板").click()
    time.sleep(2)
    s("0_dialog")

    # --- 1. 模板名称 ---
    page.get_by_role("textbox", name="*模板名称").click()
    page.get_by_role("textbox", name="*模板名称").fill(style_name)
    time.sleep(0.3)
    print("  [OK] 名称")

    # --- 2. 类目 ---
    page.get_by_role("textbox", name="*类目").click()
    time.sleep(0.3)
    page.get_by_role("textbox", name="*类目").fill(cat_path)
    time.sleep(0.5)
    # 等浮层出现, 点匹配的级联项
    try:
        # 用li:has_text匹配完整路径 — 浮层的li是el-cascader-node
        page.locator(f"li:has-text('{cat_path}')").first.click(timeout=5000)
    except:
        # fallback: 最后一段
        last_seg = cat_path.split("/")[-1].strip()
        page.get_by_role("listitem").filter(has_text=last_seg).first.click(timeout=5000)
    time.sleep(0.5)
    s("2_category")
    print("  [OK] 类目")

    # --- 3. 尺码表分类 ---
    try:
        # 弹窗内, 两个el-select, 第二个是分类(renderType=1)
        page.evaluate("""() => {
            const dlg = document.querySelector('.el-dialog__wrapper');
            if (!dlg) return;
            const selects = dlg.querySelectorAll('.el-select');
            for (const s of selects) {
                const vue = s.__vue__;
                if (vue && vue.renderType === 1) { s.click(); return; }
            }
            // fallback: 含"分类"或"童装"文本的
            for (const s of selects) {
                if (s.innerText.includes('分类') || s.innerText.includes('童装'))
                    { s.click(); return; }
            }
        }""")
        time.sleep(0.5)
        page.get_by_role("listitem").filter(has_text=size_category).first.click(timeout=3000)
        time.sleep(0.3)
        print(f"  [OK] 分类: {size_category}")
    except:
        print(f"  [WARN] 分类跳过")
    s("3_size_category")

    # --- 4. 勾选尺码参数 ---
    for pl in param_labels:
        try:
            page.locator(f"label:has-text('{pl}') .jx-checkbox__inner").click(timeout=2000)
            time.sleep(0.15)
        except:
            pass
    s("4_params")
    print(f"  [OK] 参数勾选: {len(param_labels)}")

    # --- 5. 取消全选 ---
    try:
        page.locator("th .jx-checkbox__inner").first.click(timeout=2000)
        time.sleep(0.2)
        page.locator("th .jx-checkbox__inner").first.click(timeout=2000)
        time.sleep(0.3)
    except:
        pass

    # --- 6. 勾选尺码 ---
    for sz in sizes:
        try:
            td = page.locator(f"td:text-is('{sz}')").first
            td.scroll_into_view_if_needed()
            time.sleep(0.25)
            page.locator(f"tr:has(td:text-is('{sz}')) .jx-checkbox__inner").first.click(timeout=3000)
            time.sleep(0.15)
        except Exception as e:
            print(f"    尺码 {sz} 失败: {e}")
    s("6_sizes")
    print(f"  [OK] 尺码勾选")

    # --- 7. 粘贴导入 ---
    try:
        page.locator("span:has-text('Excel快速编辑')").first.click()
        time.sleep(0.5)
        page.locator("text=第二步：粘贴导入").first.click()
        time.sleep(1)

        # JS 强行写入 textarea
        page.evaluate("""(text) => {
            const ta = document.querySelector('textarea');
            if (ta) {
                ta.focus();
                ta.value = text;
                ta.dispatchEvent(new Event('input', { bubbles: true }));
                ta.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }""", paste_text)
        time.sleep(0.3)

        # 再点一下 textarea 确保聚焦
        page.locator("textarea").first.click()
        s("7_pasted")
        print("  [OK] 粘贴完成(未点导入)")
    except Exception as e:
        print(f"  [FAIL] 粘贴: {e}")
        s("7_paste_fail")

    return True


def main():
    p = sync_playwright().start()
    b = p.chromium.launch(headless=False, slow_mo=200)
    ctx = b.new_context(
        storage_state=str(STATE_FILE) if STATE_FILE.exists() else None,
        viewport={"width": 1920, "height": 1080}
    )
    page = ctx.new_page()
    page.goto(SIZE_CHART_URL, wait_until="domcontentloaded")
    time.sleep(4)

    fill_one(page, "儿童拉毛卫衣",
        "服装、鞋靴和珠宝饰品/男童时尚/男童服装/男童时尚帽衫和卫衣/男童时尚帽衫",
        "男童装")

    print("\n=== 截图保存在 step2_screenshots/ ===")
    print("检查完毕后手动关闭浏览器")
    input("按 Enter 关闭...")
    b.close()
    p.stop()


if __name__ == "__main__":
    main()
