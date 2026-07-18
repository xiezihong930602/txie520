# 商品数据模型
from dataclasses import dataclass, field
from typing import List, Optional
from .style import Style


@dataclass
class Product:
    """商品数据结构"""
    product_id: str                  # 商品编号
    main_style: Style                # 主款式
    combo_type: str                  # 组合类型：single/2pack/suit/3pack
    title: str                       # 商品标题(英文)
    image_urls: List[str] = field(default_factory=list)  # 主图URL
    colors: List[str] = field(default_factory=list)      # 颜色列表
    sizes: Optional[List[str]] = None  # 尺码（为空则用款式默认）
    sub_style: Optional[Style] = None  # 副款式（套装用）
    
    # 可覆盖字段（为空则自动计算）
    price_override: Optional[float] = None     # 供货价覆盖
    net_weight_override: Optional[float] = None  # 净重覆盖
    gross_weight_override: Optional[float] = None # 毛重覆盖
    sku_class_override: Optional[str] = None   # SKU分类覆盖
    
    # 结果字段
    status: str = "pending"         # pending/running/success/failed
    skc_id: Optional[str] = None    # 上架成功后的SKC ID
    error_msg: Optional[str] = None # 错误信息
    
    @property
    def final_price(self) -> float:
        """最终供货价：覆盖值优先，否则成本×2"""
        if self.price_override is not None:
            return self.price_override
        from config.settings import PRICE_MULTIPLIER
        base_cost = self.main_style.cost_price
        if self.combo_type == "2pack":
            base_cost *= 2
        elif self.combo_type == "3pack":
            base_cost *= 3
        elif self.combo_type == "suit" and self.sub_style:
            base_cost += self.sub_style.cost_price
        return round(base_cost * PRICE_MULTIPLIER, 2)
    
    @property
    def final_net_weight(self) -> float:
        """最终净重"""
        if self.net_weight_override is not None:
            return self.net_weight_override
        w = self.main_style.net_weight
        if self.combo_type == "2pack":
            w *= 2
        elif self.combo_type == "3pack":
            w *= 3
        elif self.combo_type == "suit" and self.sub_style:
            w += self.sub_style.net_weight
        return w
    
    @property
    def final_gross_weight(self) -> float:
        """最终毛重"""
        if self.gross_weight_override is not None:
            return self.gross_weight_override
        w = self.main_style.gross_weight
        if self.combo_type == "2pack":
            w *= 2
        elif self.combo_type == "3pack":
            w *= 3
        elif self.combo_type == "suit" and self.sub_style:
            w += self.sub_style.gross_weight
        return w
    
    @property
    def final_sku_class(self) -> str:
        """最终SKU分类"""
        if self.sku_class_override:
            return self.sku_class_override
        mapping = {
            "single": "单品",
            "2pack": "2件装",
            "3pack": "3件装",
            "suit": "套装"
        }
        return mapping.get(self.combo_type, self.main_style.default_sku_class)
    
    @property
    def final_sizes(self) -> List[str]:
        """最终尺码列表"""
        if self.sizes:
            return self.sizes
        return self.main_style.sizes
    
    @property
    def template_name(self) -> str:
        """使用的模板名称"""
        return self.main_style.template_name
