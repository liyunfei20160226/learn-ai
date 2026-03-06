#!/usr/bin/env python3
"""
测试Python文件 - 用于代码分析测试
这是一个多行注释的示例
"""

import os
import sys


def hello_world():
    """打印Hello World"""
    print("Hello, World!")
    return True


def calculate_sum(a, b):
    # 单行注释：计算两个数的和
    result = a + b
    return result


class Calculator:
    """计算器类"""

    def __init__(self):
        """初始化"""
        self.value = 0

    def add(self, x):
        """添加值"""
        self.value += x
        return self.value

    def reset(self):
        # 重置为0
        self.value = 0


def main():
    """主函数"""
    # 调用函数
    hello_world()

    # 计算
    total = calculate_sum(10, 20)
    print(f"总和: {total}")

    # 使用类
    calc = Calculator()
    calc.add(5)
    calc.add(10)
    print(f"计算器值: {calc.value}")


if __name__ == "__main__":
    main()