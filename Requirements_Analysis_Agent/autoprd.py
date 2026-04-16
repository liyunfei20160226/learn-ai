#!/usr/bin/env python3
# AutoPRD - Automatic PRD Generation Agent
# 自动PRD生成Agent - 通过多轮自问自答完善需求，生成完整PRD

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# 设置编码，解决Windows控制台中文显示问题
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from dotenv import load_dotenv


def to_kebab_case(text: str) -> str:
    """将文本转换为kebab-case"""
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text).lower()
    words = text.split()[:5]
    result = '-'.join(words).strip('-')
    # 如果结果为空，返回默认名称
    return result if result else 'auto-generated'


def call_openai(prompt: str) -> str:
    """调用 OpenAI API (via LangChain)"""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print('错误: 使用 openai 工具时必须设置 OPENAI_API_KEY', file=sys.stderr)
        print('提示: 可以在项目根目录创建 .env 文件添加 OPENAI_API_KEY=your-key', file=sys.stderr)
        sys.exit(1)

    model = os.getenv('OPENAI_MODEL', 'gpt-4o')
    base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    timeout = int(os.getenv('OPENAI_TIMEOUT', '300'))
    max_retries = int(os.getenv('OPENAI_MAX_RETRIES', '3'))

    llm = ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=0.7,
        timeout=timeout,
        max_retries=max_retries,
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as e:
        print('\n❌ OpenAI API 调用失败', file=sys.stderr)
        print(f'错误信息: {str(e)}', file=sys.stderr)
        print('\n可能原因:', file=sys.stderr)
        print('  1. 网络连接问题或API地址不正确', file=sys.stderr)
        print('  2. API Key 无效或过期', file=sys.stderr)
        print('  3. API 服务暂时不可用（已重试后仍然失败）', file=sys.stderr)
        print('  4. 超过当前API Key的配额限制', file=sys.stderr)
        print('\n请检查你的 .env 配置后重试。', file=sys.stderr)
        sys.exit(1)


def call_claude(prompt: str, tool: str) -> str:
    """调用本地 claude 命令行工具"""
    cmd = ['claude', '--dangerously-skip-permissions', '--print']

    try:
        # Windows上需要shell=True才能正确找到.cmd扩展名的命令
        is_windows = sys.platform.startswith('win')
        result = subprocess.run(
            cmd,
            input=prompt.encode('utf-8'),
            capture_output=True,
            shell=is_windows
        )
        result.check_returncode()
        return result.stdout.decode('utf-8').strip()
    except Exception as e:
        print('\n❌ claude 调用失败', file=sys.stderr)
        print(f'错误信息: {str(e)}', file=sys.stderr)
        print('\n可能原因:', file=sys.stderr)
        print('  1. claude 命令行工具未安装或不在 PATH 中', file=sys.stderr)
        print('  2. 权限不足', file=sys.stderr)
        print('\n请检查你的 claude 安装后重试。', file=sys.stderr)
        sys.exit(1)


def call_ai(prompt: str, tool: str) -> str:
    """根据工具选择调用方式"""
    if tool == 'openai':
        return call_openai(prompt)
    else:
        return call_claude(prompt, tool)


