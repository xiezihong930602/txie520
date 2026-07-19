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

    # ── 5. 勾选参数后等重渲染 ──
    time.sleep(1)

    # ── 6. 取消全选 — 点表头已勾选的checkbox ──
    try:
        page.locator(".pro-virtual-table__checkbox.is-checked .jx-checkbox__inner").first.click(timeout=3000)
        time.sleep(0.3)
        print(f"  [OK] 取消全选")
    except Exception as e:
        print(f"  取消全选失败: {e}")

    # ── 7. Python滚+JS原子填充：每200px设scrollTop → sleep给浏览器渲染 → 单次evaluate扫描+勾选+fill ──
    checked = set()
    remaining = set(str(r[0]) for r in data_rows)
    data_map = {str(r[0]): r[1:] for r in data_rows}

    for pos in range(0, 10000, 200):
        page.evaluate(f"document.querySelector('.vue-recycle-scroller').scrollTop = {pos}")
        time.sleep(0.3)

        result = page.evaluate("""(args) => {
            const ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            const filled = [];
            const items = args.remaining.length ? document.querySelectorAll('.vue-recycle-scroller__item-view') : [];
            for (const item of items) {
                const txt = item.innerText.trim().split(/[\s\n]+/)[0];
                if (args.remaining.includes(txt)) {
                    const cb = item.querySelector('.jx-checkbox__inner');
                    if (cb) cb.click();
                    const inputs = item.querySelectorAll('input[type="text"]');
                    const cols = args.dataMap[txt];
                    if (cols) {
                        for (let j = 0; j < cols.length && j < inputs.length; j++) {
                            ns.call(inputs[j], String(cols[j] || ''));
                        }
                    }
                    filled.push(txt);
                }
            }
            return filled;
        }""", {"remaining": list(remaining), "dataMap": data_map})

        for sz in result:
            remaining.discard(sz)
            checked.add(sz)
            print(f"    filled: {sz}")

        if not remaining:
            break

    s("6_sizes")
    print(f"  [OK] 尺码填充: {len(checked)}/{len(data_rows)} 行 ({sorted(checked)})")

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
