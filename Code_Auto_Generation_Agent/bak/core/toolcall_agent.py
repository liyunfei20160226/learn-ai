"""基于 LangGraph 的工具调用 Agent 后端 - ReAct 模式"""

import os
from typing import Annotated, Any, Dict, List, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from config import get_config
from core.ai_backend import AIBackend
from utils.file_utils import write_file as file_utils_write_file
from utils.logger import get_logger

logger = get_logger()
config = get_config()


class AgentState(TypedDict):
    """Agent 运行状态"""
    prompt: str
    generated_files: Annotated[List[Dict[str, str]], "每次调用后追加"]
    messages: Annotated[List[BaseMessage], "每次调用后追加"]


class ToolCallingAgent(AIBackend):
    """基于 LangGraph 的文件操作 Agent - 使用 ReAct 工具调用模式

    核心优势：
    - 100% 准确的文件路径（通过工具参数传递，不需要正则解析）
    - 依赖任务接口一致性（完整代码缓存注入）
    - 完整的可观测性（每一步工具调用都有日志）
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
        working_dir: str = None
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.working_dir = working_dir or os.getcwd()

        # 运行时状态
        self._generated_files: List[Dict[str, str]] = []  # 缓存当前任务生成的文件

        # 定义工具
        self.tools = self._define_tools()
        self.tool_node = ToolNode(self.tools)

        # 初始化 LLM
        self.llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0.7,
            timeout=600
        )
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # 构建 LangGraph
        self.graph = self._build_graph()

    def _define_tools(self) -> List:
        """定义 5 个文件操作工具"""

        @tool
        def write_file(file_path: str, content: str) -> str:
            """新建或写入文件。如果文件已存在，将被覆盖。

            Args:
                file_path: 相对项目根目录的路径，如 "backend/app/main.py"
                content: 文件完整内容
            """
            full_path = os.path.join(self.working_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            if file_utils_write_file(full_path, content):
                # 记录到缓存
                self._generated_files.append({
                    "file_path": file_path,
                    "content": content
                })
                logger.info(f"✓ write_file: {file_path} ({len(content)} 字符)")
                return f"✓ 文件已写入: {file_path} ({len(content)} 字符)"
            else:
                logger.error(f"✗ write_file 失败: {file_path}")
                return f"✗ 写入失败: {file_path}"

        @tool
        def append_file(file_path: str, content: str) -> str:
            """向已存在的文件追加内容（用于大文件分块写入）

            Args:
                file_path: 相对项目根目录的路径
                content: 要追加的内容
            """
            full_path = os.path.join(self.working_dir, file_path)
            if not os.path.exists(full_path):
                logger.warning(f"✗ append_file: 文件不存在 {file_path}")
                return f"✗ 文件不存在，请先使用 write_file 创建: {file_path}"

            try:
                with open(full_path, 'a', encoding='utf-8') as f:
                    f.write(content)

                # 更新缓存
                for f in self._generated_files:
                    if f["file_path"] == file_path:
                        f["content"] += content
                        break

                logger.info(f"✓ append_file: {file_path} (+{len(content)} 字符)")
                return f"✓ 已追加内容到: {file_path} (+{len(content)} 字符)"
            except Exception as e:
                logger.error(f"✗ append_file 失败: {file_path}, {e}")
                return f"✗ 追加失败: {file_path}, {str(e)}"

        @tool
        def overwrite_file(file_path: str, content: str) -> str:
            """完全覆盖已有文件（用于错误修复场景）

            Args:
                file_path: 相对项目根目录的路径
                content: 文件完整的新内容
            """
            logger.info(f"🔧 overwrite_file: {file_path} ({len(content)} 字符)")
            return write_file(file_path, content)  # 复用 write_file 逻辑

        @tool
        def read_file(file_path: str) -> str:
            """读取已存在文件的完整内容（用于检查依赖接口或修复前查看）

            Args:
                file_path: 相对项目根目录的路径
            """
            full_path = os.path.join(self.working_dir, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    logger.info(f"✓ read_file: {file_path} ({len(content)} 字符)")
                    return f"--- {file_path} ---\n{content}"
                except Exception as e:
                    logger.error(f"✗ read_file 失败: {file_path}, {e}")
                    return f"✗ 读取失败: {file_path}, {str(e)}"
            logger.warning(f"✗ read_file: 文件不存在 {file_path}")
            return f"✗ 文件不存在: {file_path}"

        @tool
        def list_generated_files() -> str:
            """列出当前任务已生成的所有文件（用于回顾）"""
            if not self._generated_files:
                return "暂无已生成文件"
            return "已生成文件:\n" + "\n".join(
                f"- {f['file_path']} ({len(f['content'])} 字符)"
                for f in self._generated_files
            )

        return [write_file, append_file, overwrite_file, read_file, list_generated_files]

    def _build_graph(self) -> StateGraph:
        """构建 ReAct 循环图"""

        def should_continue(state: AgentState) -> str:
            """判断是否需要继续：最后一条是工具调用则继续，否则结束"""
            messages = state["messages"]
            last_message = messages[-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        def call_model(state: AgentState) -> Dict[str, Any]:
            """调用 LLM，可能选择调用工具或直接回答"""
            messages = state["messages"]
            response = self.llm_with_tools.invoke(messages)
            return {"messages": [response], "generated_files": state["generated_files"]}

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", self.tool_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    def is_available(self) -> bool:
        """检查配置是否完整"""
        if not self.api_key:
            logger.error("OpenAI API key 未提供")
            return False
        return True

    def implement_story(self, prompt: str, write_files: bool = True) -> str:
        """实现用户故事 - 使用工具调用模式

        Args:
            prompt: 实现 prompt
            write_files: 兼容接口参数（本后端总是写入文件）
        """
        logger.info("🚀 启动 ToolCallingAgent (ReAct 模式)")
        self._generated_files = []  # 清空缓存

        system_prompt = """你是一个专业的代码生成工程师。你的任务是根据用户提供的需求，
