"""
Day 5: Prototype to Production
==============================

本番環境への移行に必要な概念:
1. Multi-Agent Systems（マルチエージェントシステム）
2. Sequential Agents（順次実行エージェント）
3. Parallel Agents（並列実行エージェント）
4. Agent Orchestration（エージェントのオーケストレーション）
5. Agent2Agent (A2A) Protocol（エージェント間通信）
6. Production Best Practices（本番環境のベストプラクティス）
"""

import asyncio
import os
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


# ===========================================
# 1. 専門エージェントの定義
# ===========================================

# --- Research Agent（調査エージェント）---
def search_web(query: str) -> dict:
    """Search the web for information."""
    # シミュレートされたWeb検索
    mock_results = {
        "ai trends": "Top AI trends in 2025: Multi-agent systems, AI agents in production, Context engineering",
        "python best practices": "Python best practices: Type hints, async/await, virtual environments, testing",
        "machine learning": "ML advances: Foundation models, fine-tuning, RAG systems, agent architectures",
    }
    
    for key, value in mock_results.items():
        if key in query.lower():
            return {"status": "success", "query": query, "results": value}
    
    return {"status": "success", "query": query, "results": f"General information about: {query}"}


research_agent = Agent(
    model='gemini-2.0-flash',
    name='research_agent',
    description="A research specialist that searches for information.",
    instruction="""You are a research specialist. Your job is to:
1. Search for information using the search_web tool
2. Summarize findings clearly and concisely
3. Provide relevant facts and data

Always use the search_web tool to find information before responding.
""",
    tools=[search_web],
)


# --- Analysis Agent（分析エージェント）---
def analyze_data(data: str, analysis_type: str = "summary") -> dict:
    """Analyze data and provide insights."""
    analysis_types = {
        "summary": f"Summary: {data[:100]}... Key points extracted.",
        "sentiment": f"Sentiment Analysis: The text appears to be neutral/informative in tone.",
        "keywords": f"Key Topics: AI, agents, production, development",
        "recommendations": f"Recommendations based on analysis: Focus on testing, monitoring, and scalability.",
    }
    
    return {
        "status": "success",
        "analysis_type": analysis_type,
        "result": analysis_types.get(analysis_type, "General analysis completed.")
    }


analysis_agent = Agent(
    model='gemini-2.0-flash',
    name='analysis_agent',
    description="An analysis specialist that processes and analyzes data.",
    instruction="""You are an analysis specialist. Your job is to:
1. Analyze data provided using the analyze_data tool
2. Extract insights and patterns
3. Provide actionable recommendations

Use different analysis types: summary, sentiment, keywords, recommendations.
""",
    tools=[analyze_data],
)


# --- Writer Agent（執筆エージェント）---
def format_document(content: str, format_type: str = "report") -> dict:
    """Format content into a structured document."""
    templates = {
        "report": f"""
# Report
## Executive Summary
{content[:200]}...

## Key Findings
- Finding 1
- Finding 2
- Finding 3

## Conclusion
Based on the analysis...
""",
        "email": f"""
Subject: Summary Report

Dear Team,

{content[:150]}...

Best regards,
AI Assistant
""",
        "presentation": f"""
# Slide 1: Title
{content[:50]}

# Slide 2: Key Points
- Point 1
- Point 2

# Slide 3: Conclusion
Summary...
""",
    }
    
    return {
        "status": "success",
        "format": format_type,
        "document": templates.get(format_type, content)
    }


writer_agent = Agent(
    model='gemini-2.0-flash',
    name='writer_agent',
    description="A writing specialist that creates formatted documents.",
    instruction="""You are a writing specialist. Your job is to:
1. Take information and format it into documents
2. Use the format_document tool with appropriate format types
3. Create clear, professional content

Available formats: report, email, presentation.
""",
    tools=[format_document],
)


# ===========================================
# 2. オーケストレーターエージェント
# ===========================================

def delegate_to_research(query: str) -> dict:
    """Delegate research tasks to the research agent."""
    return {"status": "delegated", "agent": "research_agent", "task": query}


