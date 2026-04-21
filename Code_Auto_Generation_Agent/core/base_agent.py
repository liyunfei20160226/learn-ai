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
        def should_continue(state: Dict[str, Any]) -> str:
            """判断是否需要继续：最后一条是工具调用则继续"""
            messages = state["messages"]
            last_message = messages[-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        def call_model(state: Dict[str, Any]) -> Dict[str, Any]:
            """调用 LLM，可能选择调用工具或直接回答"""
            messages = state["messages"]
            response = self.llm_with_tools.invoke(messages)
            return {"messages": [response]}

        workflow = StateGraph(Dict[str, Any])
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", self.tool_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    def run(self, user_input: str, recursion_limit: int = None, **prompt_kwargs: Any) -> Dict[str, Any]:
        """统一的运行入口（无日志输出）

        Args:
            user_input: 用户输入内容
            recursion_limit: 最大循环次数，默认使用配置中的 max_iterations
            **prompt_kwargs: 提示词模板变量

        Returns:
            包含 messages 的结果字典
        """
        limit = recursion_limit or self.config.max_iterations
        initial_state = {
            "messages": [
                SystemMessage(content=self._get_system_prompt(**prompt_kwargs)),
                HumanMessage(content=user_input),
            ]
        }

        return self.graph.invoke(initial_state, {"recursion_limit": limit})

    def run_stream(self, user_input: str, recursion_limit: int = None,
                   tool_callback: ToolLogCallback = None, **prompt_kwargs: Any) -> Dict[str, Any]:
        """流式运行入口（支持实时日志输出）

        Args:
            user_input: 用户输入内容
            recursion_limit: 最大循环次数，默认使用配置中的 max_iterations
            tool_callback: 工具调用回调函数 (node_name, tool_name, result)
            **prompt_kwargs: 提示词模板变量

        Returns:
            包含 messages 的结果字典
        """
        limit = recursion_limit or self.config.max_iterations
        initial_state = {
            "messages": [
                SystemMessage(content=self._get_system_prompt(**prompt_kwargs)),
                HumanMessage(content=user_input),
            ]
        }

        final_state = None
        for output in self.graph.stream(initial_state, {"recursion_limit": limit}):
            for node_name, node_output in output.items():
                if node_name == "tools" and tool_callback:
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        tool_name = msg.name
                        result = msg.content
                        tool_callback(node_name, tool_name, result)
            final_state = output

        return final_state if final_state else initial_state

    def get_last_message(self, result: Dict[str, Any]) -> str:
        """获取最后一条消息内容"""
        messages = result.get("messages", [])
        if messages:
            return messages[-1].content
        return ""
