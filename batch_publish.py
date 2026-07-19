import functools
print = functools.partial(print, flush=True)
# -*- coding: utf-8 -*-
"""
批量上架主入口
从飞书多维表格读取待上架商品，逐个调用RPA上架，回填结果
"""
import os
import sys

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from config.settings import (
    MIAOSHOU_BASE_URL, RPA_HEADLESS, RPA_SLOW_MO,
    LOGIN_MODE, LOCAL_CHROME_USER_DATA, LOCAL_CHROME_PROFILE,
    RPA_USER_DATA_DIR, FEISHU_BASE_TOKEN, STYLE_LIBRARY_PATH,
    FEISHU_APP_ID, FEISHU_APP_SECRET
)
from data_source.excel_loader import load_styles_from_excel, get_style_by_name
from data_source.product_loader import FeishuProductLoader
from models.product import Product
from executors.rpa_publisher import RpaPublisherExecutor


def build_rpa_config():
    """构建RPA配置字典"""
    config = {
        "base_url": MIAOSHOU_BASE_URL,
        "headless": RPA_HEADLESS,
        "slow_mo": RPA_SLOW_MO,
    }
    if LOGIN_MODE == "local_chrome":
        config["user_data_dir"] = LOCAL_CHROME_USER_DATA
        config["profile_directory"] = LOCAL_CHROME_PROFILE
        config["channel"] = "chrome"
    elif LOGIN_MODE == "standalone":
        config["user_data_dir"] = RPA_USER_DATA_DIR
    return config


def build_product(data: dict, style_lib: list) -> tuple:
    """从飞书数据构建Product对象"""
    style_names = data.get("style_names", [])
    style_name = data.get("style_name", "")
    template_name = data.get("template_name", "")
    title = data.get("title", f"Product {style_name}")
    sku_quantity = data.get("sku_quantity", 1) or 1
    sku_class = data.get("sku_class", "单品") or "单品"
    
    # 从款式库查主款式
    style = get_style_by_name(style_lib, style_name)
    if not style:
        return None, f"找不到款式「{style_name}」"
    
    style.template_name = template_name
    
    # 混合套装：读取所有副款式
    all_extra_styles = []
    combo_type = "single"
    if sku_class == "混合套装" and len(style_names) >= 2:
        for sn in style_names[1:]:  # 第一个已经是main_style
            extra = get_style_by_name(style_lib, sn)
            if not extra:
                return None, f"找不到副款式「{sn}」"
            extra.template_name = template_name
            all_extra_styles.append(extra)
        combo_type = "suit"
        # 套装默认2件，用户填了就用用户的
        if sku_quantity <= 1:
            sku_quantity = 2
    
    # 构建颜色列表（带图片URL）
    colors = []
    for c in data.get("colors", []):
        image_urls = []
        for img in c.get("images", []):
            # 公网URL直接用字符串
            if isinstance(img, str):
                if img:
                    image_urls.append(img)
            elif isinstance(img, dict):
                url = img.get("url", "") or img.get("file_token", "")
                if url:
                    image_urls.append(url)
        if c.get("name"):
            colors.append({
                "name": c["name"],
                "image_urls": image_urls
            })
    
    # 构造Product
    product = Product(
        product_id=data.get("record_id", "P001"),
        main_style=style,
        combo_type=combo_type,
        sub_style=sub_style,
        title=title,
        colors=colors,
    )
    product.sku_quantity = sku_quantity
    product.sku_class_override = sku_class
    
    return product, None


def main():
    print("=" * 50)
    print("  TEMU全托管批量上架")
    print("=" * 50)
    print()
    
    # 加载款式库
    print("[1/4] 加载款式库Excel...")
    styles = load_styles_from_excel(STYLE_LIBRARY_PATH)
    print(f"  共 {len(styles)} 款")
    
    # 加载飞书数据
    print("\n[2/4] 从飞书读取待上架数据...")
    try:
        loader = FeishuProductLoader(
            base_token=FEISHU_BASE_TOKEN,
            excel_path=STYLE_LIBRARY_PATH
        )
        products_data = loader.load_pending_products()
        print(f"  找到 {len(products_data)} 个待上架商品")
    except Exception as e:
        print(f"  读取失败: {e}")
        print("  请检查lark-cli是否配置正确")
        print("  临时可用 test_from_csv.py 进行单款测试")
        return
    
    if not products_data:
        print("  没有待上架的商品")
        return
    
    # 逐个上架
    print(f"\n[3/4] 开始批量上架，共 {len(products_data)} 个")
    print("-" * 50)
    
    success_count = 0
    fail_count = 0
    
    for i, data in enumerate(products_data, 1):
        title = data.get("title", "未命名")
        record_id = data.get("record_id", "")
        print(f"\n[{i}/{len(products_data)}] {title}")
        
        # 标记上架中
        try:
            loader.update_product_status(record_id, "上架中")
        except:
            pass
        
        # 构建Product
        product, err = build_product(data, styles)
        if err:
            print(f"  [FAIL] 数据错误: {err}")
            try:
                loader.update_product_status(record_id, "上架失败", error=err)
            except:
                pass
            fail_count += 1
            continue
        
        # 每个产品新建浏览器实例，避免状态污染
        print("  初始化浏览器...")
        rpa_config = build_rpa_config()
        executor = RpaPublisherExecutor(rpa_config)
        
        # 执行上架
        try:
            result = executor.execute(product, auto_close=True, auto_submit=False)
            
            if result.get("success"):
                skc_id = result.get("data", {}).get("skc_id", "")
                print(f"  [OK] 上架成功, SKC: {skc_id}")
                try:
                    loader.update_product_status(record_id, "已上架", skc_id=skc_id)
                except:
                    pass
                success_count += 1
            else:
                err_msg = result.get("error", "未知错误")
                print(f"  [FAIL] 上架失败: {err_msg}")
                try:
                    loader.update_product_status(record_id, "上架失败", error=err_msg)
                except:
                    pass
                fail_count += 1
        except Exception as e:
            print(f"  [FAIL] 异常: {str(e)}")
            try:
                loader.update_product_status(record_id, "上架失败", error=str(e))
            except:
                pass
            fail_count += 1
        
        # 关闭浏览器
        try:
            executor.close()
        except:
            pass
    
    print("\n" + "=" * 50)
    print(f"  全部完成！成功 {success_count}，失败 {fail_count}")
    print("=" * 50)


if __name__ == "__main__":
    main()
