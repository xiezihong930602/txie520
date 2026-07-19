"""
批量创建尺码表模板
用法: python batch_create_sizetables.py
"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from step1_read_data import load_size_data, map_param_labels, get_size_list

SIZE_CHART_URL = "https://erp.91miaoshou.com/pddkj/move_collect/template_management/sizeChart"
EXCEL_PATH = Path(r"C:\Users\Administrator\Downloads\款式尺码对照表（上衣裤子分格式）.xlsx")
STATE_FILE = Path(__file__).parent / "storage_state.json"

# 类目映射：根据款式类型和名称关键词
def get_category(style_name, is_top):
    if "成人" in style_name:
        return "服装、鞋靴和珠宝饰品/男装/男装上衣" if is_top else "服装、鞋靴和珠宝饰品/男装/男装下装"
    elif "女童" in style_name:
        return "服装、鞋靴和珠宝饰品/女童时尚/女童服装/女童上装" if is_top else "服装、鞋靴和珠宝饰品/女童时尚/女童服装/女童下装"
    else:  # 儿童/男童
        return "服装、鞋靴和珠宝饰品/男童时尚/男童服装/男童时尚帽衫和卫衣/男童时尚帽衫" if is_top else "服装、鞋靴和珠宝饰品/男童时尚/男童服装/男童下装"


def create_sizetable(page, style_name, cat_path):
    headers, data_rows, is_top = load_size_data(EXCEL_PATH, style_name)
    if not data_rows:
        print(f"  [SKIP] 无数据")
        return False

    param_labels = map_param_labels(headers)
    sizes = get_size_list(data_rows)
    data_map = {str(r[0]): r[1:] for r in data_rows}
    print(f"  {style_name} 尺码:{sizes} 参数:{param_labels}")

    # 0. 打开弹窗
    page.get_by_role("button", name="创建尺码表模板").click()
    time.sleep(2)

    # 1. 名称
    page.get_by_role("textbox", name="*模板名称").click()
    page.get_by_role("textbox", name="*模板名称").fill(style_name)
    time.sleep(0.3)

    # 2. 类目 — 键盘搜索
    cat_kw = cat_path.split("/")[-1].strip()
    page.get_by_role("textbox", name="*类目").click()
    time.sleep(0.3)
    page.get_by_role("textbox", name="*类目").fill(cat_kw)
    time.sleep(2)
    try:
        page.locator(f"li:has-text('{cat_kw}')").first.click(timeout=5000)
    except:
        page.keyboard.press("ArrowDown")
        time.sleep(0.3)
        page.keyboard.press("Enter")
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

    # 5. 两阶段填充
    remaining = set(sizes)
    checked = set()
    for i in range(80):
        page.evaluate("(p) => document.querySelector('.vue-recycle-scroller').scrollTop = p", i * 150)
        time.sleep(0.3)
        page.evaluate("""(args) => {
            const items = document.querySelectorAll('.vue-recycle-scroller__item-view');
            for (const item of items) {
                const txt = (item.innerText || '').trim().split(' ')[0];
                if (args.remaining.includes(txt)) {
                    const cb = item.querySelector('.jx-checkbox__inner');
                    if (cb) cb.click();
                }
            }
        }""", {"remaining": list(remaining)})
        time.sleep(0.15)

        result = page.evaluate("""(args) => {
            const filled = [];
            const items = document.querySelectorAll('.vue-recycle-scroller__item-view');
            for (const item of items) {
                const txt = (item.innerText || '').trim().split(' ')[0];
                if (args.remaining.includes(txt)) {
                    const inputs = item.querySelectorAll('input[type="text"]');
                    const cols = args.dataMap[txt];
                    if (cols && inputs.length > 0 && !inputs[0].disabled) {
                        for (let j = 0; j < cols.length && j < inputs.length; j++) {
                            const inp = inputs[j];
                            inp.focus();
                            inp.select();
                            document.execCommand('insertText', false, String(cols[j] || ''));
                        }
                        filled.push(txt);
                    }
                }
            }
            return filled;
        }""", {"remaining": list(remaining), "dataMap": data_map})

        for sz in result:
            remaining.discard(sz)
            checked.add(sz)
        if not remaining:
            break

    ok_fill = len(checked) == len(sizes)
    print(f"    填充:{len(checked)}/{len(sizes)} {'OK' if ok_fill else 'FAIL'}")

    # 6. 保存
    page.get_by_role("button", name="保存").click(force=True)
    time.sleep(2)
    print(f"    [SAVED]")
    return True


def main():
    # 测试款式列表（先用已验证的儿童拉毛卫衣 + 一个裤子）
    test_styles = [
        "儿童拉毛卫衣",
        "儿童拉毛卫裤",
    ]

    p = sync_playwright().start()
    b = p.chromium.launch(headless=False, slow_mo=200)
    ctx = b.new_context(storage_state=str(STATE_FILE), viewport={"width": 1920, "height": 1080})
    page = ctx.new_page()
    page.goto(SIZE_CHART_URL, wait_until="domcontentloaded")
    time.sleep(4)

    for name in test_styles:
        headers, data_rows, is_top = load_size_data(EXCEL_PATH, name)
        cat = get_category(name, is_top)
        print(f"\n--- {name} (类目: {cat.split('/')[-1]}) ---")
        create_sizetable(page, name, cat)

    print("\n全部完成。检查浏览器后按 Enter 关闭...")
    input()
    b.close()
    p.stop()


if __name__ == "__main__":
    main()
