"""
vanna_setup.py — Initializes the Vanna 2.0 Agent with Google Gemini LLM,
SQLite runner, tool registry, and agent memory.

Shared by seed_memory.py and main.py.
"""

import os
from dotenv import load_dotenv

load_dotenv()

from vanna import Agent, AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import SaveQuestionToolArgsTool, SearchSavedCorrectToolUsesTool
from vanna.integrations.sqlite import SqliteRunner
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.google import GeminiLlmService

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clinic.db")

# ─── Singleton instances ───────────────────────────────────────────────────────

_agent = None
_agent_memory = None


class ClinicUserResolver(UserResolver):
    """Simple user resolver that returns a default clinic user."""

    def resolve_user(self, request_context: RequestContext) -> User:
        return User(
            id="clinic_user",
            username="clinic_user",
            email="user@clinic.com",
            group_memberships=["clinic_users"],
            metadata={},
        )


def get_agent_memory() -> DemoAgentMemory:
    """Get or create the shared DemoAgentMemory instance."""
    global _agent_memory
    if _agent_memory is None:
        _agent_memory = DemoAgentMemory(max_items=1000)
    return _agent_memory


def create_agent() -> Agent:
    """Create and return a fully configured Vanna 2.0 Agent."""
    global _agent

    if _agent is not None:
        return _agent

    # 1. LLM Service — Google Gemini
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set. Check your .env file.")

    llm_service = GeminiLlmService(
        api_key=api_key,
        model="gemini-2.5-flash",
    )

    # 2. SQL Runner — SQLite
    sql_runner = SqliteRunner(database_path=DB_PATH)

    # 3. Agent Memory
    agent_memory = get_agent_memory()

    # 4. Tool Registry
    tools = ToolRegistry()

    tools.register_local_tool(
        RunSqlTool(sql_runner=sql_runner),
        access_groups=["clinic_users"],
    )

    tools.register_local_tool(
        VisualizeDataTool(),
        access_groups=["clinic_users"],
    )

    tools.register_local_tool(
        SaveQuestionToolArgsTool(),
        access_groups=["clinic_users"],
    )

    tools.register_local_tool(
        SearchSavedCorrectToolUsesTool(),
        access_groups=["clinic_users"],
    )

    # 5. User Resolver
    user_resolver = ClinicUserResolver()

    # 6. Create Agent
    _agent = Agent(
        llm_service=llm_service,
        tool_registry=tools,
        user_resolver=user_resolver,
        agent_memory=agent_memory,
        config=AgentConfig(),
    )

    return _agent


if __name__ == "__main__":
    agent = create_agent()
    print("Vanna 2.0 Agent created successfully!")
    print(f"Database: {DB_PATH}")
    print(f"LLM: Google Gemini (gemini-2.5-flash)")
    print(f"Memory items: {get_agent_memory()}")
