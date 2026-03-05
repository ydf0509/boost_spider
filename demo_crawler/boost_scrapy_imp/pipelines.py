
from boost_scrapy.pipeline import SQLModelPipeline, ConsolePipeline
from boost_scrapy import Pipeline

# ================= 定义 Pipeline =================

# 这里可以留空，或者重新导出，或者如果需要自定义扩展，再继承
# 目前直接从框架导入即可

# 为了兼容 demo 中的引用，我们重新导出
__all__ = ['SQLModelPipeline', 'ConsolePipeline', ]

# 如果你想扩展功能：
# class MyCustomPipeline(SQLModelPipeline):
#     def process_item(self, item, spider):
#         print("Before save...")
#         super().process_item(item, spider)
#         print("After save...")
#         return item