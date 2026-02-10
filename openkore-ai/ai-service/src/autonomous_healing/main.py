"""
OpenKore Autonomous Self-Healing System - Main Entry Point
Real-time monitoring, intelligent analysis, and automatic repair using CrewAI
"""

import asyncio
import sys
import argparse
from pathlib import Path
from typing import Optional
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import time

# CRITICAL: Add parent directory to sys.path BEFORE any local imports
# This allows the script to work when src/main.py is run directly
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Now safe to import third-party and local modules
from crewai import Crew, Process
import yaml

from llm.provider_chain import LLMProviderChain
from utils.config_resolver import get_recvpackets_path, get_table_file_path

# Use absolute imports instead of relative imports to avoid "attempted relative import beyond top-level package" errors
from autonomous_healing.agents import (
    create_monitor_agent,
    create_analysis_agent,
    create_solution_agent,
    create_validation_agent,
    create_execution_agent,
    create_learning_agent
)
from autonomous_healing.core.log_monitor import LogMonitor
from autonomous_healing.core.issue_detector import IssueDetector
from autonomous_healing.core.knowledge_base import KnowledgeBase
from autonomous_healing.tasks import (
    create_monitoring_task,
    create_analysis_task,
    create_solution_task,
    create_validation_task,
    create_execution_task,
    create_learning_task
)


