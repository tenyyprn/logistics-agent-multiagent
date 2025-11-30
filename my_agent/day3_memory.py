"""
Day 3: Context Engineering - Sessions & Memory
==============================================

セッション（Session）: 1つの会話の履歴を保持（短期記憶）
メモリ（Memory）: 複数のセッションにまたがる情報を保持（長期記憶）

このデモでは：
1. InMemorySessionService - セッション内での会話履歴
2. 複数ターンの会話 - コンテキストの維持
3. ユーザー情報の記憶 - 長期メモリのシミュレーション
"""

import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


# ===========================================
# ユーザーメモリ（長期記憶のシミュレーション）
# ===========================================

# 実際のアプリではデータベースに保存
user_memory = {}

def save_user_preference(user_id: str, key: str, value: str) -> dict:
    """
    Save a user preference to long-term memory.
    
    Args:
        user_id: The user's identifier
        key: The preference key (e.g., "favorite_color", "name", "language")
        value: The preference value
    
    Returns:
        dict: Confirmation of saved preference
    """
    if user_id not in user_memory:
        user_memory[user_id] = {}
    
    user_memory[user_id][key] = {
        "value": value,
        "saved_at": datetime.now().isoformat()
    }
    
    return {
        "status": "success",
        "message": f"Saved {key}='{value}' for user {user_id}"
    }


def get_user_preference(user_id: str, key: str) -> dict:
    """
    Retrieve a user preference from long-term memory.
    
    Args:
        user_id: The user's identifier
        key: The preference key to retrieve
    
    Returns:
        dict: The stored preference or error if not found
    """
    if user_id not in user_memory:
        return {
            "status": "not_found",
            "message": f"No preferences found for user {user_id}"
        }
    
    if key not in user_memory[user_id]:
        return {
            "status": "not_found", 
            "message": f"Preference '{key}' not found for user {user_id}"
        }
    
    pref = user_memory[user_id][key]
    return {
        "status": "success",
        "key": key,
        "value": pref["value"],
        "saved_at": pref["saved_at"]
    }


def get_all_user_preferences(user_id: str) -> dict:
    """
    Retrieve all preferences for a user.
    
    Args:
        user_id: The user's identifier
    
    Returns:
        dict: All stored preferences for the user
    """
    if user_id not in user_memory or not user_memory[user_id]:
        return {
            "status": "empty",
            "message": f"No preferences stored for user {user_id}",
            "preferences": {}
        }
    
    return {
        "status": "success",
        "user_id": user_id,
        "preferences": {k: v["value"] for k, v in user_memory[user_id].items()}
    }


# ===========================================
# タスク管理ツール（セッション状態のデモ）
# ===========================================

# セッションごとのタスクリスト
session_tasks = {}

