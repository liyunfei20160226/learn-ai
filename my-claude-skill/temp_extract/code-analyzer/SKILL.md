---
name: code-analyzer
description: |
  分析代码库的统计信息，包括行数、注释、函数数量等。

  当用户需要分析代码库的统计信息、查看代码规模、计算代码行数、分析代码质量指标时，使用此技能。

  具体触发场景包括：
  - 用户询问"分析这个项目的代码行数"
  - 用户说"统计一下这个目录的代码量"
  - 用户需要代码质量报告、代码度量指标
  - 用户想了解项目的规模、复杂度
  - 用户要求生成代码统计报告

  此技能会自动扫描当前目录及其子目录，分析所有支持的代码文件，生成详细的JSON格式统计报告。

  支持的语言：Python (.py), Java (.java), Go (.go), JavaScript (.js), TypeScript (.ts), JSX (.jsx), TSX (.tsx), C++ (.cpp, .cxx, .cc), C (.c), C# (.cs), PHP (.php), Ruby (.rb), Swift (.swift), Kotlin (.kt), Rust (.rs), Shell (.sh, .bash), HTML (.html), CSS (.css), Markdown (.md) 等主流编程语言。
---

# 代码分析技能

此技能用于分析代码库的统计信息，生成详细的代码度量报告。

## 功能概述

1. **递归扫描**：扫描当前目录及其所有子目录
2. **智能过滤**：自动排除常见依赖目录和隐藏文件
3. **多语言支持**：支持主流编程语言的代码分析
4. **详细统计**：提供行数、注释、函数数量等指标
5. **JSON输出**：生成结构化的JSON格式报告
6. **多语言HTML报告**：默认生成中文、英文、日文三种语言的HTML报告，支持页面内语言切换

## 使用方式

当技能触发时，Claude会自动执行以下步骤：

1. 扫描当前工作目录及其子目录
2. 识别所有支持的代码文件
3. 分析每个文件的统计信息
4. 生成汇总报告和详细文件列表
5. 以JSON格式输出结果

用户无需提供额外参数，技能会自动分析当前目录。

## 排除规则

技能会自动排除以下目录和文件：
- 隐藏文件/目录（以`.`开头）
- 版本控制目录：`.git`, `.svn`, `.hg`
- 依赖目录：`node_modules`, `vendor`, `dist`, `build`, `target`, `out`
- 虚拟环境目录：`.venv`, `venv`, `env`, `.env`
- 缓存目录：`__pycache__`, `.pytest_cache`, `.mypy_cache`
- 生成的文件：`.class`, `.o`, `.so`, `.dll`

## 统计指标

对于每个代码文件，技能会计算以下指标：

### 基础统计
- `total_lines`：总行数
- `code_lines`：实际代码行数（不含空行和注释）
- `comment_lines`：注释行数
- `blank_lines`：空行数
- `function_count`：函数/方法数量

### 语言特定统计
- 根据语言类型，准确识别函数定义
- 支持不同语言的注释风格
- 正确处理嵌套结构

## 输出格式

技能输出为JSON格式，包含以下结构：

```json
{
  "summary": {
    "total_files": 整数,
    "total_lines": 整数,
    "code_lines": 整数,
    "comment_lines": 整数,
    "blank_lines": 整数,
    "total_functions": 整数,
    "analyzed_languages": {
      "python": 文件数,
      "javascript": 文件数,
      // ... 其他语言
    }
  },
  "files": [
    {
      "file_path": "相对路径",
      "language": "语言类型",
      "total_lines": 整数,
      "code_lines": 整数,
      "comment_lines": 整数,
      "blank_lines": 整数,
      "function_count": 整数,
      "error": "错误信息（如果有）"
    },
    // ... 其他文件
  ],
  "warnings": [
    "跳过的文件或目录",
    // ... 其他警告
  ],
  "metadata": {
    "scan_directory": "扫描的目录",
    "scan_time": "扫描时间戳",
    "duration_ms": "分析耗时（毫秒）"
  }
}
```

## HTML报告特性

除了JSON格式的输出外，技能还会生成美观的HTML报告，具有以下特性：

### 多语言支持
- **默认行为**：自动生成中文 (`_zh.html`)、英文 (`_en.html`)、日文 (`_ja.html`) 三种语言的HTML报告
- **语言切换**：HTML报告包含语言选择器，用户可以在页面内实时切换语言
- **单语言模式**：如需只生成特定语言报告，可使用 `--lang` 参数（如 `--lang en`）

### 报告内容
- **统计概览**：以卡片形式展示总文件数、总行数、代码行、注释行、空行、函数总数
- **语言分布**：可视化显示项目中各种编程语言的文件数量分布
- **文件详情**：表格展示每个文件的详细统计信息
- **对比分析**：如果存在历史分析数据，会自动显示与上一次分析的对比
- **警告信息**：显示分析过程中遇到的任何问题或跳过的文件

