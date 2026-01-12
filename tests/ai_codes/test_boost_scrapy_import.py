# coding=utf-8
"""测试 boost_scrapy 模块导入"""

import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print("Testing import...")

try:
    from boost_scrapy import Spider, Request, Item, Engine, Pipeline, Response
    print("✓ boost_scrapy import success!")
    
    # 测试 Request
    req = Request("http://example.com", method="GET", meta={'page': 1})
    print(f"✓ Request: {req}")
    
    # 测试 Item
    class TestItem(Item):
        pass
    
    item = TestItem(name="test", value=123)
    print(f"✓ Item: {item}")
    print(f"  item['name'] = {item['name']}")
    print(f"  item.value = {item.value}")
    
    # 测试 Spider
    class TestSpider(Spider):
        name = "test_spider"
        
        def start_requests(self):
            yield Request("http://example.com")
    
    spider = TestSpider()
    print(f"✓ Spider: {spider}")
    
    # 测试 Engine
    engine = Engine()
    print(f"✓ Engine created")
    
    print()
    print("=" * 50)
    print("All tests passed!")
    print("=" * 50)
    
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
