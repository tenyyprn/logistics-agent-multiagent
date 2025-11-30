import asyncio
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Tool implementation
def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city."""
    import datetime
    
    tz_offsets = {
        "tokyo": 9, "new york": -5, "london": 0, 
        "paris": 1, "los angeles": -8
    }
    
    offset = tz_offsets.get(city.lower(), 0)
    utc_now = datetime.datetime.utcnow()
    local_time = utc_now + datetime.timedelta(hours=offset)
    
    return {
        "status": "success", 
        "city": city, 
        "time": local_time.strftime("%I:%M %p")
    }

root_agent = Agent(
    model='gemini-2.0-flash',
    name='root_agent',
    description="Tells the current time in a specified city.",
    instruction="You are a helpful assistant that tells the current time in cities. Use the 'get_current_time' tool for this purpose.",
    tools=[get_current_time],
)

# エージェントを実行する関数
async def run_agent(user_input: str):
    APP_NAME = "my_agent"
    USER_ID = "user1"
    
    session_service = InMemorySessionService()
    
    # await を追加
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID
    )
    
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    content = types.Content(
        role="user",
        parts=[types.Part(text=user_input)]
    )
    
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=content
    ):
        if event.is_final_response():
            return event.content.parts[0].text
    
    return "No response"

# メイン実行
if __name__ == "__main__":
    question = "What time is it in Tokyo?"
    print(f"質問: {question}")
    
    result = asyncio.run(run_agent(question))
    print(f"回答: {result}")