### 输出文件
HTML报告文件保存在 `result/` 目录中，命名格式为：
- `code_analysis_YYYYMMDD_HHMMSS_zh.html` - 中文报告
- `code_analysis_YYYYMMDD_HHMMSS_en.html` - 英文报告
- `code_analysis_YYYYMMDD_HHMMSS_ja.html` - 日文报告

### 使用示例
```bash
# 默认生成所有语言版本（推荐）
python code-analyzer/scripts/analyzer.py .

# 只生成英文报告
python code-analyzer/scripts/analyzer.py . --lang en

# 不生成HTML报告
python code-analyzer/scripts/analyzer.py . --no-html
```

## 实现细节

### 文件识别
根据文件扩展名识别语言类型：
- `.py` → Python
- `.java` → Java
- `.go` → Go
- `.js` → JavaScript
- `.ts` → TypeScript
- `.jsx` → JSX
- `.tsx` → TSX
- `.cpp`, `.cxx`, `.cc` → C++
- `.c` → C
- `.cs` → C#
- `.php` → PHP
- `.rb` → Ruby
- `.swift` → Swift
- `.kt` → Kotlin
- `.rs` → Rust
- `.sh`, `.bash` → Shell
- `.html` → HTML
- `.css` → CSS
- `.md` → Markdown

### 注释识别
- 单行注释：`//` (JS/TS/Java/C++/C#/Go), `#` (Python/Ruby/Shell), `--` (SQL)
- 多行注释：`/* */` (JS/TS/Java/C++/C#), `""" """` 或 `''' '''` (Python)
- 文档注释：`/** */` (Java/JS/TS), `///` (Rust/C#)

### 函数识别
- Python: `def` 关键字
- JavaScript/TypeScript: `function` 关键字、箭头函数、方法定义
- Java: `public/private/protected` + 方法定义
- Go: `func` 关键字
- C++/C: 函数定义模式
- 其他语言：类似模式匹配

## 错误处理

- 无法读取的文件会被跳过，并在warnings中记录
- 不支持的扩展名会被跳过
- 解析错误会被记录在文件的error字段中
- 技能会继续处理其他文件

## 使用示例

用户可以说：
- "分析这个项目的代码"
- "统计一下代码行数"
- "生成代码质量报告"
- "这个项目有多少行代码？"
- "查看代码统计信息"

技能会自动执行并返回JSON格式的报告。

## 注意事项

1. 对于大型项目，分析可能需要一些时间
2. 技能会跳过二进制文件和无法解析的文件
3. 函数计数可能因语言复杂性而略有差异
4. 建议在项目的根目录运行以获得完整统计

## 执行步骤

当用户请求代码分析时，请按照以下步骤操作：

### 1. 检查当前目录
首先确认当前工作目录。用户可能希望在特定目录中运行分析。如果用户指定了目录，请切换到该目录。

### 2. 运行分析脚本
使用内置的Python分析脚本执行代码分析：

```bash
cd "当前目录"
python "code-analyzer/scripts/analyzer.py"
```

默认情况下，脚本会：
1. 生成JSON格式的详细数据文件（保存在 `result/` 目录）
2. 生成中文、英文、日文三种语言的HTML报告
3. 自动与之前的结果进行对比（如果存在）

如需自定义输出，可以使用以下参数：
```bash
# 指定输出文件名
python "code-analyzer/scripts/analyzer.py" --output "my_analysis.json"

# 只生成特定语言的报告
python "code-analyzer/scripts/analyzer.py" --lang en

# 不生成HTML报告
python "code-analyzer/scripts/analyzer.py" --no-html

# 只显示汇总信息
python "code-analyzer/scripts/analyzer.py" --summary
```

### 3. 读取和分析结果
分析完成后，读取生成的JSON文件：

```python
import json
with open('code_analysis_result.json', 'r', encoding='utf-8') as f:
    results = json.load(f)
```

### 4. 呈现结果
将结果以清晰、易读的格式呈现给用户：

1. **显示汇总信息**：
   - 总文件数、总行数
   - 代码行、注释行、空行分布
   - 函数总数
   - 语言分布

2. **显示详细统计**（如果文件数量合理）：
   - 列出前10-20个文件的详细统计
   - 按文件大小或代码行数排序

3. **显示警告信息**：
   - 列出遇到的任何问题或跳过的文件

4. **提供JSON数据**：
   - 将完整的JSON结果呈现给用户，方便进一步处理

5. **提供HTML报告**：
   - 告知用户已生成多语言HTML报告
   - 提供HTML报告的文件路径
   - 说明HTML报告的语言切换功能
   - 建议用户打开HTML报告查看可视化结果

### 5. 清理临时文件
如果需要，可以删除临时生成的JSON文件：

```bash
rm -f code_analysis_result.json
```

## 开发说明

如需修改或扩展此技能，请参考：
- 添加新语言支持：扩展文件扩展名映射和解析逻辑
- 调整排除规则：修改目录排除列表
- 优化性能：实现增量分析或缓存机制