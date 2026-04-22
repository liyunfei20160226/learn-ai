import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from prompts import PromptTemplate, get_prompt_loader

from .config import AgentConfig, get_config


class BaseAgentState(Dict):
    """Agent 状态基类"""
    messages: List[BaseMessage]

    # 安全控制
    iteration: int = 0              # 当前迭代次数（防死循环）
    start_time: float = 0           # 开始时间戳（超时控制）
    max_iterations: int = 50        # 最大迭代次数
    timeout_seconds: int = 300      # 超时时间（秒）

    # 基础统计
    tools_called: List[str] = []    # 已调用的工具列表
    tool_call_count: Dict[str, int] = {}  # 各工具调用次数


ToolLogCallback = Callable[[str, str, Optional[str]], None]


class BaseAgent(ABC):
    """所有 Agent 的抽象基类

    统一的工具初始化、系统提示、运行流程
    """

    def __init__(self, llm: BaseChatModel, working_dir: str, config: AgentConfig = None):
        self.llm = llm
        self.working_dir = working_dir
        self.config = config or get_config()
        self.role_name = self.__class__.__name__.replace("Agent", "")

        # Initialize prompt loader
        self.prompt_loader = get_prompt_loader(self.config.prompts_dir)

        self.tools = self._init_tools()
        self.tool_node = ToolNode(self.tools)
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.graph = self._build_graph()

    @abstractmethod
    def _init_tools(self) -> List:
        """定义并返回可用工具列表"""
        pass

    @abstractmethod
    def _get_prompt_template_name(self) -> str:
        """返回提示词模板文件名（不含 .md 后缀）"""
        pass

    def _get_system_prompt(self, **kwargs: Any) -> str:
        """从模板加载系统提示词

        Args:
            **kwargs: 模板变量

        Returns:
            渲染后的提示词
        """
        template_name = self._get_prompt_template_name()
        template: PromptTemplate = self.prompt_loader.load(template_name)
        return template.render(**kwargs)

    def _build_graph(self) -> Any:
        """构建 LangGraph ReAct 循环"""
        def should_continue(state: BaseAgentState) -> str:
            """判断是否需要继续：检查超时、迭代限制，然后看是否有工具调用"""
            # 1. 检查迭代次数
            if state["iteration"] >= state["max_iterations"]:
                print(f"⚠️ 超过最大迭代次数 ({state['max_iterations']})，强制结束")
                return END

            # 2. 检查超时
            elapsed = time.time() - state["start_time"]
            if elapsed >= state["timeout_seconds"]:
                print(f"⏰ 运行超时 ({elapsed:.1f}s >= {state['timeout_seconds']}s)，强制结束")
                return END

            # 3. 正常判断是否有工具调用
            messages = state["messages"]
            last_message = messages[-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        def call_model(state: BaseAgentState) -> Dict[str, Any]:
            """调用 LLM，可能选择调用工具或直接回答"""
            messages = state["messages"]
            response = self.llm_with_tools.invoke(messages)
            return {
                "messages": [response],
                "iteration": state["iteration"] + 1,
            }

        workflow = StateGraph(BaseAgentState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", self.tool_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    def run(self, user_input: str, recursion_limit: int = None,
            tool_callback: ToolLogCallback = None, **prompt_kwargs: Any) -> Dict[str, Any]:
        """统一的运行入口，支持实时日志输出回调。

        Args:
            user_input: 用户输入内容
            recursion_limit: 最大循环次数，默认使用配置中的 max_iterations
            tool_callback: 工具调用回调函数 (node_name, tool_name, result)
            **prompt_kwargs: 提示词模板变量

        Returns:
            包含完整 messages 历史的结果字典
        """
        limit = recursion_limit or self.config.max_iterations
        initial_state: BaseAgentState = {
            "messages": [
                SystemMessage(content=self._get_system_prompt(**prompt_kwargs)),
                HumanMessage(content=user_input),
            ],
            "iteration": 0,
            "start_time": time.time(),
            "max_iterations": limit,
            "timeout_seconds": self.config.openai_timeout or 300,
            "tools_called": [],
            "tool_call_count": {},
        }

        full_state = initial_state.copy()
        for output in self.graph.stream(initial_state, {"recursion_limit": limit + 10}):
            for node_name, node_output in output.items():
                # 累积所有状态字段
                for key, value in node_output.items():
                    if key == "messages":
                        full_state.setdefault("messages", []).extend(value)
                    else:
                        full_state[key] = value

                # 工具节点：更新统计信息
                if node_name == "tools":
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        tool_name = msg.name
                        # 统计调用次数
                        full_state["tool_call_count"][tool_name] = \
                            full_state["tool_call_count"].get(tool_name, 0) + 1
                        # 记录调用历史
                        full_state["tools_called"].append(tool_name)
                        # 调用日志回调
                        if tool_callback:
                            tool_callback(node_name, msg.name, msg.content)

        return full_state

    def get_last_message(self, result: Dict[str, Any]) -> str:
        """获取最后一条消息内容"""
        messages = result.get("messages", [])
        if messages:
            return messages[-1].content
        return ""
