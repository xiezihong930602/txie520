# 从CSV读取测试数据的RPA上架脚本
# 用法：修改 测试数据.csv，然后运行 python test_from_csv.py

import sys
import os
import csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_source.excel_loader import load_styles_from_excel, get_style_by_name
from models.product import Product
from executors.rpa_publisher import RpaPublisherExecutor
from config.settings import MIAOSHOU_BASE_URL


def main():
    csv_path = os.path.join(os.path.dirname(__file__), "测试数据.csv")
    
    # 读取测试数据
    with open(csv_path, 'r', encoding='gbk') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        print("测试数据.csv 为空")
        sys.exit(1)
    
    row = rows[0]
    style_name = row['款式名称']
    template_name = row['模板名称']
    sku_class = row['SKU分类']
    sku_quantity = int(row['SKU数量'])
    
    # 1. 加载款式库
    excel_path = os.path.join(os.path.dirname(__file__), "款式库模板_v4_填尺码_最终版.xlsx")
    styles = load_styles_from_excel(excel_path)
    
    style = get_style_by_name(styles, style_name)
    if not style:
        print(f"错误: 找不到款式「{style_name}」")
        sys.exit(1)
    
    # 设置模板名（款式库不存，手动指定）
    style.template_name = template_name
    
    # 2. 构造商品对象
    product = Product(
        product_id=f"TEST-{style.style_id}",
        main_style=style,
        combo_type="single",  # 占位，用下面的override覆盖
        title=f"Test {style.style_name} Kids Clothing",
        colors=[
            {
                "name": "白色",
                "image_urls": [
                    "https://aka.doubaocdn.com/s/5wyU1wuoJ8",
                    "https://aka.doubaocdn.com/s/QfQp1wuoJ8",
                    "https://aka.doubaocdn.com/s/AFm31wuoJ5",
                    "https://aka.doubaocdn.com/s/sQUv1wuoJ6",
                    "https://aka.doubaocdn.com/s/UqTC1wuoJ6",
                ]
            },
        ],
    )
    # 覆盖SKU分类和数量
    product.sku_class_override = sku_class
    product.sku_quantity = sku_quantity
    
    print("=" * 50)
    print("测试数据:")
    print(f"  款式: {style.style_name} ({style.style_id})")
    print(f"  模板: {template_name}")
    print(f"  SKU分类: {sku_class}")
    print(f"  SKU数量: {sku_quantity}")
    print(f"  供货价: {product.final_price}元")
    print("=" * 50)
    
    # 3. 执行RPA上架
    print("\n开始执行RPA上架...")
    
    from config.settings import (RPA_HEADLESS, RPA_SLOW_MO, MIAOSHOU_BASE_URL,
                                 LOGIN_MODE, LOCAL_CHROME_USER_DATA, 
                                 LOCAL_CHROME_PROFILE, RPA_USER_DATA_DIR)
    
    rpa_config = {
        "base_url": MIAOSHOU_BASE_URL,
        "headless": RPA_HEADLESS,
        "slow_mo": RPA_SLOW_MO,
    }
    
    if LOGIN_MODE == "local_chrome":
        rpa_config["user_data_dir"] = LOCAL_CHROME_USER_DATA
        rpa_config["profile_directory"] = LOCAL_CHROME_PROFILE
        rpa_config["channel"] = "chrome"
        print("  [模式] 本地Chrome Profile模式")
    elif LOGIN_MODE == "standalone":
        rpa_config["user_data_dir"] = RPA_USER_DATA_DIR
        print("  [模式] 独立浏览器持久化目录")
    else:
        print("  [模式] storage_state 自动登录")
    
    executor = RpaPublisherExecutor(rpa_config)
    result = executor.execute(product, auto_close=False, auto_submit=False)
    
    # 4. 输出结果
    print("\n执行结果:")
    if result["success"]:
        print(f"  成功! SKC ID: {result['data'].get('skc_id')}")
    else:
        print(f"  失败: {result['error']}")
    
    # 保持浏览器打开，方便手动检查
    print("\n浏览器保持打开状态，检查完成后按回车键退出...")
    input()
    executor._close_browser()


if __name__ == "__main__":
    main()
