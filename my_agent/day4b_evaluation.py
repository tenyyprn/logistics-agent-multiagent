"""
Day 4B: Agent Evaluation
========================

エージェント評価の主要な手法:
1. Golden Test Cases（ゴールデンテスト）: 期待される入出力のテスト
2. LLM-as-a-Judge（LLM審判）: LLMを使って応答品質を評価
3. Automated Metrics（自動メトリクス）: 定量的な評価指標
4. Human-in-the-Loop（人間によるフィードバック）

このデモでは:
- テストケースの定義と自動実行
- LLMによる応答品質の評価
- 評価レポートの生成
"""

import asyncio
import os
import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import google.genai as genai


# ===========================================
# 1. 評価用データ構造
# ===========================================

class EvalResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"


@dataclass
class TestCase:
    """テストケースの定義"""
    id: str
    name: str
    input_query: str
    expected_keywords: list[str]  # 応答に含まれるべきキーワード
    expected_tool_calls: list[str] = field(default_factory=list)  # 呼び出されるべきツール
    description: str = ""


@dataclass
class EvalScore:
    """評価スコア"""
    relevance: float = 0.0      # 関連性 (0-1)
    accuracy: float = 0.0       # 正確性 (0-1)
    completeness: float = 0.0   # 完全性 (0-1)
    helpfulness: float = 0.0    # 有用性 (0-1)
    
    @property
    def overall(self) -> float:
        """総合スコア"""
        return (self.relevance + self.accuracy + self.completeness + self.helpfulness) / 4


@dataclass
class TestResult:
    """テスト結果"""
    test_case: TestCase
    actual_response: str
    result: EvalResult
    keyword_matches: dict
    tool_call_matches: dict
    llm_eval_score: Optional[EvalScore] = None
    llm_eval_feedback: str = ""
    execution_time: float = 0.0
    error: str = ""


# ===========================================
# 2. テスト対象のエージェント
# ===========================================

def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    weather_data = {
        "tokyo": {"temp": 22, "condition": "sunny", "humidity": 45},
        "osaka": {"temp": 24, "condition": "cloudy", "humidity": 55},
        "new york": {"temp": 18, "condition": "rainy", "humidity": 70},
        "london": {"temp": 15, "condition": "foggy", "humidity": 80},
    }
    
    city_lower = city.lower()
    if city_lower in weather_data:
        return {"status": "success", "city": city, **weather_data[city_lower]}
    return {"status": "error", "message": f"Weather data not available for {city}"}


def convert_temperature(temp: float, from_unit: str, to_unit: str) -> dict:
    """Convert temperature between Celsius and Fahrenheit."""
    if from_unit.lower() == "celsius" and to_unit.lower() == "fahrenheit":
        converted = (temp * 9/5) + 32
    elif from_unit.lower() == "fahrenheit" and to_unit.lower() == "celsius":
        converted = (temp - 32) * 5/9
    else:
        return {"status": "error", "message": "Invalid units"}
    
    return {
        "status": "success",
        "original": temp,
        "from_unit": from_unit,
        "converted": round(converted, 1),
        "to_unit": to_unit
    }


def get_recommendation(city: str, activity: str) -> dict:
    """Get activity recommendation based on weather."""
    weather = get_weather(city)
    
    if weather["status"] == "error":
        return weather
    
    condition = weather["condition"]
    recommendations = {
        "outdoor": {
            "sunny": "Great day for outdoor activities!",
            "cloudy": "Okay for outdoor activities, but bring a jacket.",
            "rainy": "Not recommended for outdoor activities today.",
            "foggy": "Be careful with visibility if going outside."
        },
        "indoor": {
            "sunny": "Nice day, but indoor activities are always good!",
            "cloudy": "Good day for indoor activities.",
            "rainy": "Perfect day for indoor activities!",
            "foggy": "Indoor activities recommended."
        }
    }
    
    activity_type = "outdoor" if activity.lower() in ["hiking", "running", "cycling", "sports"] else "indoor"
    
    return {
        "status": "success",
        "city": city,
        "activity": activity,
        "weather_condition": condition,
        "recommendation": recommendations.get(activity_type, {}).get(condition, "No specific recommendation.")
    }


# テスト対象のエージェント
weather_agent = Agent(
    model='gemini-2.0-flash',
    name='weather_assistant',
    description="A weather assistant that provides weather information and recommendations.",
    instruction="""You are a helpful weather assistant. You can:
1. Get current weather using get_weather
2. Convert temperatures using convert_temperature
3. Provide activity recommendations using get_recommendation

Always provide accurate information based on tool results.
Be concise but informative in your responses.
""",
    tools=[get_weather, convert_temperature, get_recommendation],
)


