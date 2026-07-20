# RPA上架执行器
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

from executors.base import BaseExecutor
from models.product import Product
from playwright.sync_api import sync_playwright, Page, BrowserContext, expect
import time

# 指定浏览器驱动路径（避免系统目录权限问题）
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "browser_drivers"))


class RpaPublisherExecutor(BaseExecutor):
    """
    基于Playwright的妙手后台RPA上架执行器
    通过引用模板 + 覆盖变量字段的方式创建商品
    """
    
    name = "rpa_publisher"
    
    def __init__(self, config=None):
        super().__init__(config)
        self.playwright = None
        self.browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        # 配置
        config = config or {}
        self.base_url = config.get("base_url", "https://erp.91miaoshou.com")
        self.user_data_dir = config.get("user_data_dir", None)
        self.profile_directory = config.get("profile_directory", None)
        self.headless = config.get("headless", False)
        self.slow_mo = config.get("slow_mo", 200)
        self.channel = config.get("channel", None)
    
    def execute(self, product: Product, auto_close: bool = True, auto_submit: bool = True) -> dict:
        """执行完整上架流程"""
        try:
            self._init_browser()
            self._open_create_page()
            self._select_shop("Noble Boys")
            self._apply_template(product.template_name)
            # 模板选完后立刻读类目（需等渲染+切到类别&属性标签页）
            time.sleep(2)
            self._switch_tab("类别&属性")
            self._cached_category = self._read_product_category()
            print(f"  缓存类目: {self._cached_category}")
            self._fill_variable_attributes(product)
            self._fill_basic_info(product)
            self._fill_sku_info(product)
            if auto_submit:
                result = self._submit()
                return {"success": True, "data": {"skc_id": result.get("skc_id"), "product_url": result.get("product_url")}, "error": None}
            return {"success": True, "data": {"skc_id": None, "product_url": None}, "error": None}
        except Exception as e:
            if self.page:
                try:
                    self.page.screenshot(path=f"error_{product.product_id}.png", full_page=True)
                except:
                    pass
            return {
                "success": False,
                "data": {},
                "error": str(e)
            }
        finally:
            if auto_close:
                self._close_browser()
    
    def _init_browser(self):
        """初始化浏览器"""
        self.playwright = sync_playwright().start()
        
        # 登录状态文件
        state_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage_state.json")
        
        if self.user_data_dir:
            # 持久化用户目录模式
            launch_args = ["--start-maximized"]
            if self.profile_directory:
                launch_args.append(f"--profile-directory={self.profile_directory}")
            if not self.channel:
                launch_args.append("--disable-blink-features=AutomationControlled")
            
            context_kwargs = {
                "user_data_dir": self.user_data_dir,
                "headless": self.headless,
                "slow_mo": self.slow_mo,
                "args": launch_args,
            }
            if self.channel:
                context_kwargs["channel"] = self.channel
            
            self.context = self.playwright.chromium.launch_persistent_context(**context_kwargs)
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        else:
            # 普通模式 + storage_state 登录态
            browser_kwargs = {
                "headless": self.headless,
                "slow_mo": self.slow_mo,
                "args": ["--start-maximized", "--disable-blink-features=AutomationControlled"]
            }
            if self.channel:
                browser_kwargs["channel"] = self.channel
            
            self.browser = self.playwright.chromium.launch(**browser_kwargs)
            
            context_kwargs = {"viewport": {"width": 1920, "height": 1080}}
            # 如果有保存的登录状态，自动加载
            if os.path.exists(state_file):
                context_kwargs["storage_state"] = state_file
            
            self.context = self.browser.new_context(**context_kwargs)
            self.page = self.context.new_page()
    
    def _open_create_page(self):
        """打开创建产品弹窗"""
        # 导航到TEMU全托管产品管理页
        self.page.goto(f"{self.base_url}/pddkj/item/item", wait_until="domcontentloaded")
        time.sleep(5)
        
        # 关闭可能的广告/通知弹窗
        self._dismiss_popups()
        
        # 点击右上角「创建产品」按钮，带重试（最多刷新3次）
        create_btn = None
        for retry in range(3):
            # 每轮重试前先关闭弹窗
            self._dismiss_popups()
            
            selectors = [
                self.page.get_by_role("button", name="创建产品"),
                self.page.locator("button:has-text('创建产品')"),
                self.page.locator(".jx-button--primary:has-text('创建产品')"),
            ]
            
            for sel in selectors:
                try:
                    if sel.first.is_visible(timeout=2000):
                        create_btn = sel.first
                        break
                except:
                    continue
            
            if create_btn:
                break
            
            print(f"  第{retry+1}次没找到按钮，刷新重试...")
            self.page.reload(wait_until="domcontentloaded")
            time.sleep(5)
            self._dismiss_popups()
        
        if not create_btn:
            raise Exception("找不到创建产品按钮（可能登录态过期，请重新运行login_browser.py）")
        
        create_btn.click()
        time.sleep(1)
        
        # 等弹窗，但排除广告通知弹窗
        # notice-message-box-dialog 是广告弹窗，我们要的是 pro-dialog
        try:
            self.page.wait_for_selector(".jx-dialog:not(.notice-message-box-dialog)", state="visible", timeout=10000)
        except:
            # 兜底：原来的选择器
            self.page.wait_for_selector(".jx-dialog", state="visible", timeout=10000)
        time.sleep(1)
    
    def _dismiss_popups(self):
        """关闭妙手后台可能弹出的所有弹窗/遮罩层"""
        try:
            # 策略1: 用Playwright原生定位找"关闭"按钮
            close_selectors = [
                self.page.locator("button:has-text('关闭')"),
                self.page.locator(":text-is('关闭')"),
                self.page.locator(".jx-dialog__close"),
                self.page.locator(".el-icon-close"),
                self.page.locator("button:has-text('我知道了')"),
                self.page.locator(":text-is('我知道了')"),
            ]
            closed_count = 0
            for sel in close_selectors:
                try:
                    count = sel.count()
                    for i in range(count):
                        el = sel.nth(i)
                        if el.is_visible():
                            el.click()
                            closed_count += 1
                            time.sleep(0.3)
                            break
                except:
                    continue
            
            # 策略2: JS强制关闭所有可见弹窗
            js_closed = self.page.evaluate("""() => {
                let count = 0;
                for (let i = 0; i < 5; i++) {
                    let closed = false;
                    const all = document.querySelectorAll('.jx-dialog, .jx-overlay-dialog, [role="dialog"], .el-dialog, .notice-message-box-dialog');
                    for (const d of all) {
                        const r = d.getBoundingClientRect();
                        if (r.height < 10) continue;
                        
                        // 找关闭按钮(×)
                        const closeIcons = d.querySelectorAll('.jx-dialog__close, .el-icon-close, [class*="close"], .el-dialog__close, .el-overlay-dialog__close');
                        for (const btn of closeIcons) {
                            if (btn.getBoundingClientRect().height > 0) { btn.click(); closed = true; count++; break; }
                        }
                        if (closed) break;
                        
                        // 找文字按钮
                        const btns = d.querySelectorAll('button, span, a');
                        for (const btn of btns) {
                            const t = (btn.innerText || '').trim();
                            if (t === '关闭' || t === '我知道了' || t === '确定' || t === '×' || t === '✕') {
                                btn.click(); closed = true; count++; break;
                            }
                        }
                        if (closed) break;
                    }
                    if (!closed) break;
                }
                return count;
            }""")
            closed_count += js_closed
            
            if closed_count > 0:
                print(f"  已关闭 {closed_count} 个弹窗")
                time.sleep(0.8)
        except Exception as e:
            print(f"  关闭弹窗异常(忽略): {e}")
    
    def _dump_size_chart_debug(self):
        """诊断：输出尺码表区域的DOM详情"""
        try:
            info = self.page.evaluate("""() => {
                const result = [];
                // alt approach: also check for el-select elements containing "尺码表" label
                const allSelects = document.querySelectorAll('.el-select');
                allSelects.forEach((sel, i) => {
                    const r = sel.getBoundingClientRect();
                    if (r.height > 10) {
                        const parent = sel.closest('.el-form-item');
                        const label = parent ? (parent.querySelector('.el-form-item__label')?.innerText || '') : '';
                        result.push({type: 'el-select', idx: i, label: label.trim(), top: Math.round(r.top), html: sel.outerHTML.substring(0, 200)});
                    }
                });
                
                // Also check size-template-select-container
                const containers = document.querySelectorAll('.size-template-select-container');
                containers.forEach((c, i) => {
                    const r = c.getBoundingClientRect();
                    result.push({type: 'container', idx: i, top: Math.round(r.top), hasInput: !!c.querySelector('input'), html: c.outerHTML.substring(0, 300)});
                });
                return result;
            }""")
            print(f"  [诊断-尺码表区域]: {json.dumps(info, ensure_ascii=False, indent=2)}")
        except Exception as e:
            print(f"  [诊断异常]: {e}")
    
    def _dump_color_row_debug(self):
        """诊断：输出颜色行的DOM详情"""
        try:
            info = self.page.evaluate("""() => {
                const result = [];
                const dialog = document.querySelector('.jx-dialog');
                if (!dialog) return {error: 'no dialog'};
                
                // 找所有图片上传占位框 (100-150px empty divs)
                const all = dialog.querySelectorAll('div');
                const imgBoxes = [];
                all.forEach(el => {
                    const r = el.getBoundingClientRect();
                    if (r.width >= 100 && r.width <= 150 && r.height >= 100 && r.height <= 150) {
                        imgBoxes.push({top: Math.round(r.top), left: Math.round(r.left), empty: el.innerText.trim() === '', children: el.children.length});
                    }
                });
                
                // 找包含颜色名的元素
                const colorLabels = [];
                const allText = dialog.querySelectorAll('*');
                allText.forEach(el => {
                    const t = (el.innerText || '').trim();
                    if (t.length > 0 && t.length < 10 && el.children.length === 0) {
                        const r = el.getBoundingClientRect();
                        if (r.width > 10 && r.height > 10) {
                            colorLabels.push({text: t, top: Math.round(r.top), left: Math.round(r.left)});
                        }
                    }
                });
                
                return {imgBoxes, colorLabels: colorLabels.slice(-10)};
            }""")
            print(f"  [诊断-颜色/图片]: {json.dumps(info, ensure_ascii=False, indent=2)}")
        except Exception as e:
            print(f"  [诊断异常]: {e}")
    
    def _select_shop(self, shop_name: str):
        """选择店铺：codegen验证的jx-选择器"""
        print(f"\n=== 店铺选择 ===")

        # 1. 删除已有tag（codegen路径）
        print(f"  [1/4] 删除已有店铺...")
        try:
            self.page.locator(".jx-cascader__tags .jx-tag .jx-icon").first.click(timeout=3000)
        except:
            pass
        time.sleep(0.5)

        # 2. 点×后输入框已聚焦，直接键盘输入
        print(f"  [2/4] 输入「{shop_name}」...")
        self.page.keyboard.type(shop_name, delay=100)
        time.sleep(1.5)

        # 3. 回车选中搜索结果
        print(f"  [3/4] 选中搜索结果...")
        self.page.keyboard.press("Enter")
        time.sleep(0.5)

        # 4. 点击空白关闭浮层
        print(f"  [4/4] 关闭浮层...")
        self.page.mouse.click(10, 10)
        time.sleep(0.5)
    
    def _apply_template(self, template_name: str):
        """引用品类模板"""
        # 找到「引用模板」触发按钮并点击展开
        # 先找包含"引用模板"文字的按钮/触发器
        trigger = self.page.get_by_role("button", name="引用模板").first
        if not trigger.is_visible():
            # 试试其他形式的触发器
            trigger = self.page.locator(":text-is('引用模板')").locator("xpath=ancestor::button | ancestor::*[contains(@class,'trigger')] | ancestor::a").first
        
        trigger.wait_for(state="visible")
        trigger.click()
        time.sleep(0.8)
        
        # 等待下拉菜单出现并选择目标模板
        menu = self.page.locator(".template-dropdown").first
        menu.wait_for(state="visible")
        
        template_item = menu.get_by_text(template_name, exact=True).first
        template_item.wait_for(state="visible")
        template_item.click()
        time.sleep(0.5)
        
        # 处理确认弹窗（"您确定引用此模板？"）
        try:
            dialog = self.page.get_by_role("dialog", name="提示")
            dialog.wait_for(state="visible", timeout=5000)
            confirm_btn = dialog.get_by_role("button", name="确定")
            confirm_btn.wait_for(state="visible", timeout=3000)
            confirm_btn.click()
            # 等待模板数据加载完成，弹窗重新渲染
            time.sleep(7)
        except:
            pass
    
    def _switch_tab(self, tab_text: str):
        """切换创建产品弹窗顶部的标签页"""
        dialog = self.page.locator(".jx-dialog").last
        tab = dialog.get_by_text(tab_text, exact=True).first
        tab.wait_for(state="visible", timeout=10000)
        tab.click()
        time.sleep(0.8)
    
    def _fill_variable_attributes(self, product: Product):
        """填充变量属性：面料克重、季节、版型、织造方式"""
        self._switch_tab("类别&属性")
        
        style = product.main_style
        
        # 逐个填充属性
        if style.fabric_weight:
            self._set_form_input("克重", style.fabric_weight)
        
        if style.season:
            self._set_form_select("季节", style.season)
        
        if style.fit:
            self._set_form_select("版型", style.fit)
        
        if style.weave_method:
            self._set_form_select("织造方式", style.weave_method)
        
        time.sleep(0.5)
    
    def _fill_basic_info(self, product: Product):
        """填充产品基础信息：标题、主货号等"""
        self._switch_tab("产品信息")
        
        # 填写产品标题（中文标题）
        if product.title:
            title_input = self.page.locator("input[placeholder*='产品标题']").first
            if title_input.is_visible():
                title_input.fill(product.title)
        
        # 填写主货号（用商品编号）
        sku_input = self.page.locator("input[placeholder*='主货号']").first
        if sku_input.is_visible():
            sku_input.fill(product.product_id)
        
        # TODO: 上传产品轮播图（对接生图模块后实现）
        time.sleep(0.5)
    
    def _fill_sku_info(self, product: Product):
        """填充销售属性：颜色、尺码、尺码表、价格、SKU分类"""
        self._switch_tab("销售属性")
        
        # 1. 添加颜色并上传图片
        print(f"  [调试] 颜色数量: {len(product.colors) if product.colors else 0}")
        if product.colors:
            for color in product.colors:
                if isinstance(color, str):
                    color_name = color
                    image_urls = []
                else:
                    color_name = color.get("name")
                    image_urls = color.get("image_urls", [])
                print(f"  [调试] 添加颜色: {color_name}, 图片数: {len(image_urls)}")
                self._add_color_with_images(color_name, image_urls)
        
        # 2. 勾选尺码 + 选择尺码表（混合套装特殊处理）
        is_mixed_set = (product.combo_type == "suit" or 
                       getattr(product, 'sku_class_override', '') == "混合套装")
        
        if is_mixed_set and product.all_styles:
            print(f"  [流程] 进入混合套装分支: combo_type={is_mixed_set}, all_styles数量={len(product.all_styles)}, 款式名={[s.style_name for s in product.all_styles]}")
            # 混合套装：所有款式尺码取交集，每个款式一个尺码表
            all_style_sizes = [product.main_style.sizes] + [s.sizes for s in product.all_styles]
            intersect_sizes = all_style_sizes[0]
            for sz in all_style_sizes[1:]:
                intersect_sizes = [s for s in intersect_sizes if s in sz]
            print(f"  套装款式数: {product.style_count}, 尺码交集={intersect_sizes}")
            
            if intersect_sizes:
                self._select_sizes(intersect_sizes)
            else:
                print(f"  警告: 款式间无交集尺码，使用主款尺码")
                self._select_sizes(all_style_sizes[0])
            time.sleep(0.5)
            
            # 所有款式名列表
            all_names = [product.main_style.style_name] + [s.style_name for s in product.all_styles]
            self._select_size_chart_mixed_set(all_names)
            time.sleep(1)
            
            # 勾选重点展示部件
            self._check_key_display_parts(*all_names[:2])  # 最多传两个
        else:
            # 非混合套装：原有逻辑
            if product.final_sizes:
                self._select_sizes(product.final_sizes)
            time.sleep(0.5)
            
            if product.main_style:
                self._select_size_chart(product.main_style.style_name)
        
        # 等待SKU表格生成
        time.sleep(2)
        
        # 3. 批量设置供货价
        if product.final_price:
            self._batch_set_price("供货价", product.final_price)
        
        # 4. 批量设置建议售价（供货价 × 2.5）
        if product.final_price:
            suggest_price = round(product.final_price * 2.5, 2)
            self._batch_set_price("建议售价", suggest_price)
        
        # 5. 批量设置SKU分类
        if product.final_sku_class:
            quantity = getattr(product, 'sku_quantity', 1)
            self._batch_set_sku_class(product.final_sku_class, quantity)
        
        # 6. 批量设置尺寸（长宽高）
        quantity = getattr(product, 'sku_quantity', 1)
        length = 25 + (quantity - 1) * 3
        width = 20 + (quantity - 1) * 3
        height = 3 + (quantity - 1) * 1
        self._batch_set_size(length, width, height)
        
        # 7. 批量设置重量（按尺码逐个设置）
        if product.main_style and product.main_style.size_details:
            quantity = getattr(product, 'sku_quantity', 1)
            self._batch_set_weight(product.main_style.size_details, quantity)
        
        time.sleep(0.5)
    
    def _submit(self) -> dict:
        """提交创建，等待完成，提取SKC ID和商品链接"""
        print("  [提交] 点击「确定创建」按钮...")
        # 兼容不同按钮文本：确定创建/提交/保存
        submit_selectors = [
            self.page.get_by_role("button", name="确定创建"),
            self.page.locator(".jx-dialog .jx-button--primary:has-text('确定创建')"),
            self.page.locator(".jx-dialog .jx-button--primary:has-text('提交')"),
            self.page.locator(".jx-dialog .jx-button--primary:has-text('保存')"),
        ]
        submit_btn = None
        for sel in submit_selectors:
            try:
                if sel.first.is_visible(timeout=2000):
                    submit_btn = sel.first
                    break
            except:
                continue
        if not submit_btn:
            raise Exception("找不到确定创建/提交按钮")
        
        # 滚动到按钮位置点击
        submit_btn.scroll_into_view_if_needed()
        submit_btn.click()
        
        # 处理可能的二次确认弹窗
        time.sleep(1)
        try:
            confirm_btn = self.page.get_by_role("button", name="确定").first
            if confirm_btn.is_visible(timeout=2000):
                confirm_btn.click()
                print("  [提交] 处理二次确认弹窗")
        except:
            pass
        
        # 等待提交完成：等成功提示/弹窗关闭
        print("  [提交] 等待上传提交完成（最长等待30秒）...")
        skc_id = None
        product_url = None
        try:
            # 等待成功提示出现
            self.page.wait_for_selector(":text('创建成功')", timeout=30000)
            print("  [提交] 商品创建成功！")
            time.sleep(2)
            # 提取SKC ID和链接
            result = self.page.evaluate("""() => {
                // 从成功提示/跳转页提取SKC ID
                const allText = document.body.innerText;
                const skcMatch = allText.match(/SKC[:：\s]*(\d+)/i);
                const skc = skcMatch ? skcMatch[1] : null;
                // 提取商品链接
                const links = Array.from(document.querySelectorAll('a'));
                let url = null;
                for (const a of links) {
                    if (a.href && (a.href.includes('item/detail') || a.href.includes('skc_id'))) {
                        url = a.href;
                        break;
                    }
                }
                return {skc_id: skc, url: url};
            }""")
            skc_id = result.get('skc_id')
            product_url = result.get('url')
            # 关闭成功弹窗
            try:
                self.page.locator(".jx-dialog__close, .el-dialog__close, button:has-text('确定')").first.click(timeout=3000)
            except:
                pass
        except Exception as e:
            print(f"  [提交] 等待结果超时: {e}，保存截图查看")
            self.page.screenshot(path="submit_error.png", full_page=True)
        
        return {"skc_id": skc_id, "product_url": product_url}
    
    def _close_browser(self):
        """关闭浏览器资源"""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except:
            pass
    
    # ========== 辅助方法 ==========
    
    def _close_message_boxes(self):
        """关闭弹窗 + 强制清除遮罩层"""
        try:
            # 先尝试点确定按钮关弹窗
            for _ in range(3):
                confirm_btn = self.page.locator(".jx-overlay-message-box .jx-button-primary, .jx-message-box .jx-button-primary, .jx-dialog .jx-button--primary").first
                if confirm_btn.is_visible(timeout=500):
                    confirm_btn.click()
                    time.sleep(0.3)
                else:
                    break
        except:
            pass
        
        # 强制清除所有遮罩层（防止loading遮罩卡住）
        try:
            self.page.evaluate("""
                document.querySelectorAll('.jx-overlay').forEach(el => {
                    el.style.display = 'none';
                    el.style.visibility = 'hidden';
                });
                document.querySelectorAll('.jx-overlay-message-box, .jx-message-box').forEach(el => {
                    el.style.display = 'none';
                });
            """)
        except:
            pass
        
        time.sleep(0.3)
    
    def _set_form_input(self, label: str, value: str):
        """设置表单输入框的值（通过标签名查找）"""
        # 找到包含label文字的表单项，再找里面的input
        form_item = self.page.locator(f":text-is('{label}')").locator("..").first
        input_el = form_item.locator("input").first
        if input_el.is_visible():
            input_el.click()
            input_el.fill(value)
    
    def _set_form_select(self, label: str, option_text: str):
        """设置表单下拉框的值（标签用locator定位，选项用鼠标点击确保生效）"""
        # 找到label
        label_el = self.page.locator(f":text-is('{label}')").first
        try:
            label_el.wait_for(state="visible", timeout=3000)
        except:
            print(f"  警告: 未找到下拉标签: {label}")
            return
        
        # 找旁边的下拉触发器并点击展开
        select_trigger = label_el.locator("xpath=../following-sibling::*//*[contains(@class,'select') or @role='combobox']").first
        if select_trigger.count() == 0:
            select_trigger = label_el.locator("xpath=following-sibling::*//*[contains(@class,'select') or @role='combobox']").first
        
        try:
            select_trigger.wait_for(state="visible", timeout=3000)
            select_trigger.click()
        except:
            print(f"  警告: 未找到下拉触发器: {label}")
            return
        time.sleep(0.5)
        
        # 用JS找选项坐标，鼠标点击确保触发Vue事件
        option_pos = self.page.evaluate("""(text) => {
                const all = document.querySelectorAll('.jx-select-dropdown li, .select-dropdown li, [class*="dropdown"] li, [role="option"]');
                const found = [];
                for (const el of all) {
                    const t = (el.innerText || '').trim();
                    if (t && el.getBoundingClientRect().height > 5) {
                        found.push(t);
                        if (t === text) {
                            const r = el.getBoundingClientRect();
                            return {x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2)};
                        }
                    }
                }
                // 没找到精确匹配，输出可用选项供诊断
                return {available: found.slice(0, 20), target: text};
            }""", option_text)
        
        if option_pos and 'x' in option_pos:
            self.page.mouse.click(option_pos['x'], option_pos['y'])
            time.sleep(0.3)
        elif option_pos and 'available' in option_pos:
            # 模糊匹配：去除/等符号后归一化比较
            import re as _re
            available = option_pos['available']
            target = option_text
            target_norm = _re.sub(r'[/\s（）()]', '', target)
            best = None
            for opt in available:
                opt_norm = _re.sub(r'[/\s（）()]', '', opt)
                if target_norm in opt_norm or opt_norm in target_norm:
                    best = opt
                    break
            if best:
                print(f"  模糊匹配: 「{target}」→「{best}」")
                opt2 = self.page.evaluate("""(t) => {
                    const all = document.querySelectorAll('.jx-select-dropdown li, .select-dropdown li, [class*="dropdown"] li, [role="option"]');
                    for (const el of all) {
                        if ((el.innerText || '').trim() === t) {
                            const r = el.getBoundingClientRect();
                            return {x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2)};
                        }
                    }
                    return null;
                }""", best)
                if opt2 and 'x' in opt2:
                    self.page.mouse.click(opt2['x'], opt2['y'])
                    time.sleep(0.3)
                else:
                    self.page.keyboard.press("Escape")
            else:
                print(f"  警告: 下拉选项未找到「{target}」，可用: {available}")
                self.page.keyboard.press("Escape")
        
        time.sleep(0.2)
    
    def _add_color_with_images(self, color_name: str, image_urls: list):
        """添加一个颜色规格并立即上传图片（每色单独处理，避免位置漂移）"""
        # 滚动到颜色区
        self.page.evaluate("""() => {
            const all = document.querySelectorAll('.jx-dialog *');
            for (const el of all) {
                if (el.innerText && el.innerText.includes('颜色(')) {
                    el.scrollIntoView({block: 'center'}); break;
                }
            }
        }""")
        time.sleep(0.3)
        
        # 点击「+ 新增」添加颜色行
        add_link = self.page.locator(":text-is('+ 新增')").first
        add_link.click()
        time.sleep(2)
        
        # 找到新增颜色行的输入框（最后一个颜色输入）
        color_input_pos = self.page.evaluate("""() => {
            const inputs = document.querySelectorAll('input[placeholder*="颜色"], input[placeholder*="自定义"]');
            if (inputs.length === 0) return null;
            const inp = inputs[inputs.length - 1];
            const r = inp.getBoundingClientRect();
            return {x: r.left + r.width/2, y: r.top + r.height/2};
        }""")
        
        if not color_input_pos:
            print(f"  警告: 未找到颜色输入框")
            return
        
        self.page.mouse.click(color_input_pos['x'], color_input_pos['y'])
        time.sleep(0.3)
        self.page.keyboard.press("Control+A")
        time.sleep(0.1)
        self.page.keyboard.type(color_name)
        time.sleep(1)
        
        # 创建自定义颜色
        self.page.evaluate("""(name) => {
            const all = document.querySelectorAll('*');
            for (const el of all) {
                if (el.children.length === 0 && (el.innerText || '').trim().startsWith('创建自定义颜色-')) {
                    const r = el.getBoundingClientRect();
                    if (r.height > 0 && r.width > 0) { el.click(); return true; }
                }
            }
            return false;
        }""", color_name)
        time.sleep(1)
        
        # 立即上传本颜色的图片（不等其他颜色，避免位置漂移）
        if image_urls:
            # 基于颜色输入框位置定位图片上传框：颜色行的图片框就在颜色输入框旁边
            img_box = self.page.evaluate("""(name) => {
                const inputs = document.querySelectorAll('input');
                let targetInput = null;
                for (const inp of inputs) {
                    if (inp.value && (inp.value === name || inp.value.includes(name) || name.includes(inp.value))) {
                        targetInput = inp; break;
                    }
                    // 也检查没有value但有颜色的placeholder的input
                    if (!inp.value && inp.placeholder && (inp.placeholder.includes('颜色') || inp.placeholder.includes('自定义'))) {
                        // 找input旁边的文本节点
                        const parent = inp.parentElement;
                        if (parent && parent.innerText && parent.innerText.includes(name)) {
                            targetInput = inp; break;
                        }
                    }
                }
                if (!targetInput) return null;
                
                // 从输入框向上找到颜色行容器
                let row = targetInput.parentElement;
                for (let i = 0; i < 8; i++) {
                    if (!row || row.classList.contains('jx-dialog')) break;
                    const r = row.getBoundingClientRect();
                    if (r.width > 400 && r.height > 40) break;
                    row = row.parentElement;
                }
                
                if (!row) return null;
                
                // 在颜色行内找图片上传框（带+号的空区域）
                const allDivs = row.querySelectorAll('div');
                for (const div of allDivs) {
                    const r = div.getBoundingClientRect();
                    // 图片框特征：尺寸在60-180px，在颜色输入框右侧，空的或有+号
                    const isRightOfInput = r.left > targetInput.getBoundingClientRect().left + 50;
                    if (isRightOfInput && r.width >= 60 && r.width <= 180 && r.height >= 60 && r.height <= 180) {
                        return {x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2), w: Math.round(r.width), h: Math.round(r.height)};
                    }
                }
                
                // 兜底: 找row内任何60-180px的div
                for (const div of allDivs) {
                    const r = div.getBoundingClientRect();
                    if (r.width >= 60 && r.width <= 180 && r.height >= 60 && r.height <= 180) {
                        return {x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2), w: Math.round(r.width), h: Math.round(r.height)};
                    }
                }
                return null;
            }""", color_name)
            
            if img_box:
                print(f"  [定位] 找到图片框: w={img_box.get('w')}, h={img_box.get('h')}")
                self._do_upload_images_from_box(img_box['x'], img_box['y'], image_urls)
            else:
                print(f"  警告: 未找到 {color_name} 的图片上传框")
        time.sleep(0.5)
    
    def _do_upload_images_from_box(self, x: int, y: int, image_urls: list):
        """从指定坐标的图片框上传图片"""
        image_urls = self._sort_images_by_filename(image_urls)
        
        self.page.mouse.click(x, y)
        time.sleep(0.5)
        
        # 点击"使用网络图片"
        self.page.evaluate("""() => {
            const all = document.querySelectorAll('*');
            for (const el of all) {
                if (el.children.length === 0 && el.innerText && el.innerText.trim() === '使用网络图片') {
                    if (el.getBoundingClientRect().width > 0) { el.click(); return; }
                }
            }
        }""")
        time.sleep(0.8)
        
        # 取消保存到图片空间
        self.page.evaluate("""() => {
            const dialogs = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
            for (const d of dialogs) {
                if (d.innerText && d.innerText.includes('使用网络图片')) {
                    const checkboxes = d.querySelectorAll('input[type="checkbox"]');
                    for (const cb of checkboxes) { if (cb.checked) cb.click(); }
                    return;
                }
            }
        }""")
        
        # 填入URL
        textarea_pos = self.page.evaluate("""() => {
            const dialogs = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
            for (const d of dialogs) {
                if (d.innerText && d.innerText.includes('使用网络图片')) {
                    const ta = d.querySelector('textarea');
                    if (ta) {
                        const r = ta.getBoundingClientRect();
                        return {x: Math.round(r.left + 10), y: Math.round(r.top + 10)};
                    }
                }
            }
            return null;
        }""")
        
        if textarea_pos:
            self.page.mouse.click(textarea_pos['x'], textarea_pos['y'])
            time.sleep(0.2)
            self.page.keyboard.press("Control+A")
            time.sleep(0.1)
            self.page.keyboard.press("Backspace")
            self.page.keyboard.type("\n".join(image_urls))
            time.sleep(0.3)
            
            self.page.evaluate("""() => {
                const dialogs = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
                for (const d of dialogs) {
                    if (d.innerText && d.innerText.includes('使用网络图片')) {
                        const btns = d.querySelectorAll('button');
                        for (const btn of btns) {
                            if (btn.innerText.trim() === '确定') { btn.click(); return; }
                        }
                    }
                }
            }""")
            time.sleep(5)
    
    def _sort_images_by_filename(self, images: list) -> list:
        """按文件名中的数字智能排序图片，确保1、2、3...顺序正确
        images: 元素可以是str(URL)或dict(含name和url)
        """
        import re
        
        def extract_num(item):
            if isinstance(item, dict):
                name = item.get('name', '')
            else:
                # 从URL末尾提取文件名
                name = str(item).split('/')[-1].split('?')[0]
            nums = re.findall(r'\d+', name)
            return int(nums[0]) if nums else 99999
        
        try:
            return sorted(images, key=extract_num)
        except:
            return images
    
    def _upload_color_images(self, image_urls: list, color_name: str = None):
        """给当前颜色行上传图片（网络图片方式）
        
        Args:
            color_name: 颜色名称，用于精确定位刚添加的颜色行的图片框
        """
        # 先按文件名数字智能排序
        image_urls = self._sort_images_by_filename(image_urls)
        
        if not color_name:
            img_box_pos = None
        else:
            img_box_pos = None
        
        # 策略1: color_name 精准匹配
        if color_name:
            img_box_pos = self.page.evaluate("""(name) => {
                const dialog = document.querySelector('.jx-dialog');
                if (!dialog) return null;
                const allEls = dialog.querySelectorAll('*');
                for (const el of allEls) {
                    const t = (el.innerText || '').trim();
                    if (el.children.length === 0 && t === name) {
                        let parent = el.parentElement;
                        for (let i = 0; i < 8; i++) {
                            if (!parent || parent === dialog) break;
                            const pRect = parent.getBoundingClientRect();
                            if (pRect.width > 300 && pRect.height > 30) {
                                const divs = parent.querySelectorAll('div');
                                for (const div of divs) {
                                    const rect = div.getBoundingClientRect();
                                    if (rect.width >= 100 && rect.width <= 150 && rect.height >= 100 && rect.height <= 150 && div.innerText.trim() === '' && div.children.length <= 2) {
                                        return {x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)};
                                    }
                                }
                            }
                            parent = parent.parentElement;
                        }
                    }
                }
                return null;
            }""", color_name)
            
            if img_box_pos:
                print(f"  [精准] 找到图片框(颜色={color_name})")
        
        # 策略2: 传统兜底 - 找dialog内所有符合条件的图片框，取最后(最下方)的
        if not img_box_pos:
            img_box_pos = self.page.evaluate("""() => {
                const dialog = document.querySelector('.jx-dialog');
                if (!dialog) return null;
                const all = dialog.querySelectorAll('div');
                const matches = [];
                for (const el of all) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width >= 100 && rect.width <= 150 && rect.height >= 100 && rect.height <= 150 && el.innerText.trim() === '' && el.children.length <= 2) {
                        matches.push({x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2), top: rect.top});
                    }
                }
                if (matches.length === 0) return null;
                matches.sort((a, b) => a.top - b.top);
                return matches[matches.length - 1];
            }""")
            if img_box_pos:
                print(f"  [兜底] 找到图片框 (top={img_box_pos.get('top','?')})")
        
        if not img_box_pos:
            print(f"  警告: 未找到图片上传框 (颜色: {color_name})")
            # 完整诊断：列出所有可见div的尺寸
            self.page.evaluate("""() => {
                const all = document.querySelectorAll('.jx-dialog div');
                const visible = [];
                all.forEach(d => {
                    const r = d.getBoundingClientRect();
                    if (r.width > 20 && r.height > 20 && r.top > 0 && r.top < 2000) {
                        visible.push({w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.left), y: Math.round(r.top)});
                    }
                });
                console.log('ALL_VISIBLE_DIVS', JSON.stringify(visible.slice(0, 50)));
                return 'logged';
            }""")
            # 更宽泛地搜图片框：扩大到50-300px范围
            img_box_pos = self.page.evaluate("""() => {
                const dialog = document.querySelector('.jx-dialog');
                if (!dialog) return null;
                const all = dialog.querySelectorAll('div');
                const matches = [];
                for (const el of all) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width >= 50 && rect.width <= 300 && rect.height >= 50 && rect.height <= 300 && rect.top > 0 && rect.top < 2000) {
                        matches.push({x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2), top: rect.top, w: rect.width, h: rect.height});
                    }
                }
                if (matches.length === 0) return null;
                matches.sort((a, b) => a.top - b.top);
                return matches[matches.length - 1];
            }""")
            if img_box_pos:
                print(f"  [宽搜] 找到图片框: w={img_box_pos.get('w')}, h={img_box_pos.get('h')}")
            return
        
        # 点击图片框弹出菜单
        self.page.mouse.click(img_box_pos['x'], img_box_pos['y'])
        time.sleep(0.5)
        
        # 点击"使用网络图片"
        self.page.evaluate("""
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
        
        # 取消"同时保存图片到妙手图片空间"的勾选
        self.page.evaluate("""
            () => {
                const dialogs = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
                for (const d of dialogs) {
                    const rect = d.getBoundingClientRect();
                    if (rect.width > 400 && rect.height > 200 && 
                        d.innerText && d.innerText.includes('使用网络图片')) {
                        const checkboxes = d.querySelectorAll('input[type="checkbox"]');
                        for (const cb of checkboxes) {
                            if (cb.checked) cb.click();
                        }
                        return;
                    }
                }
            }
        """)
        
        # 找到textarea并填入URL（换行分隔）
        textarea_pos = self.page.evaluate("""
            () => {
                const dialogs = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
                for (const d of dialogs) {
                    const rect = d.getBoundingClientRect();
                    if (rect.width > 400 && rect.height > 200 && 
                        d.innerText && d.innerText.includes('使用网络图片')) {
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
        
        if textarea_pos:
            # 点击并输入
            self.page.mouse.click(textarea_pos['x'], textarea_pos['y'])
            time.sleep(0.2)
            self.page.keyboard.press("Control+A")
            time.sleep(0.1)
            self.page.keyboard.press("Backspace")
            time.sleep(0.1)
            
            urls_text = "\n".join(image_urls)
            self.page.keyboard.type(urls_text)
            time.sleep(0.3)
            
            # 点击确定
            self.page.evaluate("""
                () => {
                    const dialogs = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog');
                    for (const d of dialogs) {
                        const rect = d.getBoundingClientRect();
                        if (rect.width > 400 && rect.height > 200 && 
                            d.innerText && d.innerText.includes('使用网络图片')) {
                            const btns = d.querySelectorAll('button');
                            for (const btn of btns) {
                                if (btn.innerText.trim() === '确定') {
                                    btn.click();
                                    return true;
                                }
                            }
                        }
                    }
                    return false;
                }
            """)
            time.sleep(5)  # 等待上传完成
    
    def _select_sizes(self, sizes: list):
        """勾选尺码复选框（用JS遍历查找）"""
        for size in sizes:
            size_str = str(size)
            found = self.page.evaluate("""
                (sizeText) => {
                    const els = document.querySelectorAll('.jx-checkbox, input[type=checkbox]');
                    for (const el of els) {
                        const label = el.closest('label') || el.parentElement;
                        if (label && label.textContent.trim() === sizeText) {
                            if (!el.checked) el.click();
                            return true;
                        }
                    }
                    const all = document.querySelectorAll('*');
                    for (const el of all) {
                        if (el.children.length === 0 && el.textContent.trim() === sizeText) {
                            const checkbox = el.previousElementSibling?.querySelector('input');
                            if (checkbox && !checkbox.checked) {
                                checkbox.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }
            """, size_str)
            if not found:
                print(f"  警告: 未找到尺码 {size_str}")
        time.sleep(0.5)
    
    def _read_product_category(self) -> str:
        """从上架页面读取当前产品的类目路径（优先返回缓存值）"""
        if hasattr(self, '_cached_category') and self._cached_category:
            return self._cached_category
        cat = self.page.evaluate("""() => {
            // 方法1：找级联选择器(input的value包含完整类目路径)
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {
                const v = (inp.value || '');
                if (v.startsWith('服装、') && v.includes('/')) return v;
            }
            // 方法2：找.el-form-item的label含"类目"的
            const formItems = document.querySelectorAll('.el-form-item');
            for (const fi of formItems) {
                const label = fi.querySelector('.el-form-item__label');
                if (label && (label.innerText || '').includes('类目')) {
                    const inner = fi.querySelector('.el-input__inner');
                    if (inner && inner.value) return inner.value;
                    const txt = (fi.innerText || '').replace(label.innerText, '').trim();
                    if (txt && txt.includes('服装')) return txt;
                }
            }
            return '';
        }""")
        return cat.strip() if cat else ""

    def _select_size_chart(self, style_name: str):
        """选择尺码表（按款式名匹配）"""
        select_container = self.page.locator(".size-template-select-container").first
        try:
            select_container.wait_for(state="visible", timeout=3000)
        except:
            print("  警告: 未找到尺码表选择框")
            return
        
        # 点击展开下拉
        select_container.click()
        time.sleep(1.5)  # 加长等待下拉渲染
        
        # 调试：看下拉有没有出现
        dropdown_debug = self.page.evaluate("""() => {
            const dds = document.querySelectorAll('.el-select-dropdown, [class*="select-dropdown"], [role="listbox"]');
            const r = [];
            dds.forEach(dd => { const rect = dd.getBoundingClientRect(); r.push({h: Math.round(rect.height), w: Math.round(rect.width), visible: rect.height > 10}); });
            return r;
        }""")
        print(f"  [调试-下拉框] 点击后: {json.dumps(dropdown_debug, ensure_ascii=False)}")
        
        # 找到搜索输入框并点击聚焦
        search_input = self.page.evaluate("""
            () => {
                const container = document.querySelector('.size-template-select-container');
                if (!container) return null;
                const input = container.querySelector('input');
                if (input) {
                    const r = input.getBoundingClientRect();
                    return {x: r.left + 10, y: r.top + r.height/2};
                }
                return null;
            }
        """)
        
        if search_input:
            self.page.mouse.click(search_input['x'], search_input['y'])
            time.sleep(0.2)
            self.page.keyboard.press("Control+A")
            time.sleep(0.1)
        
        # 输入款式名搜索
        self.page.keyboard.type(style_name)
        time.sleep(1.2)  # 多等一下搜索结果
        
        # 点击第一个匹配的选项
        chosen = self.page.evaluate("""
            (name) => {
                // 找下拉弹层里的选项
                const dropdowns = document.querySelectorAll('.el-select-dropdown, [class*="select-dropdown"], [role="listbox"]');
                for (const dd of dropdowns) {
                    const rect = dd.getBoundingClientRect();
                    if (rect.height < 10) continue;
                    const items = dd.querySelectorAll('li, [class*="dropdown-item"], [class*="select-item"], [role="option"]');
                    for (const item of items) {
                        const text = (item.innerText || '').trim();
                        const r = item.getBoundingClientRect();
                        if (text.includes(name) && r.height > 10) {
                            item.click();
                            return true;
                        }
                    }
                }
                // 兜底：全局找
                const all = document.querySelectorAll('li, [class*="dropdown-item"], [class*="select-item"]');
                for (const item of all) {
                    const text = (item.innerText || '').trim();
                    const r = item.getBoundingClientRect();
                    if (text.includes(name) && r.height > 10) {
                        item.click();
                        return true;
                    }
                }
                return false;
            }
        """, style_name)
        
        if chosen:
            print(f"  尺码表: {style_name}")
        else:
            print(f"  未找到尺码表 {style_name}，自动创建...")
            self.page.keyboard.press("Escape")
            time.sleep(0.5)
            # 从当前上架页面读取产品类目
            try:
                cat_path = self._read_product_category()
                print(f"  读取到类目: {cat_path or '(空，将自动推断)'}")
            except Exception as e:
                print(f"  读取类目失败: {e}，将自动推断")
                cat_path = ""
            # 新标签页打开尺码表管理页面
            try:
                sz_page = self.context.new_page()
                sz_page.goto("https://erp.91miaoshou.com/pddkj/move_collect/template_management/sizeChart",
                             wait_until="domcontentloaded")
                time.sleep(4)
                from utils.sizetable_creator import create_sizetable_for_style
                sz_ok = create_sizetable_for_style(sz_page, style_name, cat_path)
                sz_page.close()
            except Exception as e:
                print(f"  创建尺码表异常: {e}")
                sz_ok = False
                try:
                    sz_page.close()
                except:
                    pass
            if sz_ok:
                # 回到上架页面重新搜索（重新获取select_container，避免stale）
                time.sleep(1)
                self.page.bring_to_front()
                select_container = self.page.locator(".size-template-select-container").first
                select_container.click()
                time.sleep(1.5)
                # 点击搜索输入框
                search_input = select_container.locator("input").first
                if search_input.is_visible():
                    search_input.click()
                    time.sleep(0.2)
                self.page.keyboard.press("Control+A")
                time.sleep(0.1)
                self.page.keyboard.type(style_name)
                time.sleep(1.2)
                # 再次尝试选择
                self.page.evaluate(f"(name) => {{ const all = document.querySelectorAll('li, [class*=\"dropdown-item\"]'); for (const item of all) {{ if ((item.innerText||'').includes(name) && item.getBoundingClientRect().height>10) {{ item.click(); break; }} }} }}", style_name)
                time.sleep(0.5)
        time.sleep(0.5)
    
    def _select_size_chart_mixed_set(self, style_names: list):
        """混合套装：依次为每个款式选择尺码表，3件套以上自动点+添加尺码表"""
        self._dump_size_chart_debug()
        
        n = len(style_names)
        print(f"  套装 {n} 件套，逐一选择尺码表...")
        
        for i, sname in enumerate(style_names):
            if i >= 2:
                # 3件套起需要点"+添加尺码表"
                self._click_add_size_chart_selector()
            self._select_size_chart_by_index(i, sname)
            time.sleep(0.8)
        
        # 释放焦点
        self.page.mouse.click(10, 10)
        time.sleep(0.3)
        self.page.keyboard.press("Escape")
        time.sleep(0.3)
    
    def _click_add_size_chart_selector(self):
        """点击'+添加尺码表'按钮"""
        try:
            add_btn = self.page.locator("span:has-text('添加尺码表'), button:has-text('添加尺码表')").first
            if add_btn.is_visible(timeout=2000):
                add_btn.click()
                time.sleep(0.5)
                return
        except:
            pass
        print("  警告: 未找到添加尺码表按钮")
    
    def _select_size_chart_by_index(self, index: int, style_name: str):
        """按索引选择尺码表（0=尺码表1, 1=尺码表2）
        
        使用与 _select_size_chart 相同的 Playwright locator 方式，
        nth(index) 定位第index个容器，确保Vue事件正确触发。
        """
        select_container = self.page.locator(".size-template-select-container").nth(index)
        try:
            select_container.wait_for(state="visible", timeout=3000)
        except:
            print(f"  警告: 第{index+1}个尺码表选择框不可见")
            return
        
        # 用Playwright原生click触发Vue下拉
        select_container.click()
        time.sleep(1.5)  # 加长等待下拉渲染
        
        # 调试：看下拉有没有出现
        dropdown_debug = self.page.evaluate("""() => {
            const dds = document.querySelectorAll('.el-select-dropdown, [class*="select-dropdown"], [role="listbox"]');
            const r = [];
            dds.forEach(dd => { const rect = dd.getBoundingClientRect(); r.push({h: Math.round(rect.height), w: Math.round(rect.width), visible: rect.height > 10}); });
            return r;
        }""")
        print(f"  [调试-下拉框] 点击后: {json.dumps(dropdown_debug, ensure_ascii=False)}")
        
        # 找到搜索输入框（此时下拉已展开，input应出现）
        search_input = self.page.evaluate("""(idx) => {
            const containers = document.querySelectorAll('.size-template-select-container');
            if (!containers[idx]) return null;
            const container = containers[idx];
            const input = container.querySelector('input');
            if (input) {
                const r = input.getBoundingClientRect();
                return {x: r.left + 10, y: r.top + r.height/2};
            }
            return null;
        }""", index)
        
        if search_input:
            self.page.mouse.click(search_input['x'], search_input['y'])
            time.sleep(0.2)
            self.page.keyboard.press("Control+A")
            time.sleep(0.1)
        
        # 输入并搜索
        self.page.keyboard.type(style_name)
        time.sleep(1.2)
        
        # 点击匹配项
        chosen = self.page.evaluate("""(name) => {
            const dropdowns = document.querySelectorAll('.el-select-dropdown, [class*="select-dropdown"], [role="listbox"]');
            for (const dd of dropdowns) {
                const rect = dd.getBoundingClientRect();
                if (rect.height < 10) continue;
                const items = dd.querySelectorAll('li, [class*="dropdown-item"], [class*="select-item"], [role="option"]');
                for (const item of items) {
                    if ((item.innerText || '').includes(name) && item.getBoundingClientRect().height > 10) {
                        item.click();
                        return true;
                    }
                }
            }
            return false;
        }""", style_name)
        
        if chosen:
            print(f"  尺码表{index+1}: {style_name}")
        else:
            print(f"  未找到尺码表{index+1}: {style_name}，自动创建...")
            self.page.keyboard.press("Escape")
            time.sleep(0.5)
            try:
                cat_path = self._read_product_category()
                print(f"  读取到类目: {cat_path or '(空)'}")
            except Exception as e:
                print(f"  读取类目失败: {e}")
                cat_path = ""
            try:
                sz_page = self.context.new_page()
                sz_page.goto("https://erp.91miaoshou.com/pddkj/move_collect/template_management/sizeChart",
                             wait_until="domcontentloaded")
                time.sleep(4)
                from utils.sizetable_creator import create_sizetable_for_style
                sz_ok = create_sizetable_for_style(sz_page, style_name, cat_path)
                sz_page.close()
            except Exception as e:
                print(f"  创建尺码表异常: {e}")
                sz_ok = False
                try: sz_page.close()
                except: pass
            if sz_ok:
                time.sleep(1)
                self.page.bring_to_front()
                # 点同步刷新尺码表列表
                try:
                    self.page.locator('button, span, a, div').filter(has_text='同步').first.click(timeout=3000)
                    time.sleep(2)
                except:
                    pass
                select_container = self.page.locator(".size-template-select-container").nth(index)
                try:
                    select_container.wait_for(state="visible", timeout=5000)
                except:
                    print(f"  警告: 尺码表选择器{index+1}不可见，重试中")
                    self.page.bring_to_front()
                    time.sleep(2)
                    select_container = self.page.locator(".size-template-select-container").nth(index)
                select_container.click()
                time.sleep(1.5)
                search_input = select_container.locator("input").first
                if search_input.is_visible():
                    search_input.click()
                    time.sleep(0.2)
                self.page.keyboard.press("Control+A")
                time.sleep(0.1)
                self.page.keyboard.type(style_name)
                time.sleep(1.2)
                # JS点击搜索结果
                clicked = self.page.evaluate(f"""(name) => {{
                    const all = document.querySelectorAll('li, [class*="dropdown-item"]');
                    for (const item of all) {{
                        if ((item.innerText||'').includes(name) && item.getBoundingClientRect().height>10) {{
                            item.click(); return true;
                        }}
                    }}
                    return false;
                }}""", style_name)
                if not clicked:
                    print(f"  警告: JS未找到搜索结果，尝试keyboard Enter")
                    self.page.keyboard.press("Enter")
                time.sleep(0.5)
                print(f"  尺码表{index+1}: {style_name} (已创建)")
            else:
                print(f"  尺码表{index+1}: 创建失败")
    
    def _check_key_display_parts(self, top_name: str, bottom_name: str):
        """勾选重点展示部件：多选下拉，点选项勾选"""
        print(f"  勾选重点展示部件: {top_name}, {bottom_name}")
        
        # 1. 搜placeholder："请选择其中1个重点部件" — 优先查input属性
        clicked = self.page.evaluate("""() => {
            // 策略1：找input/textarea的placeholder属性
            const inputs = document.querySelectorAll('input, textarea');
            for (const inp of inputs) {
                const ph = (inp.placeholder || inp.getAttribute('placeholder') || '');
                if (ph.includes('请选择其中')) {
                    // 往上找可点击的el-select容器
                    let p = inp;
                    for (let i = 0; i < 8; i++) {
                        if (p.classList.contains('el-select') || p.classList.contains('jx-select')) {
                            p.click();
                            return 'clicked_el_select';
                        }
                        p = p.parentElement;
                        if (!p) break;
                    }
                    inp.click();
                    return 'clicked_input';
                }
            }
            // 策略2：innerText兜底（排除html/body等根元素）
            const all = document.querySelectorAll('.jx-dialog *, .el-dialog *');
            for (const el of all) {
                if (el.tagName === 'HTML' || el.tagName === 'BODY') continue;
                const t = (el.innerText || '').trim();
                if (t === '请选择其中1个重点部件给到用户参考') {
                    // 往上找select
                    let p = el;
                    for (let i = 0; i < 8; i++) {
                        if (!p || p.tagName === 'BODY') break;
                        const s = p.querySelector('.el-select, input[readonly]');
                        if (s) { s.click(); return 'clicked_parent_select'; }
                        p = p.parentElement;
                    }
                    el.click();
                    return 'clicked_fallback';
                }
            }
            return 'not_found';
        }""")
        print(f"  [placeholder搜索] {clicked}")
        
        if clicked == 'not_found':
            print("  警告: 未能点击重点展示部件")
            return
        
        time.sleep(1)
        
        # 3. 点击下拉选项 — 搜所有可见的下拉列表
        for name in [top_name, bottom_name]:
            result = self.page.evaluate("""(n) => {
                // 找所有可见的下拉容器（不限class）
                const allDds = document.querySelectorAll('[class*=dropdown], [class*=popper], [role="listbox"]');
                for (const dd of allDds) {
                    const r = dd.getBoundingClientRect();
                    if (r.height < 20) continue;
                    const items = dd.querySelectorAll('li, .el-select-dropdown__item, [role="option"]');
                    for (const item of items) {
                        if ((item.innerText||'').includes(n) && item.getBoundingClientRect().height > 5) {
                            const isChecked = item.querySelector('.el-icon-check, [class*=checked], [class*=selected], .is-checked, .active');
                            if (isChecked) return 'already_checked';
                            item.click();
                            return 'clicked';
                        }
                    }
                }
                return 'not_in_list';
            }""", name)
            print(f"  [{name}]: {result}")
            time.sleep(0.3)
        
        self.page.keyboard.press("Escape")
        time.sleep(0.3)
    
    def _get_small_dialog(self):
        """获取批量设置小弹窗（排除创建产品大弹窗）"""
        result = self.page.evaluate("""
            () => {
                const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                let dialogs = [];
                all.forEach(d => {
                    const rect = d.getBoundingClientRect();
                    if (rect.width > 100 && rect.height > 50) {
                        dialogs.push({w: rect.width, h: rect.height});
                    }
                });
                dialogs.sort((a, b) => b.w - a.w);
                return dialogs.length >= 2;
            }
        """)
        return result
    
    def _get_small_dialog_by_title(self, title_keyword: str):
        """通过标题关键词找到批量设置小弹窗的JS对象"""
        return self.page.evaluate("""
            (keyword) => {
                const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                for (const d of all) {
                    // 找标题
                    const titleEl = d.querySelector('.jx-dialog__title, .el-dialog__title, [class*="title"]');
                    if (titleEl && titleEl.innerText && titleEl.innerText.includes(keyword)) {
                        return d;
                    }
                    // 兜底：检查弹窗内所有文字
                    if (d.innerText && d.innerText.includes(keyword)) {
                        const rect = d.getBoundingClientRect();
                        // 小弹窗宽度不超过800
                        if (rect.width < 800 && rect.width > 200) {
                            return d;
                        }
                    }
                }
                return null;
            }
        """, title_keyword)
    
    def _get_dialog_inputs_ordered(self, dialog_keyword: str = "批量"):
        """通过aria-label关键词找到批量弹窗，返回所有可见输入框"""
        return self.page.evaluate("""
            (keyword) => {
                // 优先通过aria-label找批量弹窗（只找可见的）
                const all = document.querySelectorAll('[role="dialog"]');
                let targetDlg = null;
                for (const d of all) {
                    const label = d.getAttribute('aria-label') || '';
                    if (label.includes(keyword)) {
                        const rect = d.getBoundingClientRect();
                        // 只考虑可见的弹窗（宽度>0）
                        if (rect.width > 100) {
                            targetDlg = d;
                            break;
                        }
                    }
                }
                // 兜底：找宽度小于800的弹窗
                if (!targetDlg) {
                    const allDlg = document.querySelectorAll('.jx-dialog, .el-dialog');
                    for (const d of allDlg) {
                        const rect = d.getBoundingClientRect();
                        if (rect.width >= 200 && rect.width <= 800 && rect.height > 100) {
                            targetDlg = d;
                            break;
                        }
                    }
                }
                if (!targetDlg) return [];
                
                const result = [];
                const inputs = targetDlg.querySelectorAll('input');
                inputs.forEach(inp => {
                    const r = inp.getBoundingClientRect();
                    if (r.width < 30 || r.height < 15) return;
                    if (inp.type === 'radio' || inp.type === 'checkbox' || inp.type === 'hidden') return;
                    result.push({
                        x: Math.round(r.left + 15),
                        y: Math.round(r.top + r.height/2),
                        top: r.top,
                        left: r.left,
                        type: inp.type,
                        value: inp.value
                    });
                });
                result.sort((a, b) => {
                    const ydiff = a.top - b.top;
                    if (Math.abs(ydiff) < 20) return a.left - b.left;
                    return ydiff;
                });
                return result;
            }
        """, dialog_keyword)
    
    def _click_dialog_button(self, btn_text: str, dialog_keyword: str = "批量"):
        """点击批量弹窗中的按钮（通过aria-label定位弹窗）"""
        return self.page.evaluate("""
            ({btnText, keyword}) => {
                const all = document.querySelectorAll('[role="dialog"]');
                let targetDlg = null;
                for (const d of all) {
                    const label = d.getAttribute('aria-label') || '';
                    if (label.includes(keyword)) {
                        const rect = d.getBoundingClientRect();
                        // 只考虑可见的弹窗（宽度>100）
                        if (rect.width > 100) {
                            targetDlg = d;
                            break;
                        }
                    }
                }
                if (!targetDlg) {
                    // 兜底找小弹窗
                    const allDlg = document.querySelectorAll('.jx-dialog, .el-dialog');
                    for (const d of allDlg) {
                        const rect = d.getBoundingClientRect();
                        if (rect.width >= 200 && rect.width <= 800 && rect.height > 100) {
                            targetDlg = d;
                            break;
                        }
                    }
                }
                if (!targetDlg) return false;
                
                const btns = targetDlg.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.innerText.trim() === btnText) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }
        """, {"btnText": btn_text, "keyword": dialog_keyword})
    
    def _get_select_input_by_label(self, label_text: str):
        """找标签同行的下拉输入框（jx-select）"""
        return self.page.evaluate("""
            (labelText) => {
                const all = document.querySelectorAll('[role="dialog"], .jx-dialog, .el-dialog, .jx-message-box');
                let dialogs = [];
                all.forEach(d => {
                    const rect = d.getBoundingClientRect();
                    if (rect.width > 100 && rect.height > 50) {
                        dialogs.push({el: d, w: rect.width});
                    }
                });
                dialogs.sort((a, b) => b.w - a.w);
                if (dialogs.length < 2) return null;
                const dlg = dialogs[1].el;
                
                let targetY = 0;
                const spans = dlg.querySelectorAll('span, label, div');
                for (const s of spans) {
                    if (s.innerText && s.innerText.trim() === labelText) {
                        const r = s.getBoundingClientRect();
                        targetY = r.top + r.height / 2;
                        break;
                    }
                }
                if (!targetY) return null;
                
                // 找同行的jx-select input（type=text，可点击展开下拉）
                const inputs = dlg.querySelectorAll('input[type="text"]');
                let best = null;
                for (const inp of inputs) {
                    const r = inp.getBoundingClientRect();
                    if (r.width < 30) continue;
                    const dist = Math.abs((r.top + r.height/2) - targetY);
                    if (dist < 30 && (!best || dist < best.dist)) {
                        best = {
                            x: Math.round(r.left + 20),
                            y: Math.round(r.top + r.height/2),
                            dist: dist
                        };
                    }
                }
                return best;
            }
        """, label_text)
    
    def _select_dropdown(self, input_pos, option_text: str):
        """点击下拉输入框，选择指定选项"""
        self.page.mouse.click(input_pos['x'], input_pos['y'])
        time.sleep(0.4)
        
        selected = self.page.evaluate("""
            (optText) => {
                const all = document.querySelectorAll('*');
                for (const el of all) {
                    if (el.children.length === 0 && el.innerText && el.innerText.trim() === optText) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 20 && rect.height > 10) {
                            el.click();
                            return true;
                        }
                    }
                }
                return false;
            }
        """, option_text)
        time.sleep(0.3)
        return selected
    
    def _batch_set_price(self, field_name: str, price: float):
        """批量设置价格类字段（供货价、建议售价）"""
        # 找到批量按钮
        batch_pos = self.page.evaluate(f"""
            () => {{
                const all = document.querySelectorAll('.jx-dialog *');
                let bestEl = null;
                let smallestArea = 9999999;
                // 找包含字段名的最小元素（最内层）
                for (const el of all) {{
                    if (el.innerText && el.innerText.includes('{field_name}')) {{
                        const r = el.getBoundingClientRect();
                        const area = r.width * r.height;
                        if (area > 100 && area < smallestArea) {{
                            // 里面要有批量按钮
                            const btns = el.querySelectorAll('button');
                            let hasBatch = false;
                            for (const btn of btns) {{
                                if (btn.innerText.trim() === '批量') {{ hasBatch = true; break; }}
                            }}
                            if (hasBatch) {{
                                smallestArea = area;
                                bestEl = el;
                            }}
                        }}
                    }}
                }}
                if (!bestEl) return null;
                const btns = bestEl.querySelectorAll('button');
                for (const btn of btns) {{
                    if (btn.innerText.trim() === '批量') {{
                        btn.scrollIntoView({{block: 'center'}});
                        const rect = btn.getBoundingClientRect();
                        return {{
                            x: Math.round(rect.left + rect.width/2),
                            y: Math.round(rect.top + rect.height/2)
                        }};
                    }}
                }}
                return null;
            }}
        """)
        
        if not batch_pos:
            print(f"  警告: 未找到 {field_name} 批量按钮")
            return False
        
        print(f"  [调试] {field_name} 批量按钮位置: {batch_pos}")
        
        # 先滚动到按钮位置
        self.page.evaluate("""
            (y) => {
                window.scrollTo(0, y - 200);
            }
        """, batch_pos['y'])
        time.sleep(0.3)
        
        self.page.mouse.click(batch_pos['x'], batch_pos['y'])
        time.sleep(1.2)  # 等弹窗完全渲染
        
        # 找价格输入框（弹窗里第一个可输入框）
        # 【调试】打印所有弹窗信息
        all_dialogs = self.page.evaluate("""
            () => {
                const result = [];
                const all = document.querySelectorAll('[role="dialog"]');
                all.forEach((d, i) => {
                    const r = d.getBoundingClientRect();
                    const z = parseInt(window.getComputedStyle(d).zIndex) || 0;
                    const label = d.getAttribute('aria-label') || '';
                    const inputs = d.querySelectorAll('input');
                    result.push({
                        idx: i,
                        label: label.substring(0, 20),
                        w: Math.round(r.width),
                        z: z,
                        inputs: inputs.length
                    });
                });
                return result;
            }
        """)
        print(f"  [调试] 所有弹窗: {all_dialogs}")
        
        inputs = self._get_dialog_inputs_ordered(f"批量修改{field_name}")
        print(f"  [调试] {field_name} 弹窗输入框数: {len(inputs)}")
        if not inputs:
            print(f"  警告: 未找到 {field_name} 价格输入框")
            self.page.keyboard.press("Escape")
            time.sleep(0.3)
            return False
        
        price_pos = inputs[0]
        
        # 输入价格
        self.page.mouse.click(price_pos['x'], price_pos['y'])
        time.sleep(0.15)
        self.page.keyboard.press("Control+A")
        time.sleep(0.1)
        self.page.keyboard.type(str(price))
        time.sleep(0.2)
        
        # 点击确定
        self._click_dialog_button("确定")
        print(f"  {field_name} 批量设置: {price}")
        return True
    
    def _batch_set_sku_class(self, class_type: str, quantity: int = 1):
        """批量设置SKU分类
        class_type: single(单品) / multi_pack(同款多件装) / mixed_set(混合套装)
        quantity: 件数（分类旁边的数量）
        """
        class_name_map = {
            "single": "单品",
            "multi_pack": "同款多件装",
            "mixed_set": "混合套装"
        }
        class_name = class_name_map.get(class_type, class_type)
        
        # 找到批量按钮
        batch_pos = self.page.evaluate("""
            () => {
                const all = document.querySelectorAll('.jx-dialog *');
                let bestEl = null;
                let smallestArea = 9999999;
                // 找包含SKU分类的最小元素（最内层）
                for (const el of all) {
                    if (el.innerText && el.innerText.includes('SKU分类')) {
                        const r = el.getBoundingClientRect();
                        const area = r.width * r.height;
                        if (area > 100 && area < smallestArea) {
                            const btns = el.querySelectorAll('button');
                            let hasBatch = false;
                            for (const btn of btns) {
                                if (btn.innerText.trim() === '批量') { hasBatch = true; break; }
                            }
                            if (hasBatch) {
                                smallestArea = area;
                                bestEl = el;
                            }
                        }
                    }
                }
                if (!bestEl) return null;
                const btns = bestEl.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.innerText.trim() === '批量') {
                        btn.scrollIntoView({block: 'center'});
                        const rect = btn.getBoundingClientRect();
                        return {
                            x: Math.round(rect.left + rect.width/2),
                            y: Math.round(rect.top + rect.height/2)
                        };
                    }
                }
                return null;
            }
        """)
        
        if not batch_pos:
            print("  警告: 未找到 SKU分类 批量按钮")
            return False
        
        self.page.mouse.click(batch_pos['x'], batch_pos['y'])
        time.sleep(0.8)
        
        # 获取所有输入框（按位置排序）
        inputs = self._get_dialog_inputs_ordered("SKU分类")
        print(f"  弹窗输入框数量: {len(inputs)}")
        for i, inp in enumerate(inputs):
            print(f"    [{i}] type={inp['type']} pos=({inp['x']},{inp['y']}) value='{inp['value']}'")
        
        if len(inputs) < 2:
            print("  警告: 输入框数量不足")
            self.page.keyboard.press("Escape")
            return False
        
        # 1. 选择分类（第0个input是分类下拉）
        class_input = inputs[0]
        self._select_dropdown(class_input, class_name)
        time.sleep(0.6)
        
        # 2. 填分类旁边的数量（第1个input）
        qty_input = inputs[1]
        self.page.mouse.click(qty_input['x'], qty_input['y'])
        time.sleep(0.15)
        self.page.keyboard.press("Control+A")
        time.sleep(0.1)
        self.page.keyboard.type(str(quantity))
        time.sleep(0.2)
        
        # 3. 填单位（第2个input，下拉选择，统一选"件"）
        unit_input = inputs[2]
        self._select_dropdown(unit_input, "件")
        time.sleep(0.5)
        
        # 重新获取input（DOM可能变化了）
        inputs = self._get_dialog_inputs_ordered("SKU分类")
        print(f"  [调试] 选完分类后输入框数: {len(inputs)}")
        for i, inp in enumerate(inputs):
            print(f"    [{i}] pos=({inp['x']},{inp['y']}) value='{inp['value']}'")
        
        # 4. 分情况处理（通过label文字定位，不依赖索引）
        if class_name == "单品":
            # 单品：共计内含填1
            total_pos = self._get_select_input_by_label("共计内含")
            if total_pos:
                self.page.evaluate("""
                    ({x, y, val}) => {
                        let el = document.elementFromPoint(x, y);
                        while (el && el.tagName !== 'INPUT') {
                            el = el.querySelector('input') || el.firstElementChild;
                        }
                        if (el && el.tagName === 'INPUT') {
                            const nativeSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                            nativeSetter.call(el, val);
                            el.dispatchEvent(new Event('input', {bubbles: true}));
                            el.dispatchEvent(new Event('change', {bubbles: true}));
                        }
                    }
                """, {"x": total_pos['x'], "y": total_pos['y'], "val": "1"})
                print(f"  共计内含已填: 1")
            else:
                print("  警告: 未找到共计内含输入框")
            time.sleep(0.3)
        
        elif class_name == "同款多件装":
            # 同款多件装：是否独立包装选否 + 共计内含填数量
            # 是否独立包装：第二排最左边的下拉框（索引3）
            inputs = self._get_dialog_inputs_ordered("SKU分类")
            pack_pos = inputs[3] if len(inputs) > 3 else None
            
            if pack_pos:
                self._select_dropdown(pack_pos, "不是独立包装")
            else:
                print("  警告: 未找到是否独立包装下拉框")
            time.sleep(0.4)
            
            total_pos = self._get_select_input_by_label("共计内含")
            if total_pos:
                self.page.evaluate("""
                    ({x, y, val}) => {
                        let el = document.elementFromPoint(x, y);
                        while (el && el.tagName !== 'INPUT') {
                            el = el.querySelector('input') || el.firstElementChild;
                        }
                        if (el && el.tagName === 'INPUT') {
                            const nativeSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                            nativeSetter.call(el, val);
                            el.dispatchEvent(new Event('input', {bubbles: true}));
                            el.dispatchEvent(new Event('change', {bubbles: true}));
                        }
                    }
                """, {"x": total_pos['x'], "y": total_pos['y'], "val": str(quantity)})
                print(f"  共计内含已填: {quantity}")
            else:
                print("  警告: 未找到共计内含输入框")
            time.sleep(0.3)
        
        elif class_name == "混合套装":
            # 混合套装：是否独立包装选否
            # 先调试：打印所有包含包装的文字
            debug_info = self.page.evaluate("""
                () => {
                    const all = document.querySelectorAll('[role="dialog"], .jx-dialog');
                    let dlg = null;
                    for (const d of all) {
                        const r = d.getBoundingClientRect();
                        if (r.width > 100 && r.width < 1200) { dlg = d; break; }
                    }
                    if (!dlg) return {error: 'no dialog found'};
                    
                    const texts = [];
                    const spans = dlg.querySelectorAll('span, label, div');
                    for (const s of spans) {
                        if (s.innerText && s.innerText.includes('包装')) {
                            const r = s.getBoundingClientRect();
                            if (r.width > 5 && r.height > 5) {
                                texts.push({text: s.innerText.trim(), x: r.left, y: r.top, w: r.width, h: r.height});
                            }
                        }
                    }
                    return {dialogW: dlg.getBoundingClientRect().width, texts: texts};
                }
            """)
            print(f"  [调试] 包装相关label: {debug_info}")
            
            pack_pos = self.page.evaluate("""
                () => {
                    const all = document.querySelectorAll('[role="dialog"], .jx-dialog');
                    let dlg = null;
                    for (const d of all) {
                        const r = d.getBoundingClientRect();
                        if (r.width > 100 && r.width < 1200) { dlg = d; break; }
                    }
                    if (!dlg) return null;
                    
                    let targetY = 0;
                    const spans = dlg.querySelectorAll('span, label, div');
                    for (const s of spans) {
                        if (s.innerText && s.innerText.includes('独立包装')) {
                            const r = s.getBoundingClientRect();
                            if (r.width > 10 && r.height > 10) {
                                targetY = r.top + r.height / 2;
                                break;
                            }
                        }
                    }
                    if (!targetY) return null;
                    
                    const inputs = dlg.querySelectorAll('input[type="text"]');
                    let best = null;
                    for (const inp of inputs) {
                        const r = inp.getBoundingClientRect();
                        if (r.width < 30) continue;
                        const dist = Math.abs((r.top + r.height/2) - targetY);
                        if (dist < 30 && (!best || dist < best.dist)) {
                            best = {x: Math.round(r.left + 20), y: Math.round(r.top + r.height/2), dist: dist};
                        }
                    }
                    return best;
                }
            """)
            if pack_pos:
                print(f"  [调试] 是否独立包装位置: {pack_pos}")
                self._select_dropdown(pack_pos, "不是独立包装")
            else:
                print("  警告: 未找到是否独立包装下拉框")
            time.sleep(0.4)
        
        # 5. 点击确定
        self._click_dialog_button("确定", "SKU分类")
        print(f"  SKU分类批量设置: {class_name} x{quantity}")
        return True
    
    def _batch_set_field(self, field_name: str, value: str):
        """批量设置SKU表格某一列的值（兼容旧接口）"""
        if field_name in ("供货价", "建议售价"):
            return self._batch_set_price(field_name, float(value))
        elif field_name == "SKU分类":
            return self._batch_set_sku_class(value)
        else:
            print(f"  警告: 不支持的批量字段: {field_name}")
            return False
    
    def _batch_set_size(self, length: float, width: float, height: float):
        """批量设置尺寸（长宽高）"""
        # 找到尺寸列的批量按钮（复用供货价逻辑，只横向滚动）
        batch_pos = self.page.evaluate("""
            () => {
                const all = document.querySelectorAll('.jx-dialog *');
                let bestEl = null;
                let smallestArea = 9999999;
                // 找包含"尺寸"且有批量按钮的最小单元格
                for (const el of all) {
                    if (el.innerText && el.innerText.includes('尺寸')) {
                        const r = el.getBoundingClientRect();
                        const area = r.width * r.height;
                        if (area > 100 && area < smallestArea) {
                            const btns = el.querySelectorAll('button');
                            let hasBatch = false;
                            for (const btn of btns) {
                                if (btn.innerText.trim() === '批量') { hasBatch = true; break; }
                            }
                            if (hasBatch) {
                                smallestArea = area;
                                bestEl = el;
                            }
                        }
                    }
                }
                if (!bestEl) return null;
                const btns = bestEl.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.innerText.trim() === '批量') {
                        // 只横向滚动到视口内，垂直方向不动
                        btn.scrollIntoView({inline: 'center', block: 'nearest'});
                        const rect = btn.getBoundingClientRect();
                        return {
                            x: Math.round(rect.left + rect.width/2),
                            y: Math.round(rect.top + rect.height/2)
                        };
                    }
                }
                return null;
            }
        """)
        
        if not batch_pos:
            print("  警告: 未找到尺寸批量按钮")
            return False
        
        print(f"  [调试] 尺寸 批量按钮位置: {batch_pos}")
        
        # 点击批量按钮
        self.page.mouse.click(batch_pos['x'], batch_pos['y'])
        time.sleep(1.0)
        
        # 获取弹窗里的输入框（长宽高三个）
        inputs = self._get_dialog_inputs_ordered("尺寸")
        print(f"  [调试] 尺寸弹窗输入框数: {len(inputs)}")
        
        if len(inputs) < 3:
            print("  警告: 尺寸弹窗输入框不足3个")
            return False
        
        # 按顺序填：长、宽、高
        for i, val in enumerate([length, width, height]):
            inp = inputs[i]
            self.page.evaluate("""
                ({x, y, val}) => {
                    let el = document.elementFromPoint(x, y);
                    while (el && el.tagName !== 'INPUT') {
                        el = el.querySelector('input') || el.firstElementChild;
                    }
                    if (el && el.tagName === 'INPUT') {
                        const nativeSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                        nativeSetter.call(el, String(val));
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                }
            """, {"x": inp['x'], "y": inp['y'], "val": val})
            time.sleep(0.1)
        
        # 点击确定
        self._click_dialog_button("确定", "尺寸")
        print(f"  尺寸批量设置: {length} x {width} x {height}")
        time.sleep(0.3)
        return True
    
    def _batch_set_weight(self, size_details: dict, quantity: int = 1):
        """批量设置重量（按尺码逐个设置）
        size_details: {尺码名: {净重(g): 值, ...}}
        """
        # 找到毛重列的批量按钮
        batch_pos = self.page.evaluate("""
            () => {
                const all = document.querySelectorAll('.jx-dialog *');
                let bestEl = null;
                let smallestArea = 9999999;
                for (const el of all) {
                    if (el.innerText && el.innerText.includes('毛重')) {
                        const r = el.getBoundingClientRect();
                        const area = r.width * r.height;
                        if (area > 100 && area < smallestArea) {
                            const btns = el.querySelectorAll('button');
                            let hasBatch = false;
                            for (const btn of btns) {
                                if (btn.innerText.trim() === '批量') { hasBatch = true; break; }
                            }
                            if (hasBatch) {
                                smallestArea = area;
                                bestEl = el;
                            }
                        }
                    }
                }
                if (!bestEl) return null;
                const btns = bestEl.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.innerText.trim() === '批量') {
                        btn.scrollIntoView({inline: 'center', block: 'nearest'});
                        const rect = btn.getBoundingClientRect();
                        return {
                            x: Math.round(rect.left + rect.width/2),
                            y: Math.round(rect.top + rect.height/2)
                        };
                    }
                }
                return null;
            }
        """)
        
        if not batch_pos:
            print("  警告: 未找到毛重批量按钮")
            return False
        
        print(f"  [调试] 毛重 批量按钮位置: {batch_pos}")
        
        # 点击批量按钮打开弹窗
        self.page.mouse.click(batch_pos['x'], batch_pos['y'])
        time.sleep(1.2)
        
        # 1. 选择「指定规格的SKU」
        spec_radio = self.page.evaluate("""
            () => {
                const dlg = document.querySelector('[aria-label*="批量修改毛重"], [aria-label*="重量"]');
                if (!dlg) return null;
                const radios = dlg.querySelectorAll('input[type="radio"]');
                for (const r of radios) {
                    const label = r.closest('label') || r.parentElement;
                    if (label && label.innerText && label.innerText.includes('指定规格')) {
                        const rect = r.getBoundingClientRect();
                        return {x: rect.left + 5, y: rect.top + rect.height/2};
                    }
                }
                return null;
            }
        """)
        if spec_radio:
            self.page.mouse.click(spec_radio['x'], spec_radio['y'])
            print("  已选择: 指定规格的SKU")
            time.sleep(0.3)
        else:
            print("  警告: 未找到指定规格的SKU选项")
        
        # 2. 颜色勾选「全选」
        color_all = self.page.evaluate("""
            () => {
                const dlg = document.querySelector('[aria-label*="批量修改重量"], [aria-label*="毛重"]');
                if (!dlg) return null;
                const checkboxes = dlg.querySelectorAll('input[type="checkbox"]');
                for (const cb of checkboxes) {
                    const label = cb.closest('label') || cb.parentElement;
                    if (label && label.innerText && label.innerText.trim() === '全选') {
                        const rect = cb.getBoundingClientRect();
                        // 上面的是颜色全选，下面的是尺码全选
                        if (rect.top < 550) {
                            return {x: rect.left + 5, y: rect.top + rect.height/2};
                        }
                    }
                }
                return null;
            }
        """)
        if color_all:
            self.page.mouse.click(color_all['x'], color_all['y'])
            print("  颜色已勾选: 全选")
            time.sleep(0.2)
        else:
            print("  警告: 未找到颜色全选复选框")
        
        # 3. 滚动到弹窗底部，显示尺码区域
        self.page.evaluate("""
            () => {
                const dlg = document.querySelector('[aria-label*="批量修改重量"], [aria-label*="毛重"]');
                if (dlg) {
                    dlg.scrollTop = dlg.scrollHeight;
                }
            }
        """)
        time.sleep(0.3)
        
        # 4. 逐个尺码设置重量
        for size_name, detail in size_details.items():
            size_str = str(size_name)
            net_weight = detail.get("净重(g)", 0)
            if not net_weight:
                print(f"  跳过尺码 {size_str}: 无净重数据")
                continue
            
            # 公式：单重 × 件数 + 10 + 10 × 件数
            final_weight = int(net_weight * quantity + 10 + 10 * quantity)
            
            print(f"  处理尺码: {size_str}, 净重: {net_weight}g, 最终: {final_weight}g")
            
            # 4.1 取消所有尺码勾选
            self.page.evaluate("""
                () => {
                    const dlg = document.querySelector('[aria-label*="批量修改重量"], [aria-label*="毛重"]');
                    if (!dlg) return;
                    const cbs = dlg.querySelectorAll('input[type="checkbox"]');
                    for (const cb of cbs) {
                        const rect = cb.getBoundingClientRect();
                        // 只处理尺码区域的（top > 600）
                        if (rect.top > 600 && cb.checked) {
                            cb.click();
                        }
                    }
                }
            """)
            time.sleep(0.2)
            
            # 4.2 勾选当前尺码
            size_checked = self.page.evaluate("""
                (sizeStr) => {
                    const dlg = document.querySelector('[aria-label*="批量修改重量"], [aria-label*="毛重"]');
                    if (!dlg) return false;
                    const cbs = dlg.querySelectorAll('input[type="checkbox"]');
                    for (const cb of cbs) {
                        const label = cb.closest('label') || cb.parentElement;
                        if (label && label.innerText && label.innerText.trim() === sizeStr) {
                            const rect = cb.getBoundingClientRect();
                            if (rect.top > 600) {
                                if (!cb.checked) cb.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }
            """, size_str)
            
            if not size_checked:
                print(f"  警告: 未找到尺码 {size_str}")
                continue
            
            time.sleep(0.2)
            
            # 4.3 找到「使用新重量」输入框（最上面第一个），填入重量
            weight_input = self.page.evaluate("""
                () => {
                    const dlg = document.querySelector('[aria-label*="批量修改重量"], [aria-label*="毛重"]');
                    if (!dlg) return null;
                    const inputs = dlg.querySelectorAll('input[type="text"]');
                    let topMost = null;
                    let minTop = 9999;
                    for (const inp of inputs) {
                        const r = inp.getBoundingClientRect();
                        if (r.width < 50) continue;
                        if (r.top < minTop) {
                            minTop = r.top;
                            topMost = {x: Math.round(r.left + 20), y: Math.round(r.top + r.height/2)};
                        }
                    }
                    return topMost;
                }
            """)
            
            if weight_input:
                self.page.evaluate("""
                    ({x, y, val}) => {
                        let el = document.elementFromPoint(x, y);
                        while (el && el.tagName !== 'INPUT') {
                            el = el.querySelector('input') || el.firstElementChild;
                        }
                        if (el && el.tagName === 'INPUT') {
                            const nativeSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                            nativeSetter.call(el, String(val));
                            el.dispatchEvent(new Event('input', {bubbles: true}));
                            el.dispatchEvent(new Event('change', {bubbles: true}));
                        }
                    }
                """, {"x": weight_input['x'], "y": weight_input['y'], "val": final_weight})
                print(f"  已填入重量: {final_weight}")
            else:
                print("  警告: 未找到使用新重量输入框")
                continue
            
            time.sleep(0.2)
            
            # 4.4 点击确定
            self._click_dialog_button("确定", "重量")
            time.sleep(0.3)
        
        # 关闭重量弹窗（点右上角×）
        self.page.evaluate("""
            () => {
                const dlg = document.querySelector('[aria-label*="批量修改重量"], [aria-label*="毛重"]');
                if (dlg) {
                    const closeBtn = dlg.querySelector('.jx-dialog__close, .el-dialog__close, [aria-label="close"]');
                    if (closeBtn) closeBtn.click();
                }
            }
        """)
        time.sleep(0.3)
        print("  重量批量设置完成")
        return True
