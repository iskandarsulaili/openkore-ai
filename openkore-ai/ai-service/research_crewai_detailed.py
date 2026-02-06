"""
Detailed CrewAI 1.9.3+ API research
"""
from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from crewai.memory import EntityMemory, ShortTermMemory, LongTermMemory
from crewai.llm import LLM
from pydantic import Field
import json
import os

print("=" * 80)
print("CrewAI 1.9.3+ Detailed API Research")
print("=" * 80)

# Set up LLM
os.environ["OPENAI_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", "dummy_key")
os.environ["OPENAI_API_BASE"] = "https://api.deepseek.com"

# Example Agent creation to see what fields are available
print("\n### CREATING TEST AGENT ###")
try:
    llm = LLM(model="deepseek-chat", base_url="https://api.deepseek.com", api_key=os.getenv("DEEPSEEK_API_KEY"))
    test_agent = Agent(
        role="Test Agent",
        goal="Test goal",
        backstory="Test backstory",
        verbose=True,
        llm=llm
    )
    print("OK Agent created successfully")
    print(f"  Agent model fields: {list(test_agent.model_fields.keys())}")
except Exception as e:
    print(f"ERROR Error creating agent: {e}")

# Example Task creation
print("\n### CREATING TEST TASK ###")
try:
    test_task = Task(
        description="Test task description",
        expected_output="Test expected output",
        agent=test_agent
    )
    print("OK Task created successfully")
    print(f"  Task model fields: {list(test_task.model_fields.keys())}")
except Exception as e:
    print(f"ERROR Error creating task: {e}")

# Example Crew creation
print("\n### CREATING TEST CREW ###")
try:
    test_crew = Crew(
        agents=[test_agent],
        tasks=[test_task],
        verbose=True,
        process=Process.sequential
    )
    print("OK Crew created successfully")
    print(f"  Crew model fields: {list(test_crew.model_fields.keys())}")
except Exception as e:
    print(f"ERROR Error creating crew: {e}")

# Memory capabilities
print("\n### MEMORY CAPABILITIES ###")
try:
    print(f"EntityMemory fields: {list(EntityMemory.model_fields.keys()) if hasattr(EntityMemory, 'model_fields') else 'Check docs'}")
    print(f"ShortTermMemory fields: {list(ShortTermMemory.model_fields.keys()) if hasattr(ShortTermMemory, 'model_fields') else 'Check docs'}")
    print(f"LongTermMemory fields: {list(LongTermMemory.model_fields.keys()) if hasattr(LongTermMemory, 'model_fields') else 'Check docs'}")
except Exception as e:
    print(f"Memory inspection error: {e}")

# Tool creation example
print("\n### CUSTOM TOOL EXAMPLE ###")
try:
    class TestTool(BaseTool):
        name: str = "test_tool"
        description: str = "A test tool"
        
        def _run(self, argument: str) -> str:
            return f"Executed with: {argument}"
    
    test_tool = TestTool()
    print("OK Custom tool created")
    print(f"  Tool fields: {list(test_tool.model_fields.keys())}")
except Exception as e:
    print(f"ERROR Tool creation error: {e}")

# Check async support
print("\n### ASYNC SUPPORT ###")
try:
    if hasattr(test_crew, 'kickoff_async'):
        print("OK Async execution supported (kickoff_async)")
    else:
        print("ERROR No async execution method found")
except Exception as e:
    print(f"Async check error: {e}")

# Check delegation
print("\n### DELEGATION SUPPORT ###")
try:
    if 'allow_delegation' in test_agent.model_fields:
        print("OK Delegation supported (allow_delegation parameter)")
    else:
        print("ERROR Delegation parameter not found in agent fields")
except Exception as e:
    print(f"Delegation check error: {e}")

# Check hierarchical process
print("\n### HIERARCHICAL PROCESS ###")
try:
    print(f"Available processes: {[p.value for p in Process]}")
    if Process.hierarchical:
        print("OK Hierarchical process available")
except Exception as e:
    print(f"Hierarchical check error: {e}")

print("\n" + "=" * 80)
