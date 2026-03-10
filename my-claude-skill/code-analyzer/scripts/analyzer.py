#!/usr/bin/env python3
"""
代码分析器 - 分析代码文件的统计信息
支持多种编程语言的行数、注释、函数统计
"""

import os
import re
import json
import sys
import glob
import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import time

class CodeAnalyzer:
    """代码分析器主类"""

    # 支持的扩展名映射
    EXTENSION_MAP = {
        # Python
        '.py': 'python',
        '.pyw': 'python',

        # Java
        '.java': 'java',

        # Go
        '.go': 'go',

        # JavaScript/TypeScript
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',

        # C/C++
        '.c': 'c',
        '.cpp': 'cpp',
        '.cxx': 'cpp',
        '.cc': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.hxx': 'cpp',

        # C#
        '.cs': 'csharp',

        # PHP
        '.php': 'php',

        # Ruby
        '.rb': 'ruby',

        # Swift
        '.swift': 'swift',

        # Kotlin
        '.kt': 'kotlin',
        '.kts': 'kotlin',

        # Rust
        '.rs': 'rust',

        # Shell
        '.sh': 'shell',
        '.bash': 'shell',
        '.zsh': 'shell',

        # Web
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',

        # Markdown
        '.md': 'markdown',
        '.markdown': 'markdown',

        # Other
        '.sql': 'sql',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.json': 'json',
        '.xml': 'xml',
    }

    # 排除的目录模式
    EXCLUDED_DIRS = {
        # 版本控制
        '.git', '.svn', '.hg',

        # 依赖管理
        'node_modules', 'vendor', 'bower_components', 'jspm_packages',
        'packages', 'dist', 'build', 'target', 'out', 'bin', 'obj',

        # 虚拟环境
        '.venv', 'venv', 'env', '.env', 'virtualenv',

        # 缓存
        '__pycache__', '.pytest_cache', '.mypy_cache', '.cache',
        '.idea', '.vscode', '.vs',

        # 生成文件
        'coverage', '.nyc_output', '.next', '.nuxt',
    }

    # 排除的文件模式
    EXCLUDED_FILES = {
        'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
        'composer.lock', 'Gemfile.lock', 'Cargo.lock',
        '.DS_Store', 'Thumbs.db',
    }

    # 多语言字符串映射
    HTML_STRINGS = {
        'en': {
            'report_title': 'Code Analysis Report',
            'scan_directory': 'Scan Directory',
            'scan_time': 'Scan Time',
            'duration': 'Duration',
            'summary_statistics': 'Summary Statistics',
            'total_files': 'Total Files',
            'total_lines': 'Total Lines',
            'code_lines': 'Code Lines',
            'comment_lines': 'Comment Lines',
            'blank_lines': 'Blank Lines',
            'total_functions': 'Total Functions',
            'language_distribution': 'Language Distribution',
            'file_details': 'File Details',
            'showing_files': 'Showing {} analyzed files',
            'file_path': 'File Path',
            'language': 'Language',
            'total_lines_col': 'Total Lines',
            'code_lines_col': 'Code Lines',
            'comment_lines_col': 'Comment Lines',
            'blank_lines_col': 'Blank Lines',
            'functions': 'Functions',
            'warnings': 'Warnings',
            'comparison_title': 'Comparison with Previous Analysis',
            'previous_scan': 'Previous scan',
            'current_scan': 'Current scan',
            'metric': 'Metric',
            'previous': 'Previous',
            'current': 'Current',
            'change': 'Change',
            'percent_change': '% Change',
            'from_previous': 'from previous',
            'files_suffix': 'files',
            'report_generated': 'Report generated at',
            'no_files_found': 'No supported code files found.',
        },
        'zh': {
            'report_title': '代码分析报告',
            'scan_directory': '扫描目录',
            'scan_time': '扫描时间',
            'duration': '耗时',
            'summary_statistics': '统计概览',
            'total_files': '总文件数',
            'total_lines': '总行数',
            'code_lines': '代码行',
            'comment_lines': '注释行',
            'blank_lines': '空行',
            'total_functions': '总函数数',
            'language_distribution': '语言分布',
            'file_details': '文件详情',
            'showing_files': '共分析了 {} 个文件',
            'file_path': '文件路径',
            'language': '语言',
            'total_lines_col': '总行数',
            'code_lines_col': '代码行',
            'comment_lines_col': '注释行',
            'blank_lines_col': '空行',
            'functions': '函数数',
            'warnings': '警告',
            'comparison_title': '与上一次分析对比',
            'previous_scan': '上一次扫描',
            'current_scan': '当前扫描',
            'metric': '指标',
            'previous': '上一次',
            'current': '当前',
            'change': '变化',
            'percent_change': '变化率',
            'from_previous': '较上一次',
            'files_suffix': '文件',
            'report_generated': '报告生成时间',
            'no_files_found': '未找到支持的代码文件。',
        },
        'ja': {
            'report_title': 'コード分析レポート',
            'scan_directory': 'スキャンディレクトリ',
            'scan_time': 'スキャン時間',
            'duration': '所要時間',
            'summary_statistics': '統計概要',
            'total_files': '総ファイル数',
            'total_lines': '総行数',
            'code_lines': 'コード行',
            'comment_lines': 'コメント行',
            'blank_lines': '空白行',
            'total_functions': '総関数数',
            'language_distribution': '言語分布',
            'file_details': 'ファイル詳細',
            'showing_files': '分析したファイル数: {}',
            'file_path': 'ファイルパス',
            'language': '言語',
            'total_lines_col': '総行数',
            'code_lines_col': 'コード行',
            'comment_lines_col': 'コメント行',
            'blank_lines_col': '空白行',
            'functions': '関数数',
            'warnings': '警告',
            'comparison_title': '前回分析との比較',
            'previous_scan': '前回スキャン',
            'current_scan': '現在のスキャン',
            'metric': '指標',
            'previous': '前回',
            'current': '現在',
            'change': '変化',
            'percent_change': '変化率',
            'from_previous': '前回から',
            'files_suffix': 'ファイル',
            'report_generated': 'レポート生成時間',
            'no_files_found': 'サポートされているコードファイルが見つかりません。',
        }
    }

    def __init__(self, root_dir: str = "."):
        """初始化分析器

        Args:
            root_dir: 要分析的根目录
        """
        self.root_dir = Path(root_dir).resolve()
        self.results = {
            'summary': {
                'total_files': 0,
                'total_lines': 0,
                'code_lines': 0,
                'comment_lines': 0,
                'blank_lines': 0,
                'total_functions': 0,
                'analyzed_languages': {}
            },
            'files': [],
            'warnings': [],
            'metadata': {
                'scan_directory': str(self.root_dir),
                'scan_time': None,
                'duration_ms': 0
            }
        }

    def should_exclude(self, path: Path) -> bool:
        """检查路径是否应该被排除

        Args:
            path: 要检查的路径

        Returns:
            bool: 是否排除
        """
        # 检查隐藏文件/目录
        for part in path.parts:
            if part.startswith('.') and part != '.' and part != '..':
                return True

        # 检查排除目录
        if path.is_dir():
            if path.name in self.EXCLUDED_DIRS:
                return True
        else:
            if path.name in self.EXCLUDED_FILES:
                return True

        return False

    def get_language(self, file_path: Path) -> Optional[str]:
        """根据文件扩展名获取语言类型

        Args:
            file_path: 文件路径

        Returns:
            Optional[str]: 语言类型，如果不支持则返回None
        """
        ext = file_path.suffix.lower()
        return self.EXTENSION_MAP.get(ext)

    def analyze_file(self, file_path: Path) -> Optional[Dict]:
        """分析单个文件

        Args:
            file_path: 文件路径

        Returns:
            Optional[Dict]: 分析结果，如果分析失败则返回None
        """
        try:
            language = self.get_language(file_path)
            if not language:
                return None

            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # 初始化统计
            stats = {
                'file_path': str(file_path.relative_to(self.root_dir)),
                'language': language,
                'total_lines': len(lines),
                'code_lines': 0,
                'comment_lines': 0,
                'blank_lines': 0,
                'function_count': 0,
                'error': None
            }

            # 根据语言调用相应的分析器
            if language == 'python':
                self._analyze_python(lines, stats)
            elif language in ['javascript', 'typescript']:
                self._analyze_javascript(lines, stats)
            elif language == 'java':
                self._analyze_java(lines, stats)
            elif language == 'go':
                self._analyze_go(lines, stats)
            elif language == 'csharp':
                self._analyze_csharp(lines, stats)
            elif language == 'cpp':
                self._analyze_cpp(lines, stats)
            elif language == 'c':
                self._analyze_c(lines, stats)
            elif language == 'php':
                self._analyze_php(lines, stats)
            elif language == 'ruby':
                self._analyze_ruby(lines, stats)
            elif language == 'rust':
                self._analyze_rust(lines, stats)
            else:
                # 对于其他语言，使用通用分析器
                self._analyze_generic(lines, stats)

            return stats

        except Exception as e:
            error_msg = f"Error analyzing file: {str(e)}"
            self.results['warnings'].append(f"{file_path}: {error_msg}")
            return {
                'file_path': str(file_path.relative_to(self.root_dir)),
                'language': 'unknown',
                'total_lines': 0,
                'code_lines': 0,
                'comment_lines': 0,
                'blank_lines': 0,
                'function_count': 0,
                'error': error_msg
            }

    def _analyze_python(self, lines: List[str], stats: Dict):
        """分析Python代码"""
        in_multiline_comment = False
        in_docstring = False

        for line in lines:
            stripped = line.strip()

            # 空行
            if not stripped:
                stats['blank_lines'] += 1
                continue

            # 处理多行注释和文档字符串
            if in_multiline_comment or in_docstring:
                stats['comment_lines'] += 1
                if stripped.endswith('"""') or stripped.endswith("'''"):
                    in_multiline_comment = False
                    in_docstring = False
                continue

            # 单行注释
            if stripped.startswith('#'):
                stats['comment_lines'] += 1
                continue

            # 多行注释/文档字符串开始
            if stripped.startswith('"""') or stripped.startswith("'''"):
                stats['comment_lines'] += 1
                if not (stripped.endswith('"""') and len(stripped) > 3) and \
                   not (stripped.endswith("'''") and len(stripped) > 3):
                    in_multiline_comment = True
                    in_docstring = True
                continue

            # 函数定义
            if stripped.startswith('def '):
                stats['function_count'] += 1

            # 代码行
            stats['code_lines'] += 1

    def _analyze_javascript(self, lines: List[str], stats: Dict):
        """分析JavaScript/TypeScript代码"""
        in_multiline_comment = False

        for line in lines:
            stripped = line.strip()

            # 空行
            if not stripped:
                stats['blank_lines'] += 1
                continue

            # 多行注释中
            if in_multiline_comment:
                stats['comment_lines'] += 1
                if '*/' in stripped:
                    in_multiline_comment = False
                continue

            # 单行注释
            if stripped.startswith('//'):
                stats['comment_lines'] += 1
                continue

            # JSDoc或多行注释开始
            if stripped.startswith('/*'):
                stats['comment_lines'] += 1
                if not '*/' in stripped:
                    in_multiline_comment = True
                continue

            # 函数定义
            # 匹配: function name, const name = () =>, class method, etc.
            if re.match(r'^(export\s+)?(async\s+)?function\b', stripped) or \
               re.match(r'^(export\s+)?(const|let|var)\s+\w+\s*=\s*(async\s*)?\(', stripped) or \
               re.match(r'^(public|private|protected)?\s*\w+\s*\([^)]*\)\s*{', stripped) or \
               re.match(r'^\w+\s*:\s*(async\s*)?\([^)]*\)\s*=>', stripped):
                stats['function_count'] += 1

            # 代码行
            stats['code_lines'] += 1

    def _analyze_java(self, lines: List[str], stats: Dict):
        """分析Java代码"""
        in_multiline_comment = False

        for line in lines:
            stripped = line.strip()

            # 空行
            if not stripped:
                stats['blank_lines'] += 1
                continue

            # 多行注释中
            if in_multiline_comment:
                stats['comment_lines'] += 1
                if '*/' in stripped:
                    in_multiline_comment = False
                continue

            # 单行注释
            if stripped.startswith('//'):
                stats['comment_lines'] += 1
                continue

            # Javadoc或多行注释开始
            if stripped.startswith('/*'):
                stats['comment_lines'] += 1
                if not '*/' in stripped:
                    in_multiline_comment = True
                continue

            # 方法定义
            # 匹配: public void method(), private static Type method(), etc.
            if re.match(r'^(public|private|protected|static|\s)+[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*{', stripped) or \
               re.match(r'^@Override\s+', stripped):
                stats['function_count'] += 1

            # 代码行
            stats['code_lines'] += 1

    def _analyze_go(self, lines: List[str], stats: Dict):
        """分析Go代码"""
        in_multiline_comment = False

        for line in lines:
            stripped = line.strip()

            # 空行
            if not stripped:
                stats['blank_lines'] += 1
                continue

            # 多行注释中
            if in_multiline_comment:
                stats['comment_lines'] += 1
                if '*/' in stripped:
                    in_multiline_comment = False
                continue

            # 单行注释
            if stripped.startswith('//'):
                stats['comment_lines'] += 1
                continue

            # 多行注释开始
            if stripped.startswith('/*'):
                stats['comment_lines'] += 1
                if not '*/' in stripped:
                    in_multiline_comment = True
                continue

            # 函数定义
            if stripped.startswith('func '):
                stats['function_count'] += 1

            # 代码行
            stats['code_lines'] += 1

    def _analyze_cpp(self, lines: List[str], stats: Dict):
        """分析C++代码"""
        self._analyze_c(lines, stats)  # 使用相同的逻辑

    def _analyze_c(self, lines: List[str], stats: Dict):
        """分析C代码"""
        in_multiline_comment = False

        for line in lines:
            stripped = line.strip()

            # 空行
            if not stripped:
                stats['blank_lines'] += 1
                continue

            # 多行注释中
            if in_multiline_comment:
                stats['comment_lines'] += 1
                if '*/' in stripped:
                    in_multiline_comment = False
                continue

            # 单行注释
            if stripped.startswith('//'):
                stats['comment_lines'] += 1
                continue

            # 多行注释开始
            if stripped.startswith('/*'):
                stats['comment_lines'] += 1
                if not '*/' in stripped:
                    in_multiline_comment = True
                continue

            # 函数定义
            # 匹配返回类型 + 函数名 + 参数
            if re.match(r'^[\w\*]+\s+\w+\s*\([^)]*\)\s*{', stripped):
                stats['function_count'] += 1

            # 代码行
            stats['code_lines'] += 1

    def _analyze_csharp(self, lines: List[str], stats: Dict):
        """分析C#代码"""
        in_multiline_comment = False

        for line in lines:
            stripped = line.strip()

            # 空行
            if not stripped:
                stats['blank_lines'] += 1
                continue

            # 多行注释中
            if in_multiline_comment:
                stats['comment_count'] += 1
                if '*/' in stripped:
                    in_multiline_comment = False
                continue

            # 单行注释
            if stripped.startswith('//'):
                stats['comment_lines'] += 1
                continue

            # XML文档注释或多行注释开始
            if stripped.startswith('/*') or stripped.startswith('///'):
                stats['comment_lines'] += 1
                if stripped.startswith('/*') and not '*/' in stripped:
                    in_multiline_comment = True
                continue

            # 方法定义
            # 匹配: public void Method(), private static Type Method(), etc.
            if re.match(r'^(public|private|protected|internal|static|\s)+[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*{', stripped):
                stats['function_count'] += 1

            # 代码行
            stats['code_lines'] += 1

    def _analyze_php(self, lines: List[str], stats: Dict):
        """分析PHP代码"""
        in_multiline_comment = False

        for line in lines:
            stripped = line.strip()

            # 空行
            if not stripped:
                stats['blank_lines'] += 1
                continue

            # 多行注释中
            if in_multiline_comment:
                stats['comment_lines'] += 1
                if '*/' in stripped:
                    in_multiline_comment = False
                continue

            # 单行注释
            if stripped.startswith('//') or stripped.startswith('#'):
                stats['comment_lines'] += 1
                continue

            # 多行注释开始
            if stripped.startswith('/*'):
                stats['comment_lines'] += 1
                if not '*/' in stripped:
                    in_multiline_comment = True
                continue

            # 函数定义
            if stripped.startswith('function '):
                stats['function_count'] += 1

            # 代码行
            stats['code_lines'] += 1

    def _analyze_ruby(self, lines: List[str], stats: Dict):
        """分析Ruby代码"""
        in_multiline_comment = False

        for line in lines:
            stripped = line.strip()

            # 空行
            if not stripped:
                stats['blank_lines'] += 1
                continue

            # =begin/=end 多行注释
            if in_multiline_comment:
                stats['comment_lines'] += 1
                if stripped.startswith('=end'):
                    in_multiline_comment = False
                continue

            # 单行注释
            if stripped.startswith('#'):
                stats['comment_lines'] += 1
                continue

            # 多行注释开始
            if stripped.startswith('=begin'):
                stats['comment_lines'] += 1
                in_multiline_comment = True
                continue

            # 方法定义
            if stripped.startswith('def '):
                stats['function_count'] += 1

            # 代码行
            stats['code_lines'] += 1

    def _analyze_rust(self, lines: List[str], stats: Dict):
        """分析Rust代码"""
        in_multiline_comment = False

        for line in lines:
            stripped = line.strip()

            # 空行
            if not stripped:
                stats['blank_lines'] += 1
                continue

            # 多行注释中
            if in_multiline_comment:
                stats['comment_lines'] += 1
                if '*/' in stripped:
                    in_multiline_comment = False
                continue

            # 单行注释
            if stripped.startswith('//'):
                stats['comment_lines'] += 1
                continue

            # 多行注释开始
            if stripped.startswith('/*'):
                stats['comment_lines'] += 1
                if not '*/' in stripped:
                    in_multiline_comment = True
                continue

            # 函数定义
            if stripped.startswith('fn '):
                stats['function_count'] += 1

            # 代码行
            stats['code_lines'] += 1

    def _analyze_generic(self, lines: List[str], stats: Dict):
        """通用代码分析器"""
        for line in lines:
            stripped = line.strip()

            # 空行
            if not stripped:
                stats['blank_lines'] += 1
                continue

            # 简单注释检测（可能不准确）
            if stripped.startswith(('//', '#', '--', '/*', '*/', '<!--', '-->')):
                stats['comment_lines'] += 1
                continue

            # 代码行
            stats['code_lines'] += 1

    def scan_directory(self):
        """Scan directory and analyze all files"""
        start_time = time.time()

        for root, dirs, files in os.walk(self.root_dir, topdown=True):
            root_path = Path(root)

            # 过滤排除的目录
            dirs[:] = [d for d in dirs if not self.should_exclude(root_path / d)]

            for file_name in files:
                file_path = root_path / file_name

                # 跳过排除的文件
                if self.should_exclude(file_path):
                    continue

                # 分析文件
                result = self.analyze_file(file_path)
                if result:
                    self.results['files'].append(result)

                    # 更新汇总统计
                    self.results['summary']['total_files'] += 1
                    self.results['summary']['total_lines'] += result['total_lines']
                    self.results['summary']['code_lines'] += result['code_lines']
                    self.results['summary']['comment_lines'] += result['comment_lines']
                    self.results['summary']['blank_lines'] += result['blank_lines']
                    self.results['summary']['total_functions'] += result['function_count']

                    # 更新语言统计
                    lang = result['language']
                    if lang not in self.results['summary']['analyzed_languages']:
                        self.results['summary']['analyzed_languages'][lang] = 0
                    self.results['summary']['analyzed_languages'][lang] += 1

        # 计算耗时
        end_time = time.time()
        self.results['metadata']['duration_ms'] = int((end_time - start_time) * 1000)
        self.results['metadata']['scan_time'] = time.strftime('%Y-%m-%d %H:%M:%S')

        return self.results

    def print_summary(self):
        """Print summary information"""
        summary = self.results['summary']
        print(f"Analysis completed!")
        print(f"Scan directory: {self.results['metadata']['scan_directory']}")
        print(f"Time taken: {self.results['metadata']['duration_ms']}ms")
        print(f"\nSummary statistics:")
        print(f"  Total files: {summary['total_files']}")
        print(f"  Total lines: {summary['total_lines']}")
        print(f"  Code lines: {summary['code_lines']}")
        print(f"  Comment lines: {summary['comment_lines']}")
        print(f"  Blank lines: {summary['blank_lines']}")
        print(f"  Total functions: {summary['total_functions']}")

        if summary['analyzed_languages']:
            print(f"\nLanguage distribution:")
            for lang, count in sorted(summary['analyzed_languages'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {lang}: {count} files")

        if self.results['warnings']:
            print(f"\nWarnings ({len(self.results['warnings'])}):")
            for warning in self.results['warnings'][:5]:  # Only show first 5 warnings
                print(f"  - {warning}")
            if len(self.results['warnings']) > 5:
                print(f"  ... and {len(self.results['warnings']) - 5} more warnings")

    def generate_html_report(self, html_path: str, comparison_data: Dict = None, lang: str = 'zh'):
        """Generate HTML report from analysis results

        Args:
            html_path: Path to save HTML file
            comparison_data: Optional comparison data from previous analysis
            lang: Language for report ('zh', 'en', or 'ja')
        """
        import datetime

        # Validate language
        if lang not in self.HTML_STRINGS:
            lang = 'zh'  # default to Chinese

        # Get language strings
        strings = self.HTML_STRINGS[lang]

        # Map language to HTML lang attribute
        html_lang_map = {'en': 'en', 'zh': 'zh-CN', 'ja': 'ja'}
        html_lang = html_lang_map.get(lang, 'en')

        summary = self.results['summary']
        metadata = self.results['metadata']

        # 构建HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="{html_lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{strings['report_title']} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        h1 {{
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background-color: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 15px;
            border-radius: 5px;
        }}
        .stat-card h3 {{
            margin-top: 0;
            font-size: 14px;
            color: #7f8c8d;
            text-transform: uppercase;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .stat-diff {{
            font-size: 14px;
            margin-top: 5px;
        }}
        .stat-diff.positive {{
            color: #27ae60;
        }}
        .stat-diff.negative {{
            color: #e74c3c;
        }}
        .language-chart {{
            margin: 30px 0;
        }}
        .language-bar {{
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }}
        .language-name {{
            width: 120px;
            font-weight: bold;
        }}
        .language-bar-inner {{
            flex-grow: 1;
            height: 20px;
            background-color: #ecf0f1;
            border-radius: 3px;
            overflow: hidden;
        }}
        .language-bar-fill {{
            height: 100%;
            background-color: #3498db;
            border-radius: 3px;
        }}
        .language-count {{
            width: 80px;
            text-align: right;
        }}
        .file-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .file-table th, .file-table td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .file-table th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        .file-table tr:hover {{
            background-color: #f5f5f5;
        }}
        .warning-box {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }}
        .comparison-section {{
            background-color: #e8f4fd;
            border: 1px solid #b3e0ff;
            border-radius: 5px;
            padding: 20px;
            margin: 30px 0;
        }}
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        .comparison-table th, .comparison-table td {{
            padding: 10px;
            text-align: center;
            border: 1px solid #b3e0ff;
        }}
        .comparison-table th {{
            background-color: #d1ecf1;
        }}
        .timestamp {{
            color: #7f8c8d;
            font-size: 12px;
            text-align: right;
            margin-top: 30px;
            padding-top: 10px;
            border-top: 1px solid #eee;
        }}
        .language-selector {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 10px;
            margin-bottom: 20px;
        }}
        .language-selector label {{
            font-weight: bold;
            color: #2c3e50;
        }}
        .language-selector select {{
            padding: 5px 10px;
            border: 1px solid #3498db;
            border-radius: 4px;
            background-color: white;
            color: #2c3e50;
            font-size: 14px;
        }}
        .language-selector select:focus {{
            outline: none;
            border-color: #2980b9;
            box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
        }}
        .language-selector option {{
            padding: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 {strings['report_title']}</h1>
        <div class="language-selector">
            <label for="language-select">{strings['language']}:</label>
            <select id="language-select" onchange="changeLanguage(this.value)">
                <option value="zh" {"selected" if lang == "zh" else ""}>中文</option>
                <option value="en" {"selected" if lang == "en" else ""}>English</option>
                <option value="ja" {"selected" if lang == "ja" else ""}>日本語</option>
            </select>
        </div>
        <p><strong>{strings['scan_directory']}:</strong> {metadata['scan_directory']}</p>
        <p><strong>{strings['scan_time']}:</strong> {metadata['scan_time']}</p>
        <p><strong>{strings['duration']}:</strong> {metadata['duration_ms']}ms</p>

        <h2>📈 {strings['summary_statistics']}</h2>
        <div class="summary-grid">
            <div class="stat-card">
                <h3>{strings['total_files']}</h3>
                <div class="stat-value">{summary['total_files']}</div>
                {self._format_comparison('total_files', comparison_data, strings) if comparison_data else ''}
            </div>
            <div class="stat-card">
                <h3>{strings['total_lines']}</h3>
                <div class="stat-value">{summary['total_lines']}</div>
                {self._format_comparison('total_lines', comparison_data, strings) if comparison_data else ''}
            </div>
            <div class="stat-card">
                <h3>{strings['code_lines']}</h3>
                <div class="stat-value">{summary['code_lines']}</div>
                {self._format_comparison('code_lines', comparison_data, strings) if comparison_data else ''}
            </div>
            <div class="stat-card">
                <h3>{strings['comment_lines']}</h3>
                <div class="stat-value">{summary['comment_lines']}</div>
                {self._format_comparison('comment_lines', comparison_data, strings) if comparison_data else ''}
            </div>
            <div class="stat-card">
                <h3>{strings['blank_lines']}</h3>
                <div class="stat-value">{summary['blank_lines']}</div>
                {self._format_comparison('blank_lines', comparison_data, strings) if comparison_data else ''}
            </div>
            <div class="stat-card">
                <h3>{strings['total_functions']}</h3>
                <div class="stat-value">{summary['total_functions']}</div>
                {self._format_comparison('total_functions', comparison_data, strings) if comparison_data else ''}
            </div>
        </div>

        {self._generate_comparison_section(comparison_data, strings) if comparison_data else ''}

        <h2>🌐 {strings['language_distribution']}</h2>
        <div class="language-chart">
            {self._generate_language_chart(summary['analyzed_languages'], strings)}
        </div>

        <h2>📄 {strings['file_details']}</h2>
        <p>{strings['showing_files'].format(len(self.results['files']))}</p>
        <table class="file-table">
            <thead>
                <tr>
                    <th>{strings['file_path']}</th>
                    <th>{strings['language']}</th>
                    <th>{strings['total_lines_col']}</th>
                    <th>{strings['code_lines_col']}</th>
                    <th>{strings['comment_lines_col']}</th>
                    <th>{strings['blank_lines_col']}</th>
                    <th>{strings['functions']}</th>
                </tr>
            </thead>
            <tbody>
                {self._generate_file_rows()}
            </tbody>
        </table>

        {self._generate_warnings_section(strings) if self.results['warnings'] else ''}

        <div class="timestamp">
            {strings['report_generated']} {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
    <script>
        function changeLanguage(selectedLang) {{
            // 获取当前文件名
            const currentFile = window.location.pathname.split('/').pop();
            // 移除语言后缀和扩展名
            const baseName = currentFile.replace(/_(en|zh|ja)\\.html$/i, '').replace(/\\.html$/i, '');

            // 构建新文件名（标准格式：基础名_语言.html）
            const newFileName = baseName + '_' + selectedLang + '.html';

            // 尝试加载新语言的文件
            const newFileUrl = newFileName;

            // 检查文件是否存在（通过尝试加载）
            fetch(newFileUrl, {{ method: 'HEAD' }})
                .then(response => {{
                    if (response.ok) {{
                        window.location.href = newFileUrl;
                    }} else {{
                        // 文件不存在，显示提示信息
                        const langNames = {{'zh': '中文', 'en': 'English', 'ja': '日本語'}};
                        const langName = langNames[selectedLang] || 'Unknown';

                        // 根据当前语言选择消息
                        const currentLang = document.getElementById('language-select')?.value || 'zh';
                        let message;

                        if (currentLang === 'zh') {{
                            message = langName + '版本的报告不存在。\\n\\n要生成它，请运行：\\npython analyzer.py . --lang ' + selectedLang;
                        }} else if (currentLang === 'ja') {{
                            message = langName + 'バージョンのレポートは存在しません。\\n\\n生成するには、次を実行してください：\\npython analyzer.py . --lang ' + selectedLang;
                        }} else {{
                            message = 'The ' + langName + ' version of this report does not exist.\\n\\nTo generate it, run:\\npython analyzer.py . --lang ' + selectedLang;
                        }}

                        alert(message);
                    }}
                }})
                .catch(() => {{
                    const langNames = {{'zh': '中文', 'en': 'English', 'ja': '日本語'}};
                    const langName = langNames[selectedLang] || 'Unknown';

                    // 根据当前语言选择消息
                    const currentLang = document.getElementById('language-select')?.value || 'zh';
                    let message;

                    if (currentLang === 'zh') {{
                        message = langName + '版本的报告不存在。\\n\\n要生成它，请运行：\\npython analyzer.py . --lang ' + selectedLang;
                    }} else if (currentLang === 'ja') {{
                        message = langName + 'バージョンのレポートは存在しません。\\n\\n生成するには、次を実行してください：\\npython analyzer.py . --lang ' + selectedLang;
                    }} else {{
                        message = 'The ' + langName + ' version of this report does not exist.\\n\\nTo generate it, run:\\npython analyzer.py . --lang ' + selectedLang;
                    }}

                    alert(message);
                }});
        }}

        // 页面加载时显示当前语言
        document.addEventListener('DOMContentLoaded', function() {{
            const langSelect = document.getElementById('language-select');
            if (langSelect) {{
                const currentLang = langSelect.value;
                const langNames = {{'zh': '中文', 'en': 'English', 'ja': '日本語'}};
                console.log('Code Analysis Report - ' + langNames[currentLang] + ' version');
            }}
        }});
    </script>
</body>
</html>
        """

        # 写入HTML文件
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _format_comparison(self, metric: str, comparison_data: Dict, strings: Dict) -> str:
        """Format comparison data for HTML display"""
        if not comparison_data or metric not in comparison_data.get('summary', {}):
            return ''

        prev_value = comparison_data['summary'][metric]
        curr_value = self.results['summary'][metric]
        diff = curr_value - prev_value

        if diff == 0:
            diff_class = ''
            diff_symbol = '→'
        elif diff > 0:
            diff_class = 'positive'
            diff_symbol = '↑'
        else:
            diff_class = 'negative'
            diff_symbol = '↓'

        return f'<div class="stat-diff {diff_class}">{diff_symbol} {diff:+d} {strings["from_previous"]}</div>'

    def _generate_comparison_section(self, comparison_data: Dict, strings: Dict) -> str:
        """Generate comparison section HTML"""
        if not comparison_data:
            return ''

        prev_time = comparison_data['metadata']['scan_time']
        curr_time = self.results['metadata']['scan_time']

        comparison_html = f'''
        <div class="comparison-section">
            <h2>🔄 {strings['comparison_title']}</h2>
            <p><strong>{strings['previous_scan']}:</strong> {prev_time} | <strong>{strings['current_scan']}:</strong> {curr_time}</p>
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>{strings['metric']}</th>
                        <th>{strings['previous']}</th>
                        <th>{strings['current']}</th>
                        <th>{strings['change']}</th>
                        <th>{strings['percent_change']}</th>
                    </tr>
                </thead>
                <tbody>
        '''

        metric_keys = ['total_files', 'total_lines', 'code_lines', 'comment_lines', 'blank_lines', 'total_functions']

        for metric_key in metric_keys:
            metric_name = strings[metric_key]
            prev_val = comparison_data['summary'].get(metric_key, 0)
            curr_val = self.results['summary'].get(metric_key, 0)
            diff = curr_val - prev_val

            if prev_val != 0:
                pct_change = (diff / prev_val) * 100
                pct_str = f'{pct_change:+.1f}%'
            else:
                pct_str = 'N/A'

            diff_class = 'positive' if diff > 0 else 'negative' if diff < 0 else ''
            diff_symbol = '↑' if diff > 0 else '↓' if diff < 0 else '→'

            comparison_html += f'''
                    <tr>
                        <td><strong>{metric_name}</strong></td>
                        <td>{prev_val}</td>
                        <td>{curr_val}</td>
                        <td class="{diff_class}">{diff_symbol} {diff:+d}</td>
                        <td class="{diff_class}">{pct_str}</td>
                    </tr>
            '''

        comparison_html += '''
                </tbody>
            </table>
        </div>
        '''

        return comparison_html

    def _generate_language_chart(self, language_dist: Dict, strings: Dict) -> str:
        """Generate language distribution chart HTML"""
        if not language_dist:
            return f'<p>{strings["no_files_found"]}</p>'

        total_files = sum(language_dist.values())
        html = ''

        for lang, count in sorted(language_dist.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_files) * 100
            html += f'''
            <div class="language-bar">
                <div class="language-name">{lang}</div>
                <div class="language-bar-inner">
                    <div class="language-bar-fill" style="width: {percentage}%"></div>
                </div>
                <div class="language-count">{count} {strings["files_suffix"]} ({percentage:.1f}%)</div>
            </div>
            '''

        return html

    def _generate_file_rows(self) -> str:
        """Generate file rows for HTML table"""
        rows = ''
        for file_stats in self.results['files']:
            rows += f'''
            <tr>
                <td>{file_stats['file_path']}</td>
                <td>{file_stats['language']}</td>
                <td>{file_stats['total_lines']}</td>
                <td>{file_stats['code_lines']}</td>
                <td>{file_stats['comment_lines']}</td>
                <td>{file_stats['blank_lines']}</td>
                <td>{file_stats['function_count']}</td>
            </tr>
            '''

        return rows

    def _generate_warnings_section(self, strings: Dict) -> str:
        """Generate warnings section HTML"""
        warnings = self.results['warnings']
        html = f'''
        <div class="warning-box">
            <h2>⚠️ {strings["warnings"]} ({{}})</h2>
            <ul>
        '''.format(len(warnings))

        for warning in warnings[:10]:  # Show first 10 warnings
            html += f'<li>{warning}</li>'

        if len(warnings) > 10:
            html += f'<li>... and {len(warnings) - 10} more warnings</li>'

        html += '''
            </ul>
        </div>
        '''

        return html


def find_previous_result(result_dir: str) -> Optional[Dict]:
    """Find and load the most recent previous analysis result

    Args:
        result_dir: Directory containing result files

    Returns:
        Previous analysis results or None if not found
    """
    try:
        # Ensure directory exists
        os.makedirs(result_dir, exist_ok=True)

        # Find all JSON result files
        pattern = os.path.join(result_dir, "code_analysis_*.json")
        json_files = glob.glob(pattern)

        if not json_files:
            return None

        # Sort by modification time (newest first)
        json_files.sort(key=os.path.getmtime, reverse=True)

        # Load the most recent file (skip current run if it already exists)
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Verify it has the expected structure
                if 'summary' in data and 'metadata' in data:
                    return data
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load previous result {file_path}: {e}")
                continue

        return None
    except Exception as e:
        print(f"Warning: Error searching for previous results: {e}")
        return None


def ensure_result_directory() -> str:
    """Ensure the result directory exists and return its path

    Returns:
        Path to result directory
    """
    # 尝试多种可能的result目录位置
    possible_paths = []

    # 1. 当前目录下的result目录
    possible_paths.append(os.path.join(os.getcwd(), "result"))

    # 2. 当前目录下的my-claude-skill/result目录
    possible_paths.append(os.path.join(os.getcwd(), "my-claude-skill", "result"))

    # 3. 如果当前脚本在code-analyzer/scripts目录中，尝试找到项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 检查是否在code-analyzer/scripts目录中
    if "code-analyzer" in script_dir and "scripts" in script_dir:
        # 向上两级到code-analyzer目录的父目录
        code_analyzer_dir = os.path.dirname(script_dir)
        project_dir = os.path.dirname(code_analyzer_dir)
        possible_paths.append(os.path.join(project_dir, "result"))

    # 检查每个可能的路径，如果目录已存在则使用它
    for path in possible_paths:
        if os.path.exists(path) and os.path.isdir(path):
            return path

    # 如果都不存在，创建第一个路径（当前目录下的result目录）
    result_dir = possible_paths[0]
    os.makedirs(result_dir, exist_ok=True)
    return result_dir


def generate_output_filenames(result_dir: str, lang: str = 'zh') -> Tuple[str, str]:
    """Generate JSON and HTML filenames with timestamp

    Args:
        result_dir: Directory for output files
        lang: Language code for filename

    Returns:
        Tuple of (json_path, html_path)
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"code_analysis_{timestamp}.json"
    html_filename = f"code_analysis_{timestamp}_{lang}.html"

    json_path = os.path.join(result_dir, json_filename)
    html_path = os.path.join(result_dir, html_filename)

    return json_path, html_path


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='代码分析工具')
    parser.add_argument('directory', nargs='?', default='.', help='要分析的目录（默认为当前目录）')
    parser.add_argument('--output', '-o', help='输出JSON文件路径')
    parser.add_argument('--summary', '-s', action='store_true', help='只显示汇总信息')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    parser.add_argument('--no-html', action='store_true', help='不生成HTML报告')
    parser.add_argument('--no-comparison', action='store_true', help='不进行前后结果对比')
    parser.add_argument('--lang', default=None, choices=['en', 'zh', 'ja'], help='HTML报告语言: en (英文), zh (中文), ja (日文)。如果未指定，则生成所有语言的报告')
    parser.add_argument('--all-langs', action='store_true', help='生成所有语言的HTML报告（与不指定--lang效果相同）')

    args = parser.parse_args()

    # 检查目录是否存在
    if not os.path.exists(args.directory):
        print(f"错误: 目录 '{args.directory}' 不存在")
        sys.exit(1)

    # 创建分析器
    analyzer = CodeAnalyzer(args.directory)

    # 扫描和分析
    print(f"Analyzing directory: {args.directory}")
    results = analyzer.scan_directory()

    # 显示汇总信息
    analyzer.print_summary()

    # 确定输出文件路径
    json_path = args.output
    html_path = None
    comparison_data = None

    # 如果没有指定输出文件，使用默认的带时间戳的文件名
    if not json_path:
        result_dir = ensure_result_directory()
        # 当生成多语言报告时，html_path应为None，因为我们会有多个HTML文件
        # 传递'zh'作为默认语言给generate_output_filenames，但忽略其返回的html_path
        lang_for_filename = args.lang if args.lang is not None else 'zh'
        json_path, temp_html_path = generate_output_filenames(result_dir, lang_for_filename)
        # 只有当生成单语言报告时才使用html_path
        html_path = temp_html_path if args.lang is not None else None

        # 查找前一次结果进行比较（除非明确禁用）
        if not args.no_comparison:
            comparison_data = find_previous_result(result_dir)
            if comparison_data:
                print(f"\nFound previous analysis from {comparison_data['metadata']['scan_time']}")
                print("Comparison data will be included in the report.")
    else:
        # 如果指定了输出文件，仍然尝试查找前一次结果（在同一目录中）
        if not args.no_comparison:
            result_dir = os.path.dirname(json_path) or '.'
            comparison_data = find_previous_result(result_dir)
            if comparison_data:
                print(f"\nFound previous analysis from {comparison_data['metadata']['scan_time']}")

    # 输出JSON
    if json_path:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nDetailed results saved to: {json_path}")

    # 生成HTML报告（除非明确禁用）
    if not args.no_html:
        # 确定要生成哪些语言的报告
        languages_to_generate = []

        # 逻辑规则：
        # 1. 如果指定了--all-langs，生成所有语言
        # 2. 如果指定了--lang，只生成指定语言
        # 3. 如果未指定任何语言参数，默认生成所有语言
        if args.all_langs or args.lang is None:
            languages_to_generate = ['zh', 'en', 'ja']
            if args.lang is None and not args.all_langs:
                print(f"\nGenerating reports for all languages by default: Chinese, English, Japanese")
            else:
                print(f"\nGenerating reports for all languages: Chinese, English, Japanese")
        else:
            languages_to_generate = [args.lang]

        for lang in languages_to_generate:
            # 确定HTML文件路径
            lang_html_path = None
            if html_path is None:
                # 如果没有指定html_path，生成相应的文件名
                if json_path:
                    base_name = os.path.splitext(json_path)[0]
                    # 移除可能存在的语言后缀
                    base_name = re.sub(r'_(en|zh|ja)$', '', base_name)
                    lang_html_path = f"{base_name}_{lang}.html"
                else:
                    # 理论上不会走到这里，因为上面已经设置了html_path
                    result_dir = ensure_result_directory()
                    _, lang_html_path = generate_output_filenames(result_dir, lang)
            else:
                # 如果指定了html_path，修改语言后缀
                base_name = os.path.splitext(html_path)[0]
                base_name = re.sub(r'_(en|zh|ja)$', '', base_name)
                lang_html_path = f"{base_name}_{lang}.html"

            try:
                analyzer.generate_html_report(lang_html_path, comparison_data, lang)
                print(f"HTML report saved to: {lang_html_path}")
            except Exception as e:
                print(f"Warning: Could not generate {lang} HTML report: {e}")

    # 如果需要详细输出
    if args.verbose and results['files']:
        print(f"\n前10个文件的详细统计:")
        for i, file_stats in enumerate(results['files'][:10]):
            print(f"\n{i+1}. {file_stats['file_path']} ({file_stats['language']})")
            print(f"   总行数: {file_stats['total_lines']}")
            print(f"   代码行: {file_stats['code_lines']}")
            print(f"   注释行: {file_stats['comment_lines']}")
            print(f"   空行: {file_stats['blank_lines']}")
            print(f"   函数数: {file_stats['function_count']}")

        if len(results['files']) > 10:
            print(f"\n... 还有 {len(results['files']) - 10} 个文件")

    # 显示比较摘要（如果存在）
    if comparison_data:
        print(f"\n[Comparison Summary]:")
        # Use English strings for console output
        english_strings = analyzer.HTML_STRINGS['en']
        metric_keys = ['total_files', 'total_lines', 'code_lines', 'comment_lines', 'blank_lines', 'total_functions']

        for metric_key in metric_keys:
            metric_name = english_strings[metric_key]
            prev_val = comparison_data['summary'].get(metric_key, 0)
            curr_val = results['summary'].get(metric_key, 0)
            diff = curr_val - prev_val

            if prev_val != 0:
                pct_change = (diff / prev_val) * 100
                pct_str = f'({pct_change:+.1f}%)'
            else:
                pct_str = ''

            diff_symbol = '↑' if diff > 0 else '↓' if diff < 0 else '→'
            print(f"  {metric_name}: {prev_val} → {curr_val} {diff_symbol} {diff:+d} {pct_str}")

    return results


if __name__ == '__main__':
    main()