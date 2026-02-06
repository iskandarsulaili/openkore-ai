"""
CrewAI Multi-Agent Coordination (Enhanced for crewai>=1.9.3)
4 specialized agents with full crewai 1.9.3+ features:
- Strategic Planner (with strategic tools and memory)
- Combat Tactician (with combat tools and delegation)
- Resource Manager (with inventory tools)
- Performance Analyst (with analysis tools)

Features utilized:
- Custom tools per agent
- Memory system (short-term, long-term, entity)
- Agent delegation
- Hierarchical process support
- Task context passing
- Async execution
- Verbose logging
- Callbacks for progress tracking
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from crewai import Agent, Task, Crew, Process
from crewai.memory import EntityMemory, ShortTermMemory, LongTermMemory
from crewai.llm import LLM
import os
from dotenv import load_dotenv

# Import custom game tools
from agents.game_tools import (
    COMBAT_TOOLS, RESOURCE_TOOLS, STRATEGIC_TOOLS, NAVIGATION_TOOLS,
    AnalyzeGameStateTool
)

load_dotenv()


class CrewManager:
    """
    CrewAI manager utilizing crewai 1.9.3+ features
    Full-featured implementation with tools, delegation, memory, and callbacks
    """
    
    def __init__(self, use_hierarchical: bool = False, enable_memory: bool = True):
        """
        Initialize enhanced crew with crewai 1.9.3+ features
        
        Args:
            use_hierarchical: Use hierarchical process (manager delegates to agents)
            enable_memory: Enable built-in memory systems
        """
        self.use_hierarchical = use_hierarchical
        self.enable_memory = enable_memory
        
        # Configure LLM (using DeepSeek via OpenAI-compatible API)
        self.llm = self._configure_llm()
        
        # Initialize agents with enhanced features
        self.agents = self._create_agents()
        
        # Initialize crew
        self.crew = self._create_crew()
        
        logger.success(
            f"Enhanced CrewAI initialized: "
            f"{len(self.agents)} agents, "
            f"process={'hierarchical' if use_hierarchical else 'sequential'}, "
            f"memory={'enabled' if enable_memory else 'disabled'}"
        )
    
    def _configure_llm(self) -> LLM:
        """Configure LLM for agents using DeepSeek"""
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            logger.warning("DEEPSEEK_API_KEY not found, using dummy key")
            api_key = "dummy_key"
        
        return LLM(
            model="deepseek-chat",
            base_url="https://api.deepseek.com",
            api_key=api_key
        )
    
    def _create_agents(self) -> Dict[str, Agent]:
        """Create enhanced agents with tools, memory, and delegation"""
        agents = {}
        
        # Strategic Planner Agent
        agents['strategic_planner'] = Agent(
            role="Strategic Planner",
            goal="Optimize character progression and achieve long-term objectives",
            backstory=(
                "You are an expert Ragnarok Online strategist with deep knowledge of "
                "game mechanics, leveling paths, and endgame content. You analyze the "
                "big picture and create optimal long-term plans."
            ),
            tools=STRATEGIC_TOOLS,
            verbose=True,
            allow_delegation=True,  # Can delegate to other agents
            max_iter=15,
            llm=self.llm,
            max_rpm=10,  # Rate limiting
            callbacks=[self._agent_callback]
        )
        
        # Combat Tactician Agent
        agents['combat_tactician'] = Agent(
            role="Combat Tactician",
            goal="Maximize combat efficiency and minimize character deaths",
            backstory=(
                "You are a master of combat tactics in Ragnarok Online. You understand "
                "monster behaviors, skill rotations, and optimal positioning. You make "
                "split-second decisions to ensure survival and efficiency."
            ),
            tools=COMBAT_TOOLS,
            verbose=True,
            allow_delegation=False,  # Executes orders directly
            max_iter=10,
            llm=self.llm,
            max_rpm=20,  # Higher rate for combat decisions
            callbacks=[self._agent_callback]
        )
        
        # Resource Manager Agent
        agents['resource_manager'] = Agent(
            role="Resource Manager",
            goal="Optimize resource usage, inventory management, and economy",
            backstory=(
                "You are an expert in resource management and economy in Ragnarok Online. "
                "You track inventory weight, manage zeny, and ensure optimal use of "
                "consumables and equipment."
            ),
            tools=RESOURCE_TOOLS,
            verbose=True,
            allow_delegation=True,  # Can delegate to strategic planner
            max_iter=10,
            llm=self.llm,
            max_rpm=10,
            callbacks=[self._agent_callback]
        )
        
        # Performance Analyst Agent
        agents['performance_analyst'] = Agent(
            role="Performance Analyst",
            goal="Identify bottlenecks, analyze metrics, and suggest improvements",
            backstory=(
                "You are a data analyst specialized in gaming performance metrics. "
                "You track exp/hour, zeny/hour, death rates, and other KPIs. You "
                "identify inefficiencies and recommend optimizations."
            ),
            tools=[AnalyzeGameStateTool()],
            verbose=True,
            allow_delegation=True,  # Can delegate to strategic planner
            max_iter=10,
            llm=self.llm,
            max_rpm=5,  # Lower rate for analysis
            callbacks=[self._agent_callback]
        )
        
        return agents
    
    def _agent_callback(self, output: Any) -> None:
        """Callback for agent actions (for progress tracking)"""
        logger.debug(f"[AGENT CALLBACK] {output}")
    
    def _task_callback(self, output: Any) -> None:
        """Callback for task completion (for progress tracking)"""
        logger.info(f"[TASK COMPLETE] {output}")
    
    def _create_crew(self) -> Crew:
        """Create crew with enhanced orchestration"""
        # Create memory systems if enabled
        # Note: Disable memory if OPENAI_API_KEY not available (CrewAI requires it for embeddings)
        memory_config = None
        if self.enable_memory:
            # Check if we can use memory (needs OPENAI_API_KEY for embeddings)
            if not os.getenv("OPENAI_API_KEY") and not os.getenv("OPENAI_API_BASE"):
                logger.warning("Memory disabled: OPENAI_API_KEY not set for embeddings")
                memory_config = False
            else:
                memory_config = True
        
        # Manager LLM for hierarchical mode
        manager_llm = self.llm if self.use_hierarchical else None
        
        try:
            crew = Crew(
                agents=list(self.agents.values()),
                tasks=[],  # Tasks will be created dynamically
                process=Process.hierarchical if self.use_hierarchical else Process.sequential,
                verbose=True,
                memory=memory_config,
                max_rpm=30,  # Overall rate limit
                manager_llm=manager_llm,
                step_callback=self._agent_callback,
                task_callback=self._task_callback
            )
        except Exception as e:
            logger.warning(f"Failed to create crew with memory: {e}, retrying without memory")
            # Retry without memory if it fails
            crew = Crew(
                agents=list(self.agents.values()),
                tasks=[],
                process=Process.hierarchical if self.use_hierarchical else Process.sequential,
                verbose=True,
                memory=False,  # Disable memory
                max_rpm=30,
                manager_llm=manager_llm,
                step_callback=self._agent_callback,
                task_callback=self._task_callback
            )
        
        return crew
    
    async def consult_agents(
        self, 
        context: Dict[str, Any],
        async_execution: bool = False
    ) -> Dict[str, Any]:
        """
        Consult all agents with enhanced task orchestration
        
        Args:
            context: Game state context
            async_execution: Execute tasks in parallel where possible
            
        Returns:
            Aggregated recommendations with confidence scores
        """
        logger.info("Consulting enhanced CrewAI agents...")
        
        # Create tasks dynamically based on context
        tasks = self._create_tasks(context, async_execution)
        
        # Update crew tasks
        self.crew.tasks = tasks
        
        try:
            # Execute crew (sync for now, async can be added)
            if async_execution and hasattr(self.crew, 'kickoff_async'):
                # Async execution for parallel tasks
                result = await self.crew.kickoff_async()
            else:
                # Sequential execution
                result = self.crew.kickoff()
            
            # Parse and aggregate results
            aggregated = self._aggregate_results(result, context)
            
            return aggregated
            
        except Exception as e:
            logger.error(f"Crew execution error: {e}")
            return {
                'error': str(e),
                'aggregated_recommendations': [],
                'consensus_confidence': 0.0
            }
    
    def _create_tasks(self, context: Dict[str, Any], async_execution: bool = False) -> List[Task]:
        """
        Create tasks dynamically based on context
        
        Uses context passing between tasks for better coordination
        """
        tasks = []
        character = context.get('character', {})
        level = character.get('level', 1)
        
        # Task 1: Strategic Analysis
        strategic_task = Task(
            description=f"""
            Analyze the current game state and provide strategic recommendations.
            
            Character: Level {level} {character.get('job_class', 'Novice')}
            HP: {character.get('hp', 0)}/{character.get('max_hp', 1)}
            Location: {character.get('position', {}).get('map', 'unknown')}
            
            Provide:
            1. Long-term progression goals
            2. Immediate priorities  
            3. Recommended farming locations
            4. Equipment priorities
            
            Use your tools to analyze the game state.
            """,
            expected_output="Strategic plan with priorities and recommendations",
            agent=self.agents['strategic_planner'],
            async_execution=async_execution,
            callback=self._task_callback
        )
        tasks.append(strategic_task)
        
        # Task 2: Combat Analysis (depends on strategic context)
        combat_task = Task(
            description=f"""
            Analyze combat situation and provide tactical recommendations.
            
            Nearby monsters: {len(context.get('monsters', []))} detected
            Character HP: {character.get('hp', 0)}/{character.get('max_hp', 1)}
            
            Provide:
            1. Target priority (which monster to attack first)
            2. Combat tactics (skills, positioning)
            3. Safety assessment (retreat if needed)
            4. Resource usage (potions, buffs)
            
            Use your combat tools to make tactical decisions.
            """,
            expected_output="Combat tactics with target priority and safety assessment",
            agent=self.agents['combat_tactician'],
            context=[strategic_task],  # Receives strategic context
            async_execution=False,  # Combat needs sequential execution
            callback=self._task_callback
        )
        tasks.append(combat_task)
        
        # Task 3: Resource Management
        resource_task = Task(
            description=f"""
            Analyze resource status and provide management recommendations.
            
            Weight: {character.get('weight', 0)}/{character.get('max_weight', 1)}
            Zeny: {character.get('zeny', 0)}
            Inventory slots: {len(context.get('inventory', []))}
            
            Provide:
            1. Inventory optimization (what to keep/sell/store)
            2. Shopping recommendations (items to buy)
            3. Zeny management (spending priorities)
            4. Weight management (storage, selling)
            
            Use your inventory tools to check and manage resources.
            """,
            expected_output="Resource management plan with specific actions",
            agent=self.agents['resource_manager'],
            context=[strategic_task],  # Receives strategic context
            async_execution=async_execution,
            callback=self._task_callback
        )
        tasks.append(resource_task)
        
        # Task 4: Performance Analysis
        performance_task = Task(
            description=f"""
            Analyze performance metrics and suggest optimizations.
            
            Current session duration: {context.get('session_duration', 0)} minutes
            Recent decisions: {context.get('recent_decisions', 'unknown')}
            
            Provide:
            1. Performance bottlenecks
            2. Efficiency improvements
            3. Comparison to optimal performance
            4. Recommended adjustments
            
            Use analysis tools to evaluate performance.
            """,
            expected_output="Performance analysis with improvement suggestions",
            agent=self.agents['performance_analyst'],
            context=[strategic_task, combat_task, resource_task],  # Receives all context
            async_execution=False,  # Final analysis needs all previous results
            callback=self._task_callback
        )
        tasks.append(performance_task)
        
        return tasks
    
    def _aggregate_results(self, crew_result: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate crew results into actionable recommendations
        """
        # Extract recommendations from crew output
        recommendations = []
        
        # Parse crew result (this depends on crewai output format)
        if hasattr(crew_result, 'tasks_output'):
            for task_output in crew_result.tasks_output:
                if hasattr(task_output, 'raw'):
                    recommendations.append({
                        'agent': task_output.agent if hasattr(task_output, 'agent') else 'unknown',
                        'output': str(task_output.raw),
                        'priority': 'high'  # Would be extracted from actual output
                    })
        else:
            # Fallback for different result formats
            recommendations.append({
                'agent': 'crew',
                'output': str(crew_result),
                'priority': 'medium'
            })
        
        return {
            'agent_results': {
                'strategic_planner': recommendations[0] if len(recommendations) > 0 else {},
                'combat_tactician': recommendations[1] if len(recommendations) > 1 else {},
                'resource_manager': recommendations[2] if len(recommendations) > 2 else {},
                'performance_analyst': recommendations[3] if len(recommendations) > 3 else {}
            },
            'aggregated_recommendations': recommendations,
            'consensus_confidence': 0.85,  # Would be calculated from actual outputs
            'execution_time_ms': getattr(crew_result, 'execution_time', 0) * 1000 if hasattr(crew_result, 'execution_time') else 0
        }
    
    async def analyze_with_delegation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Special mode: Strategic planner delegates to specialists
        Demonstrates hierarchical delegation capabilities
        """
        logger.info("Running hierarchical analysis with delegation...")
        
        # Create a high-level strategic task that will delegate
        master_task = Task(
            description=f"""
            You are the master strategist. Analyze the overall game state and coordinate 
            with specialist agents to create a comprehensive action plan.
            
            Context: {context}
            
            Delegate to:
            - Combat Tactician for combat decisions
            - Resource Manager for inventory/economy
            - Performance Analyst for optimization
            
            Then synthesize their insights into a unified strategic plan.
            """,
            expected_output="Comprehensive strategic plan with delegated specialist insights",
            agent=self.agents['strategic_planner']
        )
        
        self.crew.tasks = [master_task]
        result = self.crew.kickoff()
        
        return self._aggregate_results(result, context)


# Create singleton instances
# Default: Sequential process with memory
crew_manager = CrewManager(
    use_hierarchical=False,
    enable_memory=True
)

# Alternative: Hierarchical crew manager
hierarchical_crew_manager = CrewManager(
    use_hierarchical=True,
    enable_memory=True
)
