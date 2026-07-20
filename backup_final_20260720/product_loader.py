# -*- coding: utf-8 -*-
"""
从飞书多维表格读取完整的上架产品数据
整合商品链接、款式、模板、店铺、颜色明细
"""
import os
from typing import List, Dict, Any, Optional
from .feishu import FeishuDataSource
from .excel_loader import load_styles_from_excel, get_style_by_name
from models.product import Product
from models.style import Style


# 各表table_id
TABLE_PRODUCT = "tbl8vDRirTY5Cv3Y"    # 商品链接表
TABLE_COLOR = "tblxluGYXQyNK36g"      # 颜色明细表
TABLE_STYLE = "tblgsBQC5kMCaDr4"      # 款式库表
TABLE_TEMPLATE = "tbl8MDtm0ijDycp"   # 模板表
TABLE_SHOP = "tblcstU6w77Klawo"       # 店铺表


class FeishuProductLoader:
    """飞书产品数据加载器"""

    def __init__(self, base_token: str, excel_path: str):
        self.base_token = base_token
        self.work_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 各表数据源
        self.product_ds = FeishuDataSource(base_token, TABLE_PRODUCT)
        self.color_ds = FeishuDataSource(base_token, TABLE_COLOR)
        self.style_ds = FeishuDataSource(base_token, TABLE_STYLE)
        self.template_ds = FeishuDataSource(base_token, TABLE_TEMPLATE)
        self.shop_ds = FeishuDataSource(base_token, TABLE_SHOP)
        
        # 加载Excel款式库（查详细尺码重量等）
        self._style_list = load_styles_from_excel(excel_path)
        
        # 缓存
        self._style_cache = {}
        self._template_cache = {}
        self._shop_cache = {}
        self._color_cache = {}

    def _get_link_ids(self, record: dict, field: str) -> List[str]:
        """提取关联字段的record_id列表"""
        val = record.get(field, [])
        if not val:
            return []
        # 关联字段格式：[{"record_ids": ["xxx"], "table_id": "...", "text": "..."}]
        ids = []
        for item in val:
            if isinstance(item, dict):
                if "record_ids" in item:
                    ids.extend(item.get("record_ids", []))
                elif "id" in item:
                    ids.append(item.get("id", ""))
        return ids
    
    def _get_link_text(self, record: dict, field: str) -> str:
        """直接提取关联字段的显示文本（如模板名称、店铺名称），无需二次查表"""
        val = record.get(field, [])
        if not val or not isinstance(val, list):
            return ""
        for item in val:
            if isinstance(item, dict) and item.get("text"):
                return item["text"]
        return ""

    def _get_style_name(self, record_id: str) -> str:
        """根据款式record_id查款式名称"""
        if record_id in self._style_cache:
            return self._style_cache[record_id]
        rec = self.style_ds.get_record(record_id)
        name = rec.get("款式名称", "") if rec else ""
        self._style_cache[record_id] = name
        return name

    def _get_template_name(self, record_id: str) -> str:
        """根据模板record_id查模板名称"""
        if record_id in self._template_cache:
            return self._template_cache[record_id]
        rec = self.template_ds.get_record(record_id)
        name = rec.get("模板名称", "") if rec else ""
        self._template_cache[record_id] = name
        return name

    def _get_shop_name(self, record_id: str) -> str:
        """根据店铺record_id查店铺名称"""
        if record_id in self._shop_cache:
            return self._shop_cache[record_id]
        rec = self.shop_ds.get_record(record_id)
        name = rec.get("店铺名称", "") if rec else ""
        self._shop_cache[record_id] = name
        return name

    def _get_color_info(self, record_id: str) -> Dict[str, Any]:
        """根据颜色record_id查颜色详情"""
        if record_id in self._color_cache:
            return self._color_cache[record_id]
        rec = self.color_ds.get_record(record_id)
        if not rec:
            info = {"name": "", "images": []}
            self._color_cache[record_id] = info
            return info

        # 优先用公网URL字段（已转存的）
        url_text = rec.get("图片公网URL", "")
        images = []
        if url_text:
            images = [u.strip() for u in str(url_text).split("\n") if u.strip()]
        else:
            # 回退：用附件URL（可能鉴权失败）
            images = rec.get("商品主图", [])

        info = {
            "name": rec.get("颜色名称", ""),
            "images": images
        }
        self._color_cache[record_id] = info
        return info

    def load_pending_products(self) -> List[Dict[str, Any]]:
        """加载所有待上架的产品完整数据"""
        pending = self.product_ds.get_pending_records()
        products = []

        for rec in pending:
            # 基础信息
            product_data = {
                "record_id": rec.get("_record_id", ""),
                "title": rec.get("产品标题", ""),
                "sku_quantity": int(rec.get("SKU件数", 1) or 1),
                "sku_class": rec.get("SKU分类", ["单品"]),
            }
            # SKU分类是select数组，取第一个
            if isinstance(product_data["sku_class"], list) and product_data["sku_class"]:
                product_data["sku_class"] = product_data["sku_class"][0]
            
            # 关联款式（支持多选，混合套装用）
            style_ids = self._get_link_ids(rec, "款式库表")
            if not style_ids:
                style_ids = self._get_link_ids(rec, "关联款式")
            
            # 所有款式名称列表
            style_names = [self._get_style_name(sid) for sid in style_ids if sid]
            style_name = style_names[0] if style_names else ""  # 主款式

            # 关联模板：直接取关联字段显示文本（就是模板名称，无需二次查表）
            template_name = self._get_link_text(rec, "模板表 3")

            # 关联店铺：直接取关联字段显示文本（就是店铺名称，无需二次查表）
            shop_name = self._get_link_text(rec, "店铺表 3")

            # 颜色明细
            color_ids = self._get_link_ids(rec, "颜色明细")
            if not color_ids:
                color_ids = self._get_link_ids(rec, "颜色明细表")
            colors = []
            for cid in color_ids:
                cinfo = self._get_color_info(cid)
                if cinfo.get("name"):
                    colors.append(cinfo)
            
            # 从Excel款式库查详细信息
            style_info = None
            if style_name:
                style_info = get_style_by_name(self._style_list, style_name)
            
            product_data.update({
                "style_name": style_name,
                "style_names": style_names,
                "template_name": template_name,
                "shop_name": shop_name,
                "colors": colors,
                "style_info": style_info
            })
            products.append(product_data)

        return products

    def update_product_status(self, record_id: str, status: str, 
                              skc_id: str = "", error: str = "") -> bool:
        """更新产品上架状态"""
        ok = self.product_ds.update_status(record_id, status)
        if skc_id:
            self.product_ds.update_skc_id(record_id, skc_id)
        if error:
            self.product_ds.update_error(record_id, error)
        return ok
