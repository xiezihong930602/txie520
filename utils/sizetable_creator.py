"""
尺码表自动创建模块（供RPA上架流程调用）
"""
import time
from pathlib import Path

EXCEL_PATH = Path(r"C:\Users\Administrator\Downloads\款式尺码对照表（上衣裤子分格式）.xlsx")


def create_sizetable_for_style(page, style_name: str, cat_path: str = "") -> bool:
    """在已打开的页面中创建尺码表（page需已导航到尺码表管理页）"""
    from step1_read_data import load_size_data, map_param_labels, get_size_list

    headers, data_rows, is_top = load_size_data(EXCEL_PATH, style_name)
    if not data_rows:
        print(f"  [SKIP] 无尺码数据")
        return False

    if not cat_path:
        print(f"  [SKIP] 无类目路径")
        return False

    param_labels = map_param_labels(headers)
    sizes = get_size_list(data_rows)
    data_map = {str(r[0]): r[1:] for r in data_rows}
    print(f"  创建尺码表: {style_name} 尺码:{sizes}")

    # 0. 打开弹窗
    page.get_by_role("button", name="创建尺码表模板").click()
    time.sleep(2)

    # 1. 名称
    page.get_by_role("textbox", name="*模板名称").click()
    page.get_by_role("textbox", name="*模板名称").fill(style_name)
    time.sleep(0.3)

    # 2. 类目 — 同step2_fill_only验证过的方式
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

    # 5. 两阶段填充（同step2_fill_only验证过的逻辑）
    remaining = set(sizes)
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
        if not remaining:
            break

    # 6. 保存
    page.get_by_role("button", name="保存").click(force=True)
    time.sleep(2)
    print(f"  [OK] 尺码表已创建: {style_name}")
    return True
