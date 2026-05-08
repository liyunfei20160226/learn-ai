import time
import asyncio

print('='*60)
print('STEP 1: Import Agent')
print('='*60)
start = time.time()
from agent.core import Agent
print(f'  Import took {time.time() - start:.3f}s')

print()
print('='*60)
print('STEP 2: Create Agent with mock LLM')
print('='*60)

class MockLLM:
    provider_name = 'Mock'
    model = 'mock-model'

    async def chat_completion_stream(self, messages, tools=None, system=None):
        print(f'  [MockLLM] chat_completion_stream called')
        print(f'  [MockLLM] messages count = {len(messages)}')
        for i, m in enumerate(messages):
            print(f'    {i}: {m}')
        yield {'type': 'text', 'content': '你好！我是'}
        yield {'type': 'text', 'content': '你的'}
        yield {'type': 'text', 'content': '编程助手！'}
        print('  [MockLLM] stream completed')

start = time.time()
agent = Agent(llm_provider=MockLLM(), max_iterations=5)
print(f'  Agent creation took {time.time() - start:.3f}s')

print()
print('='*60)
print('STEP 3: Run agent with input "你好"')
print('='*60)
start = time.time()

async def main():
    result = await agent.run('你好')
    print(f'  Result: {result}')
    print(f'  Agent run took {time.time() - start:.3f}s')

asyncio.run(main())
print()
print('='*60)
print('ALL TESTS PASSED!')
print('='*60)