def parse_analysis_output(analysis_output: str) -> list[dict[str, str]]:
    """解析AI分析输出，提取问题和AI回答列表"""
    questions = []

    # 宽松匹配：允许中文或英文冒号，允许任意空白
    question_pattern = re.compile(r'问题\s*[:：]\s*(.+?)(?=\s*回答\s*[:：])', re.UNICODE | re.DOTALL)
    answer_pattern = re.compile(r'回答\s*[:：]\s*(.+)', re.UNICODE | re.DOTALL)

    # 方法1: 按 --- 分隔块
    blocks = re.split(r'^\s*-{3,}\s*$', analysis_output, flags=re.MULTILINE)
    blocks = [b.strip() for b in blocks if b.strip()]

    for block in blocks:
        q_match = question_pattern.search(block)
        a_match = answer_pattern.search(block)
        if q_match and a_match:
            questions.append({
                'question': q_match.group(1).strip(),
                'ai_answer': a_match.group(1).strip()
            })

    # 如果方法1没找到，尝试方法2: 在整个文本中直接查找所有问题-回答对
    if not questions:
        # 查找所有 问题:...回答:... 模式
        all_pairs = re.findall(r'问题\s*[:：]\s*(.+?)\s*回答\s*[:：]\s*(.+?)(?=\s*问题\s*[:：]|$)', analysis_output, re.UNICODE | re.DOTALL)
        for q_text, a_text in all_pairs:
            q_text = q_text.strip()
            a_text = a_text.strip()
            if q_text and a_text:
                questions.append({
                    'question': q_text,
                    'ai_answer': a_text
                })

    # 如果方法2还没找到，尝试方法3: 逐行查找，只要找到问题行，后面就是回答直到下一个问题或结束
    if not questions:
        lines = analysis_output.splitlines()
        current_q = None
        current_a = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            q_match = re.match(r'问题\s*[:：]\s*(.+)', line)
            if q_match:
                # 保存上一个问题
                if current_q is not None and current_a:
                    questions.append({
                        'question': current_q.strip(),
                        'ai_answer': '\n'.join(current_a).strip()
                    })
                # 开始新问题
                current_q = q_match.group(1)
                current_a = []
            elif current_q is not None:
                a_match = re.match(r'回答\s*[:：]\s*(.+)', line)
                if a_match:
                    current_a.append(a_match.group(1))
                else:
                    current_a.append(line)
        # 保存最后一个问题
        if current_q is not None and current_a:
            questions.append({
                'question': current_q.strip(),
                'ai_answer': '\n'.join(current_a).strip()
            })

    return questions


def collect_user_answers(
    questions: list[dict[str, str]],
    task = None,
) -> str:
    """交互式收集用户回答，重新格式化为原输出格式

    Args:
        questions: 问题列表
        task: 可选，Web 环境下的 Task 对象，如果提供则等待 Web 前端回答
    """
    if not questions:
        return ''

    if task is not None:
        # Web 环境：存储问题等待用户前端回答
        from web.task_manager import TaskStatus, task_manager
        with task_manager._lock:
            task.pending_questions = questions
            task.status = TaskStatus.WAITING_FOR_ANSWER
            task.answer_condition = threading.Condition(task_manager._lock)
            task.answers_ready = False
            task.user_answers = []

        # 等待用户回答
        print(f"\n⚠️  等待 Web 前端用户回答 {len(questions)} 个问题...\n")
        with task.answer_condition:
            task.answer_condition.wait()

        # 用户回答完成，恢复运行
        from web.task_manager import task_manager
        with task_manager._lock:
            task.status = TaskStatus.RUNNING
            result = []
            for i, q in enumerate(questions):
                user_answer = task.user_answers[i]
                result.append({
                    'question': q['question'],
                    'answer': user_answer['answer'],
                })
    else:
        # CLI 环境：终端交互式收集
        result = []
        total = len(questions)
        for i, q in enumerate(questions, 1):
            print()
            print('=' * 60)
            print(f'问题 {i} / {total}')
            print('=' * 60)
            print(f'\n{q["question"]}\n')
            print('AI建议回答：')
            print(f'  {q["ai_answer"]}\n')
            print('请选择：')
            print('  [1] 使用AI建议回答')
            print('  [2] 我自己输入回答')
            print()

            while True:
                choice = input('你的选择 (1/2): ').strip()
                if choice in ['1', '2']:
                    break
                print('请输入 1 或 2')

            if choice == '1':
                final_answer = q['ai_answer']
            else:
                print('\n请输入你的回答（输入完后按 Ctrl+D 或回车两次结束，或直接回车使用AI回答）：')
                lines = []
                try:
                    while True:
                        line = input()
                        if not line and lines and lines[-1] == '':
                            break
                        lines.append(line)
                except EOFError:
                    pass
                user_input = '\n'.join(lines).strip()
                final_answer = user_input if user_input else q['ai_answer']

            result.append({
                'question': q['question'],
                'answer': final_answer,
            })
            print('=' * 60)
            print()

    # 重新格式化为原格式
    output = []
    for item in result:
        output.append('---')
        output.append(f'问题：{item["question"]}')
        output.append(f'回答：{item["answer"]}')
        output.append('---')

    return '\n'.join(output)


def should_skip_path(path: str) -> bool:
    """判断是否应该跳过这个路径"""
    skip_dirs = ['.git', 'node_modules', '__pycache__', '.venv', 'venv', '.idea', '.vscode', 'build', 'dist']
    skip_exts = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.pdf', '.zip', '.tar', '.gz', '.rar', '.exe', '.bin', '.pyc']
    p = Path(path)
    # 跳过隐藏目录/文件
    if p.name.startswith('.') and p.name != '.env':
        return True
    # 跳过缓存目录
    if p.name in skip_dirs:
        return True
    # 跳过二进制/图片
    if p.suffix.lower() in skip_exts:
        return True
    return False


