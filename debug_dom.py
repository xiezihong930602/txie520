"""
Debug: 导航到妙手产品创建页，诊断DOM结构
用法: python debug_dom.py
"""
import sys, os, json, time, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_drivers"))

from playwright.sync_api import sync_playwright
from config.settings import MIAOSHOU_BASE_URL

def main():
    pw = sync_playwright().start()
    
    state_file = os.path.join(os.path.dirname(__file__), "storage_state.json")
    
    browser = pw.chromium.launch(headless=True, slow_mo=100,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
    
    ctx_kwargs = {"viewport": {"width": 1920, "height": 1080}}
    if os.path.exists(state_file):
        ctx_kwargs["storage_state"] = state_file
    
    ctx = browser.new_context(**ctx_kwargs)
    page = ctx.new_page()
    
    print("=== 1. 导航到产品管理页 ===")
    page.goto(f"{MIAOSHOU_BASE_URL}/pddkj/item/item", wait_until="domcontentloaded")
    time.sleep(5)
    
    # 关闭弹窗 - 用Playwright原生定位+JS双重策略
    print("=== 关闭弹窗 ===")
    # 策略1: Playwright原生定位
    for sel_text in ['关闭', '我知道了']:
        try:
            btn = page.locator(f"button:has-text('{sel_text}')").first
            if btn.is_visible(timeout=2000):
                btn.click()
                print(f"已点击 '{sel_text}' 按钮")
                time.sleep(1)
        except:
            pass
    
    # 策略2: JS强制关闭
    page.evaluate("""() => {
        for (let i=0;i<5;i++){
            let closed=false;
            const all=document.querySelectorAll('.jx-dialog,.jx-overlay-dialog,[role="dialog"],.el-dialog,.notice-message-box-dialog');
            for(const d of all){
                const r=d.getBoundingClientRect();
                if(r.height<10)continue;
                const closeIcons=d.querySelectorAll('.jx-dialog__close,.el-icon-close,[class*="close"],.el-dialog__close');
                for(const btn of closeIcons){
                    if(btn.getBoundingClientRect().height>0){btn.click();closed=true;break;}
                }
                if(closed)break;
                const btns=d.querySelectorAll('button,span,a');
                for(const btn of btns){
                    const t=(btn.innerText||'').trim();
                    if(t==='关闭'||t==='我知道了'){btn.click();closed=true;break;}
                }
                if(closed)break;
            }
            if(!closed)break;
        }
    }""")
    time.sleep(2)
    
    # 截图
    page.screenshot(path=os.path.join(os.path.dirname(__file__), "debug_step1_products.png"), full_page=True)
    print("截图保存: debug_step1_products.png")
    
    print("=== 2. 点击创建产品 ===")
    try:
        page.get_by_role("button", name="创建产品").first.click(timeout=5000)
    except:
        page.locator("button:has-text('创建产品')").first.click()
    time.sleep(2)
    
    print("=== 2a. 在弹窗中切换到销售属性标签页 ===")
    try:
        page.locator(":text-is('销售属性')").first.click(timeout=5000)
    except:
        page.locator("text=销售属性").first.click(timeout=5000)
    time.sleep(2)
    
    # 截图销售属性页
    page.screenshot(path=os.path.join(os.path.dirname(__file__), "debug_step2_sales.png"), full_page=False)
    print("截图保存: debug_step2_sales.png")
    
    print("=== 3. DOM诊断(销售属性页) ===")
    
    # 全面DOM导出
    full_diag = page.evaluate("""() => {
        const dialog = document.querySelector('.jx-dialog');
        if (!dialog) return {error: 'no dialog'};
        
        const formItems = [];
        const items = dialog.querySelectorAll('.el-form-item, .form-item');
        items.forEach(item => {
            const label = item.querySelector('.el-form-item__label, label');
            const inputs = item.querySelectorAll('input');
            const selects = item.querySelectorAll('.el-select');
            const labelText = label ? label.innerText.trim() : item.innerText.substring(0, 50);
            if (labelText) {
                formItems.push({
                    label: labelText,
                    top: Math.round(item.getBoundingClientRect().top),
                    hasInput: inputs.length > 0,
                    hasSelect: selects.length > 0,
                });
            }
        });
        
        return {formItems, totalFormItems: formItems.length};
    }""")
    print(f"表单项目: {json.dumps(full_diag, ensure_ascii=False, indent=2)}")
    
    print("\n=== 诊断完成 ===")
    print("截图已保存: debug_step1_products.png, debug_step2_dialog.png")
    
    ctx.close()
    browser.close()
    pw.stop()
    print("浏览器已关闭")

if __name__ == "__main__":
    main()
