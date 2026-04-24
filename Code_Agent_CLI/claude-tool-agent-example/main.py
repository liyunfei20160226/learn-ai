#!/usr/bin/env python3
"""
基于 Claude 的 LLM Code Agent 主程序示例
"""
import os
import asyncio
from typing import List, Dict, Any
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

from agent.tool_registry import ToolRegistry
from agent.tool_registry_initializer import initialize_tools
from agent.tool_executor import ToolExecutor


# 加载环境变量
load_dotenv()

# 初始化 Anthropic 客户端
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# 初始化工具注册表
initialize_tools()


async def chat_with_claude(prompt: str, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """与 Claude 进行对话并处理工具调用"""
    messages = history or []
    
    # 添加用户提示
    messages.append({
        "role": "user",
        "content": prompt
    })
    
    while True:
        # 调用 Claude API
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=messages,
            tools=ToolRegistry.get_tool_descriptions(),
            tool_choice={"type": "auto"}
        )
        
        # 处理响应
        if response.stop_reason == "tool_use":
            print("\n=== Claude 需要调用工具 ===")
            
            # 处理每个工具调用
            for tool_call in response.content:
                if tool_call.type == "tool_use":
                    print(f"调用工具: {tool_call.name}")
                    print(f"工具参数: {tool_call.input}")
                    
                    # 执行工具
                    tool_result = await ToolExecutor.handle_tool_call({
                        "name": tool_call.name,
                        "parameters": tool_call.input
                    })
                    
                    print(f"\n工具执行结果:\n{tool_result}")
                    
                    # 添加工具响应到消息历史
                    messages.append({
                        "role": "assistant",
                        "content": [{
                            "type": "tool_use",
                            "id": tool_call.id,
                            "name": tool_call.name,
                            "input": tool_call.input
                        }]
                    })
                    
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": tool_result
                        }]
                    })
            
            # 继续循环，让 Claude 根据工具结果生成最终回答
            continue
        else:
            # 没有工具调用，返回最终响应
            return {
                "messages": messages,
                "final_response": response.content[0].text,
                "usage": response.usage
            }


async def main():
    """主函数"""
    print("=== Claude Code Agent 示例 ===")
    print("输入 'quit' 或 'exit' 退出程序")
    
    history = []
    
    while True:
        user_input = input("\n用户: ")
        
        if user_input.lower() in ["quit", "exit"]:
            print("再见!")
            break
            
        if not user_input.strip():
            continue
        
        # 与 Claude 对话
        result = await chat_with_claude(user_input, history)
        
        # 更新历史
        history = result["messages"]
        
        # 打印结果
        print(f"\nClaude: {result['final_response']}")
        
        # 打印使用统计
        print(f"\n--- 使用统计 ---")
        print(f"输入令牌: {result['usage'].input_tokens}")
        print(f"输出令牌: {result['usage'].output_tokens}")


if __name__ == "__main__":
    asyncio.run(main())