def load_background_documents(background_path: str):
    """加载背景资料，支持单个文件或目录"""
    from langchain_community.document_loaders import (
        TextLoader, UnstructuredPDFLoader, UnstructuredWordDocumentLoader,
        UnstructuredPowerPointLoader, UnstructuredExcelLoader
    )

    documents = []
    path = Path(background_path)

    if path.is_file():
        # 单个文件
        if should_skip_path(str(path)):
            print(f'⚠️ 跳过不支持的文件类型: {path}')
            return []
        try:
            ext = path.suffix.lower()
            if ext in ['.pdf']:
                loader = UnstructuredPDFLoader(str(path))
            elif ext in ['.docx', '.doc']:
                loader = UnstructuredWordDocumentLoader(str(path))
            elif ext in ['.pptx', '.ppt']:
                loader = UnstructuredPowerPointLoader(str(path))
            elif ext in ['.xlsx', '.xls']:
                loader = UnstructuredExcelLoader(str(path), mode="elements")
            else:
                # 默认当作文本文件
                loader = TextLoader(str(path), encoding='utf-8')
            docs = loader.load()
            for doc in docs:
                doc.metadata['source'] = str(path)
            documents.extend(docs)
            print(f'✓ 加载文件: {path} ({len(docs)} 块)')
        except Exception as e:
            print(f'⚠️ 加载文件失败 {path}: {str(e)}，跳过')
            return []
    elif path.is_dir():
        # 目录，递归遍历
        for item in path.rglob('*'):
            if item.is_file() and not should_skip_path(str(item)):
                rel_path = item.relative_to(path)
                try:
                    ext = item.suffix.lower()
                    if ext in ['.pdf']:
                        loader = UnstructuredPDFLoader(str(item))
                    elif ext in ['.docx', '.doc']:
                        loader = UnstructuredWordDocumentLoader(str(item))
                    elif ext in ['.pptx', '.ppt']:
                        loader = UnstructuredPowerPointLoader(str(item))
                    elif ext in ['.xlsx', '.xls']:
                        loader = UnstructuredExcelLoader(str(item), mode="elements")
                    else:
                        loader = TextLoader(str(item), encoding='utf-8')
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata['source'] = str(rel_path)
                    documents.extend(docs)
                    print(f'✓ 加载文件: {rel_path} ({len(docs)} 块)')
                except Exception as e:
                    print(f'⚠️ 加载文件失败 {rel_path}: {str(e)}，跳过')
                    continue
    else:
        print(f'错误: 路径不存在: {background_path}', file=sys.stderr)
        sys.exit(1)

    return documents


def build_rag_vectorstore(documents):
    """构建RAG向量库"""
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    if not documents:
        return None

    # 统计有多少个不同的源文件
    source_files = set()
    for doc in documents:
        source = doc.metadata.get('source', '')
        if source:
            source_files.add(source)
    num_files = len(source_files)

    print(f'\n开始构建RAG索引：{num_files} 个文件，共 {len(documents)} 个原始块...')

    # 切分文本
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True
    )
    chunks = text_splitter.split_documents(documents)
    print(f'切分为 {len(chunks)} 个文本块')

    # 生成embedding，构建FAISS索引
    embedding_model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
    base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    api_key = os.getenv('OPENAI_API_KEY')
    timeout = int(os.getenv('OPENAI_TIMEOUT', '300'))
    max_retries = int(os.getenv('OPENAI_MAX_RETRIES', '3'))

    print(f'使用Embedding模型: {embedding_model}')
    embeddings = OpenAIEmbeddings(
        model=embedding_model,
        openai_api_key=api_key,
        openai_api_base=base_url,
        request_timeout=timeout,
        max_retries=max_retries
    )
    vectorstore = FAISS.from_documents(chunks, embeddings)

    print('✅ RAG索引构建完成')
    return vectorstore


