"""step2 v2 - 修复版: 类目搜索/分类跳过/尺码trim匹配/预写剪贴板供CtrlV"""
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
    os.makedirs(str(OUT_DIR), exist_ok=True)
    s = lambda n: page.screenshot(path=str(OUT_DIR / f"{style_name}_{n}.png"))

    headers, data_rows, is_top = load_size_data(EXCEL_PATH, style_name)
    if not data_rows:
        print(f"  [SKIP]"); return False

    param_labels = map_param_labels(headers)
    sizes = get_size_list(data_rows)
    paste_text = gen_paste_text(headers, data_rows)

    print(f"  参数: {param_labels}")
    print(f"  尺码: {sizes}")

    # ── 0. 打开弹窗 ──
    page.get_by_role("button", name="创建尺码表模板").click()
    time.sleep(2)
    s("0_dialog")

    # ── 1. 名称 ──
    page.get_by_role("textbox", name="*模板名称").click()
    page.get_by_role("textbox", name="*模板名称").fill(style_name)
    time.sleep(0.3)
    print("  [OK] 名称")

    # ── 2. 类目 - 用搜索方式 ──
    cat_kw = cat_path.split("/")[-1].strip()
    page.get_by_role("textbox", name="*类目").click()
    time.sleep(0.3)
    page.get_by_role("textbox", name="*类目").fill(cat_kw)
    time.sleep(2)
    # 点浮层匹配项 — 用Li文本完整匹配
    try:
        # 先用完整类目路径模糊匹配
        found = page.locator(f"li:has-text('{cat_kw}')").first
        found.click(timeout=5000)
        time.sleep(1.5)  # 等待页面刷新（尺码参数列表加载）
        print(f"  [OK] 类目: {cat_kw}")
    except Exception as e:
        # fallback: 键盘 ArrowDown + Enter
        print(f"  li click失败: {e}, 尝试键盘选择")
        page.keyboard.press("ArrowDown")
        time.sleep(0.3)
        page.keyboard.press("Enter")
        time.sleep(1.5)
        print(f"  [OK] 类目(键盘)")
    s("2_category")

    # ── 3. 分类：已自动填好(男童装-上装/男童装-下装) ──
    # 跳过，如果以后需要用codegen录的方式
    print(f"  [SKIP] 分类(已自动)")

    # ── 4. 参数勾选 ──
    for pl in param_labels:
        try:
            page.locator(f"label:has-text('{pl}') .jx-checkbox__inner").click(timeout=2000)
            time.sleep(0.15)
        except: pass
    s("4_params")
    print(f"  [OK] 参数: {len(param_labels)}")

    # ── 5. 取消全选 → 先通过JS清空已勾选，再勾目标尺码 ──
    # 取消全选：直接改Vue内部checked状态清空选中的行
    page.evaluate("""() => {
        // 找到虚拟表格的Vue实例，清空selection
        const vt = document.querySelector('.pro-virtual-table, [class*="virtual-table"]');
        if (vt && vt.__vue__) {
            const vue = vt.__vue__;
            // 清空选中行
            if (vue.selection && Array.isArray(vue.selection)) vue.selection = [];
            if (vue.selectedRows && Array.isArray(vue.selectedRows)) vue.selectedRows = [];
        }
    }""")
    time.sleep(0.3)

    # 尺码列表很长，需要虚拟滚动到目标区域。用JS直接在虚拟表格数据层取勾选
    checked = page.evaluate("""(targets) => {
        // 虚拟表格的数据通常挂在 Vue 实例的 data 或 tableData 上
        const vt = document.querySelector('.pro-virtual-table, [class*="virtual-table"]');
        if (!vt || !vt.__vue__) return 0;
        const vue = vt.__vue__;
        const tableData = vue.tableData || vue.data || vue.list || [];
        let n = 0;
        // 直接在数据层匹配
        tableData.forEach(row => {
            const sizeText = String(row.size || row[Object.keys(row)[0]] || '').trim();
            if (targets.includes(sizeText)) {
                // 切换到选中状态
                if (!vue.selection) vue.selection = [];
                vue.selection.push(row);
                n++;
            }
        });
        // 强制更新视图
        if (vue.$forceUpdate) vue.$forceUpdate();
        return n;
    }""", sizes)
    print(f"  [OK] 尺码勾选(Vue层): {checked}/{len(sizes)}")

    # ── 7. 粘贴导入 ──
    try:
        # 先写剪贴板（Windows）
        import subprocess
        clip = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
        clip.communicate(input=paste_text.encode('utf-16-le'))
        clip.wait()

        page.locator("span:has-text('Excel快速编辑')").first.click()
        time.sleep(0.5)
        page.locator("text=第二步：粘贴导入").first.click()
        time.sleep(1)

        # Ctrl+V粘贴
        page.locator("textarea").first.click()
        time.sleep(0.3)
        page.keyboard.press("Control+a")
        page.keyboard.press("Control+v")
        time.sleep(0.5)
        s("7_pasted")
        print("  [OK] 粘贴(导入弹窗内, 未点导入)")
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

    print("\n=== 截图在 step2_screenshots/ ===")
    print("检查OK后手动关浏览器")
    input("按 Enter 关闭...")
    b.close()
    p.stop()


if __name__ == "__main__":
    main()