# ===========================================
# 3. テストケースの定義
# ===========================================

TEST_CASES = [
    TestCase(
        id="TC001",
        name="Basic Weather Query",
        input_query="What's the weather in Tokyo?",
        expected_keywords=["tokyo", "22", "sunny"],
        expected_tool_calls=["get_weather"],
        description="Basic weather query should return temperature and condition"
    ),
    TestCase(
        id="TC002",
        name="Temperature Conversion",
        input_query="Convert 25 degrees Celsius to Fahrenheit",
        expected_keywords=["77", "fahrenheit"],
        expected_tool_calls=["convert_temperature"],
        description="Temperature conversion should be accurate"
    ),
    TestCase(
        id="TC003",
        name="Activity Recommendation - Sunny",
        input_query="Is it a good day for hiking in Tokyo?",
        expected_keywords=["tokyo", "outdoor", "great"],
        expected_tool_calls=["get_recommendation"],
        description="Should recommend outdoor activity on sunny day"
    ),
    TestCase(
        id="TC004",
        name="Activity Recommendation - Rainy",
        input_query="Should I go running in New York today?",
        expected_keywords=["new york", "rainy", "not recommended"],
        expected_tool_calls=["get_recommendation"],
        description="Should not recommend outdoor activity on rainy day"
    ),
    TestCase(
        id="TC005",
        name="Unknown City",
        input_query="What's the weather in Paris?",
        expected_keywords=["not available", "paris"],
        expected_tool_calls=["get_weather"],
        description="Should handle unknown city gracefully"
    ),
    TestCase(
        id="TC006",
        name="Complex Query",
        input_query="What's the weather in Osaka and is it good for cycling?",
        expected_keywords=["osaka", "24", "cloudy"],
        expected_tool_calls=["get_weather"],
        description="Should handle multi-part queries"
    ),
]


# ===========================================
# 4. エージェント実行関数
# ===========================================

# ツール呼び出しを記録するためのグローバル変数
tool_calls_log = []


def create_logged_tool(func):
    """ツール呼び出しをログするラッパー関数を作成"""
    def wrapper(*args, **kwargs):
        tool_calls_log.append(func.__name__)
        return func(*args, **kwargs)
    
    # 重要: 元の関数の属性をコピー
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    wrapper.__annotations__ = func.__annotations__
    
    # functools.wraps の代わりに手動でコピー
    import inspect
    wrapper.__signature__ = inspect.signature(func)
    
    return wrapper


async def run_agent_for_eval(query: str) -> tuple[str, list[str], float]:
    """評価用にエージェントを実行"""
    import time
    
    global tool_calls_log
    tool_calls_log = []
    
    start_time = time.time()
    
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="eval_app",
        user_id="eval_user"
    )
    
    # ログ付きツールを作成
    logged_get_weather = create_logged_tool(get_weather)
    logged_convert_temperature = create_logged_tool(convert_temperature)
    logged_get_recommendation = create_logged_tool(get_recommendation)
    
    # 評価用エージェントを作成
    eval_agent = Agent(
        model='gemini-2.0-flash',
        name='weather_assistant',
        description=weather_agent.description,
        instruction=weather_agent.instruction,
        tools=[
            logged_get_weather,
            logged_convert_temperature,
            logged_get_recommendation
        ],
    )
    
    runner = Runner(
        agent=eval_agent,
        app_name="eval_app",
        session_service=session_service
    )
    
    content = types.Content(
        role="user",
        parts=[types.Part(text=query)]
    )
    
    response_text = ""
    async for event in runner.run_async(
        user_id="eval_user",
        session_id=session.id,
        new_message=content
    ):
        if event.is_final_response():
            response_text = event.content.parts[0].text
    
    execution_time = time.time() - start_time
    
    return response_text, tool_calls_log.copy(), execution_time
# ===========================================
# 5. 評価関数
# ===========================================

def evaluate_keywords(response: str, expected_keywords: list[str]) -> dict:
    """キーワードマッチの評価"""
    response_lower = response.lower()
    matches = {}
    
    for keyword in expected_keywords:
        matches[keyword] = keyword.lower() in response_lower
    
    return matches


