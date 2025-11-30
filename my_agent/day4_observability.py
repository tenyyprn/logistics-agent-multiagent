"""
Day 4A: Agent Observability
===========================

Observability（可観測性）の3つの柱:
1. Logs（ログ）: 何が起きたかの記録
2. Traces（トレース）: リクエストの流れを追跡
3. Metrics（メトリクス）: パフォーマンスの計測

このデモでは:
- Python標準のloggingモジュールの活用
- エージェントの実行詳細のトレーシング
- 実行時間やツール呼び出しの計測
"""

import asyncio
import os
import logging
import time
from datetime import datetime
from functools import wraps
from typing import Callable, Any
from dotenv import load_dotenv

load_dotenv()

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


# ===========================================
# 1. ロギングの設定
# ===========================================

# ADKのログを有効化（DEBUG レベルで詳細表示）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# カスタムロガーの作成
logger = logging.getLogger("agent_observability")
logger.setLevel(logging.DEBUG)

# ADKの内部ロガーも設定（詳細を見たい場合）
adk_logger = logging.getLogger("google_adk")
adk_logger.setLevel(logging.WARNING)  # INFO or DEBUG for more details


# ===========================================
# 2. メトリクス収集クラス
# ===========================================

class MetricsCollector:
    """エージェントのメトリクスを収集するクラス"""
    
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "tool_calls": {},
            "response_times": [],
            "errors": []
        }
        self.start_time = datetime.now()
    
    def record_request(self, success: bool, duration: float, error: str = None):
        """リクエストを記録"""
        self.metrics["total_requests"] += 1
        self.metrics["response_times"].append(duration)
        
        if success:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1
            if error:
                self.metrics["errors"].append({
                    "time": datetime.now().isoformat(),
                    "error": error
                })
    
    def record_tool_call(self, tool_name: str, duration: float):
        """ツール呼び出しを記録"""
        if tool_name not in self.metrics["tool_calls"]:
            self.metrics["tool_calls"][tool_name] = {
                "count": 0,
                "total_time": 0,
                "avg_time": 0
            }
        
        self.metrics["tool_calls"][tool_name]["count"] += 1
        self.metrics["tool_calls"][tool_name]["total_time"] += duration
        self.metrics["tool_calls"][tool_name]["avg_time"] = (
            self.metrics["tool_calls"][tool_name]["total_time"] / 
            self.metrics["tool_calls"][tool_name]["count"]
        )
    
    def get_summary(self) -> dict:
        """メトリクスのサマリーを取得"""
        response_times = self.metrics["response_times"]
        
        return {
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "total_requests": self.metrics["total_requests"],
            "success_rate": (
                self.metrics["successful_requests"] / self.metrics["total_requests"] * 100
                if self.metrics["total_requests"] > 0 else 0
            ),
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "tool_calls": self.metrics["tool_calls"],
            "recent_errors": self.metrics["errors"][-5:]  # 最新5件のエラー
        }
    
    def print_summary(self):
        """サマリーを表示"""
        summary = self.get_summary()
        
        print("\n" + "=" * 60)
        print("📊 METRICS SUMMARY")
        print("=" * 60)
        print(f"  Uptime: {summary['uptime_seconds']:.1f} seconds")
        print(f"  Total Requests: {summary['total_requests']}")
        print(f"  Success Rate: {summary['success_rate']:.1f}%")
        print(f"  Avg Response Time: {summary['avg_response_time']:.3f}s")
        print(f"  Min Response Time: {summary['min_response_time']:.3f}s")
        print(f"  Max Response Time: {summary['max_response_time']:.3f}s")
        
        if summary["tool_calls"]:
            print("\n  📦 Tool Calls:")
            for tool, stats in summary["tool_calls"].items():
                print(f"    - {tool}: {stats['count']} calls, avg {stats['avg_time']:.3f}s")
        
        if summary["recent_errors"]:
            print("\n  ❌ Recent Errors:")
            for err in summary["recent_errors"]:
                print(f"    - {err['time']}: {err['error']}")
        
        print("=" * 60)


