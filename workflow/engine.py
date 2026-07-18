# 工作流引擎
from typing import List
from models.product import Product
from executors.base import BaseExecutor


class WorkflowEngine:
    """
    工作流调度引擎
    按顺序执行配置的执行器列表
    """
    
    def __init__(self, executors: List[BaseExecutor]):
        self.executors = executors
    
    def run(self, product: Product) -> dict:
        """
        运行完整工作流
        
        Args:
            product: 商品数据对象
            
        Returns:
            dict: 最终执行结果
        """
        product.status = "running"
        
        for executor in self.executors:
            print(f"执行模块: {executor.name}")
            result = executor.execute(product)
            
            if not result.get("success"):
                product.status = "failed"
                product.error_msg = result.get("error", "未知错误")
                return {
                    "success": False,
                    "product": product,
                    "failed_at": executor.name,
                    "error": product.error_msg
                }
            
            # 把执行结果的数据回填到product
            data = result.get("data", {})
            self._merge_result(product, data)
        
        product.status = "success"
        return {
            "success": True,
            "product": product
        }
    
    def _merge_result(self, product: Product, data: dict):
        """把执行模块的结果回填到商品对象"""
        # 生图模块回填图片URL
        if "image_urls" in data:
            product.image_urls = data["image_urls"]
        
        # 上架模块回填SKC ID
        if "skc_id" in data:
            product.skc_id = data["skc_id"]