def add_task(session_id: str, task: str, priority: str = "medium") -> dict:
    """
    Add a task to the current session's task list.
    
    Args:
        session_id: Current session identifier
        task: Task description
        priority: "low", "medium", or "high"
    
    Returns:
        dict: Confirmation with task details
    """
    if session_id not in session_tasks:
        session_tasks[session_id] = []
    
    task_item = {
        "id": len(session_tasks[session_id]) + 1,
        "task": task,
        "priority": priority,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    
    session_tasks[session_id].append(task_item)
    
    return {
        "status": "success",
        "message": f"Task added: '{task}' with {priority} priority",
        "task_id": task_item["id"]
    }


def get_tasks(session_id: str) -> dict:
    """
    Get all tasks for the current session.
    
    Args:
        session_id: Current session identifier
    
    Returns:
        dict: List of all tasks in the session
    """
    if session_id not in session_tasks or not session_tasks[session_id]:
        return {
            "status": "empty",
            "message": "No tasks in this session",
            "tasks": []
        }
    
    return {
        "status": "success",
        "total_tasks": len(session_tasks[session_id]),
        "tasks": session_tasks[session_id]
    }


def complete_task(session_id: str, task_id: int) -> dict:
    """
    Mark a task as completed.
    
    Args:
        session_id: Current session identifier
        task_id: ID of the task to complete
    
    Returns:
        dict: Confirmation of task completion
    """
    if session_id not in session_tasks:
        return {"status": "error", "message": "No tasks found in this session"}
    
    for task in session_tasks[session_id]:
        if task["id"] == task_id:
            task["status"] = "completed"
            return {
                "status": "success",
                "message": f"Task {task_id} marked as completed"
            }
    
    return {"status": "error", "message": f"Task {task_id} not found"}


# ===========================================
# メモリ対応エージェント
# ===========================================

memory_agent = Agent(
    model='gemini-2.0-flash',
    name='memory_assistant',
    description="A personal assistant with memory capabilities.",
    instruction="""You are a helpful personal assistant with memory capabilities.

You can:
1. Remember user preferences using save_user_preference (name, favorite_color, language, etc.)
2. Recall user preferences using get_user_preference or get_all_user_preferences
3. Manage tasks in the current session using add_task, get_tasks, complete_task

Important behaviors:
- When users tell you their preferences, save them for future reference
- When greeting returning users, try to recall their preferences
- Keep track of tasks within the conversation
- Be friendly and personalized based on what you remember about the user

The user_id is always "user1" and session_id is provided in each interaction.
""",
    tools=[
        save_user_preference,
        get_user_preference,
        get_all_user_preferences,
        add_task,
        get_tasks,
        complete_task
    ],
)


# ===========================================
# 会話クラス（複数ターン対応）
# ===========================================

class ConversationSession:
    """複数ターンの会話を管理するクラス"""
    
    def __init__(self, user_id: str = "user1"):
        self.user_id = user_id
        self.app_name = "memory_app"
        self.session_service = InMemorySessionService()
        self.session = None
        self.runner = None
    
    async def start(self):
        """セッションを開始"""
        self.session = await self.session_service.create_session(
            app_name=self.app_name,
            user_id=self.user_id
        )
        
        self.runner = Runner(
            agent=memory_agent,
            app_name=self.app_name,
            session_service=self.session_service
        )
        
        print(f"📝 セッション開始: {self.session.id[:8]}...")
        return self.session.id
    
    async def chat(self, message: str) -> str:
        """メッセージを送信して応答を取得"""
        content = types.Content(
            role="user",
            parts=[types.Part(text=message)]
        )
        
        print(f"\n👤 You: {message}")
        
        response_text = ""
        async for event in self.runner.run_async(
            user_id=self.user_id,
            session_id=self.session.id,
            new_message=content
        ):
            if event.is_final_response():
                response_text = event.content.parts[0].text
                print(f"🤖 Assistant: {response_text}")
        
        return response_text


# ===========================================
# デモシナリオ
# ===========================================

async def demo_session_memory():
    """セッションとメモリのデモ"""
    
    print("=" * 70)
    print("Day 3: Context Engineering - Sessions & Memory デモ")
    print("=" * 70)
    
    # APIキーチェック
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ エラー: GOOGLE_API_KEY が設定されていません")
        return
    
    # ===========================================
    # デモ 1: 短期記憶（セッション内の会話履歴）
    # ===========================================
    
    print("\n" + "=" * 70)
    print("📌 デモ 1: セッション内の会話履歴（短期記憶）")
    print("=" * 70)
    
    session1 = ConversationSession()
    await session1.start()
    
    # 複数ターンの会話 - エージェントは前の発言を覚えている
    await session1.chat("Hi! My name is Taro and I'm from Tokyo.")
    await session1.chat("What's my name and where am I from?")  # 前の発言を参照
    
    # ===========================================
    # デモ 2: 長期記憶（ユーザー設定の保存）
    # ===========================================
    
    print("\n" + "=" * 70)
    print("📌 デモ 2: 長期記憶（ユーザー設定の保存）")
    print("=" * 70)
    
    session2 = ConversationSession()
    await session2.start()
    
    await session2.chat("Please remember that my favorite color is blue and I prefer Japanese language.")
    await session2.chat("What are my saved preferences?")
    
    # ===========================================
    # デモ 3: タスク管理（セッション状態）
    # ===========================================
    
    print("\n" + "=" * 70)
    print("📌 デモ 3: タスク管理（セッション状態）")
    print("=" * 70)
    
    session3 = ConversationSession()
    session_id = await session3.start()
    
    # セッションIDをツールで使えるように
    await session3.chat(f"Add a high priority task: Finish the AI course. My session ID is {session_id}")
    await session3.chat(f"Add another task: Review Day 3 materials. Session ID: {session_id}")
    await session3.chat(f"Show me all my tasks. Session ID: {session_id}")
    
    # ===========================================
    # デモ 4: 新しいセッションでも長期記憶は保持
    # ===========================================
    
    print("\n" + "=" * 70)
    print("📌 デモ 4: 新しいセッションでの長期記憶呼び出し")
    print("=" * 70)
    
    session4 = ConversationSession()
    await session4.start()
    
    await session4.chat("Do you remember my preferences from before? What's my favorite color?")
    
    # ===========================================
    # メモリの状態を表示
    # ===========================================
    
    print("\n" + "=" * 70)
    print("📊 現在のメモリ状態")
    print("=" * 70)
    print(f"\n長期メモリ（user_memory）:")
    for user_id, prefs in user_memory.items():
        print(f"  User: {user_id}")
        for key, value in prefs.items():
            print(f"    - {key}: {value['value']}")
    
    print(f"\nセッションタスク（session_tasks）:")
    for sid, tasks in session_tasks.items():
        print(f"  Session: {sid[:8]}...")
        for task in tasks:
            print(f"    - [{task['status']}] {task['task']} ({task['priority']})")


# ===========================================
# インタラクティブモード
# ===========================================

async def interactive_mode():
    """インタラクティブな会話モード"""
    
    print("=" * 70)
    print("Day 3: インタラクティブ会話モード")
    print("=" * 70)
    print("'quit' または 'exit' で終了")
    print("'new' で新しいセッションを開始")
    print("=" * 70)
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ エラー: GOOGLE_API_KEY が設定されていません")
        return
    
    session = ConversationSession()
    await session.start()
    
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                print("👋 さようなら！")
                break
            
            if user_input.lower() == 'new':
                session = ConversationSession()
                await session.start()
                print("🆕 新しいセッションを開始しました")
                continue
            
            if not user_input:
                continue
            
            await session.chat(user_input)
            
        except KeyboardInterrupt:
            print("\n👋 さようなら！")
            break


# ===========================================
# メイン
# ===========================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        # インタラクティブモード: python day3_memory.py --interactive
        asyncio.run(interactive_mode())
    else:
        # デモモード
        asyncio.run(demo_session_memory())