通过调用工具来生成代码文件。

工作流程：
1. 先完整理解需求、架构要求、验收标准
2. 列出需要创建的所有文件清单
3. 调用 write_file 逐个生成每个文件
4. 对于依赖文件，可以调用 read_file 查看接口确保一致
5. 特别大的文件可以分多次 append_file 追加
6. 所有文件生成完成后，用自然语言总结完成情况

重要规则：
- 文件路径必须从项目根目录开始（如 backend/app/main.py）
- 不要输出 markdown 代码块，所有文件都必须通过工具写入！
- 必须确保生成的代码之间接口、类型、命名、导入路径完全一致
- 写完后可以调用 list_generated_files 检查完整性
"""

        initial_state: AgentState = {
            "prompt": prompt,
            "generated_files": [],
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt)
            ]
        }

        try:
            result = self.graph.invoke(initial_state)

            final_message = result["messages"][-1]
            final_output = final_message.content if hasattr(final_message, 'content') else str(final_message)

            logger.info(f"✅ Agent 完成，共生成 {len(self._generated_files)} 个文件")

            # 返回摘要 + 文件列表
            files_summary = "\n".join(f"- {f['file_path']}" for f in self._generated_files)
            return f"{final_output}\n\n---\n生成的文件:\n{files_summary}"

        except Exception as e:
            logger.error(f"❌ Agent 执行失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"Agent 执行失败: {str(e)}")

    def fix_errors(self, original_prompt: str, errors: List[str], target_dir: str = None) -> str:
        """使用工具调用模式修复错误"""
        from prompts import get_fix_errors_prompt

        error_text = "\n".join(f"- {error}" for error in errors)
        template = get_fix_errors_prompt(target_dir or self.working_dir)

        fix_prompt = template.replace("{{ORIGINAL_PROMPT}}", original_prompt)
        fix_prompt = fix_prompt.replace("{{ERROR_LIST}}", error_text)
        fix_prompt = fix_prompt.replace("{{FILE_CONTENTS}}", "（请通过 read_file 工具读取需要修复的文件）")

        fix_prompt += """

⚠️ 修复特别说明：
1. 必须先调用 read_file 读取需要修复的文件完整内容
2. 然后使用 overwrite_file 工具覆盖完整文件
3. 不要使用 append_file 追加（会导致重复）
4. 每个文件只调用一次 overwrite_file
5. 修复后确保代码可以正常运行
"""

        return self.implement_story(fix_prompt)

    def get_generated_files(self) -> List[Dict[str, str]]:
        """获取当前任务生成的所有文件（用于任务级缓存）"""
        return self._generated_files.copy()
