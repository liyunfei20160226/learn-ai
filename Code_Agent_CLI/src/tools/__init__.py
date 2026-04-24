# tools 包 - 包含所有工具实现
#
# 设计原则：
# - 所有工具继承自 BaseTool
# - 所有工具通过 ToolRegistry 注册和查找
# - 每个工具单独一个文件，职责单一