def evaluate_tool_calls(actual_calls: list[str], expected_calls: list[str]) -> dict:
    """ツール呼び出しの評価"""
    matches = {}
    
    for expected in expected_calls:
        matches[expected] = expected in actual_calls
    
    return matches


async def llm_evaluate_response(
    query: str,
    response: str,
    test_case: TestCase
) -> tuple[EvalScore, str]:
    """LLM-as-a-Judge: LLMを使って応答を評価"""
    
    client = genai.Client()
    
    eval_prompt = f"""You are an AI response evaluator. Evaluate the following agent response based on the given criteria.

USER QUERY: {query}

AGENT RESPONSE: {response}

TEST DESCRIPTION: {test_case.description}

EXPECTED KEYWORDS: {', '.join(test_case.expected_keywords)}

Please evaluate the response on these criteria (score 0.0 to 1.0):
1. RELEVANCE: How relevant is the response to the user's query?
2. ACCURACY: How accurate is the information provided?
3. COMPLETENESS: Does the response fully address the query?
4. HELPFULNESS: How helpful is the response to the user?

Respond in this exact JSON format:
{{
    "relevance": <score>,
    "accuracy": <score>,
    "completeness": <score>,
    "helpfulness": <score>,
    "feedback": "<brief explanation of scores>"
}}
"""
    
    try:
        eval_response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=eval_prompt
        )
        
        # JSONをパース
        response_text = eval_response.text
        # JSON部分を抽出
        import re
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        
        if json_match:
            eval_data = json.loads(json_match.group())
            score = EvalScore(
                relevance=float(eval_data.get("relevance", 0)),
                accuracy=float(eval_data.get("accuracy", 0)),
                completeness=float(eval_data.get("completeness", 0)),
                helpfulness=float(eval_data.get("helpfulness", 0))
            )
            feedback = eval_data.get("feedback", "")
            return score, feedback
    except Exception as e:
        print(f"LLM evaluation error: {e}")
    
    return EvalScore(), "Evaluation failed"


def determine_result(
    keyword_matches: dict,
    tool_matches: dict,
    llm_score: Optional[EvalScore]
) -> EvalResult:
    """総合結果を判定"""
    
    # キーワードマッチ率
    keyword_rate = sum(keyword_matches.values()) / len(keyword_matches) if keyword_matches else 1.0
    
    # ツールマッチ率
    tool_rate = sum(tool_matches.values()) / len(tool_matches) if tool_matches else 1.0
    
    # LLMスコア
    llm_rate = llm_score.overall if llm_score else 0.5
    
    # 総合判定
    if keyword_rate >= 0.8 and tool_rate >= 0.8 and llm_rate >= 0.7:
        return EvalResult.PASS
    elif keyword_rate >= 0.5 or tool_rate >= 0.5 or llm_rate >= 0.5:
        return EvalResult.PARTIAL
    else:
        return EvalResult.FAIL


# ===========================================
# 6. テスト実行エンジン
# ===========================================