def add_rag_background(prompt: str, query: str, vectorstore, topk: int) -> str:
    """添加检索到的背景资料到prompt"""
    if vectorstore is None:
        return prompt

    retriever = vectorstore.as_retriever(search_kwargs={"k": topk})
    relevant_docs = retriever.invoke(query)

    if not relevant_docs:
        return prompt

    prompt += '\n\n## 参考背景资料\n\n以下是现有项目相关资料，请参考这些内容回答问题。如果发现背景资料和当前问题相关，请优先遵循背景资料中的约定。\n\n'
    for i, doc in enumerate(relevant_docs, 1):
        source = doc.metadata.get('source', f'片段{i}')
        content = doc.page_content
        prompt += f'--- [{source}]\n{content}\n\n'

    return prompt


def run_prd_generation(
    requirement: str,
    tool: str,
    mode: str,
    max_iterations: int,
    output_dir: Path,
    vectorstore = None,
    rag_topk: int = 5,
    task = None,
) -> None:
    """Run the full PRD generation process.

    Args:
        requirement: User requirement description
        tool: AI tool to use (claude/openai)
        mode: run mode (auto/interactive)
        max_iterations: maximum number of iterations
        output_dir: output directory path
        vectorstore: optional pre-built RAG vectorstore
        rag_topk: number of top documents to retrieve from RAG
    """
    script_dir = Path(__file__).parent
    prompts_dir = script_dir / 'prompts'
    logs_dir = script_dir / 'logs'

    # Create directories
    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Log file
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_file = logs_dir / f'autoprd-{timestamp}.log'

    # Print startup info
    print('================================================')
    print('AutoPRD - Automatic PRD Generation Agent')
    print(f'需求: {requirement}')
    print(f'最大迭代次数: {max_iterations}')
    print(f'AI工具: {tool}')
    print(f'运行模式: {mode}')
    if tool == 'openai':
        model = os.getenv('OPENAI_MODEL', 'gpt-4o')
        base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        print(f'OpenAI模型: {model}')
        print(f'OpenAI API地址: {base_url}')
    if vectorstore:
        print(f'RAG检索片段数: {rag_topk}')
    print(f'输出目录: {output_dir}')
    print(f'日志文件: {log_file}')
    print('================================================')
    print()

    # Write log header
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f'AutoPRD started at {timestamp}\n')
        f.write(f'Requirement: {requirement}\n')
        f.write(f'Max iterations: {max_iterations}\n')
        f.write(f'Tool: {tool}\n')
        f.write('\n')

    prd_file = output_dir / 'prd.md'
    history_file = output_dir / 'iteration_history.md'
    current_iteration = 1

    # Resume from existing PRD if it exists
    if prd_file.exists():
        print('检测到已有PRD文件，启用断点续传...')
        print('从现有PRD继续迭代...\n')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write('Resuming from existing PRD\n\n')
    else:
        print('首次运行，生成初始PRD...\n')
        # Read system prompt
        with open(prompts_dir / 'autoprd-system.md', 'r', encoding='utf-8') as f:
            system_prompt = f.read()

        # Build initial prompt
        initial_prompt = f"""{system_prompt}

# 用户原始需求

{requirement}

请根据上述需求生成一份初始的完整PRD。遵循标准PRD结构，使用中文编写。

⚠️  **重要：直接输出PRD内容即可！不要输出思考过程，不要输出自问自答的问答历史，不要写"第一轮分析"这类内容。只需要纯PRD。**"""

        # Add RAG background
        if vectorstore:
            initial_prompt = add_rag_background(initial_prompt, requirement, vectorstore, rag_topk)

        print('生成初始PRD...')
        initial_output = call_ai(initial_prompt, tool)

        # Save initial PRD
        with open(prd_file, 'w', encoding='utf-8') as f:
            f.write(initial_output)
        # Initialize iteration history
        with open(history_file, 'w', encoding='utf-8') as f:
            f.write('# 迭代问答历史\n\n')
            f.write('## 初始PRD\n\n')
            f.write(initial_output)
            f.write('\n\n---\n\n')
        print(f'初始PRD已保存到 {prd_file}\n')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write('--- Initial PRD generated ---\n')
            f.write(initial_output)
            f.write('\n\n')

    # Start iteration loop
    while current_iteration <= max_iterations:
        print('------------------------------------------------')
        print(f'迭代 {current_iteration} / {max_iterations}')
        print('------------------------------------------------')
        print()

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write('------------------------------------------------\n')
            f.write(f'Iteration {current_iteration} / {max_iterations}\n')
            f.write('------------------------------------------------\n\n')

        # Read current PRD
        with open(prd_file, 'r', encoding='utf-8') as f:
            current_prd = f.read()

        # Read analysis prompt template
        with open(prompts_dir / 'autoprd-analysis.md', 'r', encoding='utf-8') as f:
            analysis_template = f.read()

        # Replace template variables
        analysis_prompt = analysis_template\
            .replace('{{USER_REQUIREMENT}}', requirement)\
            .replace('{{CURRENT_PRD}}', current_prd)

        # Add RAG background
        if vectorstore:
            analysis_prompt = add_rag_background(analysis_prompt, analysis_prompt, vectorstore, rag_topk)

        # Call AI for analysis
        print('正在分析PRD完整性...')
        analysis_output = call_ai(analysis_prompt, tool)

        # Check if complete
        if '<promise>COMPLETE</promise>' in analysis_output:
            print()
            print('✅ AI判定PRD已完整，结束迭代')
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write('\n✅ PRD marked as complete, stopping.\n')
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write('✅ AI判定PRD已完整，迭代结束\n')
            break

        # Interactive mode: let user answer
        if mode == 'interactive':
            questions = parse_analysis_output(analysis_output)
            if questions:
                print()
                print(f'检测到 {len(questions)} 个问题，请回答：')
                analysis_output = collect_user_answers(questions, task)
            else:
                print()
                print('⚠️  无法解析问题格式，使用AI原始输出继续')

        # Save analysis result to log and history
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f'--- Iteration {current_iteration} 分析结果 ---\n')
            f.write(analysis_output)
            f.write('\n\n')
        with open(history_file, 'a', encoding='utf-8') as f:
            f.write(f'## 迭代 {current_iteration} - 分析问答\n\n')
            f.write(analysis_output)
            f.write('\n\n---\n\n')

        # Integrate if there are new answers
        print('获取了新的问题和回答，正在整合到PRD...')

        # Read integration template
        with open(prompts_dir / 'autoprd-integration.md', 'r', encoding='utf-8') as f:
            integration_template = f.read()

        # Replace template variables
        integration_prompt = integration_template\
            .replace('{{CURRENT_PRD}}', current_prd)\
            .replace('{{QUESTIONS_ANSWERS}}', analysis_output)

        # Call AI integration
        integration_output = call_ai(integration_prompt, tool)

        # Save updated PRD
        with open(prd_file, 'w', encoding='utf-8') as f:
            f.write(integration_output)
        # Append to history
        with open(history_file, 'a', encoding='utf-8') as f:
            f.write(f'## 迭代 {current_iteration} - 更新后PRD\n\n')
            f.write(integration_output)
            f.write('\n\n---\n\n')
        print('PRD已更新\n')

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write('--- Updated PRD ---\n')
            f.write(integration_output)
            f.write('\n\n')

        current_iteration += 1

        # Check max iterations
        if current_iteration > max_iterations:
            print()
            print(f'⚠️  达到最大迭代次数 {max_iterations}，停止迭代')
            print('已输出当前所有结果，可增加--max-iterations重新运行断点续传')
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f'\n⚠️  Reached max iterations {max_iterations}, stopping.\n')
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write(f'⚠️  达到最大迭代次数 {max_iterations}，停止迭代\n')
            break

        time.sleep(2)

    print()
    print('================================================')
    print('迭代完成，开始转换为Ralph prd.json格式...')
    print('================================================')
    print()

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write('\n================================================\n')
        f.write('Iteration complete, converting to Ralph prd.json...\n')
        f.write('================================================\n\n')

    # Convert to Ralph prd.json
    with open(prd_file, 'r', encoding='utf-8') as f:
        final_prd = f.read()

    # Extract project name from first heading
    project_name = requirement
    for line in final_prd.splitlines():
        if line.startswith('#'):
            project_name = re.sub(r'^#\s*', '', line).strip()
            break

    # Generate branch name
    branch_name = to_kebab_case(project_name)
    branch_name = f'autoprd/{branch_name}'[:50]

    # Extract project description from first non-empty line
    project_description = requirement
    for line in final_prd.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            project_description = line
            break

    # Read conversion template
    with open(prompts_dir / 'autoprd-conversion.md', 'r', encoding='utf-8') as f:
        conversion_template = f.read()

    # Replace template variables
    conversion_prompt = conversion_template\
        .replace('{project_name}', project_name)\
        .replace('{branch_name}', branch_name)\
        .replace('{project_description}', project_description)\
        .replace('{final_prd}', final_prd)

    # Call AI to generate prd.json
    print('正在生成prd.json...')
    json_output = call_ai(conversion_prompt, tool)

    # Clean JSON output - extract JSON from possible markdown wrapping
    match = re.search(r'(\{.*\})', json_output, re.DOTALL)
    if match:
        clean_json = match.group(1)
    else:
        # Remove markdown code block markers ```json ... ```
        clean_json = re.sub(r'^```(?:json)?\n', '', json_output)
        clean_json = re.sub(r'\n```$', '', clean_json)
        clean_json = clean_json.strip()

    # Pre-processing: fix common JSON formatting issues
    # 1. Remove any trailing commas before closing brackets
    clean_json = re.sub(r',\s*([\]}])', r'\1', clean_json)
    # 2. Fix common issue: unescaped quotes inside strings
    # This is a heuristic but helps with common cases
    def fix_unescaped_quotes(s):
        # Find positions between " that are not preceded by \
        result = []
        i = 0
        in_string = False
        while i < len(s):
            if s[i] == '"' and (i == 0 or s[i-1] != '\\'):
                if in_string:
                    # closing quote
                    result.append('"')
                    in_string = False
                else:
                    # opening quote
                    result.append('"')
                    in_string = True
            elif s[i] == '"' and s[i-1] == '\\':
                # already escaped, keep it
                result.append(s[i])
                i += 1
                in_string = not in_string if not in_string else in_string
            else:
                if in_string and s[i] == '"':
                    # unescaped quote inside string, escape it
                    result.append('\\')
                    result.append('"')
                else:
                    result.append(s[i])
                in_string = not in_string if not in_string else in_string
            i += 1
        return ''.join(result)

    try:
        clean_json = fix_unescaped_quotes(clean_json)
    except Exception:
        # if our heuristic fails, proceed with original
        pass

    # Parse and re-serialize with Python to ensure correct escaping of quotes
    # This fixes issues where AI doesn't properly escape double quotes in content
    try:
        parsed = json.loads(clean_json)
        # Save prd.json with proper JSON formatting and escaping
        json_file = output_dir / 'prd.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
        print(f'✅ prd.json 已保存到 {json_file}')
    except json.JSONDecodeError as e:
        print(f'⚠️ AI输出JSON格式不正确，尝试修复后仍然无法解析，保存原始输出: {e}')
        print('⚠️ 请手动修复JSON格式后使用')
        # Fallback: save original output
        json_file = output_dir / 'prd.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            f.write(clean_json)

    print(f'prd.json 已保存到 {json_file}')
    print()

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f'prd.json saved to {json_file}\n')
        f.write('\n')

    # Done
    print('================================================')
    print('✅ AutoPRD 完成！')
    print('================================================')
    print()
    print('输出文件：')
    print(f'  PRD: {prd_file}')
    print(f'  prd.json: {json_file}')
    print()
    print('接下来可以将prd.json复制到Ralph项目目录进行自动化开发：')
    print(f'  cp {json_file} /path/to/ralph/')
    print('  cd /path/to/ralph && ./ralph.sh')
    print()


