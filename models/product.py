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
    shop_name: str = "Noble Boys"    # 店铺名称
    image_urls: List[str] = field(default_factory=list)  # 主图URL
    colors: List[str] = field(default_factory=list)      # 颜色列表
    sizes: Optional[List[str]] = None  # 尺码（为空则用款式默认）
    all_styles: List[Style] = field(default_factory=list)  # 套装所有款式（含主款式）
    sku_quantity: int = 1            # SKU件数
    
    # 兼容旧代码
    @property
    def sub_style(self) -> Optional[Style]:
        return self.all_styles[0] if self.all_styles else None
    
    @sub_style.setter
    def sub_style(self, value):
        if value:
            self.all_styles = [value]
    
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
    def style_count(self) -> int:
        """套装组成件数"""
        if self.combo_type == "suit":
            return max(1, len(self.all_styles) + 1)  # +1 = main_style
        return 1
    
    @property
    def final_price(self) -> float:
        """供货价：单品=成本×2, 多件装=成本×件数×2, 套装=总成本×(SKU件数÷组成件数)×2"""
        if self.price_override is not None:
            return self.price_override
        from config.settings import PRICE_MULTIPLIER
        if self.combo_type == "suit":
            total_cost = self.main_style.cost_price
            for s in self.all_styles:
                total_cost += s.cost_price
            return round(total_cost * (self.sku_quantity / self.style_count) * PRICE_MULTIPLIER, 2)
        elif self.combo_type in ("2pack", "3pack"):
            return round(self.main_style.cost_price * self.sku_quantity * PRICE_MULTIPLIER, 2)
        else:
            return round(self.main_style.cost_price * PRICE_MULTIPLIER, 2)
    
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
        elif self.combo_type == "suit":
            for s in self.all_styles:
                w += s.net_weight
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
        elif self.combo_type == "suit":
            for s in self.all_styles:
                w += s.gross_weight
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
            "suit": "混合套装"
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
