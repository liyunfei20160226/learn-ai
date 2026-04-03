import os

# 用于加载.env文件中的环境变量
from dotenv import load_dotenv

# LangChain的Agent模块，提供创建Agent的功能
from langchain.agents import create_agent

# 工具模块，@tool装饰器可以把普通函数变成Agent可调用的工具
from langchain.tools import tool

# 定义消息类型（人发的消息、系统发的消息等）
from langchain_core.messages import HumanMessage, SystemMessage

# OpenAI模型的LangChain封装（这里用来调用DeepSeek）
from langchain_openai import ChatOpenAI

# 加载 .env 文件中的环境变量
load_dotenv()

# 从环境变量读取 API key 和 base URL
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")

if not api_key:
    raise ValueError("请设置 OPENAI_API_KEY 环境变量")

# 设置环境变量供LangChain使用
os.environ["OPENAI_API_KEY"] = api_key
os.environ["OPENAI_BASE_URL"] = base_url

# 初始化大语言模型
llm = ChatOpenAI(
    model="Qwen/Qwen3.5-397B-A17B",
    temperature=0,  # 温度=0，输出最确定性（每次都差不多）
    request_timeout=60,  # 60秒超时，避免卡住
)


# 定义工具函数
@tool  # 这个装饰器把普通函数变成Agent可调用的工具
def write_file(filename: str, content: str) -> str:
    """将内容写入本地文件。使用时请提供文件名和内容。"""
    try:
        # 确保文件所在目录存在
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

        # 写入文件
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

        abs_path = os.path.abspath(filename)
        return f"✅ 成功创建文件：{abs_path}"
    except Exception as e:
        return f"❌ 写入文件失败：{str(e)}"


# 创建系统提示词
system_prompt = """你是一个专业的代码生成助手。
你的任务是根据用户的需求生成对应的文件。
请使用 write_file 工具来创建文件。

当用户请求创建文件时，你应该：
1. 理解用户需要什么类型的文件
2. 生成合适的文件内容
3. 使用 write_file 工具创建文件

例如，如果用户说"创建一个 HTML 文件显示 Hello World"，你应该生成一个简单的 HTML 文件内容，然后用 write_file 工具创建它。
"""

print("🛠️  正在创建 agent...")

# 创建 agent - 使用正确的参数
try:
    agent_graph = create_agent(
        model=llm,  # 使用哪个AI模型
        tools=[write_file],  # 给Agent配备什么工具
        system_prompt=system_prompt,  # 告诉Agent它的角色
        debug=True,  # 显示详细执行过程
        name="file_writer_agent",  # 给 agent 起个名字
    )
    print("✅ Agent 创建成功！")
    """
当创建成功后，agent_graph内部其实是一个状态机，包含多个节点：
用户输入
    ↓
[思考节点] - AI分析用户说了什么，决定要做什么
    ↓
如果需要调用工具 → [工具节点] - 执行工具函数
    ↓                ↓
    ← 工具返回结果    ↓
    ↓                ↓
[继续思考] - 看工具执行结果，决定下一步
    ↓
如果完成 → [输出结果]
    """
except Exception as e:
    print(f"❌ Agent 创建失败: {e}")
    print("\n尝试备用方案：使用字符串模型标识符...")

    # 备用方案：使用字符串标识符
    try:
        agent_graph = create_agent(
            model="openai:deepseek-chat",  # 尝试使用字符串格式
            tools=[write_file],
            system_prompt=system_prompt,
            debug=True,
        )
        print("✅ Agent 创建成功（使用字符串标识符）！")
    except Exception as e2:
        print(f"❌ 备用方案也失败: {e2}")
        exit(1)


# 主程序
if __name__ == "__main__":
    user_request = (
        "创建一个 index.html，显示 'Hello from DeepSeek Agent!'，用 Tailwind 样式"
    )

    print(f"\n🤖 处理请求：{user_request}")
    print("=" * 60)

    try:
        # 准备输入 - 新版本的 agent 使用 messages 格式
        # 注意：create_agent 已经通过 system_prompt 参数添加了系统消息，这里只需要用户消息
        inputs = {
            "messages": [
                HumanMessage(content=user_request),   # 用户消息：具体请求
            ]
        }

        print("🔄 开始执行 agent...\n")

        # 使用 stream 模式执行，可以看到每一步的过程
        final_result = None
        for chunk in agent_graph.stream(inputs, stream_mode="updates"):
            print(f"📌 执行步骤: {chunk}")
            final_result = chunk

        print("\n" + "=" * 60)
        print("✅ Agent 执行完成！")

        # 或者使用 invoke 直接获取最终结果
        # result = agent_graph.invoke(inputs)
        # print(f"\n📝 执行结果: {result}")

        # 检查文件是否真的创建成功了
        if os.path.exists("index.html"):
            print("\n📄 文件内容预览：")
            with open("index.html", encoding="utf-8") as f:
                content = f.read()
                print("-" * 40)
                print(content[:500] + "..." if len(content) > 500 else content)
                print("-" * 40)

            print(f"\n📁 文件位置: {os.path.abspath('index.html')}")
            print(f"📊 文件大小: {os.path.getsize('index.html')} 字节")
        else:
            print("\n⚠️ 文件未创建，请检查执行过程")

    except Exception as e:
        print(f"❌ 执行失败：{str(e)}")
        import traceback

        traceback.print_exc()

"""
实际执行流程
第1步：Agent收到消息
    ↓
第2步：Agent思考"用户想要一个HTML文件，需要生成内容"
    ↓
第3步：Agent生成HTML代码（包含Tailwind样式）
    ↓
第4步：Agent决定调用write_file工具
    ↓
第5步：工具执行写入文件操作
    ↓
第6步：工具返回"✅ 成功创建文件：..."
    ↓
第7步：Agent看到工具执行成功，决定结束
    ↓
第8步：返回最终结果
"""