def main():
    # 加载 .env 文件
    if Path('.env').exists():
        print('从 .env 文件加载配置...')
        load_dotenv()

    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='AutoPRD - Automatic PRD Generation Agent'
    )
    parser.add_argument(
        'requirement',
        help='需求描述（一句话）'
    )
    # 从环境变量读取默认最大迭代次数
    default_max_iterations = int(os.getenv('MAX_ITERATIONS', '10'))
    parser.add_argument(
        '--max-iterations',
        type=int,
        default=default_max_iterations,
        help=f'最大迭代次数 (默认: {default_max_iterations}，可通过 .env 中 MAX_ITERATIONS 配置)'
    )
    parser.add_argument(
        '--output-dir',
        help='输出目录 (默认: 从需求自动生成)'
    )
    parser.add_argument(
        '--tool',
        choices=['claude', 'openai'],
        default='claude',
        help='AI工具 (默认: claude)'
    )
    parser.add_argument(
        '--mode',
        choices=['auto', 'interactive'],
        default='auto',
        help='运行模式: auto=全自动(默认), interactive=交互式问答'
    )
    parser.add_argument(
        '--background',
        type=str,
        help='单个背景资料文件，AI生成PRD时会参考这些内容'
    )
    parser.add_argument(
        '--background-dir',
        type=str,
        help='背景资料目录，递归遍历所有文件，AI生成PRD时会参考相关内容'
    )
    parser.add_argument(
        '--rag-topk',
        type=int,
        default=5,
        help='RAG每次检索返回多少个最相关片段 (默认: 5)'
    )
    args = parser.parse_args()

    # 如果是 openai，提前检查 API key
    if args.tool == 'openai' and not os.getenv('OPENAI_API_KEY'):
        print('错误: 使用 openai 工具时必须设置 OPENAI_API_KEY', file=sys.stderr)
        print('提示: 可以在项目根目录创建 .env 文件添加 OPENAI_API_KEY=your-key', file=sys.stderr)
        sys.exit(1)

    # 生成输出目录
    script_dir = Path(__file__).parent
    if not args.output_dir:
        feature_name = to_kebab_case(args.requirement)
        output_dir = script_dir / 'output' / feature_name
    else:
        output_dir = Path(args.output_dir)

    # 初始化RAG（如果指定了背景资料）
    vectorstore = None
    if args.background or args.background_dir:
        print('\n=== 加载背景资料 ===')
        if args.background:
            documents = load_background_documents(args.background)
        else:
            documents = load_background_documents(args.background_dir)
        if documents:
            vectorstore = build_rag_vectorstore(documents)
        else:
            print('⚠️ 没有加载到有效文档，不使用背景资料')
        print()

    # 运行PRD生成
    run_prd_generation(
        requirement=args.requirement,
        tool=args.tool,
        mode=args.mode,
        max_iterations=args.max_iterations,
        output_dir=output_dir,
        vectorstore=vectorstore,
        rag_topk=args.rag_topk,
    )


