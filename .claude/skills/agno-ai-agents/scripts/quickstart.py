#!/usr/bin/env python3
"""
Quick start examples for Agno AI Agents framework.
Run individual examples to learn patterns.
"""

def basic_agent():
    """Create a basic agent."""
    from agno.agent import Agent
    from agno.models.openai import OpenAIResponses

    agent = Agent(
        name="My Agent",
        model=OpenAIResponses(id="gpt-4o"),
        instructions="You are a helpful assistant",
        markdown=True,
    )

    response = agent.run("Hello! Tell me about yourself.")
    print(response.content)


def agent_with_tools():
    """Create agent with tools."""
    from agno.agent import Agent
    from agno.models.openai import OpenAIResponses
    from agno.tools import tool

    @tool
    def get_weather(city: str) -> str:
        """Get weather for city.

        Args:
            city (str): The city to get weather for.
        """
        return f"Weather in {city} is sunny and 75°F."

    agent = Agent(
        name="Weather Agent",
        model=OpenAIResponses(id="gpt-4o"),
        tools=[get_weather],
        instructions="Help users with weather information",
        markdown=True,
    )

    response = agent.run("What's the weather in San Francisco?")
    print(response.content)


def agent_with_knowledge():
    """Create agent with knowledge base (RAG)."""
    from agno.agent import Agent
    from agno.models.openai import OpenAIResponses
    from agno.knowledge.knowledge import Knowledge
    from agno.vectordb.lancedb import LanceDb, SearchType

    knowledge = Knowledge(
        vector_db=LanceDb(
            uri="tmp/knowledge",
            table_name="docs",
            search_type=SearchType.hybrid,
        ),
    )

    # Add sample content
    knowledge.add_content(text="Agno is a framework for building multi-agent AI systems.")

    agent = Agent(
        name="Knowledge Agent",
        model=OpenAIResponses(id="gpt-4o"),
        knowledge=knowledge,
        instructions="Use your knowledge base to answer questions",
        markdown=True,
    )

    response = agent.run("What is Agno?")
    print(response.content)


def basic_team():
    """Create a basic team."""
    from agno.agent import Agent
    from agno.models.openai import OpenAIResponses
    from agno.team import Team

    researcher = Agent(
        name="Researcher",
        model=OpenAIResponses(id="gpt-4o"),
        role="Gather information",
    )

    writer = Agent(
        name="Writer",
        model=OpenAIResponses(id="gpt-4o"),
        role="Create content",
    )

    team = Team(
        name="Content Team",
        members=[researcher, writer],
        instructions="Research topic and write article",
        markdown=True,
    )

    response = team.run("Write about AI agents")
    print(response.content)


def basic_workflow():
    """Create a basic workflow."""
    from agno.agent import Agent
    from agno.models.openai import OpenAIResponses
    from agno.workflow import Workflow, Step

    researcher = Agent(
        name="Researcher",
        model=OpenAIResponses(id="gpt-4o"),
        role="Gather information",
    )

    writer = Agent(
        name="Writer",
        model=OpenAIResponses(id="gpt-4o"),
        role="Create content",
    )

    workflow = Workflow(
        name="Content Pipeline",
        steps=[
            Step(name="research", agent=researcher),
            Step(name="write", agent=writer),
        ],
    )

    response = workflow.run("Write about AI workflows")
    print(response.content)


def agent_with_memory():
    """Create agent with memory."""
    from agno.agent import Agent
    from agno.db.sqlite import SqliteDb
    from agno.memory import MemoryManager
    from agno.models.openai import OpenAIResponses

    db = SqliteDb(db_file="tmp/agents.db")

    memory_manager = MemoryManager(
        model=OpenAIResponses(id="gpt-4o"),
        db=db,
    )

    agent = Agent(
        name="Memory Agent",
        model=OpenAIResponses(id="gpt-4o"),
        memory_manager=memory_manager,
        enable_agentic_memory=True,
        instructions="Remember user preferences",
        markdown=True,
    )

    # First interaction
    response1 = agent.run("I prefer short answers.", user_id="user@example.com")
    print(f"Response 1: {response1.content}")

    # Second interaction - agent remembers preference
    response2 = agent.run("What's 2+2?", user_id="user@example.com")
    print(f"Response 2: {response2.content}")


def agentos_deployment():
    """Create AgentOS deployment."""
    from agno.agent import Agent
    from agno.models.openai import OpenAIResponses
    from agno.os import AgentOS

    agent = Agent(
        name="My Agent",
        model=OpenAIResponses(id="gpt-4o"),
        instructions="You are a helpful assistant",
        markdown=True,
    )

    agent_os = AgentOS(agents=[agent])
    app = agent_os.get_app()

    # This creates a FastAPI app
    print("AgentOS app created!")
    print("Run with: uvicorn main:app --reload")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python quickstart.py <example>")
        print("\nAvailable examples:")
        print("  basic_agent          - Create basic agent")
        print("  agent_with_tools     - Agent with tools")
        print("  agent_with_knowledge  - Agent with knowledge base")
        print("  basic_team           - Create team")
        print("  basic_workflow       - Create workflow")
        print("  agent_with_memory    - Agent with memory")
        print("  agentos_deployment   - Deploy with AgentOS")
        sys.exit(1)

    example = sys.argv[1]

    examples = {
        "basic_agent": basic_agent,
        "agent_with_tools": agent_with_tools,
        "agent_with_knowledge": agent_with_knowledge,
        "basic_team": basic_team,
        "basic_workflow": basic_workflow,
        "agent_with_memory": agent_with_memory,
        "agentos_deployment": agentos_deployment,
    }

    if example in examples:
        print(f"\nRunning: {example}\n")
        examples[example]()
    else:
        print(f"Unknown example: {example}")
        print(f"Available: {', '.join(examples.keys())}")
