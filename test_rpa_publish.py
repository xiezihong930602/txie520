# RPA上架测试脚本
# 用法: python test_rpa_publish.py <款式名称> <模板名称> [SKU分类类型]
# SKU分类类型: single(单品,默认) / 2pack(2件装) / 3pack(3件装) / suit(套装)
# 示例: python test_rpa_publish.py "儿童拉毛卫衣" "男童圆领卫衣" 2pack

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_source.excel_loader import load_styles_from_excel, get_style_by_name
from models.product import Product
from executors.rpa_publisher import RpaPublisherExecutor
from config.settings import MIAOSHOU_BASE_URL


def main():
    if len(sys.argv) < 3:
        print("用法: python test_rpa_publish.py <款式名称> <模板名称>")
        print("示例: python test_rpa_publish.py \"儿童拉毛卫衣\" \"男童圆领卫衣\"")
        print()
        # 列出所有款式供参考
        excel_path = os.path.join(os.path.dirname(__file__), "款式库模板_v4_填尺码_最终版.xlsx")
        styles = load_styles_from_excel(excel_path)
        print(f"可选款式（共{len(styles)}款）:")
        for s in styles:
            print(f"  {s.style_id} - {s.style_name} ({s.category})")
        sys.exit(1)
    
    style_name = sys.argv[1]
    template_name = sys.argv[2]
    sku_class_type = sys.argv[3] if len(sys.argv) >= 4 else "single"  # 默认单品
    
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
        combo_type=sku_class_type,
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
        ],  # 测试颜色（白色配5张图）
    )
    
    print("=" * 50)
    print("商品信息:")
    print(f"  款式: {style.style_name} ({style.style_id})")
    print(f"  模板: {template_name}")
    print(f"  成本价: {style.cost_price}元")
    print(f"  供货价: {product.final_price}元")
    print(f"  净重: {product.final_net_weight}g")
    print(f"  尺码: {product.final_sizes}")
    print(f"  SKU分类: {product.final_sku_class}")
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
    result = executor.execute(product, auto_close=False)
    
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
