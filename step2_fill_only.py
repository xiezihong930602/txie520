"""
尺码表模板自动创建 - 精简版（只填表，不保存不截图）
"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from step1_read_data import load_size_data, map_param_labels, get_size_list

SIZE_CHART_URL = "https://erp.91miaoshou.com/pddkj/move_collect/template_management/sizeChart"
EXCEL_PATH = Path(r"C:\Users\Administrator\Downloads\款式尺码对照表（上衣裤子分格式）.xlsx")
STATE_FILE = Path(__file__).parent / "storage_state.json"


def fill_one(page, style_name, cat_path, size_category):
    headers, data_rows, is_top = load_size_data(EXCEL_PATH, style_name)
    if not data_rows:
        return False

    param_labels = map_param_labels(headers)
    sizes = get_size_list(data_rows)
    print(f"  尺码: {sizes}")

    # 0. 弹窗
    page.get_by_role("button", name="创建尺码表模板").click()
    time.sleep(2)

    # 1. 名称
    page.get_by_role("textbox", name="*模板名称").click()
    page.get_by_role("textbox", name="*模板名称").fill(style_name)
    time.sleep(0.3)

    # 2. 类目
    cat_kw = cat_path.split("/")[-1].strip()
    page.get_by_role("textbox", name="*类目").click()
    time.sleep(0.3)
    page.get_by_role("textbox", name="*类目").fill(cat_kw)
    time.sleep(2)
    page.locator(f"li:has-text('{cat_kw}')").first.click(timeout=5000)
    time.sleep(1.5)

    # 3. 参数勾选
    for pl in param_labels:
        try:
            page.locator(f"label:has-text('{pl}') .jx-checkbox__inner").click(timeout=2000)
            time.sleep(0.15)
        except:
            pass
    time.sleep(1)

    # 4. 取消全选
    try:
        page.locator(".pro-virtual-table__checkbox.is-checked .jx-checkbox__inner").first.click(timeout=3000)
        time.sleep(0.3)
    except:
        pass

    # 5. 滚动填充
    checked = set()
    remaining = set(str(r[0]) for r in data_rows)
    data_map = {str(r[0]): r[1:] for r in data_rows}

    for pos in range(0, 10000, 200):
        page.evaluate("document.querySelector('.vue-recycle-scroller').scrollTop = arguments[0]", pos)
        time.sleep(0.35)

        result = page.evaluate("""(args) => {
            const ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            const filled = [];
            const items = document.querySelectorAll('.vue-recycle-scroller__item-view');
            for (const item of items) {
                const txt = item.innerText.trim().split(/\s+/)[0];
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
            print(f"  filled: {sz}")

        if not remaining:
            break

    print(f"  结果: {len(checked)}/{len(data_rows)} 行 {sorted(checked)}")
    return len(checked) == len(data_rows)


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

    print("\n完成。关闭浏览器中...")
    time.sleep(2)
    b.close()
    p.stop()


if __name__ == "__main__":
    main()
