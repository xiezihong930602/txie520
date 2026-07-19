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

    # ── 7. 滚到底边扫描边勾选 ──
    # 先聚焦尺码表区域
    try:
        page.locator(".pro-virtual-table, [class*='virtual-table']").first.click(force=True, timeout=2000)
        time.sleep(0.2)
    except:
        pass

    # 用JS滚动+扫描
    result = page.evaluate("""(targets) => {
        const targetsLeft = [...targets];
        const checked = [];
        
        // 找滚动容器
        const scroller = document.querySelector('.vue-recycle-scroller, [class*="recycle-scroller"]');
        if (!scroller) return {checked: [], reason: 'no scroller'};
        
        // 滚到底，每100ms检查一次可见的item
        const maxScroll = scroller.scrollHeight - scroller.clientHeight;
        const step = 150;
        for (let pos = 0; pos <= maxScroll + 200; pos += step) {
            scroller.scrollTop = pos;
            // 等虚拟滚动渲染
            const start = Date.now();
            while (Date.now() - start < 80) { /* busy wait */ }
            
            // 检查当前可见的item
            const items = scroller.querySelectorAll('.vue-recycle-scroller__item-view');
            for (const item of items) {
                const txt = item.innerText.trim();
                for (let i = 0; i < targetsLeft.length; i++) {
                    if (txt.includes(targetsLeft[i])) {
                        const cb = item.querySelector('.jx-checkbox__inner');
                        if (cb) {
                            cb.click();
                            checked.push(targetsLeft[i]);
                            targetsLeft.splice(i, 1);
                            break;
                        }
                    }
                }
            }
            if (targetsLeft.length === 0) break;
        }
        return {checked, remaining: targetsLeft};
    }""", sizes)
    s("6_sizes")
    print(f"  [OK] 尺码勾选: {len(result.get('checked',[]))}/{len(sizes)} (已勾:{result.get('checked',[])}, 剩余:{result.get('remaining',[])})")

    print(f"  [DEBUG] data_rows={data_rows}")

    # ── 8. 逐行填写数据(放弃粘贴导入) ──
    filled = page.evaluate("""(rows) => {
        const scroller = document.querySelector('.vue-recycle-scroller');
        if (!scroller) return 'no scroller';
        const targets = new Set(rows.map(r => String(r[0])));
        const filled_rows = new Set();
        const step = 200;
        const total = scroller.scrollHeight - scroller.clientHeight;
        for (let pos = 0; pos <= total + step; pos += step) {
            scroller.scrollTop = pos;
            // Wait for render
            const start = Date.now();
            while (Date.now() - start < 200) { /* wait */ }
            const items = scroller.querySelectorAll('.vue-recycle-scroller__item-view');
            for (const item of items) {
                const txt = item.innerText.trim().split(/[\\s\\n]+/)[0];
                if (targets.has(txt) && !filled_rows.has(txt)) {
                    const row = rows.find(r => String(r[0]) === txt);
                    if (row) {
                        const inputs = item.querySelectorAll('input[type="text"]');
                        for (let i = 0; i < row.length - 1 && i < inputs.length; i++) {
                            inputs[i].value = String(row[i + 1] || '');
                            inputs[i].dispatchEvent(new Event('input', {bubbles: true}));
                            inputs[i].dispatchEvent(new Event('change', {bubbles: true}));
                        }
                        filled_rows.add(txt);
                    }
                }
            }
            if (filled_rows.size >= targets.size) break;
        }
        return filled_rows.size;
    }""", data_rows)
    s("8_filled")
    print(f"  [OK] 逐行填充: {filled}{'/' + str(len(data_rows)) if isinstance(filled, int) else ''} 行")

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
