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

    # ── 7. 纯JS原子操作：滚动+勾选+填数据都在一次evaluate中完成 ──
    # 每轮滚300px → 扫描 → 勾选+填 → 继续滚，全部在浏览器内同步执行
    result = page.evaluate("""(data_rows) => {
        const dataMap = {};
        data_rows.forEach(r => { dataMap[String(r[0])] = r.slice(1); });
        const remaining = Object.keys(dataMap);
        const filled = [];
        const ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
        
        const scroller = document.querySelector('.vue-recycle-scroller');
        if (!scroller) return {filled: [], reason: 'no scroller'};
        
        let lastScroll = -1;
        for (let attempt = 0; attempt < 120; attempt++) {
            scroller.scrollTop += 300;
            const cur = scroller.scrollTop;
            if (cur === lastScroll) break;
            lastScroll = cur;
            
            // 等渲染: 用requestAnimationFrame同步
            const waitStart = Date.now();
            while (Date.now() - waitStart < 400) { /* wait */ }
            
            // 从remaining中找第一个可处理的
            for (let ri = 0; ri < remaining.length; ri++) {
                const sz = remaining[ri];
                const items = scroller.querySelectorAll('.vue-recycle-scroller__item-view');
                for (const item of items) {
                    const txt = item.innerText.trim().split(/[\\s\\n]+/)[0];
                    if (txt === sz) {
                        // 勾选
                        const cb = item.querySelector('.jx-checkbox__inner');
                        if (cb) cb.click();
                        // 等Vue更新input状态
                        const start = Date.now();
                        while (Date.now() - start < 100) {}
                        // 填数据
                        const inputs = item.querySelectorAll('input[type="text"]');
                        const cols = dataMap[sz];
                        for (let i = 0; i < cols.length && i < inputs.length; i++) {
                            ns.call(inputs[i], String(cols[i] || ''));
                            inputs[i].dispatchEvent(new Event('input', {bubbles: true}));
                        }
                        filled.push(sz);
                        remaining.splice(ri, 1);
                        ri--;  // 调整索引
                        break;
                    }
                }
                if (filled.length > 0 && filled[filled.length-1] === sz) break; // 处理完一个
            }
            if (remaining.length === 0) break;
        }
        return {filled, remaining};
    }""", data_rows)
    
    s("6_sizes")
    filled = result.get('filled', [])
    print(f"  [OK] 尺码填充: {len(filled)}/{len(data_rows)} 行 ({sorted(filled)})")

    # ── 8. 保存 ──
    try:
        page.get_by_role("button", name="保存").click(force=True)
        time.sleep(3)
        # 验证保存成功：弹窗关闭且列表中出现模板名
        body = page.inner_text("body")
        ok = style_name in body and "创建尺码表模板" in body
        print(f"  {'[SAVED]' if ok else '[WARN]'} {style_name}")
    except Exception as e:
        print(f"  [FAIL] 保存: {e}")

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