def delegate_to_analysis(data: str) -> dict:
    """Delegate analysis tasks to the analysis agent."""
    return {"status": "delegated", "agent": "analysis_agent", "task": data}


def delegate_to_writer(content: str, format_type: str) -> dict:
    """Delegate writing tasks to the writer agent."""
    return {"status": "delegated", "agent": "writer_agent", "task": content, "format": format_type}


orchestrator_agent = Agent(
    model='gemini-2.0-flash',
    name='orchestrator',
    description="A manager agent that coordinates tasks between specialist agents.",
    instruction="""You are a project manager that coordinates work between specialist agents.

Available specialists:
1. research_agent - For searching and gathering information
2. analysis_agent - For analyzing data and extracting insights
3. writer_agent - For creating formatted documents

For complex tasks:
1. First, delegate research to gather information
2. Then, delegate analysis to process the information
3. Finally, delegate to the writer for final output

Coordinate the workflow efficiently and summarize results.
""",
    tools=[delegate_to_research, delegate_to_analysis, delegate_to_writer],
)


# ===========================================
# 3. マルチエージェント実行クラス
# ===========================================

@dataclass
class AgentResult:
    """エージェントの実行結果"""
    agent_name: str
    input_query: str
    output: str
    execution_time: float
    success: bool
    error: str = ""


