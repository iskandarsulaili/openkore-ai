"""
Research CrewAI 1.9.3+ features
"""
import inspect
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool

print("=" * 80)
print("CrewAI 1.9.3+ Feature Research")
print("=" * 80)

# Inspect Agent class
print("\n### AGENT CLASS ###")
print("Available parameters:")
agent_params = inspect.signature(Agent.__init__).parameters
for param_name, param in agent_params.items():
    if param_name != 'self':
        default = param.default if param.default != inspect.Parameter.empty else "REQUIRED"
        print(f"  - {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'Any'} = {default}")

# Inspect Task class
print("\n### TASK CLASS ###")
print("Available parameters:")
task_params = inspect.signature(Task.__init__).parameters
for param_name, param in task_params.items():
    if param_name != 'self':
        default = param.default if param.default != inspect.Parameter.empty else "REQUIRED"
        print(f"  - {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'Any'} = {default}")

# Inspect Crew class
print("\n### CREW CLASS ###")
print("Available parameters:")
crew_params = inspect.signature(Crew.__init__).parameters
for param_name, param in crew_params.items():
    if param_name != 'self':
        default = param.default if param.default != inspect.Parameter.empty else "REQUIRED"
        print(f"  - {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'Any'} = {default}")

# Check Process options
print("\n### PROCESS OPTIONS ###")
print(f"Available: {[p.name for p in Process]}")

# Check BaseTool
print("\n### TOOL SYSTEM ###")
print(f"BaseTool attributes: {[attr for attr in dir(BaseTool) if not attr.startswith('_')]}")

# Check for memory capabilities
try:
    from crewai.memory import EntityMemory, ShortTermMemory, LongTermMemory
    print("\n### MEMORY SYSTEM AVAILABLE ###")
    print("  - EntityMemory")
    print("  - ShortTermMemory")  
    print("  - LongTermMemory")
except ImportError:
    print("\n### MEMORY SYSTEM ###")
    print("  - Not available or different import path")

# Check for knowledge capabilities
try:
    from crewai.knowledge import Knowledge
    print("\n### KNOWLEDGE SYSTEM AVAILABLE ###")
    print("  - Knowledge")
except ImportError:
    print("\n### KNOWLEDGE SYSTEM ###")
    print("  - Not available")

print("\n" + "=" * 80)
