# 执行器基类
from abc import ABC, abstractmethod
from models.product import Product


class BaseExecutor(ABC):
    """执行器基类，所有执行模块继承此类"""
    
    name = "base_executor"
    
    def __init__(self, config=None):
        self.config = config or {}
    
    @abstractmethod
    def execute(self, product: Product) -> dict:
        """
        执行器入口方法
        
        Args:
            product: 商品数据对象
            
        Returns:
            dict: {
                "success": bool,
                "data": dict,
                "error": str | None
            }
        """
        pass
    
    def __str__(self):
        return f"<Executor: {self.name}>"
