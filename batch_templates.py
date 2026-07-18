# -*- coding: utf-8 -*-
import sys, os, time, json
from pathlib import Path

ROOT = Path(__file__).parent if '__file__' in dir() else Path(r'C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2')
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright
from config.settings import RPA_HEADLESS, RPA_SLOW_MO

def confirm(title, message):
    import ctypes
    return ctypes.windll.user32.MessageBoxW(0, message, title, 0x04|0x20|0x40000) == 6

def alert(title, message):
    import ctypes
    ctypes.windll.user32.MessageBoxW(0, message, title, 0x00|0x40|0x40000)

class TemplateCreator:
    def __init__(self):
        self.playwright = None; self.browser = None; self.context = None; self.page = None
        self.state_file = ROOT / 'storage_state.json'

    def init_browser(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=RPA_HEADLESS, slow_mo=RPA_SLOW_MO,
            args=['--start-maximized', '--disable-blink-features=AutomationControlled'])
        ctx = {'viewport': {'width': 1920, 'height': 1080}}
        if self.state_file.exists(): ctx['storage_state'] = str(self.state_file)
        self.context = self.browser.new_context(**ctx)
        self.page = self.context.new_page()

    def navigate_to_templates(self):
        self.page.goto('https://erp.91miaoshou.com/pddkj/item/item', wait_until='domcontentloaded')
        time.sleep(5)
        self._dismiss()
        self.page.locator('text=产品模板').first.click(timeout=5000)
        time.sleep(3)

    def _dismiss(self):
        for t in ['关闭','我知道了']:
            try:
                b = self.page.locator(f"button:has-text('{t}')")
                for i in range(b.count()):
                    if b.nth(i).is_visible(): b.nth(i).click(); time.sleep(0.3)
            except: pass

    def create_one(self, name, attrs=None):
        print(f'\n===== 创建: {name} =====')
        try:
            self.page.locator("button:has-text('新建模板')").first.click(timeout=5000)
        except:
            alert('错误', '找不到新建模板按钮'); return False
        time.sleep(2)
        if not confirm('确认', f'即将创建模板:\n\n{name}\n\n是=继续 否=跳过'):
            self._close_dlg(); return False
        try:
            inp = self.page.locator('input[placeholder*="请输入模板名称"]').first
            inp.click(); inp.fill(name); time.sleep(0.5)
        except Exception as e:
            alert('错误', f'填写名称失败: {e}'); return False
        if attrs and 'category_path' in attrs:
            self._select_cat(attrs['category_path'])
        if attrs:
            for k,v in attrs.items():
                if k == 'category_path': continue
                self._fill(k, v)
        os.makedirs(str(ROOT/'screenshots'), exist_ok=True)
        sp = str(ROOT / 'screenshots' / f'template_{name}.png')
        self.page.screenshot(path=sp, full_page=True)
        print(f'  截图: {sp}')
        form = self._read_form()
        s = '=== 填写结果 ===\n' + '\n'.join(f'  {k}: {v}' for k,v in form.items())
        if not confirm('确认保存', s+'\n\n是=保存 否=放弃'):
            self._close_dlg(); return False
        try:
            self.page.locator("button:has-text('保存'), button:has-text('确定')").first.click(timeout=5000)
            time.sleep(2)
        except:
            alert('错误', '找不到保存按钮'); return False
        ok = name in self.page.inner_text('body')
        alert('成功' if ok else '警告', f'模板 {name} {"创建成功!" if ok else "可能未创建,请手动检查"}')
        return ok

    def _select_cat(self, path):
        parts = [p.strip() for p in path.split('/')]
        print(f'  类目: {" > ".join(parts)}')
        try:
            self.page.locator('.category-cascader').first.click(); time.sleep(1)
        except:
            alert('警告', '找不到类目级联器'); return
        for p in parts:
            time.sleep(0.5)
            try:
                self.page.locator(f".el-cascader-node__label:has-text('{p}')").first.click(timeout=3000)
            except:
                alert('警告', f'找不到类目节点: {p}'); return

    def _fill(self, name, value):
        print(f'  填写: {name} = {value}')

    def _read_form(self):
        return self.page.evaluate("""()=>{
            const r={};
            document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio])').forEach(i=>{
                if(i.value&&i.value.length<200){
                    const l=i.closest('[class*=form]')?.querySelector('[class*=label],label')?.innerText?.trim();
                    r[l||i.placeholder||'input']=i.value;
                }
            });
            document.querySelectorAll('.el-tag,.el-select__selected-item,[class*=selected]').forEach(t=>{
                const x=(t.innerText||'').trim();
                if(x&&x.length<50&&!x.includes('\\n')){
                    const l=t.closest('[class*=form]')?.querySelector('[class*=label],label')?.innerText?.trim();
                    r[l||'tag']=x;
                }
            });
            return r;
        }""")

    def _close_dlg(self):
        try: self.page.locator('.jx-dialog__close,.el-icon-close').first.click()
        except: pass
        time.sleep(1)

    def run(self, templates):
        self.init_browser(); self.navigate_to_templates()
        ok = fail = 0
        for name, cfg in templates.items():
            if self.create_one(name, cfg.get('attributes')): ok += 1
            else: fail += 1
        alert('完成', f'成功: {ok}\n失败: {fail}')
        self.browser.close(); self.playwright.stop()

TEMPLATES_TO_CREATE = {}
if __name__ == '__main__':
    if not TEMPLATES_TO_CREATE:
        alert('模板列表为空', '请先编辑 TEMPLATES_TO_CREATE 字典。')
    else:
        TemplateCreator().run(TEMPLATES_TO_CREATE)