# グローバルメトリクスコレクター
metrics = MetricsCollector()


# ===========================================
# 3. トレーシングデコレーター
# ===========================================

def trace_tool(func: Callable) -> Callable:
    """ツール関数にトレーシングを追加するデコレーター"""
    
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        tool_name = func.__name__
        start_time = time.time()
        
        # 開始ログ
        logger.debug(f"🔧 TOOL START: {tool_name}")
        logger.debug(f"   Args: {args}, Kwargs: {kwargs}")
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            # 成功ログ
            logger.info(f"✅ TOOL SUCCESS: {tool_name} ({duration:.3f}s)")
            logger.debug(f"   Result: {result}")
            
            # メトリクス記録
            metrics.record_tool_call(tool_name, duration)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            # エラーログ
            logger.error(f"❌ TOOL ERROR: {tool_name} ({duration:.3f}s)")
            logger.error(f"   Error: {str(e)}")
            
            raise
    
    return wrapper


# ===========================================
# 4. トレース対応ツール
# ===========================================

@trace_tool
def search_database(query: str, limit: int = 10) -> dict:
    """
    Search the database for records.
    
    Args:
        query: Search query string
        limit: Maximum number of results (1-100)
    
    Returns:
        dict: Search results
    """
    # シミュレートされた処理時間
    time.sleep(0.1)
    
    if not query:
        return {"status": "error", "message": "Query cannot be empty"}
    
    # シミュレートされたデータベース検索
    mock_results = [
        {"id": 1, "name": "Product A", "price": 100},
        {"id": 2, "name": "Product B", "price": 200},
        {"id": 3, "name": "Product C", "price": 150},
    ]
    
    # クエリでフィルタリング
    filtered = [r for r in mock_results if query.lower() in r["name"].lower()][:limit]
    
    return {
        "status": "success",
        "query": query,
        "count": len(filtered),
        "results": filtered
    }


@trace_tool
def calculate_total(items: list, discount_percent: float = 0) -> dict:
    """
    Calculate the total price of items with optional discount.
    
    Args:
        items: List of item prices
        discount_percent: Discount percentage (0-100)
    
    Returns:
        dict: Calculation result
    """
    time.sleep(0.05)
    
    if not items:
        return {"status": "error", "message": "Items list cannot be empty"}
    
    if discount_percent < 0 or discount_percent > 100:
        return {"status": "error", "message": "Discount must be between 0 and 100"}
    
    subtotal = sum(items)
    discount_amount = subtotal * (discount_percent / 100)
    total = subtotal - discount_amount
    
    return {
        "status": "success",
        "subtotal": subtotal,
        "discount_percent": discount_percent,
        "discount_amount": round(discount_amount, 2),
        "total": round(total, 2)
    }


@trace_tool
def get_user_info(user_id: str) -> dict:
    """
    Get user information by ID.
    
    Args:
        user_id: The user's identifier
    
    Returns:
        dict: User information
    """
    time.sleep(0.08)
    
    # シミュレートされたユーザーデータ
    users = {
        "user1": {"name": "Alice", "email": "alice@example.com", "tier": "gold"},
        "user2": {"name": "Bob", "email": "bob@example.com", "tier": "silver"},
    }
    
    if user_id not in users:
        return {"status": "error", "message": f"User {user_id} not found"}
    
    return {
        "status": "success",
        "user_id": user_id,
        **users[user_id]
    }


# ===========================================
# 5. Observability対応エージェント
# ===========================================

observable_agent = Agent(
    model='gemini-2.0-flash',
    name='observable_assistant',
    description="An assistant with full observability capabilities.",
    instruction="""You are a helpful assistant that can:
1. Search the database using search_database
2. Calculate totals with discounts using calculate_total
3. Get user information using get_user_info

Always provide clear responses based on tool results.
""",
    tools=[search_database, calculate_total, get_user_info],
)


