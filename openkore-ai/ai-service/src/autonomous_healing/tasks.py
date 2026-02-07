"""
CrewAI Tasks for Autonomous Healing Workflow
"""

from crewai import Task
from typing import Dict, Any


def create_monitoring_task(monitor_agent) -> Task:
    """Create monitoring task"""
    return Task(
        description="""
        Monitor OpenKore logs in real-time for errors, warnings, and anomalies.
        Detect patterns like:
        - Unknown packet switches (e.g., 0BF6)
        - NPC interaction failures
        - AI stuck loops (same state repeating)
        - Route calculation issues
        - Position desyncs
        - Character deaths
        
        Return detected issues with context for analysis.
        """,
        expected_output="List of detected issues with severity and context",
        agent=monitor_agent
    )


def create_analysis_task(analysis_agent) -> Task:
    """Create analysis task"""
    return Task(
        description="""
        Analyze detected issues to identify root causes by:
        - Correlating errors with config.txt settings
        - Validating NPC coordinates against npcs.txt database
        - Checking lockMap boundaries vs spawn position
        - Reviewing monster control settings
        - Examining packet handler definitions
        
        Identify the PRIMARY root cause with confidence score.
        """,
        expected_output="Root cause analysis with confidence scores and evidence",
        agent=analysis_agent
    )


def create_solution_task(solution_agent) -> Task:
    """Create solution generation task"""
    return Task(
        description="""
        Generate intelligent, context-aware solutions based on:
        - Character level and class
        - Current map and activity
        - Game version (kRO Ragexe_2021_11_03)
        - Past successful fixes from knowledge base
        
        Solutions must be ADAPTIVE, not hardcoded.
        Include confidence scores and approval requirements.
        """,
        expected_output="List of proposed solutions with changes, confidence, and approval flags",
        agent=solution_agent
    )


def create_validation_task(validation_agent) -> Task:
    """Create validation task"""
    return Task(
        description="""
        Validate proposed solutions for:
        - Syntax correctness (regex patterns, config format)
        - Logical soundness (action matches issue)
        - Safety (won't break bot)
        - Confidence threshold (>= 0.6)
        
        Reject invalid or unsafe solutions.
        """,
        expected_output="Validation result with errors/warnings if any",
        agent=validation_agent
    )


def create_execution_task(execution_agent) -> Task:
    """Create execution task"""
    return Task(
        description="""
        Safely execute validated fixes:
        1. Create automatic backup
        2. Apply changes to config files
        3. Verify changes were applied correctly
        4. Trigger hot-reload if possible
        5. Monitor for issues post-fix
        6. Rollback if problems detected
        
        Log all actions for audit trail.
        """,
        expected_output="Execution result with success status and backup location",
        agent=execution_agent
    )


def create_learning_task(learner_agent) -> Task:
    """Create learning task"""
    return Task(
        description="""
        Learn from fix outcomes:
        - Record success/failure in knowledge base
        - Update confidence scores
        - Identify recurring patterns
        - Improve future solution generation
        
        Maintain pattern frequency and confidence decay.
        """,
        expected_output="Learning summary with updated knowledge base stats",
        agent=learner_agent
    )
