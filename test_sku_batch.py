# 测试SKU表格批量设置
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
import time

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", 
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_drivers"))

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage_state.json")
TEST_IMAGE_URLS = [
    "https://aka.doubaocdn.com/s/5wyU1wuoJ8",
    "https://aka.doubaocdn.com/s/QfQp1wuoJ8",
]

def save_screenshot(page, name):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{name}.png")
    page.screenshot(path=path, full_page=True)
    print(f"  截图: {name}.png")

def select_color(page, color_name):
    """选择颜色：输入颜色名 → 点击创建自定义颜色"""
    color_input_pos = page.evaluate("""
        () => {
            const inputs = document.querySelectorAll('.jx-dialog input');
            for (const inp of inputs) {
                const ph = inp.placeholder || '';
                if (ph.includes('颜色') || ph.includes('自定义')) {
                    const rect = inp.getBoundingClientRect();
                    return {x: Math.round(rect.left + 20), y: Math.round(rect.top + rect.height/2)};
                }
            }
            return null;
        }
    """)
    if not color_input_pos:
        return False
    
    page.mouse.click(color_input_pos['x'], color_input_pos['y'])
    time.sleep(0.3)
    page.keyboard.type(color_name)
    time.sleep(1)
    
    # 找创建自定义颜色选项
    custom_pos = page.evaluate("""
        (name) => {
            const all = document.querySelectorAll('*');
            let best = null;
            for (const el of all) {
                const text = el.innerText ? el.innerText.trim() : '';
                if (!text || el.children.length > 0) continue;
                if (text.startsWith('创建自定义颜色-') || text === '创建自定义颜色-' + name) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 20 && rect.height > 10) {
                        if (!best || rect.top > best.y) {
                            best = {x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)};
                        }
                    }
                }
            }
            return best;
        }
    """, color_name)
    
    if custom_pos:
        page.mouse.click(custom_pos['x'], custom_pos['y'])
        time.sleep(0.5)
        return True
    return False

