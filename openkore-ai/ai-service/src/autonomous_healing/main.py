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

from crewai import Crew, Process
import yaml

from .agents import (
    create_monitor_agent,
    create_analysis_agent,
    create_solution_agent,
    create_validation_agent,
    create_execution_agent,
    create_learning_agent
)
from .core.log_monitor import LogMonitor
from .core.issue_detector import IssueDetector
from .core.knowledge_base import KnowledgeBase
from .tasks import (
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
        
        self.logger.info("Autonomous Healing System initialized")
    
    def _load_config(self) -> dict:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
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
        
        agent_configs = self.config['crewai']['agents']
        
        # Create agents
        self.agents['monitor'] = create_monitor_agent(
            agent_configs['monitor'],
            self.log_monitor,
            self.issue_detector
        )
        
        self.agents['analyzer'] = create_analysis_agent(
            agent_configs['analyzer'],
            self.config['analysis']
        )
        
        self.agents['solver'] = create_solution_agent(
            agent_configs['solver'],
            self.knowledge_base,
            self.config['solution']
        )
        
        self.agents['validator'] = create_validation_agent(
            agent_configs['validator']
        )
        
        self.agents['executor'] = create_execution_agent(
            agent_configs['executor'],
            self.config['execution']
        )
        
        self.agents['learner'] = create_learning_agent(
            agent_configs['learner'],
            self.knowledge_base
        )
        
        self.logger.info(f"Initialized {len(self.agents)} agents")
    
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
        
        # Create crew with hierarchical process
        self.crew = Crew(
            agents=list(self.agents.values()),
            tasks=tasks,
            process=Process.hierarchical,  # Manager coordinates agents
            verbose=True,
            manager_llm=self.config['crewai']['model']
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
        
        while self.running:
            try:
                # Monitor for new issues
                issues = await self.log_monitor.check_for_issues()
                
                if issues:
                    self.logger.info(f"Detected {len(issues)} issue(s)")
                    
                    # Process each issue through CrewAI
                    for issue in issues:
                        await self._process_issue(issue)
                
                # Wait before next check
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                self.logger.error(f"Error in healing loop: {e}", exc_info=True)
                await asyncio.sleep(poll_interval * 2)  # Back off on error
    
    async def _process_issue(self, issue: dict):
        """Process a single issue through the CrewAI workflow"""
        self.logger.info(f"Processing issue: {issue['type']}")
        
        try:
            # Create context for this specific issue
            context = {
                'issue': issue,
                'timestamp': datetime.now().isoformat(),
                'openkore_base': str(Path(__file__).parent.parent.parent.parent),
                'config': self.config
            }
            
            # Run CrewAI crew to analyze and fix
            result = self.crew.kickoff(inputs=context)
            
            self.logger.info(f"Issue processed: {result}")
            
            # Learn from the outcome
            await self._learn_from_result(issue, result)
            
        except Exception as e:
            self.logger.error(f"Failed to process issue: {e}", exc_info=True)
    
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