class MultiAgentSystem:
    """マルチエージェントシステム"""
    
    def __init__(self):
        self.agents = {
            "research": research_agent,
            "analysis": analysis_agent,
            "writer": writer_agent,
            "orchestrator": orchestrator_agent,
        }
        self.execution_log: list[AgentResult] = []
    
    async def run_agent(self, agent_name: str, query: str) -> AgentResult:
        """単一のエージェントを実行"""
        start_time = time.time()
        
        if agent_name not in self.agents:
            return AgentResult(
                agent_name=agent_name,
                input_query=query,
                output="",
                execution_time=0,
                success=False,
                error=f"Agent '{agent_name}' not found"
            )
        
        agent = self.agents[agent_name]
        
        try:
            session_service = InMemorySessionService()
            session = await session_service.create_session(
                app_name="multi_agent_app",
                user_id="user1"
            )
            
            runner = Runner(
                agent=agent,
                app_name="multi_agent_app",
                session_service=session_service
            )
            
            content = types.Content(
                role="user",
                parts=[types.Part(text=query)]
            )
            
            response_text = ""
            async for event in runner.run_async(
                user_id="user1",
                session_id=session.id,
                new_message=content
            ):
                if event.is_final_response():
                    response_text = event.content.parts[0].text
            
            execution_time = time.time() - start_time
            
            result = AgentResult(
                agent_name=agent_name,
                input_query=query,
                output=response_text,
                execution_time=execution_time,
                success=True
            )
            
            self.execution_log.append(result)
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            result = AgentResult(
                agent_name=agent_name,
                input_query=query,
                output="",
                execution_time=execution_time,
                success=False,
                error=str(e)
            )
            self.execution_log.append(result)
            return result
    
    async def run_sequential(self, tasks: list[tuple[str, str]]) -> list[AgentResult]:
        """
        Sequential Execution（順次実行）
        タスクを順番に実行し、前のタスクの結果を次に渡す
        """
        print("\n" + "=" * 60)
        print("🔗 SEQUENTIAL EXECUTION")
        print("=" * 60)
        
        results = []
        previous_output = ""
        
        for i, (agent_name, query) in enumerate(tasks):
            # 前の出力を現在のクエリに追加
            if previous_output and i > 0:
                query = f"{query}\n\nPrevious context: {previous_output[:500]}"
            
            print(f"\n  Step {i+1}: {agent_name}")
            print(f"  Query: {query[:80]}...")
            
            result = await self.run_agent(agent_name, query)
            results.append(result)
            
            if result.success:
                previous_output = result.output
                print(f"  ✅ Completed in {result.execution_time:.2f}s")
            else:
                print(f"  ❌ Failed: {result.error}")
                break
        
        return results
    
    async def run_parallel(self, tasks: list[tuple[str, str]]) -> list[AgentResult]:
        """
        Parallel Execution（並列実行）
        複数のタスクを同時に実行
        """
        print("\n" + "=" * 60)
        print("⚡ PARALLEL EXECUTION")
        print("=" * 60)
        
        print(f"\n  Running {len(tasks)} tasks in parallel...")
        
        # 並列で実行
        coroutines = [
            self.run_agent(agent_name, query) 
            for agent_name, query in tasks
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        total_time = time.time() - start_time
        
        # 結果を処理
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(AgentResult(
                    agent_name=tasks[i][0],
                    input_query=tasks[i][1],
                    output="",
                    execution_time=0,
                    success=False,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
                status = "✅" if result.success else "❌"
                print(f"  {status} {result.agent_name}: {result.execution_time:.2f}s")
        
        print(f"\n  Total parallel time: {total_time:.2f}s")
        
        return processed_results
    
    def print_execution_summary(self):
        """実行サマリーを表示"""
        print("\n" + "=" * 60)
        print("📊 EXECUTION SUMMARY")
        print("=" * 60)
        
        total = len(self.execution_log)
        successful = sum(1 for r in self.execution_log if r.success)
        total_time = sum(r.execution_time for r in self.execution_log)
        
        print(f"\n  Total Executions: {total}")
        print(f"  Successful: {successful} ({successful/total*100:.1f}%)")
        print(f"  Total Time: {total_time:.2f}s")
        
        print("\n  📝 Execution Log:")
        for i, result in enumerate(self.execution_log, 1):
            status = "✅" if result.success else "❌"
            print(f"    {i}. {status} {result.agent_name} ({result.execution_time:.2f}s)")
            if result.output:
                print(f"       Output: {result.output[:60]}...")


# ===========================================
# 4. Production Best Practices
# ===========================================

class ProductionConfig:
    """本番環境の設定"""
    
    # リトライ設定
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    
    # タイムアウト設定
    REQUEST_TIMEOUT = 30.0
    
    # レート制限
    RATE_LIMIT_REQUESTS = 10
    RATE_LIMIT_PERIOD = 60  # seconds
    
    # ログ設定
    LOG_LEVEL = "INFO"
    
    @classmethod
    def print_config(cls):
        print("\n" + "=" * 60)
        print("⚙️ PRODUCTION CONFIGURATION")
        print("=" * 60)
        print(f"  Max Retries: {cls.MAX_RETRIES}")
        print(f"  Retry Delay: {cls.RETRY_DELAY}s")
        print(f"  Request Timeout: {cls.REQUEST_TIMEOUT}s")
        print(f"  Rate Limit: {cls.RATE_LIMIT_REQUESTS} requests / {cls.RATE_LIMIT_PERIOD}s")
        print(f"  Log Level: {cls.LOG_LEVEL}")


async def run_with_retry(system: MultiAgentSystem, agent_name: str, query: str) -> AgentResult:
    """リトライ機能付きで実行"""
    for attempt in range(ProductionConfig.MAX_RETRIES):
        result = await system.run_agent(agent_name, query)
        
        if result.success:
            return result
        
        if attempt < ProductionConfig.MAX_RETRIES - 1:
            print(f"  ⚠️ Retry {attempt + 1}/{ProductionConfig.MAX_RETRIES}...")
            await asyncio.sleep(ProductionConfig.RETRY_DELAY)
    
    return result


# ===========================================
# 5. デモ実行
# ===========================================

async def demo_multi_agent():
    """マルチエージェントシステムのデモ"""
    
    print("=" * 70)
    print("Day 5: Prototype to Production - Multi-Agent System Demo")
    print("=" * 70)
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ エラー: GOOGLE_API_KEY が設定されていません")
        return
    
    # 設定を表示
    ProductionConfig.print_config()
    
    # マルチエージェントシステムを作成
    system = MultiAgentSystem()
    
    # --- デモ 1: 単一エージェント実行 ---
    print("\n" + "=" * 60)
    print("📌 Demo 1: Single Agent Execution")
    print("=" * 60)
    
    result = await system.run_agent("research", "What are the latest AI trends?")
    if result.success:
        print(f"\n  🤖 Research Agent Response:")
        print(f"  {result.output[:200]}...")
    
    # 少し待機（レート制限対策）
    print("\n  ⏳ Waiting to avoid rate limit...")
    await asyncio.sleep(5)
    
    # --- デモ 2: 順次実行 ---
    print("\n" + "=" * 60)
    print("📌 Demo 2: Sequential Execution (Research → Analysis)")
    print("=" * 60)
    
    sequential_tasks = [
        ("research", "Search for Python best practices"),
        ("analysis", "Analyze the research findings and provide recommendations"),
    ]
    
    sequential_results = await system.run_sequential(sequential_tasks)
    
    # 結果を表示
    for result in sequential_results:
        if result.success:
            print(f"\n  📄 {result.agent_name} Output:")
            print(f"  {result.output[:150]}...")
    
    # 少し待機
    print("\n  ⏳ Waiting to avoid rate limit...")
    await asyncio.sleep(5)
    
    # --- デモ 3: 並列実行 ---
    print("\n" + "=" * 60)
    print("📌 Demo 3: Parallel Execution")
    print("=" * 60)
    
    parallel_tasks = [
        ("research", "Find information about machine learning"),
        ("analysis", "Analyze the benefits of AI agents"),
    ]
    
    parallel_results = await system.run_parallel(parallel_tasks)
    
    # --- 実行サマリー ---
    system.print_execution_summary()
    
    # --- A2A Protocol の説明 ---
    print("\n" + "=" * 60)
    print("📌 Agent2Agent (A2A) Protocol")
    print("=" * 60)
    print("""
  A2A Protocol enables agents to communicate across:
  
  • Cross-Framework: ADK ↔ LangGraph ↔ CrewAI
  • Cross-Language: Python ↔ Java ↔ Go
  • Cross-Organization: Internal ↔ External agents
  
  Key Components:
  
  1. Agent Card: Metadata describing agent capabilities
     - Name, description, supported operations
     - Endpoint URL for communication
  
  2. to_a2a(): Expose your agent as an A2A service
```python
     from google.adk.a2a.utils.agent_to_a2a import to_a2a
     public_agent = to_a2a(my_agent, port=8001)
```
  
  3. RemoteA2aAgent: Connect to external agents
```python
     from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
     remote_agent = RemoteA2aAgent(
         name="external_agent",
         agent_card="http://external-service/.well-known/agent.json"
     )
```
""")
    
    # --- Production Checklist ---
    print("\n" + "=" * 60)
    print("✅ PRODUCTION CHECKLIST")
    print("=" * 60)
    print("""
  Before deploying to production, ensure:
  
  □ Error Handling
    - Implement retry logic with exponential backoff
    - Handle API rate limits gracefully
    - Provide meaningful error messages
  
  □ Observability (Day 4A)
    - Logging at appropriate levels
    - Tracing for request flows
    - Metrics for performance monitoring
  
  □ Evaluation (Day 4B)
    - Golden test cases defined
    - Automated evaluation pipeline
    - LLM-as-Judge for quality assurance
  
  □ Security
    - API keys stored securely (env vars, secrets manager)
    - Input validation and sanitization
    - Rate limiting per user/session
  
  □ Scalability
    - Stateless agent design
    - Session storage externalized
    - Horizontal scaling ready
  
  □ Monitoring
    - Health check endpoints
    - Alerting for failures
    - Usage analytics
""")


async def demo_quick():
    """クイックデモ（単一エージェントのみ）"""
    
    print("=" * 70)
    print("Day 5: Quick Demo - Single Agent")
    print("=" * 70)
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ エラー: GOOGLE_API_KEY が設定されていません")
        return
    
    system = MultiAgentSystem()
    
    result = await system.run_agent("research", "What is Agent2Agent protocol?")
    
    if result.success:
        print(f"\n🤖 Response:\n{result.output}")
    else:
        print(f"\n❌ Error: {result.error}")
    
    system.print_execution_summary()


# ===========================================
# メイン
# ===========================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        asyncio.run(demo_quick())
    else:
        asyncio.run(demo_multi_agent())