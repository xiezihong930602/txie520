# TEMU自动上架系统 - 主入口
import sys
import os

# 把项目根目录加入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflow.engine import WorkflowEngine
from executors.rpa_publisher import RpaPublisherExecutor
from executors.image_generator import ImageGeneratorExecutor


def run_single_product(product_id: str, with_image: bool = False):
    """
    运行单个商品的上架流程
    
    Args:
        product_id: 商品编号
        with_image: 是否先生成图片
    """
    # 1. 从飞书表格读取商品数据（待实现）
    # product = load_product(product_id)
    
    # 2. 配置执行器
    executors = []
    if with_image:
        executors.append(ImageGeneratorExecutor())
    executors.append(RpaPublisherExecutor())
    
    # 3. 运行工作流
    engine = WorkflowEngine(executors)
    # result = engine.run(product)
    
    # 4. 回写结果到飞书表格（待实现）
    # update_product_result(product)
    
    print(f"商品 {product_id} 流程执行完成")
    print("（飞书对接和RPA具体实现待补充）")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python main.py <商品编号> [--with-image]")
        sys.exit(1)
    
    product_id = sys.argv[1]
    with_image = "--with-image" in sys.argv
    
    run_single_product(product_id, with_image)