# ===========================================
# 6. トレース対応の実行関数
# ===========================================

async def run_with_tracing(user_input: str, session_id: str = None) -> str:
    """トレーシング付きでエージェントを実行"""
    
    trace_id = f"trace_{datetime.now().strftime('%H%M%S%f')}"
    start_time = time.time()
    
    logger.info(f"🚀 REQUEST START [trace_id={trace_id}]")
    logger.info(f"   Input: {user_input}")
    
    try:
        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name="observable_app",
            user_id="user1"
        )
        
        runner = Runner(
            agent=observable_agent,
            app_name="observable_app",
            session_service=session_service
        )
        
        content = types.Content(
            role="user",
            parts=[types.Part(text=user_input)]
        )
        
        response_text = ""
        async for event in runner.run_async(
            user_id="user1",
            session_id=session.id,
            new_message=content
        ):
            if event.is_final_response():
                response_text = event.content.parts[0].text
        
        duration = time.time() - start_time
        
        logger.info(f"✅ REQUEST SUCCESS [trace_id={trace_id}] ({duration:.3f}s)")
        logger.debug(f"   Response: {response_text[:100]}...")
        
        metrics.record_request(success=True, duration=duration)
        
        return response_text
        
    except Exception as e:
        duration = time.time() - start_time
        
        logger.error(f"❌ REQUEST FAILED [trace_id={trace_id}] ({duration:.3f}s)")
        logger.error(f"   Error: {str(e)}")
        
        metrics.record_request(success=False, duration=duration, error=str(e))
        
        raise


# ===========================================
# 7. デモ実行
# ===========================================

async def demo_observability():
    """Observabilityのデモ"""
    
    print("=" * 70)
    print("Day 4A: Agent Observability デモ")
    print("=" * 70)
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ エラー: GOOGLE_API_KEY が設定されていません")
        return
    
    # テストクエリ
    test_queries = [
        "Search the database for 'Product'",
        "Calculate the total for items priced at 100, 200, and 150 with a 10% discount",
        "Get information about user1",
        "Search for 'Product A' and then calculate total if I buy 3 of them at 100 each",
    ]
    
    print("\n📝 Running test queries with full observability...\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"📌 Query {i}: {query}")
        print(f"{'='*60}")
        
        try:
            response = await run_with_tracing(query)
            print(f"\n🤖 Response: {response}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        print()
    
    # メトリクスサマリーを表示
    metrics.print_summary()


# ===========================================
# 8. インタラクティブモード
# ===========================================

async def interactive_observability():
    """インタラクティブモード with observability"""
    
    print("=" * 70)
    print("Day 4A: Observability Interactive Mode")
    print("=" * 70)
    print("Commands:")
    print("  'quit' - Exit")
    print("  'metrics' - Show metrics summary")
    print("  'debug on' - Enable debug logging")
    print("  'debug off' - Disable debug logging")
    print("=" * 70)
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ エラー: GOOGLE_API_KEY が設定されていません")
        return
    
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            
            if user_input.lower() == 'quit':
                metrics.print_summary()
                print("👋 Goodbye!")
                break
            
            if user_input.lower() == 'metrics':
                metrics.print_summary()
                continue
            
            if user_input.lower() == 'debug on':
                logger.setLevel(logging.DEBUG)
                adk_logger.setLevel(logging.DEBUG)
                print("🔧 Debug logging enabled")
                continue
            
            if user_input.lower() == 'debug off':
                logger.setLevel(logging.INFO)
                adk_logger.setLevel(logging.WARNING)
                print("🔧 Debug logging disabled")
                continue
            
            if not user_input:
                continue
            
            response = await run_with_tracing(user_input)
            print(f"\n🤖 Assistant: {response}")
            
        except KeyboardInterrupt:
            metrics.print_summary()
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


# ===========================================
# メイン
# ===========================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_observability())
    else:
        asyncio.run(demo_observability())