# 款式数据模型
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class Style:
    """基础款式数据结构"""
    style_id: str                    # 款式编号
    style_name: str                  # 款式名称
    template_name: str               # 对应妙手模板名称
    category: str = ""               # 分类：儿童/成人
    fabric_weight: str = ""          # 面料克重（如180g）
    season: str = ""                 # 季节
    fit: str = ""                    # 版型
    weave_method: str = ""           # 织造方式
    cost_price: float = 0.0          # 成本价(元)
    net_weight: float = 0.0          # 单件净重(g)
    gross_weight: float = 0.0        # 单件毛重(g)
    default_sku_class: str = "单品"  # 默认SKU分类
    sizes: List[str] = field(default_factory=list)  # 尺码列表
    
    # 尺码明细：{尺码: {字段: 值}}
    size_details: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    remark: Optional[str] = None     # 备注
