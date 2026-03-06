#!/usr/bin/env python3
"""
代码分析器 - 分析代码文件的统计信息
支持多种编程语言的行数、注释、函数统计
"""

import os
import re
import json
import sys
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


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='代码分析工具')
    parser.add_argument('directory', nargs='?', default='.', help='要分析的目录（默认为当前目录）')
    parser.add_argument('--output', '-o', help='输出JSON文件路径')
    parser.add_argument('--summary', '-s', action='store_true', help='只显示汇总信息')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')

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

    # 输出JSON
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nDetailed results saved to: {args.output}")

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

    return results


if __name__ == '__main__':
    main()