def upload_images(page, image_urls):
    """上传颜色行图片（网络图片方式）"""
    img_box_pos = page.evaluate("""
        () => {
            const dialog = document.querySelector('.jx-dialog');
            if (!dialog) return null;
            const all = dialog.querySelectorAll('div');
            for (const el of all) {
                const rect = el.getBoundingClientRect();
                if (rect.top >= 250 && rect.top <= 500 &&
                    rect.width >= 100 && rect.width <= 150 &&
                    rect.height >= 100 && rect.height <= 150 &&
                    el.innerText.trim() === '' &&
                    el.children.length <= 2) {
                    return {x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)};
                }
            }
            return null;
        }
    """)
    if not img_box_pos:
        return False
    
    page.mouse.click(img_box_pos['x'], img_box_pos['y'])
    time.sleep(0.5)
    
    # 点击使用网络图片
    page.evaluate("""
        () => {
            const all = document.querySelectorAll('*');
            for (const el of all) {
                if (el.children.length === 0 && el.innerText && el.innerText.trim() === '使用网络图片') {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0) { el.click(); return; }
                }
            }
        }
    """)
    time.sleep(0.8)
    
    # 取消保存到妙手
    page.evaluate("""
        () => {
            const dialogs = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
            for (const d of dialogs) {
                const rect = d.getBoundingClientRect();
                if (rect.width > 400 && rect.height > 200 && d.innerText && d.innerText.includes('使用网络图片')) {
                    const cbs = d.querySelectorAll('input[type="checkbox"]');
                    for (const cb of cbs) {
                        if (cb.checked) cb.click();
                    }
                    return;
                }
            }
        }
    """)
    
    # 填URL
    ta_pos = page.evaluate("""
        () => {
            const dialogs = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
            for (const d of dialogs) {
                const rect = d.getBoundingClientRect();
                if (rect.width > 400 && rect.height > 200 && d.innerText && d.innerText.includes('使用网络图片')) {
                    const ta = d.querySelector('textarea');
                    if (ta) {
                        const r = ta.getBoundingClientRect();
                        return {x: Math.round(r.left + 10), y: Math.round(r.top + 10)};
                    }
                }
            }
            return null;
        }
    """)
    if not ta_pos:
        return False
    
    page.mouse.click(ta_pos['x'], ta_pos['y'])
    time.sleep(0.2)
    page.keyboard.press("Control+A")
    time.sleep(0.1)
    page.keyboard.press("Backspace")
    time.sleep(0.1)
    page.keyboard.type("\n".join(image_urls))
    time.sleep(0.3)
    
    # 确定
    page.evaluate("""
        () => {
            const dialogs = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
            for (const d of dialogs) {
                const rect = d.getBoundingClientRect();
                if (rect.width > 400 && rect.height > 200 && d.innerText && d.innerText.includes('使用网络图片')) {
                    const btns = d.querySelectorAll('button');
                    for (const btn of btns) {
                        if (btn.innerText.trim() === '确定') { btn.click(); return true; }
                    }
                }
            }
            return false;
        }
    """)
    time.sleep(4)
    return True

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=200,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
        )
        
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            storage_state=STATE_FILE if os.path.exists(STATE_FILE) else None
        )
        page = context.new_page()
        
        # 1. 打开产品管理页
        print("打开产品管理页...")
        page.goto("https://erp.91miaoshou.com/pddkj/item/item", wait_until="domcontentloaded")
        time.sleep(5)
        
        # 2. 创建产品
        create_btn = page.get_by_role("button", name="创建产品").first
        create_btn.wait_for(state="visible")
        print("点击创建产品...")
        create_btn.click()
        time.sleep(1)
        page.wait_for_selector(".jx-dialog", state="visible", timeout=10000)
        time.sleep(1)
        
        # 3. 引用模板
        print("引用模板...")
        trigger = page.get_by_role("button", name="引用模板").first
        trigger.click()
        time.sleep(0.8)
        menu = page.locator(".template-dropdown").first
        menu.get_by_text("男童圆领卫衣", exact=True).first.click()
        time.sleep(0.5)
        try:
            dialog = page.get_by_role("dialog", name="提示")
            dialog.wait_for(state="visible", timeout=5000)
            dialog.get_by_role("button", name="确定").click()
            time.sleep(7)
        except:
            pass
        
        # 4. 切到销售属性
        print("切到销售属性...")
        dialog_el = page.locator(".jx-dialog").last
        dialog_el.get_by_text("销售属性", exact=True).first.click()
        time.sleep(1)
        
        # 5. 添加颜色行 + 选颜色 + 传图
        print("添加颜色行...")
        page.evaluate("""
            () => {
                const all = document.querySelectorAll('.jx-dialog *');
                for (const el of all) {
                    if (el.innerText && el.innerText.includes('颜色(')) {
                        el.scrollIntoView({block: 'center'});
                        break;
                    }
                }
            }
        """)
        time.sleep(0.3)
        page.locator(":text-is('+ 新增')").first.click()
        time.sleep(1)
        
        print("选择颜色: 白色...")
        ok = select_color(page, "白色")
        print(f"  颜色选择: {'成功' if ok else '失败'}")
        
        print("上传图片...")
        ok = upload_images(page, TEST_IMAGE_URLS)
        print(f"  图片上传: {'成功' if ok else '失败'}")
        
        # 6. 勾选尺码 + 选择尺码表
        print("处理尺码...")
        # 先滚动到尺码区
        page.evaluate("""
            () => {
                const all = document.querySelectorAll('.jx-dialog *');
                for (const el of all) {
                    if (el.innerText && (el.innerText.includes('常用尺码') || el.innerText.includes('全部尺码'))) {
                        el.scrollIntoView({block: 'center'});
                        break;
                    }
                }
            }
        """)
        time.sleep(0.5)
        
        # 勾选尺码
        for size in ["110", "120", "130"]:
            page.evaluate("""
                (sizeText) => {
                    const checkboxes = document.querySelectorAll('.jx-dialog input[type="checkbox"]');
                    for (const cb of checkboxes) {
                        const rect = cb.getBoundingClientRect();
                        if (rect.top > 650 && rect.top < 950) {
                            const label = cb.closest('label') || cb.parentElement;
                            if (label && label.textContent.trim().startsWith(sizeText)) {
                                if (!cb.checked) cb.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }
            """, size)
        
        time.sleep(0.5)
        
        # 选择尺码表
        print("  选择尺码表...")
        # 点击尺码表输入框
        page.evaluate("""
            () => {
                const labels = document.querySelectorAll('.jx-dialog label, .jx-dialog .jx-form-item__label');
                for (const l of labels) {
                    if (l.innerText && l.innerText.trim() === '尺码表') {
                        const formItem = l.closest('.jx-form-item') || l.parentElement;
                        if (formItem) {
                            const inp = formItem.querySelector('input');
                            if (inp) {
                                inp.click();
                                return true;
                            }
                        }
                    }
                }
                return false;
            }
        """)
        time.sleep(0.8)
        save_screenshot(page, "img_size_table_dropdown")
        
        # 探测尺码表下拉选项，选第一个
        print("  探测尺码表选项...")
        first_option = page.evaluate("""
            () => {
                // 找下拉弹层里的选项
                const all = document.querySelectorAll('*');
                for (const el of all) {
                    const text = el.innerText ? el.innerText.trim() : '';
                    // 找包含"卫衣"或尺码相关的选项，且是叶子节点
                    if (text && el.children.length === 0 && 
                        (text.includes('卫衣') || text.includes('上衣') || text.includes('尺码')) &&
                        text.length < 30) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 50 && rect.height > 15) {
                            return {
                                text: text,
                                x: Math.round(rect.left + rect.width/2),
                                y: Math.round(rect.top + rect.height/2)
                            };
                        }
                    }
                }
                return null;
            }
        """)
        
        if first_option:
            print(f"  选第一个: {first_option['text']}")
            page.mouse.click(first_option['x'], first_option['y'])
            time.sleep(1)
            print("  尺码表已选择")
        else:
            print("  没找到尺码表选项")
        
        time.sleep(2)
        save_screenshot(page, "img_sku_table_ready")
        
        # 7. 滚动到SKU表格区域
        print("\n滚动到SKU表格...")
        page.evaluate("""
            () => {
                // 找SKU表格（供货价附近）
                const all = document.querySelectorAll('.jx-dialog *');
                for (const el of all) {
                    if (el.innerText && el.innerText.includes('供货价') && el.children.length === 0) {
                        el.scrollIntoView({block: 'center'});
                        break;
                    }
                }
            }
        """)
        time.sleep(0.5)
        save_screenshot(page, "img_sku_table")
        
        # 探测所有含"供货价"的元素
        print("探测供货价位置:")
        price_positions = page.evaluate("""
            () => {
                const result = [];
                const all = document.querySelectorAll('.jx-dialog *');
                all.forEach(el => {
                    if (el.innerText && el.innerText.includes('供货价')) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            result.push({
                                text: el.innerText.trim().substring(0, 20),
                                tag: el.tagName,
                                class: el.className.substring(0, 40),
                                x: Math.round(rect.left),
                                y: Math.round(rect.top),
                                w: Math.round(rect.width),
                                children: el.children.length
                            });
                        }
                    }
                });
                return result.slice(0, 8);
            }
        """)
        
        for i, p in enumerate(price_positions):
            print(f"  {i}: '{p['text']}' ({p['x']},{p['y']}) {p['w']}px tag={p['tag']} children={p['children']}")
        
        # 8. 找供货价对应的批量按钮并点击
        print("\n测试供货价批量设置...")
        batch_btn_pos = page.evaluate("""
            () => {
                // 找包含"供货价"且含批量按钮的父元素
                const all = document.querySelectorAll('.jx-dialog *');
                for (const el of all) {
                    if (el.innerText && el.innerText.includes('供货价')) {
                        const btns = el.querySelectorAll('button');
                        for (const btn of btns) {
                            if (btn.innerText.trim() === '批量') {
                                const rect = btn.getBoundingClientRect();
                                return {
                                    x: Math.round(rect.left + rect.width/2),
                                    y: Math.round(rect.top + rect.height/2)
                                };
                            }
                        }
                    }
                }
                return null;
            }
        """)
        
        if batch_btn_pos:
            print(f"  供货价批量按钮位置: ({batch_btn_pos['x']}, {batch_btn_pos['y']})")
            # 先滚动到可见区域
            page.evaluate("""
                (pos) => {
                    const header = document.querySelector('.jx-dialog .pro-virtual-table__header');
                    if (header) {
                        header.scrollLeft = pos.x - 300;
                    }
                }
            """, batch_btn_pos)
            time.sleep(0.3)
            
            page.mouse.click(batch_btn_pos['x'], batch_btn_pos['y'])
            time.sleep(1)
            save_screenshot(page, "img_batch_dialog")
            
            # 探测批量设置弹窗
            print("  探测批量设置弹窗...")
            dialog_info = page.evaluate("""
                () => {
                    // 找所有包含"使用统一价"或"批量修改"的弹窗
                    const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box, [class*="dialog"]');
                    for (const d of all) {
                        const rect = d.getBoundingClientRect();
                        if (rect.width < 100 || rect.height < 50) continue;
                        const text = d.innerText || '';
                        if (text.includes('使用统一价') || text.includes('批量修改') || text.includes('供货价')) {
                            const inputs = d.querySelectorAll('input');
                            const btns = d.querySelectorAll('button');
                            const btnTexts = [];
                            btns.forEach(b => btnTexts.push(b.innerText.trim()));
                            return {
                                text: text.substring(0, 150).replace(/\\n/g, ' | '),
                                w: Math.round(rect.width),
                                h: Math.round(rect.height),
                                inputCount: inputs.length,
                                btnTexts: btnTexts
                            };
                        }
                    }
                    return null;
                }
            """)
            if dialog_info:
                print(f"    弹窗: {dialog_info['text'][:80]}")
                print(f"    输入框: {dialog_info['inputCount']}个")
                print(f"    按钮: {dialog_info['btnTexts']}")
                
                # 找价格输入框并填入19.0
                print("\n  填入价格 19.0...")
                price_input_pos = page.evaluate("""
                    () => {
                        // 找包含"使用统一价"的弹窗里的输入框
                        const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
                        for (const d of all) {
                            const text = d.innerText || '';
                            if (text.includes('使用统一价') || text.includes('批量修改')) {
                                const inputs = d.querySelectorAll('input');
                                // 找数字输入框（type=number或有CNY前缀的）
                                for (const inp of inputs) {
                                    const type = inp.type || '';
                                    if (type === 'number' || type === 'text') {
                                        const r = inp.getBoundingClientRect();
                                        if (r.width > 30) {
                                            return {x: Math.round(r.left + 10), y: Math.round(r.top + r.height/2)};
                                        }
                                    }
                                }
                            }
                        }
                        return null;
                    }
                """)
                
                if price_input_pos:
                    page.mouse.click(price_input_pos['x'], price_input_pos['y'])
                    time.sleep(0.2)
                    page.keyboard.press("Control+A")
                    time.sleep(0.1)
                    page.keyboard.type("19.0")
                    time.sleep(0.3)
                    
                    # 点击确认/确定
                    print("  点击确认...")
                    confirmed = page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
                            for (const d of all) {
                                const text = d.innerText || '';
                                if (text.includes('使用统一价') || text.includes('批量修改')) {
                                    const btns = d.querySelectorAll('button');
                                    for (const btn of btns) {
                                        const t = btn.innerText.trim();
                                        if (t === '确定' || t === '确认' || t === '提交') {
                                            btn.click();
                                            return true;
                                        }
                                    }
                                }
                            }
                            return false;
                        }
                    """)
                    time.sleep(1)
                    print(f"  供货价批量设置: {'完成' if confirmed else '按钮未找到'}")
                else:
                    print("  没找到价格输入框")
            
            # 9. 建议售价批量设置（供货价 × 2.5）
            print("\n测试建议售价批量设置...")
            suggest_btn_pos = page.evaluate("""
                () => {
                    const all = document.querySelectorAll('.jx-dialog *');
                    for (const el of all) {
                        if (el.innerText && el.innerText.includes('建议售价') && !el.innerText.includes('供货价')) {
                            const btns = el.querySelectorAll('button');
                            for (const btn of btns) {
                                if (btn.innerText.trim() === '批量') {
                                    const rect = btn.getBoundingClientRect();
                                    return {
                                        x: Math.round(rect.left + rect.width/2),
                                        y: Math.round(rect.top + rect.height/2)
                                    };
                                }
                            }
                        }
                    }
                    return null;
                }
            """)
            
            if suggest_btn_pos:
                print(f"  建议售价批量按钮位置: ({suggest_btn_pos['x']}, {suggest_btn_pos['y']})")
                page.mouse.click(suggest_btn_pos['x'], suggest_btn_pos['y'])
                time.sleep(1)
                save_screenshot(page, "img_suggest_dialog")
                
                # 填入建议售价 47.5
                print("  填入建议售价 47.5...")
                suggest_input_pos = page.evaluate("""
                    () => {
                        const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
                        for (const d of all) {
                            const text = d.innerText || '';
                            if (text.includes('使用统一价')) {
                                // 找"使用统一价"文字的位置，然后找旁边的input
                                const spans = d.querySelectorAll('span, label, div');
                                let targetY = 0;
                                for (const s of spans) {
                                    if (s.innerText && s.innerText.trim() === '使用统一价') {
                                        const r = s.getBoundingClientRect();
                                        targetY = r.top + r.height / 2;
                                        break;
                                    }
                                }
                                // 找同一行附近的input
                                const inputs = d.querySelectorAll('input');
                                let best = null;
                                for (const inp of inputs) {
                                    const r = inp.getBoundingClientRect();
                                    if (r.width > 30) {
                                        const dist = Math.abs((r.top + r.height/2) - targetY);
                                        if (!best || dist < best.dist) {
                                            best = {
                                                x: Math.round(r.left + 10),
                                                y: Math.round(r.top + r.height/2),
                                                dist: dist
                                            };
                                        }
                                    }
                                }
                                return best;
                            }
                        }
                        return null;
                    }
                """)
                
                if suggest_input_pos:
                    page.mouse.click(suggest_input_pos['x'], suggest_input_pos['y'])
                    time.sleep(0.2)
                    page.keyboard.press("Control+A")
                    time.sleep(0.1)
                    page.keyboard.type("47.5")
                    time.sleep(0.3)
                    
                    # 点击确认
                    print("  点击确认...")
                    confirmed = page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
                            for (const d of all) {
                                const text = d.innerText || '';
                                if (text.includes('使用统一价') || (text.includes('建议') && text.includes('售价'))) {
                                    const btns = d.querySelectorAll('button');
                                    for (const btn of btns) {
                                        const t = btn.innerText.trim();
                                        if (t === '确定' || t === '确认' || t === '提交') {
                                            btn.click();
                                            return true;
                                        }
                                    }
                                }
                            }
                            return false;
                        }
                    """)
                    time.sleep(1)
                    print(f"  建议售价批量设置: {'完成' if confirmed else '按钮未找到'}")
                else:
                    print("  没找到建议售价输入框")
            else:
                print("  没找到建议售价批量按钮")
            
            # 10. SKU分类批量设置
            print("\n测试SKU分类批量设置...")
            sku_class_btn_pos = page.evaluate("""
                () => {
                    const all = document.querySelectorAll('.jx-dialog *');
                    for (const el of all) {
                        if (el.innerText && el.innerText.includes('SKU分类') && !el.innerText.includes('供货价') && !el.innerText.includes('建议')) {
                            const btns = el.querySelectorAll('button');
                            for (const btn of btns) {
                                if (btn.innerText.trim() === '批量') {
                                    const rect = btn.getBoundingClientRect();
                                    return {
                                        x: Math.round(rect.left + rect.width/2),
                                        y: Math.round(rect.top + rect.height/2)
                                    };
                                }
                            }
                        }
                    }
                    return null;
                }
            """)
            
            if sku_class_btn_pos:
                print(f"  SKU分类批量按钮位置: ({sku_class_btn_pos['x']}, {sku_class_btn_pos['y']})")
                page.mouse.click(sku_class_btn_pos['x'], sku_class_btn_pos['y'])
                time.sleep(1)
                save_screenshot(page, "img_sku_class_dialog")
                
                # 探测SKU分类弹窗结构
                print("  探测SKU分类弹窗结构...")
                dialog_info = page.evaluate("""
                    () => {
                        const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                        // 排除最大的那个（创建产品大弹窗），找剩下的小弹窗
                        let dialogs = [];
                        all.forEach(d => {
                            const rect = d.getBoundingClientRect();
                            if (rect.width > 100 && rect.height > 50) {
                                dialogs.push({el: d, w: rect.width, h: rect.height, text: d.innerText || ''});
                            }
                        });
                        // 按宽度排序，最大的是创建产品弹窗，第二大的可能就是批量设置弹窗
                        dialogs.sort((a, b) => b.w - a.w);
                        
                        if (dialogs.length < 2) return null;
                        
                        const smallDlg = dialogs[1]; // 第二大的
                        const d = smallDlg.el;
                        const inputs = d.querySelectorAll('input');
                        const selects = d.querySelectorAll('select');
                        const btns = d.querySelectorAll('button');
                        const btnTexts = [];
                        btns.forEach(b => btnTexts.push(b.innerText.trim()));
                        return {
                            text: smallDlg.text.substring(0, 150).replace(/\\n/g, ' | '),
                            w: smallDlg.w,
                            h: smallDlg.h,
                            inputCount: inputs.length,
                            selectCount: selects.length,
                            btnTexts: btnTexts
                        };
                    }
                """)
                
                if dialog_info:
                    print(f"    弹窗: {dialog_info['text'][:80]}")
                    print(f"    输入框: {dialog_info['inputCount']}个 下拉: {dialog_info['selectCount']}个")
                    print(f"    按钮: {dialog_info['btnTexts']}")
                    
                    # 测试单品情况
                    print("\n  设置SKU分类: 单品, 数量1...")
                    
                    # 1. 点击分类下拉框，选择单品
                    print("  选择分类: 单品...")
                    selected = page.evaluate("""
                        () => {
                            // 找小弹窗
                            const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                            let dialogs = [];
                            all.forEach(d => {
                                const rect = d.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 50) {
                                    dialogs.push({el: d, w: rect.width});
                                }
                            });
                            dialogs.sort((a, b) => b.w - a.w);
                            if (dialogs.length < 2) return false;
                            const dlg = dialogs[1].el;
                            
                            // 点击第一个input（分类框）展开下拉
                            const inputs = dlg.querySelectorAll('input');
                            if (inputs.length === 0) return false;
                            inputs[0].click();
                            return true;
                        }
                    """)
                    time.sleep(0.5)
                    
                    # 点击"单品"选项
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('*');
                            for (const el of all) {
                                if (el.children.length === 0 && el.innerText && el.innerText.trim() === '单品') {
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width > 20 && rect.height > 10) {
                                        el.click();
                                        return;
                                    }
                                }
                            }
                        }
                    """)
                    time.sleep(0.5)
                    save_screenshot(page, "img_sku_class_selected")
                    
                    # 2. 填分类旁边的数量 = 1
                    print("  填分类数量 = 1...")
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                            let dialogs = [];
                            all.forEach(d => {
                                const rect = d.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 50) {
                                    dialogs.push({el: d, w: rect.width});
                                }
                            });
                            dialogs.sort((a, b) => b.w - a.w);
                            if (dialogs.length < 2) return;
                            const dlg = dialogs[1].el;
                            
                            // 找"单位"文字的y坐标，旁边就是数量输入框
                            let targetY = 0;
                            const spans = dlg.querySelectorAll('span, label, div');
                            for (const s of spans) {
                                if (s.innerText && s.innerText.trim() === '单位') {
                                    const r = s.getBoundingClientRect();
                                    targetY = r.top + r.height / 2;
                                    break;
                                }
                            }
                            if (!targetY) return;
                            
                            // 找同一行附近的input（分类框右边的数量）
                            const inputs = dlg.querySelectorAll('input');
                            let best = null;
                            for (const inp of inputs) {
                                const r = inp.getBoundingClientRect();
                                if (r.width < 20) continue;
                                const dist = Math.abs((r.top + r.height/2) - targetY);
                                if (dist < 30 && (!best || dist < best.dist)) {
                                    best = {el: inp, dist: dist};
                                }
                            }
                            if (best) {
                                best.el.value = '1';
                                best.el.dispatchEvent(new Event('input', {bubbles: true}));
                                best.el.dispatchEvent(new Event('change', {bubbles: true}));
                            }
                        }
                    """)
                    time.sleep(0.3)
                    
                    # 3. 填共计内含 = 1
                    print("  填共计内含 = 1...")
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                            let dialogs = [];
                            all.forEach(d => {
                                const rect = d.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 50) {
                                    dialogs.push({el: d, w: rect.width});
                                }
                            });
                            dialogs.sort((a, b) => b.w - a.w);
                            if (dialogs.length < 2) return;
                            const dlg = dialogs[1].el;
                            
                            // 找"共计内含"文字的y坐标
                            let targetY = 0;
                            const spans = dlg.querySelectorAll('span, label, div');
                            for (const s of spans) {
                                if (s.innerText && s.innerText.trim() === '共计内含') {
                                    const r = s.getBoundingClientRect();
                                    targetY = r.top + r.height / 2;
                                    break;
                                }
                            }
                            if (!targetY) return;
                            
                            // 找同一行附近的input
                            const inputs = dlg.querySelectorAll('input');
                            let best = null;
                            for (const inp of inputs) {
                                const r = inp.getBoundingClientRect();
                                if (r.width < 20) continue;
                                const dist = Math.abs((r.top + r.height/2) - targetY);
                                if (dist < 30 && (!best || dist < best.dist)) {
                                    best = {el: inp, dist: dist};
                                }
                            }
                            if (best) {
                                best.el.value = '1';
                                best.el.dispatchEvent(new Event('input', {bubbles: true}));
                                best.el.dispatchEvent(new Event('change', {bubbles: true}));
                            }
                        }
                    """)
                    time.sleep(0.3)
                    
                    # 3. 点击确定
                    print("  点击确定...")
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                            let dialogs = [];
                            all.forEach(d => {
                                const rect = d.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 50) {
                                    dialogs.push({el: d, w: rect.width});
                                }
                            });
                            dialogs.sort((a, b) => b.w - a.w);
                            if (dialogs.length < 2) return false;
                            const dlg = dialogs[1].el;
                            
                            const btns = dlg.querySelectorAll('button');
                            for (const btn of btns) {
                                if (btn.innerText.trim() === '确定') {
                                    btn.click();
                                    return true;
                                }
                            }
                            return false;
                        }
                    """)
                    time.sleep(0.8)
                    print("  SKU分类-单品 设置完成")
                    
                    # ===== 测试同款多件装 =====
                    print("\n  测试同款多件装...")
                    # 重新打开批量弹窗
                    page.mouse.click(sku_class_btn_pos['x'], sku_class_btn_pos['y'])
                    time.sleep(1)
                    
                    # 选择分类：同款多件装
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                            let dialogs = [];
                            all.forEach(d => {
                                const rect = d.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 50) {
                                    dialogs.push({el: d, w: rect.width});
                                }
                            });
                            dialogs.sort((a, b) => b.w - a.w);
                            if (dialogs.length < 2) return;
                            const dlg = dialogs[1].el;
                            const inputs = dlg.querySelectorAll('input');
                            if (inputs.length > 0) inputs[0].click();
                        }
                    """)
                    time.sleep(0.5)
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('*');
                            for (const el of all) {
                                if (el.children.length === 0 && el.innerText && el.innerText.trim() === '同款多件装') {
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width > 20 && rect.height > 10) {
                                        el.click();
                                        return;
                                    }
                                }
                            }
                        }
                    """)
                    time.sleep(0.8)
                    save_screenshot(page, "img_sku_multi_pack")
                    
                    # 填分类旁边的数量 = 2
                    print("  填分类数量 = 2")
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                            let dialogs = [];
                            all.forEach(d => {
                                const rect = d.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 50) {
                                    dialogs.push({el: d, w: rect.width});
                                }
                            });
                            dialogs.sort((a, b) => b.w - a.w);
                            if (dialogs.length < 2) return;
                            const dlg = dialogs[1].el;
                            
                            let targetY = 0;
                            const spans = dlg.querySelectorAll('span, label, div');
                            for (const s of spans) {
                                if (s.innerText && s.innerText.trim() === '单位') {
                                    const r = s.getBoundingClientRect();
                                    targetY = r.top + r.height / 2;
                                    break;
                                }
                            }
                            if (!targetY) return;
                            
                            const inputs = dlg.querySelectorAll('input');
                            let best = null;
                            for (const inp of inputs) {
                                const r = inp.getBoundingClientRect();
                                if (r.width < 20) continue;
                                const dist = Math.abs((r.top + r.height/2) - targetY);
                                if (dist < 30 && (!best || dist < best.dist)) {
                                    best = {el: inp, dist: dist};
                                }
                            }
                            if (best) {
                                best.el.value = '2';
                                best.el.dispatchEvent(new Event('input', {bubbles: true}));
                                best.el.dispatchEvent(new Event('change', {bubbles: true}));
                            }
                        }
                    """)
                    time.sleep(0.3)
                    
                    # 是否独立包装 → 选否
                    print("  是否独立包装 → 选否")
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                            let dialogs = [];
                            all.forEach(d => {
                                const rect = d.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 50) {
                                    dialogs.push({el: d, w: rect.width});
                                }
                            });
                            dialogs.sort((a, b) => b.w - a.w);
                            if (dialogs.length < 2) return;
                            const dlg = dialogs[1].el;
                            
                            // 找"是否独立包装"的下拉
                            const inputs = dlg.querySelectorAll('input');
                            // 第二个下拉应该是是否独立包装
                            if (inputs.length >= 2) {
                                inputs[1].click();
                            }
                        }
                    """)
                    time.sleep(0.5)
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('*');
                            for (const el of all) {
                                if (el.children.length === 0 && el.innerText && el.innerText.trim() === '否') {
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width > 20 && rect.height > 10) {
                                        el.click();
                                        return;
                                    }
                                }
                            }
                        }
                    """)
                    time.sleep(0.5)
                    
                    # 填共计内含 = 2
                    print("  填共计内含 = 2")
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                            let dialogs = [];
                            all.forEach(d => {
                                const rect = d.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 50) {
                                    dialogs.push({el: d, w: rect.width});
                                }
                            });
                            dialogs.sort((a, b) => b.w - a.w);
                            if (dialogs.length < 2) return;
                            const dlg = dialogs[1].el;
                            
                            let targetY = 0;
                            const spans = dlg.querySelectorAll('span, label, div');
                            for (const s of spans) {
                                if (s.innerText && s.innerText.trim() === '共计内含') {
                                    const r = s.getBoundingClientRect();
                                    targetY = r.top + r.height / 2;
                                    break;
                                }
                            }
                            if (!targetY) return;
                            
                            const inputs = dlg.querySelectorAll('input');
                            let best = null;
                            for (const inp of inputs) {
                                const r = inp.getBoundingClientRect();
                                if (r.width < 20) continue;
                                const dist = Math.abs((r.top + r.height/2) - targetY);
                                if (dist < 30 && (!best || dist < best.dist)) {
                                    best = {el: inp, dist: dist};
                                }
                            }
                            if (best) {
                                best.el.value = '2';
                                best.el.dispatchEvent(new Event('input', {bubbles: true}));
                                best.el.dispatchEvent(new Event('change', {bubbles: true}));
                            }
                        }
                    """)
                    time.sleep(0.3)
                    
                    # 点击确定
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                            let dialogs = [];
                            all.forEach(d => {
                                const rect = d.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 50) {
                                    dialogs.push({el: d, w: rect.width});
                                }
                            });
                            dialogs.sort((a, b) => b.w - a.w);
                            if (dialogs.length < 2) return false;
                            const dlg = dialogs[1].el;
                            const btns = dlg.querySelectorAll('button');
                            for (const btn of btns) {
                                if (btn.innerText.trim() === '确定') {
                                    btn.click();
                                    return true;
                                }
                            }
                            return false;
                        }
                    """)
                    time.sleep(0.8)
                    print("  SKU分类-同款多件装 设置完成")
                    
                    # ===== 测试混合套装 =====
                    print("\n  测试混合套装...")
                    page.mouse.click(sku_class_btn_pos['x'], sku_class_btn_pos['y'])
                    time.sleep(1)
                    
                    # 选择分类：混合套装
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                            let dialogs = [];
                            all.forEach(d => {
                                const rect = d.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 50) {
                                    dialogs.push({el: d, w: rect.width});
                                }
                            });
                            dialogs.sort((a, b) => b.w - a.w);
                            if (dialogs.length < 2) return;
                            const dlg = dialogs[1].el;
                            const inputs = dlg.querySelectorAll('input');
                            if (inputs.length > 0) inputs[0].click();
                        }
                    """)
                    time.sleep(0.5)
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('*');
                            for (const el of all) {
                                if (el.children.length === 0 && el.innerText && el.innerText.trim() === '混合套装') {
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width > 20 && rect.height > 10) {
                                        el.click();
                                        return;
                                    }
                                }
                            }
                        }
                    """)
                    time.sleep(0.8)
                    save_screenshot(page, "img_sku_mixed_set")
                    
                    # 填分类旁边的数量 = 2
                    print("  填分类数量 = 2")
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                            let dialogs = [];
                            all.forEach(d => {
                                const rect = d.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 50) {
                                    dialogs.push({el: d, w: rect.width});
                                }
                            });
                            dialogs.sort((a, b) => b.w - a.w);
                            if (dialogs.length < 2) return;
                            const dlg = dialogs[1].el;
                            
                            let targetY = 0;
                            const spans = dlg.querySelectorAll('span, label, div');
                            for (const s of spans) {
                                if (s.innerText && s.innerText.trim() === '单位') {
                                    const r = s.getBoundingClientRect();
                                    targetY = r.top + r.height / 2;
                                    break;
                                }
                            }
                            if (!targetY) return;
                            
                            const inputs = dlg.querySelectorAll('input');
                            let best = null;
                            for (const inp of inputs) {
                                const r = inp.getBoundingClientRect();
                                if (r.width < 20) continue;
                                const dist = Math.abs((r.top + r.height/2) - targetY);
                                if (dist < 30 && (!best || dist < best.dist)) {
                                    best = {el: inp, dist: dist};
                                }
                            }
                            if (best) {
                                best.el.value = '2';
                                best.el.dispatchEvent(new Event('input', {bubbles: true}));
                                best.el.dispatchEvent(new Event('change', {bubbles: true}));
                            }
                        }
                    """)
                    time.sleep(0.3)
                    
                    # 是否独立包装 → 选否
                    print("  是否独立包装 → 选否")
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                            let dialogs = [];
                            all.forEach(d => {
                                const rect = d.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 50) {
                                    dialogs.push({el: d, w: rect.width});
                                }
                            });
                            dialogs.sort((a, b) => b.w - a.w);
                            if (dialogs.length < 2) return;
                            const dlg = dialogs[1].el;
                            const inputs = dlg.querySelectorAll('input');
                            if (inputs.length >= 2) {
                                inputs[1].click();
                            }
                        }
                    """)
                    time.sleep(0.5)
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('*');
                            for (const el of all) {
                                if (el.children.length === 0 && el.innerText && el.innerText.trim() === '否') {
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width > 20 && rect.height > 10) {
                                        el.click();
                                        return;
                                    }
                                }
                            }
                        }
                    """)
                    time.sleep(0.5)
                    
                    # 混合套装没有共计内含，直接点确定
                    print("  点击确定（混合套装无共计内含）")
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                            let dialogs = [];
                            all.forEach(d => {
                                const rect = d.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 50) {
                                    dialogs.push({el: d, w: rect.width});
                                }
                            });
                            dialogs.sort((a, b) => b.w - a.w);
                            if (dialogs.length < 2) return false;
                            const dlg = dialogs[1].el;
                            const btns = dlg.querySelectorAll('button');
                            for (const btn of btns) {
                                if (btn.innerText.trim() === '确定') {
                                    btn.click();
                                    return true;
                                }
                            }
                            return false;
                        }
                    """)
                    time.sleep(0.8)
                    print("  SKU分类-混合套装 设置完成")
                else:
                    print("  没找到SKU分类弹窗")
            else:
                print("  没找到SKU分类批量按钮")
            
            # 11. 重量批量设置（需要横向滚动）
            print("\n测试重量批量设置...")
            
            # 先横向滚动SKU表格到最右边
            page.evaluate("""
                () => {
                    // 找SKU表格的横向滚动容器
                    const tables = document.querySelectorAll('.jx-dialog .pro-virtual-table, .jx-dialog .pro-table');
                    for (const t of tables) {
                        const rect = t.getBoundingClientRect();
                        if (rect.width > 500) {
                            t.scrollLeft = 9999; // 滚到最右
                            break;
                        }
                    }
                }
            """)
            time.sleep(0.5)
            save_screenshot(page, "img_weight_scrolled")
            
            # 找重量列的批量按钮
            weight_btn_pos = page.evaluate("""
                () => {
                    const all = document.querySelectorAll('.jx-dialog *');
                    for (const el of all) {
                        if (el.innerText && el.innerText.includes('重量') && !el.innerText.includes('净重') && !el.innerText.includes('毛重')) {
                            const btns = el.querySelectorAll('button');
                            for (const btn of btns) {
                                if (btn.innerText.trim() === '批量') {
                                    const rect = btn.getBoundingClientRect();
                                    return {
                                        x: Math.round(rect.left + rect.width/2),
                                        y: Math.round(rect.top + rect.height/2)
                                    };
                                }
                            }
                        }
                    }
                    return null;
                }
            """)
            
            if weight_btn_pos:
                print(f"  重量批量按钮位置: ({weight_btn_pos['x']}, {weight_btn_pos['y']})")
                page.mouse.click(weight_btn_pos['x'], weight_btn_pos['y'])
                time.sleep(1)
                save_screenshot(page, "img_weight_dialog")
                
                # 探测重量弹窗结构
                print("  探测重量弹窗结构...")
                dialog_info = page.evaluate("""
                    () => {
                        const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                        let dialogs = [];
                        all.forEach(d => {
                            const rect = d.getBoundingClientRect();
                            if (rect.width > 100 && rect.height > 50) {
                                dialogs.push({el: d, w: rect.width, h: rect.height, text: d.innerText || ''});
                            }
                        });
                        dialogs.sort((a, b) => b.w - a.w);
                        if (dialogs.length < 2) return null;
                        
                        const dlg = dialogs[1];
                        const inputs = dlg.el.querySelectorAll('input');
                        const btns = dlg.el.querySelectorAll('button');
                        const btnTexts = [];
                        btns.forEach(b => btnTexts.push(b.innerText.trim()));
                        return {
                            text: dlg.text.substring(0, 150).replace(/\\n/g, ' | '),
                            w: dlg.w,
                            h: dlg.h,
                            inputCount: inputs.length,
                            btnTexts: btnTexts
                        };
                    }
                """)
                
                if dialog_info:
                    print(f"    弹窗: {dialog_info['text'][:80]}")
                    print(f"    输入框: {dialog_info['inputCount']}个")
                    print(f"    按钮: {dialog_info['btnTexts']}")
                else:
                    print("  没找到重量弹窗")
            else:
                print("  没找到重量批量按钮")
        else:
            print("  没找到供货价批量按钮")
            # 打印所有表头文字
            all_headers = page.evaluate("""
                () => {
                    const header = document.querySelector('.jx-dialog .pro-virtual-table__header');
                    if (!header) return [];
                    const result = [];
                    const all = header.querySelectorAll('*');
                    all.forEach(el => {
                        if (el.children.length === 0 && el.innerText && el.innerText.trim()) {
                            const t = el.innerText.trim();
                            if (t.length < 20 && result.indexOf(t) === -1) {
                                result.push(t);
                            }
                        }
                    });
                    return result;
                }
            """)
            print(f"  表头所有文字: {all_headers}")
        
        save_screenshot(page, "img_sku_final")
        print("\n测试完成，浏览器保持开启")
        input("按回车关闭浏览器...")
        browser.close()

if __name__ == "__main__":
    main()