def handle_exception(e: Exception, log_file: Path) -> None:
    """统一异常处理，输出友好信息并保存完整traceback到日志"""
    import traceback

    # 完整traceback写入日志文件
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write('\n' + '='*60 + '\n')
        f.write('ERROR occurred\n')
        f.write('='*60 + '\n')
        tb = traceback.format_exc()
        f.write(tb)
        f.write('\n')

    # 根据异常类型给出友好提示
    print('\n❌ 程序执行出错：')

    # 网络连接错误
    if 'openai' in str(type(e).__module__) and 'ConnectError' in str(type(e).__name__):
        print('网络连接失败，请检查：')
        print('  1. 网络是否连通')
        print('  2. OPENAI_BASE_URL 配置是否正确')
        print('  3. DNS解析是否正常')
    elif 'openai.APIConnectionError' in str(type(e)):
        print('OpenAI API连接失败，请检查：')
        print('  1. 网络是否连通')
        print('  2. OPENAI_BASE_URL 配置是否正确')
    elif 'openai.BadRequestError' in str(type(e)) or 'openai.APIStatusError' in str(type(e)):
        msg = str(e)
        if 'Model does not exist' in msg or 'model' in msg.lower() and ('exist' in msg.lower() or 'found' in msg.lower()):
            print('模型不存在，请检查：')
            print('  1. OPENAI_MODEL 配置是否正确')
            print('  2. OPENAI_EMBEDDING_MODEL 配置是否正确')
        else:
            print('API请求错误，请检查：')
            print('  1. API Key是否正确')
            print('  2. 模型是否支持当前功能')
    elif 'openai.AuthenticationError' in str(type(e)):
        print('API Key认证失败，请检查：')
        print('  1. OPENAI_API_KEY 配置是否正确')
    elif 'openai.RateLimitError' in str(type(e)):
        print('触发API速率限制或额度不足，请检查：')
        print('  1. API账号剩余额度')
        print('  2. 请求频率是否过高')
    elif isinstance(e, KeyboardInterrupt):
        print('用户中断了程序执行')
        exit(0)
    else:
        # 默认提示
        print(f'错误类型: {type(e).__name__}')
        print(f'错误信息: {str(e)}')

    print()
    print(f'完整错误日志已保存到: {log_file}')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # 尝试获取log_file路径，如果main还没创建就输出到stderr
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            logs_dir = Path('logs')
            logs_dir.mkdir(exist_ok=True)
            log_file = logs_dir / f'autoprd-error-{timestamp}.log'
            handle_exception(e, log_file)
        except Exception:
            # 如果连写日志都失败，直接print traceback
            import traceback
            traceback.print_exc()
        exit(1)
