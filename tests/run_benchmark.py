"""
快速运行基准测试的脚本
使用方法: python run_benchmark.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tests.benchmark import main

if __name__ == "__main__":
    main()