class AgentEvaluator:
    """エージェント評価エンジン"""
    
    def __init__(self, test_cases: list[TestCase]):
        self.test_cases = test_cases
        self.results: list[TestResult] = []
    
    async def run_single_test(self, test_case: TestCase, use_llm_judge: bool = True) -> TestResult:
        """単一のテストを実行"""
        print(f"\n  🧪 Running: {test_case.id} - {test_case.name}")
        
        try:
            # エージェント実行
            response, tool_calls, exec_time = await run_agent_for_eval(test_case.input_query)
            
            # キーワード評価
            keyword_matches = evaluate_keywords(response, test_case.expected_keywords)
            
            # ツール呼び出し評価
            tool_matches = evaluate_tool_calls(tool_calls, test_case.expected_tool_calls)
            
            # LLM評価
            llm_score = None
            llm_feedback = ""
            if use_llm_judge:
                llm_score, llm_feedback = await llm_evaluate_response(
                    test_case.input_query,
                    response,
                    test_case
                )
            
            # 結果判定
            result = determine_result(keyword_matches, tool_matches, llm_score)
            
            test_result = TestResult(
                test_case=test_case,
                actual_response=response,
                result=result,
                keyword_matches=keyword_matches,
                tool_call_matches=tool_matches,
                llm_eval_score=llm_score,
                llm_eval_feedback=llm_feedback,
                execution_time=exec_time
            )
            
            # 結果表示
            status_icon = "✅" if result == EvalResult.PASS else "⚠️" if result == EvalResult.PARTIAL else "❌"
            print(f"     {status_icon} Result: {result.value}")
            print(f"     ⏱️  Time: {exec_time:.2f}s")
            if llm_score:
                print(f"     📊 LLM Score: {llm_score.overall:.2f}")
            
            return test_result
            
        except Exception as e:
            return TestResult(
                test_case=test_case,
                actual_response="",
                result=EvalResult.FAIL,
                keyword_matches={},
                tool_call_matches={},
                error=str(e)
            )
    
    async def run_all_tests(self, use_llm_judge: bool = True) -> list[TestResult]:
        """すべてのテストを実行"""
        print("\n" + "=" * 70)
        print("🔬 RUNNING AGENT EVALUATION TESTS")
        print("=" * 70)
        
        self.results = []
        
        for test_case in self.test_cases:
            result = await self.run_single_test(test_case, use_llm_judge)
            self.results.append(result)
        
        return self.results
    
    def generate_report(self) -> str:
        """評価レポートを生成"""
        if not self.results:
            return "No test results available."
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.result == EvalResult.PASS)
        partial = sum(1 for r in self.results if r.result == EvalResult.PARTIAL)
        failed = sum(1 for r in self.results if r.result == EvalResult.FAIL)
        
        avg_time = sum(r.execution_time for r in self.results) / total
        
        # LLMスコアの平均
        llm_scores = [r.llm_eval_score for r in self.results if r.llm_eval_score]
        avg_llm_score = sum(s.overall for s in llm_scores) / len(llm_scores) if llm_scores else 0
        
        report = f"""
{'=' * 70}
📋 AGENT EVALUATION REPORT
{'=' * 70}

📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🤖 Agent: weather_assistant

{'─' * 70}
📊 SUMMARY
{'─' * 70}
  Total Tests:     {total}
  ✅ Passed:       {passed} ({passed/total*100:.1f}%)
  ⚠️  Partial:     {partial} ({partial/total*100:.1f}%)
  ❌ Failed:       {failed} ({failed/total*100:.1f}%)
  
  ⏱️  Avg Time:    {avg_time:.2f}s
  📊 Avg LLM Score: {avg_llm_score:.2f}

{'─' * 70}
📝 DETAILED RESULTS
{'─' * 70}
"""
        
        for result in self.results:
            status = "✅" if result.result == EvalResult.PASS else "⚠️" if result.result == EvalResult.PARTIAL else "❌"
            
            report += f"""
  {status} {result.test_case.id}: {result.test_case.name}
     Query: {result.test_case.input_query}
     Response: {result.actual_response[:100]}...
     Keywords: {sum(result.keyword_matches.values())}/{len(result.keyword_matches)} matched
     Tools: {sum(result.tool_call_matches.values())}/{len(result.tool_call_matches)} called
"""
            if result.llm_eval_score:
                report += f"""     LLM Score: {result.llm_eval_score.overall:.2f}
     Feedback: {result.llm_eval_feedback[:100]}...
"""
            if result.error:
                report += f"     Error: {result.error}\n"
        
        report += f"\n{'=' * 70}\n"
        
        return report
    
    def print_report(self):
        """レポートを表示"""
        print(self.generate_report())


# ===========================================
# 7. メイン実行
# ===========================================

async def demo_evaluation():
    """評価デモを実行"""
    
    print("=" * 70)
    print("Day 4B: Agent Evaluation デモ")
    print("=" * 70)
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ エラー: GOOGLE_API_KEY が設定されていません")
        return
    
    # 評価エンジンを作成
    evaluator = AgentEvaluator(TEST_CASES)
    
    # テスト実行（LLM-as-Judge を使用）
    print("\n📌 LLM-as-Judge を使用してエージェントを評価します...")
    await evaluator.run_all_tests(use_llm_judge=True)
    
    # レポート表示
    evaluator.print_report()


async def quick_evaluation():
    """クイック評価（LLM-as-Judge なし）"""
    
    print("=" * 70)
    print("Day 4B: Quick Agent Evaluation（LLM-as-Judge なし）")
    print("=" * 70)
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ エラー: GOOGLE_API_KEY が設定されていません")
        return
    
    evaluator = AgentEvaluator(TEST_CASES)
    await evaluator.run_all_tests(use_llm_judge=False)
    evaluator.print_report()


# ===========================================
# メイン
# ===========================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # クイックモード: python day4b_evaluation.py --quick
        asyncio.run(quick_evaluation())
    else:
        # フルモード（LLM-as-Judge 使用）
        asyncio.run(demo_evaluation())