
import os
import shutil
import time

src = r"d:\codes\boost_spider\demo_crawler\funboost_imp"
dst = r"d:\codes\boost_spider\demo_crawler\boost_spider_imp"

try:
    if os.path.exists(src):
        os.rename(src, dst)
        print(f"Successfully renamed {src} to {dst}")
    elif os.path.exists(dst):
        print(f"Directory {dst} already exists")
    else:
        print(f"Source {src} not found")
except Exception as e:
    print(f"Error renaming: {e}")
