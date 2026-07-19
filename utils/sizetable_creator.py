"""
尺码表自动创建模块（供RPA上架流程调用）
"""
import time
from pathlib import Path

SIZE_CHART_URL = "https://erp.91miaoshou.com/pddkj/move_collect/template_management/sizeChart"
EXCEL_PATH = Path(r"C:\Users\Administrator\Downloads\款式尺码对照表（上衣裤子分格式）.xlsx")

# 类目映射：style.category → 完整类目路径
CATEGORY_MAP = {
    "儿童上衣": "服装、鞋靴和珠宝饰品/男童时尚/男童服装/男童时尚帽衫和卫衣/男童时尚帽衫",
    "儿童裤子": "服装、鞋靴和珠宝饰品/男童时尚/男童服装/男童下装",
    "成人上衣": "服装、鞋靴和珠宝饰品/男装/男装上衣",
    "成人裤子": "服装、鞋靴和珠宝饰品/男装/男装下装",
    "女童上衣": "服装、鞋靴和珠宝饰品/女童时尚/女童服装/女童上装",
    "女童裤子": "服装、鞋靴和珠宝饰品/女童时尚/女童服装/女童下装",
}
DEFAULT_CAT = ""  # 优先从上架页面读取，读不到才用


def get_category_path(style_name: str, category: str = "") -> str:
    """根据款式名和分类获取类目路径，失败返回空字符串"""
    if "成人" in style_name:
        return CATEGORY_MAP.get("成人上衣" if "裤" not in style_name else "成人裤子", "")
    if "女童" in style_name:
        return CATEGORY_MAP.get("女童上衣" if "裤" not in style_name else "女童裤子", "")
    if category:
        return CATEGORY_MAP.get(category, "")
    return CATEGORY_MAP.get("儿童上衣" if "裤" not in style_name else "儿童裤子", "")


def create_sizetable_for_style(page, style_name: str, cat_path: str = "") -> bool:
    """在已打开的页面中创建尺码表（page需已导航到尺码表管理页）"""
    from step1_read_data import load_size_data, map_param_labels, get_size_list

    headers, data_rows, is_top = load_size_data(EXCEL_PATH, style_name)
    if not data_rows:
        print(f"  [SKIP] 无尺码数据")
        return False

    if not cat_path:
        cat_path = get_category_path(style_name)
    if not cat_path:
        print(f"  [SKIP] 无法确定类目路径")
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

    # 2. 类目 — 打开面板→输入最后一级→找最短匹配文字点击（叶子节点）
    cat_kw = cat_path.split("/")[-1].strip()
    page.get_by_role("textbox", name="*类目").click()
    time.sleep(0.5)
    # 先点开级联面板
    page.locator(".el-cascader input, .el-input__inner").first.click()
    time.sleep(0.3)
    page.keyboard.type(cat_kw)
    time.sleep(2)
    # 找搜索下拉中文本最短的匹配项点击（最短=最末级=最精确）
    page.evaluate("""(kw) => {
        let best = null, bestLen = 999;
        const nodes = document.querySelectorAll('.el-cascader-node__label, .el-cascader-menu__item, li[role="menuitem"]');
        for (const n of nodes) {
            const t = (n.innerText || '').trim();
            if (t.includes(kw) && t.length < bestLen) {
                best = n; bestLen = t.length;
            }
        }
        if (best) best.click();
    }""", cat_kw)
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

    # 5. 先读表头列顺序，构建列名→索引映射
    col_map = page.evaluate("""(params) => {
        const result = {};
        const headers = document.querySelectorAll('.pro-virtual-table__header .pro-virtual-table__header-cell, .el-table__header th');
        headers.forEach((th, i) => {
            const txt = (th.innerText || '').trim();
            for (const p of params) {
                if (txt.includes(p) || p.includes(txt)) { result[p] = i; break; }
            }
        });
        return result;
    }""", param_labels)
    print(f"    列映射: {col_map}")

    # 6. 两阶段填充（按列映射填正确位置）
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
                        for (let j = 0; j < cols.length; j++) {
                            // 按列映射找正确的input索引
                            const param = args.paramLabels[j];
                            const targetIdx = args.colMap[param];
                            if (targetIdx !== undefined && targetIdx < inputs.length) {
                                const inp = inputs[targetIdx];
                                inp.focus();
                                inp.select();
                                document.execCommand('insertText', false, String(cols[j] || ''));
                            }
                        }
                        filled.push(txt);
                    }
                }
            }
            return filled;
        }""", {"remaining": list(remaining), "dataMap": data_map, "colMap": col_map, "paramLabels": param_labels})

        for sz in result:
            remaining.discard(sz)
        if not remaining:
            break

    # 6. 保存
    page.get_by_role("button", name="保存").click(force=True)
    time.sleep(2)
    print(f"  [OK] 尺码表已创建: {style_name}")
    return True