class AutonomousHealingSystem:
    """
    Main orchestrator for the autonomous self-healing system.
    Coordinates CrewAI agents to monitor, analyze, and fix OpenKore issues.
    """
    
    def __init__(self, config_path: str = "src/autonomous_healing/config.yaml"):
        self.config_path = Path(config_path)
        self.logger = None  # Will be set after config is loaded
        self.config = self._load_config()
        self.logger = self._setup_logging()
        
        # Core components
        self.log_monitor = LogMonitor(self.config['monitoring'])
        self.issue_detector = IssueDetector(self.config['detection'])
        self.knowledge_base = KnowledgeBase(self.config['learning']['knowledge_base_path'])
        
        # CrewAI setup
        self.crew = None
        self.agents = {}
        self.running = False
        
        # Thread pool executor for running synchronous crew.kickoff() in async context
        self.executor = ThreadPoolExecutor(max_workers=1)
        
        self.logger.info("Autonomous Healing System initialized")
    
    def _load_config(self) -> dict:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Dynamically resolve recvpackets path if set to "dynamic"
        if 'analysis' in config and 'context_files' in config['analysis']:
            context_files = config['analysis']['context_files']
            
            if context_files.get('recvpackets') == 'dynamic':
                # Resolve recvpackets path based on servers.txt and current server
                resolved_path = get_recvpackets_path()
                if resolved_path:
                    context_files['recvpackets'] = resolved_path
                    if self.logger:
                        self.logger.info(f"Dynamically resolved recvpackets path: {resolved_path}")
                else:
                    if self.logger:
                        self.logger.warning("Failed to resolve recvpackets path dynamically, using fallback")
                    context_files['recvpackets'] = "../tables/recvpackets.txt"
            
            # Optionally resolve other table files dynamically as well
            for file_key in ['monsters', 'npcs', 'maps']:
                if file_key in context_files:
                    current_path = context_files[file_key]
                    # Only resolve if it's a relative path starting with ../tables/
                    if current_path.startswith('../tables/') and '/' in current_path[len('../tables/'):]:
                        filename = Path(current_path).name
                        resolved_path = get_table_file_path(filename)
                        if resolved_path:
                            context_files[file_key] = resolved_path
                            if self.logger:
                                self.logger.info(f"Dynamically resolved {file_key}: {resolved_path}")
        
        return config
    
    def _setup_logging(self) -> logging.Logger:
        """Configure logging system"""
        log_config = self.config['logging']
        
        logger = logging.getLogger('AutonomousHealing')
        logger.setLevel(getattr(logging, log_config['level']))
        
        # File handler
        log_file = Path(log_config['file'])
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(log_config['format'])
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _initialize_agents(self):
        """Initialize all CrewAI agents"""
        self.logger.info("Initializing CrewAI agents...")
        
        # Initialize LLM provider chain (DeepSeek with failover)
        self.logger.info("Initializing LLM provider chain...")
        llm_chain = LLMProviderChain()
        llm = llm_chain.get_crewai_llm()
        self.logger.info("LLM provider initialized successfully")
        
        agent_configs = self.config['crewai']['agents']
        
        # Create agents with DeepSeek LLM
        self.agents['monitor'] = create_monitor_agent(
            agent_configs['monitor'],
            self.log_monitor,
            self.issue_detector,
            llm
        )
        
        self.agents['analyzer'] = create_analysis_agent(
            agent_configs['analyzer'],
            self.config['analysis'],
            llm
        )
        
        self.agents['solver'] = create_solution_agent(
            agent_configs['solver'],
            self.knowledge_base,
            self.config['solution'],
            llm
        )
        
        self.agents['validator'] = create_validation_agent(
            agent_configs['validator'],
            llm
        )
        
        self.agents['executor'] = create_execution_agent(
            agent_configs['executor'],
            self.config['execution'],
            llm
        )
        
        self.agents['learner'] = create_learning_agent(
            agent_configs['learner'],
            self.knowledge_base,
            llm
        )
        
        self.logger.info(f"Initialized {len(self.agents)} agents with DeepSeek LLM")
    
    def _create_crew(self):
        """Create CrewAI crew with all agents and tasks"""
        self.logger.info("Creating CrewAI crew...")
        
        # Create tasks
        tasks = [
            create_monitoring_task(self.agents['monitor']),
            create_analysis_task(self.agents['analyzer']),
            create_solution_task(self.agents['solver']),
            create_validation_task(self.agents['validator']),
            create_execution_task(self.agents['executor']),
            create_learning_task(self.agents['learner'])
        ]
        
        # Get LLM instance for manager (reuse the same LLM we created for agents)
        from llm.provider_chain import LLMProviderChain
        llm_chain = LLMProviderChain()
        manager_llm = llm_chain.get_crewai_llm()
        
        # Create crew with hierarchical process
        self.crew = Crew(
            agents=list(self.agents.values()),
            tasks=tasks,
            process=Process.hierarchical,  # Manager coordinates agents
            verbose=True,
            manager_llm=manager_llm  # Use LLM instance, not string
        )
        
        self.logger.info("CrewAI crew created successfully")
    
    async def start(self):
        """Start the autonomous healing system"""
        self.logger.info("="*60)
        self.logger.info("Starting OpenKore Autonomous Self-Healing System")
        self.logger.info("="*60)
        
        try:
            # Initialize components
            self._initialize_agents()
            self._create_crew()
            
            # Start monitoring
            self.running = True
            self.logger.info("System is now active and monitoring...")
            
            # Main loop
            await self._run_healing_loop()
            
        except KeyboardInterrupt:
            self.logger.info("Shutdown signal received")
            await self.stop()
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            await self.stop()
            raise
    
    async def _run_healing_loop(self):
        """Main healing loop - continuously monitor and heal"""
        poll_interval = self.config['monitoring']['poll_interval_seconds']
        
        self.logger.info(f"Starting healing loop (poll interval: {poll_interval}s)")
        
        cycle_count = 0
        while self.running:
            try:
                cycle_count += 1
                self.logger.debug(f"Monitoring cycle {cycle_count}")
                
                # Scan log files for issues
                log_issues = await self.log_monitor.check_for_issues()
                
                # Also scan config.txt periodically for configuration issues
                config_path = Path(self.config['analysis']['context_files']['config'])
                config_issues = []
                if config_path.exists():
                    config_issues = self.issue_detector.scan_config_file(str(config_path))
                    
                    if config_issues:
                        self.logger.warning(f"Found {len(config_issues)} configuration issues")
                        for cfg_issue in config_issues:
                            self.logger.warning(f"  - {cfg_issue['type']}: {cfg_issue['description']}")
                        
                        # CRITICAL FIX: Process config issues through CrewAI!
                        for cfg_issue in config_issues:
                            await self._process_issue(cfg_issue)
                
                # Process log issues
                if log_issues:
                    self.logger.info(f"Detected {len(log_issues)} log-based issue(s)")
                    
                    # Detect issues from log lines
                    for log_issue in log_issues:
                        detected = self.issue_detector.scan_lines(log_issue['new_lines'])
                        
                        if detected:
                            self.logger.info(f"Parsed {len(detected)} specific issues from logs")
                            
                            # Log CRITICAL issues prominently
                            critical_issues = [i for i in detected if i.get('severity') == 'CRITICAL']
                            if critical_issues:
                                self.logger.critical("="*60)
                                self.logger.critical("CRITICAL ISSUES DETECTED (Phase 31)")
                                for ci in critical_issues:
                                    self.logger.critical(f"  {ci['type']}: {ci.get('description', ci.get('line_content', 'No description'))}")
                                self.logger.critical("="*60)
                            
                            # Process each detected issue
                            for issue in detected:
                                await self._process_issue(issue)
                
                # Wait before next check
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                self.logger.error(f"Error in healing loop: {e}", exc_info=True)
                await asyncio.sleep(poll_interval * 2)  # Back off on error
    
    async def _process_issue(self, issue: dict):
        """Process a single issue through the CrewAI workflow"""
        issue_type = issue.get('type', 'unknown')
        severity = issue.get('severity', 'UNKNOWN')
        
        self.logger.info("="*60)
        self.logger.info(f"PROCESSING ISSUE: {issue_type} (Severity: {severity})")
        self.logger.info("="*60)
        
        # Console output for user visibility
        print("\n" + "="*60)
        print("[CONFIG] Autonomous Healing: Processing issue...")
        print(f"   Issue: {issue_type} (Severity: {severity})")
        print("="*60)
        
        # Log issue details
        if 'description' in issue:
            self.logger.info(f"Description: {issue['description']}")
        if 'confidence' in issue:
            self.logger.info(f"Detection confidence: {issue['confidence']:.2%}")
        
        try:
            # Create context for this specific issue
            context = {
                'issue': issue,
                'timestamp': datetime.now().isoformat(),
                'openkore_base': str(Path(__file__).parent.parent.parent.parent),
                'config': self.config,
                'character_context': {
                    'level': 6,  # TODO: Extract from logs
                    'class': 'Novice'  # TODO: Extract from logs
                }
            }
            
            # Progress logging
            self.logger.info("[RELOAD] Phase 1/6: Monitor agent analyzing issue...")
            self.logger.info(f"[LIST] Processing: {issue_type}")
            self.logger.info("[WAIT] This may take 1-3 minutes for multi-agent collaboration...")
            self.logger.info("[AI] CrewAI agents: Monitor → Analyzer → Solver → Validator → Executor → Learner")
            
            # Console output for user visibility
            print("   [WAIT] Please wait 1-3 minutes for AI agents to collaborate...")
            print("   [AI] AI Agents working...")
            
            # Start time tracking
            start_time = time.time()
            
            try:
                # Run CrewAI crew to analyze and fix (in thread pool to avoid blocking)
                # crew.kickoff() is SYNCHRONOUS, so we run it in executor
                loop = asyncio.get_event_loop()
                
                # Add timeout protection (300 seconds = 5 minutes)
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        self.executor,
                        self.crew.kickoff,
                        context
                    ),
                    timeout=300
                )
                
                # Calculate duration
                duration = time.time() - start_time
                self.logger.info(f"[TIME] Completed in {duration:.1f} seconds")
                
                # Console output for completion
                print(f"   [SUCCESS] Completed in {duration:.1f}s")
                
                # Log result
                if result.get('success'):
                    self.logger.info(f"[SUCCESS] Issue resolved: {issue_type}")
                    print(f"   [OK] Issue resolved: {issue_type}")
                    if 'solution' in result:
                        self.logger.info(f"Solution applied: {result['solution'].get('action', 'N/A')}")
                        solution_action = result['solution'].get('action', 'N/A')
                        if solution_action != 'N/A':
                            print(f"   💾 Solution: {solution_action}")
                else:
                    self.logger.warning(f" Issue resolution failed: {issue_type}")
                    print(f"   [WARNING] Issue resolution incomplete: {issue_type}")
                    if 'error' in result:
                        self.logger.error(f"Error: {result['error']}")
                        
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                self.logger.error(f"[WARNING] CrewAI workflow timeout ({duration:.1f}s / 300s max)")
                self.logger.error(f"Issue may require manual intervention: {issue_type}")
                
                # Console output for timeout
                print(f"   [TIME] Timeout after {duration:.0f}s - Issue may need manual review")
                print(f"   [INFO] Check logs for details: {self.config['logging']['file']}")
                
                self.logger.info("="*60)
                print("="*60)
                return  # Skip to next issue (exit method)
            
            self.logger.info("="*60)
            print("="*60 + "\n")
            
            # Learn from the outcome
            await self._learn_from_result(issue, result)
            
        except Exception as e:
            self.logger.error(f"Failed to process issue: {e}", exc_info=True)
            self.logger.info("="*60)
    
    async def _learn_from_result(self, issue: dict, result: dict):
        """Update knowledge base based on fix result"""
        try:
            # Store in knowledge base
            await self.knowledge_base.record_fix(
                issue_type=issue['type'],
                context=issue,
                solution=result.get('solution'),
                success=result.get('success', False),
                confidence=result.get('confidence', 0.5)
            )
            
            self.logger.debug(f"Learned from result: {result.get('success')}")
            
        except Exception as e:
            self.logger.error(f"Failed to learn from result: {e}")
    
    async def stop(self):
        """Gracefully shutdown the system"""
        self.logger.info("Shutting down autonomous healing system...")
        self.running = False
        
        # Shutdown executor
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        
        # Close knowledge base
        if hasattr(self, 'knowledge_base'):
            await self.knowledge_base.close()
        
        self.logger.info("Shutdown complete")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="OpenKore Autonomous Self-Healing System"
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='src/autonomous_healing/config.yaml',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--bot',
        type=str,
        help='Specific bot instance to monitor (e.g., kicapmasin_0)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Analyze only, do not apply fixes'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    return parser.parse_args()


async def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Create system instance
    system = AutonomousHealingSystem(config_path=args.config)
    
    # Apply CLI overrides
    if args.dry_run:
        system.config['execution']['enabled'] = False
        system.logger.info("DRY-RUN MODE: Analysis only, no fixes will be applied")
    
    if args.debug:
        system.config['logging']['level'] = 'DEBUG'
        system.logger.setLevel(logging.DEBUG)
    
    if args.bot:
        system.config['monitoring']['bot_filter'] = args.bot
        system.logger.info(f"Monitoring specific bot: {args.bot}")
    
    # Start the system
    await system.start()


if __name__ == "__main__":
    # Run the autonomous healing system
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        sys.exit(1)
