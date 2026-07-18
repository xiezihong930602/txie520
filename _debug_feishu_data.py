# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_source.product_loader import FeishuProductLoader
from config.settings import FEISHU_BASE_TOKEN, STYLE_LIBRARY_PATH

loader = FeishuProductLoader(
    base_token=FEISHU_BASE_TOKEN,
    excel_path=STYLE_LIBRARY_PATH
)

print("=== 商品链接表原始数据 ===")
products = loader.product_ds.list_records()
for i, p in enumerate(products):
    print(f"\n商品 {i+1}: {p.get('产品标题')}")
    print(f"  款式库表字段: {p.get('款式库表')}")
    print(f"  类型: {type(p.get('款式库表'))}")
    
    # 测试解析关联ID
    style_ids = loader._get_link_ids(p, "款式库表")
    print(f"  解析出的style_ids: {style_ids}")
    
    # 测试查款式名称
    if style_ids:
        name = loader._get_style_name(style_ids[0])
        print(f"  款式名称: '{name}'")
        
        # 直接看款式记录
        rec = loader.style_ds.get_record(style_ids[0])
        print(f"  款式记录所有字段: {list(rec.keys()) if rec else 'None'}")
        if rec:
            for k, v in rec.items():
                print(f"    {k}: {v}")

print("\n=== 最终load_pending_products结果 ===")
pending = loader.load_pending_products()
print(f"待上架数量: {len(pending)}")
for p in pending:
    print(f"  - {p.get('title')}: style_name='{p.get('style_name')}', 颜色数={len(p.get('colors', []))}")
