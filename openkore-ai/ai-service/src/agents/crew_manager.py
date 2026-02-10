"""
CrewAI Multi-Agent Coordination (Enhanced for crewai>=1.9.3)
4 specialized agents with full crewai 1.9.3+ features:
- Strategic Planner (with strategic tools and memory)
- Combat Tactician (with combat tools and delegation)
- Resource Manager (with inventory tools)
- Performance Analyst (with analysis tools)

Features utilized:
- Custom tools per agent
- Memory system (short-term, long-term, entity) with OpenMemory synthetic embeddings
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
from datetime import datetime, timedelta
import hashlib
import json

# Import custom game tools
from agents.game_tools import (
    COMBAT_TOOLS, RESOURCE_TOOLS, STRATEGIC_TOOLS, NAVIGATION_TOOLS,
    AnalyzeGameStateTool
)

# Import OpenMemory embedder for CrewAI memory
from memory.crewai_embedder import get_crewai_embedder

load_dotenv()


# ============================================================================
# CREWAI RESULT CACHING SYSTEM
# ============================================================================

class CrewAIResultCache:
    """
    Sophisticated caching system for CrewAI task results
    
    Features:
    - Task parameter hashing for cache keys
    - Configurable TTL (default 5 minutes)
    - Automatic expiration
    - Cache statistics tracking
    """
    
    def __init__(self, default_ttl_seconds: int = 300):
        """
        Initialize cache
        
        Args:
            default_ttl_seconds: Default time-to-live for cache entries (default: 5 minutes)
        """
        self.default_ttl = default_ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._stats = {
            'hits': 0,
            'misses': 0,
            'expirations': 0,
            'invalidations': 0
        }
        logger.info(f"CrewAI result cache initialized with {default_ttl_seconds}s TTL")
    
    def _generate_cache_key(self, context: Dict[str, Any], task_type: str = "default") -> str:
        """
        Generate cache key from task parameters
        
        Uses MD5 hash of normalized context to create unique cache keys
        
        Args:
            context: Task context/parameters
            task_type: Type of task (for cache segmentation)
            
        Returns:
            Cache key string
        """
        # Create normalized representation of context
        # Only include relevant fields that affect the result
        cache_context = {
            'task_type': task_type,
            'character_level': context.get('character', {}).get('level'),
            'job_class': context.get('character', {}).get('job_class'),
            'hp': context.get('character', {}).get('hp'),
            'max_hp': context.get('character', {}).get('max_hp'),
            'map': context.get('character', {}).get('position', {}).get('map'),
            'monsters_count': len(context.get('monsters', [])),
            'party_size': len(context.get('party', {}).get('members', [])) if context.get('party') else 0
        }
        
        # Convert to stable JSON string
        cache_str = json.dumps(cache_context, sort_keys=True)
        
        # Generate hash
        cache_hash = hashlib.md5(cache_str.encode()).hexdigest()
        
        return f"crew_{task_type}_{cache_hash}"
    
    def get(self, context: Dict[str, Any], task_type: str = "default") -> Optional[Dict[str, Any]]:
        """
        Get cached result if available and not expired
        
        Args:
            context: Task context to generate cache key
            task_type: Type of task
            
        Returns:
            Cached result or None if not found/expired
        """
        cache_key = self._generate_cache_key(context, task_type)
        
        if cache_key not in self._cache:
            self._stats['misses'] += 1
            logger.debug(f"[CACHE MISS] Key: {cache_key}")
            return None
        
        entry = self._cache[cache_key]
        
        # Check if expired
        age = datetime.now() - entry['timestamp']
        if age.total_seconds() > entry['ttl']:
            logger.debug(f"[CACHE EXPIRED] Key: {cache_key}, Age: {age.total_seconds():.1f}s")
            self._stats['expirations'] += 1
            del self._cache[cache_key]
            return None
        
        # Cache hit
        self._stats['hits'] += 1
        logger.info(f"[CACHE HIT] Key: {cache_key}, Age: {age.total_seconds():.1f}s")
        return entry['result']
    
    def set(
        self,
        context: Dict[str, Any],
        result: Dict[str, Any],
        task_type: str = "default",
        ttl: Optional[int] = None
    ) -> None:
        """
        Store result in cache
        
        Args:
            context: Task context to generate cache key
            result: Result to cache
            task_type: Type of task
            ttl: Optional custom TTL (seconds), uses default if not provided
        """
        cache_key = self._generate_cache_key(context, task_type)
        ttl = ttl if ttl is not None else self.default_ttl
        
        self._cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now(),
            'ttl': ttl,
            'context_summary': {
                'level': context.get('character', {}).get('level'),
                'map': context.get('character', {}).get('position', {}).get('map')
            }
        }
        
        logger.debug(f"[CACHE SET] Key: {cache_key}, TTL: {ttl}s")
    
    def invalidate(self, context: Dict[str, Any], task_type: str = "default") -> bool:
        """
        Manually invalidate a cache entry
        
        Args:
            context: Task context to generate cache key
            task_type: Type of task
            
        Returns:
            True if entry was found and removed, False otherwise
        """
        cache_key = self._generate_cache_key(context, task_type)
        
        if cache_key in self._cache:
            del self._cache[cache_key]
            self._stats['invalidations'] += 1
            logger.info(f"[CACHE INVALIDATE] Key: {cache_key}")
            return True
        
        return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"[CACHE CLEAR] Cleared {count} entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache performance metrics
        """
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            'total_entries': len(self._cache),
            'total_requests': total_requests,
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate_percent': round(hit_rate, 2),
            'expirations': self._stats['expirations'],
            'invalidations': self._stats['invalidations']
        }
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries
        
        Returns:
            Number of entries removed
        """
        now = datetime.now()
        expired_keys = []
        
        for key, entry in self._cache.items():
            age = now - entry['timestamp']
            if age.total_seconds() > entry['ttl']:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            self._stats['expirations'] += 1
        
        if expired_keys:
            logger.info(f"[CACHE CLEANUP] Removed {len(expired_keys)} expired entries")
        
        return len(expired_keys)


# Global cache instance
_result_cache = CrewAIResultCache(default_ttl_seconds=300)


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
        """Create crew with enhanced orchestration using OpenMemory synthetic embeddings"""
        # Create memory systems with OpenMemory synthetic embeddings
        # This enables memory without requiring OpenAI API key
        memory_config = False
        embedder_config = None
        
        if self.enable_memory:
            try:
                # Create OpenMemory embedder for CrewAI
                embedder = get_crewai_embedder(dimension=384)
                
                # Set up embedder config for CrewAI's memory system
                # CrewAI uses ChromaDB internally, so we pass the embedder directly
                embedder_config = embedder  # Pass the embedder instance directly
                
                memory_config = True
                logger.success("Memory enabled with OpenMemory synthetic embeddings (no OpenAI API required)")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenMemory embedder: {e}, memory will be disabled")
                memory_config = False
        
        # Manager LLM for hierarchical mode
        manager_llm = self.llm if self.use_hierarchical else None
        
        try:
            # Create crew with embedder configuration
            # The embedder is passed through embedder_config to RAGStorage
            crew_config = {
                "agents": list(self.agents.values()),
                "tasks": [],  # Tasks will be created dynamically
                "process": Process.hierarchical if self.use_hierarchical else Process.sequential,
                "verbose": True,
                "memory": memory_config,
                "max_rpm": 30,  # Overall rate limit
                "manager_llm": manager_llm,
                "step_callback": self._agent_callback,
                "task_callback": self._task_callback
            }
            
            # Add embedder config if memory is enabled
            if memory_config and embedder_config:
                crew_config["embedder_config"] = embedder_config
            
            crew = Crew(**crew_config)
            logger.info(f"Crew created successfully with memory={'enabled' if memory_config else 'disabled'}")
            
        except Exception as e:
            logger.warning(f"Failed to create crew with custom embedder: {e}")
            logger.info("Retrying with standard memory configuration (ChromaDB default)...")
            
            # Retry without custom embedder - ChromaDB will use default sentence-transformers
            # This still avoids OpenAI API calls
            try:
                crew = Crew(
                    agents=list(self.agents.values()),
                    tasks=[],
                    process=Process.hierarchical if self.use_hierarchical else Process.sequential,
                    verbose=True,
                    memory=memory_config,  # Still enable memory
                    max_rpm=30,
                    manager_llm=manager_llm,
                    step_callback=self._agent_callback,
                    task_callback=self._task_callback
                )
                logger.info("Crew created with ChromaDB default embeddings (sentence-transformers)")
                logger.info("Note: This uses local embeddings, no OpenAI API required")
            except Exception as e2:
                logger.warning(f"Failed to create crew with memory: {e2}, retrying without memory")
                # Final fallback: disable memory completely
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
                logger.warning("Crew created without memory")
        
        return crew
    
    async def consult_agents(
        self,
        context: Dict[str, Any],
        async_execution: bool = False,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Consult all agents with enhanced task orchestration and result caching
        
        Args:
            context: Game state context
            async_execution: Execute tasks in parallel where possible
            use_cache: Whether to use result caching (default: True)
            cache_ttl: Optional custom cache TTL in seconds
            
        Returns:
            Aggregated recommendations with confidence scores
        """
        logger.info("Consulting enhanced CrewAI agents...")
        
        # Check cache first if enabled
        if use_cache:
            cached_result = _result_cache.get(context, task_type="consult_agents")
            if cached_result:
                logger.success("Using cached CrewAI result")
                cached_result['_cached'] = True
                return cached_result
        
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
            aggregated['_cached'] = False
            
            # Cache the result if caching is enabled
            if use_cache:
                _result_cache.set(context, aggregated, task_type="consult_agents", ttl=cache_ttl)
                logger.debug("Cached CrewAI result for future use")
            
            return aggregated
            
        except Exception as e:
            logger.error(f"Crew execution error: {e}")
            return {
                'error': str(e),
                'aggregated_recommendations': [],
                'consensus_confidence': 0.0,
                '_cached': False
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
