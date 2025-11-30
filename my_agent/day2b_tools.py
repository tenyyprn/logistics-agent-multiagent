import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# ===========================================
# ベストプラクティス 1: 明確で詳細なDocstring
# ===========================================

def get_weather(city: str, unit: str = "celsius") -> dict:
    """
    Get the current weather for a specified city.
    
    Args:
        city: The name of the city (e.g., "Tokyo", "New York", "London")
        unit: Temperature unit - "celsius" or "fahrenheit" (default: "celsius")
    
    Returns:
        dict: Weather information including:
            - status: "success" or "error"
            - city: The queried city name
            - temperature: Current temperature
            - unit: The temperature unit used
            - condition: Weather condition (e.g., "sunny", "cloudy", "rainy")
    """
    # シミュレートされた天気データ
    weather_data = {
        "tokyo": {"temp_c": 22, "condition": "sunny"},
        "new york": {"temp_c": 18, "condition": "cloudy"},
        "london": {"temp_c": 15, "condition": "rainy"},
        "paris": {"temp_c": 20, "condition": "partly cloudy"},
    }
    
    city_lower = city.lower()
    
    if city_lower not in weather_data:
        return {
            "status": "error",
            "error_message": f"Weather data not available for '{city}'. Available cities: Tokyo, New York, London, Paris"
        }
    
    data = weather_data[city_lower]
    temp = data["temp_c"]
    
    if unit.lower() == "fahrenheit":
        temp = (temp * 9/5) + 32
    
    return {
        "status": "success",
        "city": city,
        "temperature": temp,
        "unit": unit,
        "condition": data["condition"]
    }


# ===========================================
# ベストプラクティス 2: エラーハンドリング
# ===========================================

def search_products(query: str, max_results: int = 5) -> dict:
    """
    Search for products in the catalog.
    
    Args:
        query: Search term for products
        max_results: Maximum number of results to return (1-10, default: 5)
    
    Returns:
        dict: Search results including status and product list
    """
    # 入力バリデーション
    if not query or len(query.strip()) == 0:
        return {
            "status": "error",
            "error_message": "Search query cannot be empty"
        }
    
    if max_results < 1 or max_results > 10:
        return {
            "status": "error", 
            "error_message": "max_results must be between 1 and 10"
        }
    
    # シミュレートされた商品データ
    products = [
        {"id": 1, "name": "Laptop", "price": 999, "category": "Electronics"},
        {"id": 2, "name": "Headphones", "price": 199, "category": "Electronics"},
        {"id": 3, "name": "Coffee Maker", "price": 79, "category": "Kitchen"},
        {"id": 4, "name": "Running Shoes", "price": 129, "category": "Sports"},
        {"id": 5, "name": "Book: AI Fundamentals", "price": 49, "category": "Books"},
    ]
    
    # 簡易検索
    results = [p for p in products if query.lower() in p["name"].lower()][:max_results]
    
    return {
        "status": "success",
        "query": query,
        "total_results": len(results),
        "products": results
    }


# ===========================================
# ベストプラクティス 3: 構造化された出力
# ===========================================

def calculate_shipping(
    weight_kg: float,
    destination_country: str,
    shipping_method: str = "standard"
) -> dict:
    """
    Calculate shipping cost for an order.
    
    Args:
        weight_kg: Package weight in kilograms (must be positive)
        destination_country: Destination country code (e.g., "US", "JP", "UK")
        shipping_method: "standard", "express", or "overnight"
    
    Returns:
        dict: Shipping details including cost and estimated delivery
    """
    # バリデーション
    if weight_kg <= 0:
        return {"status": "error", "error_message": "Weight must be positive"}
    
    valid_methods = ["standard", "express", "overnight"]
    if shipping_method.lower() not in valid_methods:
        return {
            "status": "error",
            "error_message": f"Invalid shipping method. Choose from: {valid_methods}"
        }
    
    # 料金計算（シミュレート）
    base_rates = {"standard": 5, "express": 15, "overnight": 30}
    country_multipliers = {"US": 1.0, "JP": 1.5, "UK": 1.2, "DE": 1.3}
    
    multiplier = country_multipliers.get(destination_country.upper(), 2.0)
    base = base_rates[shipping_method.lower()]
    cost = round((base + weight_kg * 2) * multiplier, 2)
    
    delivery_days = {"standard": "5-7", "express": "2-3", "overnight": "1"}
    
    return {
        "status": "success",
        "weight_kg": weight_kg,
        "destination": destination_country.upper(),
        "method": shipping_method,
        "cost_usd": cost,
        "estimated_delivery_days": delivery_days[shipping_method.lower()]
    }


# ===========================================
# エージェントの作成（複数ツール）
# ===========================================

shopping_agent = Agent(
    model='gemini-2.0-flash',
    name='shopping_assistant',
    description="A helpful shopping assistant that can check weather, search products, and calculate shipping.",
    instruction="""You are a helpful shopping assistant. You can:
1. Check the weather in different cities using get_weather
2. Search for products using search_products  
3. Calculate shipping costs using calculate_shipping

Always provide clear, helpful responses based on the tool results.
If a tool returns an error, explain it to the user in a friendly way.
""",
    tools=[get_weather, search_products, calculate_shipping],
)


# ===========================================
# 実行関数
# ===========================================

async def chat_with_agent(user_input: str):
    """エージェントと対話する関数"""
    APP_NAME = "shopping_app"
    USER_ID = "user1"
    
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID
    )
    
    runner = Runner(
        agent=shopping_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    content = types.Content(
        role="user",
        parts=[types.Part(text=user_input)]
    )
    
    print(f"\n🛒 質問: {user_input}")
    print("-" * 50)
    
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=content
    ):
        if event.is_final_response():
            print(f"🤖 回答: {event.content.parts[0].text}")
            return event.content.parts[0].text
    
    return "No response"


# ===========================================
# メイン実行
# ===========================================

async def main():
    # APIキーチェック
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ エラー: GOOGLE_API_KEY が設定されていません")
        return
    
    print("=" * 60)
    print("Day 2B: Agent Tools Best Practices デモ")
    print("=" * 60)
    
    # テストケース
    test_queries = [
        "What's the weather like in Tokyo?",
        "Search for laptops",
        "Calculate shipping for a 2kg package to Japan using express shipping",
        "What's the weather in Tokyo and can you find me some headphones?",
    ]
    
    for query in test_queries:
        await chat_with_agent(query)
        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())