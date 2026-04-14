"""
CodeStructureAgent - 代码结构分析Agent
职责：
1. 遍历目标目录生成目录树
2. 统计各类型文件数量
3. 根据配置文件自动识别技术栈
4. 调用LLM生成整体架构摘要
"""
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
import yaml
from langchain_openai import ChatOpenAI

from .base import BaseAgent
from ..types.pipeline import PipelineState
from ..types.artifacts import CodeStructure
from ..prompts import get_prompt


class CodeStructureAgent(BaseAgent):
    """代码结构分析Agent - 扫描目录，识别技术栈，生成整体架构摘要"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    async def run(self, state: PipelineState) -> PipelineState:
        """执行代码结构分析"""
        target_dir = state.target_code_dir
        if not target_dir or not os.path.isdir(target_dir):
            # 目录不存在，设置空结果
            state.code_structure = CodeStructure(
                stage_id="code_structure",
                project_id=state.project_id,
                data=CodeStructure.CodeStructureData(
                    root_directory=str(target_dir),
                    directory_tree="",
                    file_types=[],
                    detected_tech=[],
                    frontend_detected=False,
                    backend_detected=False,
                    database_detected=False,
                    summary="Error: Target directory does not exist or is not accessible."
                )
            )
            state.update_timestamp()
            return state

        # 步骤1：扫描目录，生成目录树，统计文件类型
        directory_tree, file_type_stats, detected_tech = self._scan_directory(target_dir)

        # 判断是否检测到前端/后端/数据库
        frontend_detected = any(t["category"] == "frontend" for t in detected_tech)
        backend_detected = any(t["category"] == "backend" for t in detected_tech)
        database_detected = any(t["category"] == "database" for t in detected_tech)

        # 步骤2：构建上下文，调用LLM生成架构摘要
        context = self._build_context(
            target_dir, directory_tree, file_type_stats, detected_tech,
            frontend_detected, backend_detected, database_detected
        )
        # 如果有回流反馈（上次质量闸门不通过），添加到上下文
        if state.backflow_feedback:
            context += "\n\n# 上次质量检查反馈\n"
            context += "上次分析未通过质量检查，反馈意见如下，请根据反馈改进你的分析:\n"
            context += state.backflow_feedback
            context += "\n"
        prompt_template = get_prompt("code_structure")
        full_prompt = prompt_template.replace("{{CONTEXT}}", context)

        response = self.llm.invoke(full_prompt)
        response_text = response.content.strip()

        # 解析响应，获取摘要
        summary = self._parse_response(response_text)

        # 构建制品
        file_type_list = [
            CodeStructure.FileTypeCount(extension=ext, count=stats["count"], total_lines=stats["lines"])
            for ext, stats in file_type_stats.items()
        ]

        detected_tech_list = [
            CodeStructure.DetectedTech(
                category=tech["category"],
                name=tech["name"],
                version=tech.get("version"),
                detection_source=tech["detection_source"]
            ) for tech in detected_tech
        ]

        state.code_structure = CodeStructure(
            stage_id="code_structure",
            project_id=state.project_id,
            data=CodeStructure.CodeStructureData(
                root_directory=str(target_dir),
                directory_tree=directory_tree,
                file_types=file_type_list,
                detected_tech=detected_tech_list,
                frontend_detected=frontend_detected,
                backend_detected=backend_detected,
                database_detected=database_detected,
                summary=summary
            )
        )

        state.update_timestamp()
        return state

    def _scan_directory(self, root_dir: str) -> Tuple[str, Dict, List[Dict]]:
        """扫描目录，生成目录树，统计文件，识别技术"""
        root_path = Path(root_dir)

        # 排除的目录
        exclude_dirs = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache', 'dist', 'build'}

        # 技术识别规则：根据文件名识别技术栈
        tech_detection_rules = [
            # 前端
            ('package.json', 'frontend', 'Node.js'),
            ('package-lock.json', 'frontend', 'npm'),
            ('yarn.lock', 'frontend', 'Yarn'),
            ('pnpm-lock.yaml', 'frontend', 'pnpm'),
            ('next.config.js', 'frontend', 'Next.js'),
            ('next.config.ts', 'frontend', 'Next.js'),
            ('vite.config.js', 'frontend', 'Vite'),
            ('vite.config.ts', 'frontend', 'Vite'),
            ('react', 'frontend', 'React'),
            ('vue.config.js', 'frontend', 'Vue CLI'),
            ('angular.json', 'frontend', 'Angular'),
            # 后端 Python
            ('pyproject.toml', 'backend', 'Python'),
            ('requirements.txt', 'backend', 'Python'),
            ('setup.py', 'backend', 'Python'),
            ('Pipfile', 'backend', 'Python Pipenv'),
            ('poetry.lock', 'backend', 'Python Poetry'),
            ('manage.py', 'backend', 'Django'),
            ('wsgi.py', 'backend', 'Django'),
            ('fastapi', 'backend', 'FastAPI'),
            ('flask', 'backend', 'Flask'),
            # 后端 Node.js
            ('server.js', 'backend', 'Node.js'),
            ('app.js', 'backend', 'Express'),
            ('nest-cli.json', 'backend', 'NestJS'),
            # 后端 Java
            ('pom.xml', 'backend', 'Java Maven'),
            ('build.gradle', 'backend', 'Java Gradle'),
            ('gradlew', 'backend', 'Java Gradle'),
            # 后端 Go
            ('go.mod', 'backend', 'Go'),
            ('go.sum', 'backend', 'Go'),
            # 后端 Rust
            ('Cargo.toml', 'backend', 'Rust'),
            # 数据库
            ('schema.sql', 'database', 'SQL'),
            ('migrations', 'database', 'Database Migrations'),
            ('orm', 'backend', 'ORM'),
            ('models.py', 'database', 'Python ORM'),
            ('entity.java', 'database', 'JPA Entity'),
            # 配置文件
            ('.env', 'tooling', 'Environment Config'),
            ('docker-compose.yml', 'tooling', 'Docker Compose'),
            ('Dockerfile', 'tooling', 'Docker'),
            ('Makefile', 'tooling', 'Make'),
            ('README.md', 'tooling', 'README'),
        ]

        file_type_stats = defaultdict(lambda: {"count": 0, "lines": 0})
        detected_tech = []

        # 生成目录树
        def generate_tree(path: Path, prefix: str = "") -> str:
            lines = []
            entries = sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
            entries_count = len(entries)

            for i, entry in enumerate(entries):
                if entry.name in exclude_dirs or entry.name.startswith('.'):
                    continue

                connector = "└── " if i == entries_count - 1 else "├── "
                lines.append(f"{prefix}{connector}{entry.name}/" if entry.is_dir() else f"{prefix}{connector}{entry.name}")

                # 统计文件类型
                if entry.is_file():
                    ext = entry.suffix.lower().lstrip('.')
                    if not ext:
                        ext = "(no ext)"
                    file_type_stats[ext]["count"] += 1
                    # 统计行数
                    try:
                        with open(entry, 'r', encoding='utf-8', errors='ignore') as f:
                            lines_count = sum(1 for _ in f)
                        file_type_stats[ext]["lines"] += lines_count
                    except Exception:
                        pass

                # 技术检测
                for rule_filename, category, name in tech_detection_rules:
                    if entry.name == rule_filename or (rule_filename in entry.name and entry.is_dir()):
                        version = None
                        detection_source = str(entry.relative_to(root_path))
                        # 尝试从配置文件提取版本
                        if rule_filename in ['package.json', 'pyproject.toml']:
                            try:
                                with open(entry, 'r', encoding='utf-8') as f:
                                    data = yaml.safe_load(f)
                                if rule_filename == 'package.json' and 'version' in data:
                                    version = data.get('version')
                                elif rule_filename == 'pyproject.toml' and 'project' in data and 'version' in data['project']:
                                    version = data['project']['version']
                            except Exception:
                                pass
                        detected_tech.append({
                            "category": category,
                            "name": name,
                            "version": version,
                            "detection_source": detection_source
                        })

                if entry.is_dir():
                    new_prefix = prefix + ("    " if i == entries_count - 1 else "│   ")
                    lines.append(generate_tree(entry, new_prefix))

            return "\n".join(lines)

        directory_tree = f"{root_path.name}/\n" + generate_tree(root_path)

        # 去重检测到的技术
        unique_tech = {}
        for tech in detected_tech:
            key = f"{tech['category']}:{tech['name']}"
            if key not in unique_tech:
                unique_tech[key] = tech
        detected_tech = list(unique_tech.values())

        # 根据扩展名推断语言
        for ext in file_type_stats:
            if ext in ['js', 'jsx', 'ts', 'tsx', 'vue', 'svelte', 'css', 'scss', 'less', 'html']:
                if not any(t['name'] == ext.upper() for t in detected_tech):
                    category = 'frontend'
                    name = ext.upper()
                    detected_tech.append({
                        "category": category,
                        "name": name,
                        "version": None,
                        "detection_source": f"*.{ext} files"
                    })
            elif ext in ['py', 'java', 'go', 'rs', 'rb', 'php', 'cs', 'cpp', 'c', 'h']:
                category = 'backend'
                name = ext.upper()
                if not any(t['name'] == name for t in detected_tech):
                    detected_tech.append({
                        "category": category,
                        "name": name,
                        "version": None,
                        "detection_source": f"*.{ext} files"
                    })
            elif ext in ['sql']:
                category = 'database'
                name = 'SQL'
                if not any(t['name'] == name for t in detected_tech):
                    detected_tech.append({
                        "category": category,
                        "name": name,
                        "version": None,
                        "detection_source": f"*.{ext} files"
                    })

        return directory_tree, file_type_stats, detected_tech

    def _build_context(
        self, target_dir: str, directory_tree: str,
        file_type_stats: Dict, detected_tech: List[Dict],
        frontend_detected: bool, backend_detected: bool, database_detected: bool
    ) -> str:
        """构建LLM上下文"""
        lines = []
        lines.append(f"# 目标代码目录: {target_dir}")
        lines.append("")
        lines.append("# 目录结构")
        lines.append(directory_tree)
        lines.append("")
        lines.append("# 文件类型统计")
        for ext, stats in sorted(file_type_stats.items(), key=lambda x: -x[1]["count"]):
            lines.append(f"- {ext}: {stats['count']} files, {stats['lines']} lines")
        lines.append("")
        lines.append("# 识别出的技术栈")
        for tech in detected_tech:
            version_str = f" v{tech['version']}" if tech.get('version') else ""
            lines.append(f"- [{tech['category']}] {tech['name']}{version_str} (from {tech['detection_source']})")
        lines.append("")
        lines.append("# 检测结果汇总")
        lines.append(f"- 前端代码检测: {'是' if frontend_detected else '否'}")
        lines.append(f"- 后端代码检测: {'是' if backend_detected else '否'}")
        lines.append(f"- 数据库相关代码检测: {'是' if database_detected else '否'}")
        lines.append("")
        lines.append("请根据以上信息，生成一份整体架构分析摘要：")
        lines.append("1. 这个项目是什么类型的项目？")
        lines.append("2. 整体目录结构划分是否合理？有什么初步 observations？")
        lines.append("3. 技术栈组合是否合理？")
        lines.append("4. 项目大概是做什么的？")

        return "\n".join(lines)

    def _parse_response(self, response_text: str) -> str:
        """解析LLM响应，提取摘要"""
        # 直接返回整个响应作为摘要，LLM应该已经生成了清晰的分析
        return response_text
