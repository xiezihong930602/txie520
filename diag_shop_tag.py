"""诊断店铺级联选择器当前DOM结构——用于修复"无法去掉默认店铺"问题"""
import sys, os, time, json
ROOT = r"C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from playwright.sync_api import sync_playwright
from config.settings import MIAOSHOU_BASE_URL

STATE_FILE = os.path.join(ROOT, "storage_state.json")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=200)
    context = browser.new_context(
        storage_state=STATE_FILE if os.path.exists(STATE_FILE) else None,
        viewport={"width": 1920, "height": 1080}
    )
    page = context.new_page()
    page.goto(f"{MIAOSHOU_BASE_URL}/pddkj/item/item", timeout=30000)
    page.wait_for_timeout(5000)

    # 点击「发布产品」打开创建弹窗
    print("\n=== Step 0: 打开创建弹窗 ===")
    try:
        page.get_by_text("创建产品").first.click(timeout=5000)
    except:
        page.get_by_text("发布产品").first.click(timeout=5000)
    page.wait_for_timeout(3000)

    # ===== 诊断1: 店铺级联区域全量DOM =====
    print("\n=== 诊断1: 店铺级联区域DOM结构 ===")
    dom_info = page.evaluate("""() => {
        const result = [];
        
        // 1. 查找包含"店铺"label的form-item
        const formItems = document.querySelectorAll('.jx-form-item, .el-form-item');
        for (const fi of formItems) {
            const label = fi.querySelector('label, .el-form-item__label');
            const labelText = label ? (label.innerText || '').trim() : '';
            if (labelText.includes('店铺')) {
                result.push({type: 'shop_form_item', outerHTML: fi.outerHTML.substring(0, 500)});
                
                // 找到级联组件
                const cascader = fi.querySelector('.jx-cascader, .jx-pro-cascader, [class*="cascader"]');
                if (cascader) {
                    result.push({type: 'cascader_container', classes: cascader.className});
                    
                    // 找 tags 区域
                    const tags = cascader.querySelector('.jx-cascader__tags, .jx-tag, [class*="tag"]');
                    if (tags) {
                        result.push({
                            type: 'tags_container', 
                            classes: tags.className,
                            outerHTML: tags.outerHTML.substring(0, 800)
                        });
                    }
                    
                    // 找所有tag
                    const allTags = cascader.querySelectorAll('.jx-tag, .el-tag, [class*="tag"]');
                    for (const tag of allTags) {
                        const r = tag.getBoundingClientRect();
                        if (r.height < 5) continue;
                        const tagText = (tag.innerText || '').trim();
                        const closeEl = tag.querySelector('i, span[class*="close"], .el-icon-close, svg');
                        result.push({
                            type: 'tag',
                            text: tagText,
                            top: Math.round(r.top),
                            left: Math.round(r.left),
                            classes: tag.className,
                            hasClose: !!closeEl,
                            closeTag: closeEl ? closeEl.tagName : 'none',
                            closeClasses: closeEl ? (closeEl.className?.baseVal || closeEl.className || '') : 'none',
                            closeOuterHTML: closeEl ? closeEl.outerHTML.substring(0, 200) : 'none'
                        });
                    }
                    
                    // 找搜索框
                    const searchInput = cascader.querySelector('input');
                    if (searchInput) {
                        result.push({
                            type: 'search_input',
                            placeholder: searchInput.placeholder || '',
                            classes: searchInput.className,
                            outerHTML: searchInput.outerHTML.substring(0, 200)
                        });
                    }
                }
                break;
            }
        }
        
        // 2. 全页面搜索所有 .jx-cascader__tags 和 .jx-tag
        const allCascaderTags = document.querySelectorAll('.jx-cascader__tags');
        result.push({type: 'all_cascader_tags_count', count: allCascaderTags.length});
        
        const allTags = document.querySelectorAll('.jx-tag');
        result.push({type: 'all_jx_tags_count', count: allTags.length});
        for (const t of allTags) {
            const r = t.getBoundingClientRect();
            if (r.height < 5) continue;
            const closeEl = t.querySelector('i, span[class*="close"]');
            result.push({
                type: 'all_tag_detail',
                text: (t.innerText || '').trim(),
                classes: t.className,
                hasClose: !!closeEl,
                closeHTML: closeEl ? closeEl.outerHTML.substring(0, 150) : 'none'
            });
        }
        
        return result;
    }""")

    print(json.dumps(dom_info, ensure_ascii=False, indent=2))

    # ===== 诊断2: 尝试删除tag的多种方式 =====
    print("\n=== 诊断2: 尝试删除默认店铺tag ===")
    
    # 方式1: i[class*='close']
    try:
        close_btn = page.locator(".jx-cascader__tags .jx-tag i[class*='close']").first
        if close_btn.is_visible(timeout=2000):
            print("  方式1(i[class*='close']): 找到元素，坐标=", close_btn.bounding_box())
            close_btn.click(force=True)
            time.sleep(1)
            # 检查tag是否消失
            remaining = page.locator(".jx-cascader__tags .jx-tag").count()
            print(f"  点击后剩余tag数: {remaining}")
        else:
            print("  方式1(i[class*='close']): 不可见")
    except Exception as e:
        print(f"  方式1(i[class*='close']): 失败 - {e}")

    # 方式2: 纯JS点击
    try:
        js_result = page.evaluate("""() => {
            const tags = document.querySelectorAll('.jx-cascader__tags .jx-tag');
            for (const tag of tags) {
                const closeBtn = tag.querySelector('i[class*="close"], i[class*="icon"], svg[class*="close"], span[class*="close"]');
                if (closeBtn) {
                    closeBtn.click();
                    return 'clicked: ' + closeBtn.outerHTML.substring(0, 100);
                }
            }
            // fallback: 直接移除tag
            for (const tag of tags) {
                tag.remove();
                return 'removed tag directly';
            }
            return 'no tag found';
        }""")
        print(f"  方式2(JS click): {js_result}")
    except Exception as e:
        print(f"  方式2(JS click): 失败 - {e}")

    # 截图保存
    page.screenshot(path=os.path.join(ROOT, "diag_shop_tag.png"), full_page=False)
    print(f"\n截图已保存: {os.path.join(ROOT, 'diag_shop_tag.png')}")

    print("\n诊断完成，30秒后自动关闭...")
    time.sleep(30)
    browser.close()
