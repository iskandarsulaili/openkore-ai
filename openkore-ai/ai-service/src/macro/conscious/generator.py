"""
MacroGenerator Agent
Converts strategic intent into valid OpenKore macro syntax
"""

import logging
import re
from typing import Dict, List
from crewai import Agent, Task, Crew
from pydantic import BaseModel, Field
from llm.provider_chain import llm_chain
from .reference_loader import MacroReferenceLoader

logger = logging.getLogger(__name__)


class GeneratedMacro(BaseModel):
    """Generated macro with metadata"""
    macro_text: str = Field(..., description="Complete OpenKore macro syntax")
    macro_name: str = Field(..., description="Generated macro name")
    macro_type: str = Field(..., description="Type of macro")
    estimated_performance: Dict = Field(default_factory=dict, description="Expected performance metrics")
    validation_result: Dict = Field(default_factory=dict, description="Syntax validation result")


class MacroGenerator:
    """
    MacroGenerator Agent
    
    Role: Converts strategic intent into valid OpenKore eventMacro syntax
    Capabilities:
    - Translate strategic requirements into OpenKore syntax
    - Validate macro structure and syntax
    - Optimize macro performance (timing, conditions)
    - Generate multiple macro variations
    """
    
    def __init__(self):
        """Initialize MacroGenerator agent"""
        # Load EventMacro reference document
        self.reference_summary = MacroReferenceLoader.load_reference_summary()
        self.syntax_instructions = MacroReferenceLoader.get_syntax_instructions()
        
        self.agent = self._create_agent()
        self.templates = self._load_templates()
        
        logger.info("MacroGenerator agent initialized with EventMacro reference")
    
    def _create_agent(self) -> Agent:
        """Create the CrewAI agent with integrated reference"""
        backstory = f"""You are an expert in OpenKore eventMacro Domain-Specific Language (DSL).

You have access to the complete EventMacro reference documentation and MUST follow it precisely.

{self.reference_summary}

{self.syntax_instructions}

Your core responsibilities:
1. Generate syntactically PERFECT eventMacro code following the reference
2. Validate all conditions and commands against documented syntax
3. Optimize timing, priority, and exclusivity settings
4. Include comprehensive logging for debugging
5. Ensure macro names are descriptive and follow conventions

**CRITICAL:** Every macro you generate MUST be 100% syntactically correct according to the reference.
Consult the reference documentation for any syntax questions before generating code.

Your task is to take strategic requirements and generate syntactically correct,
performant OpenKore macros that accomplish the intended goal."""
        
        return Agent(
            role="Macro Code Generator",
            goal="Convert strategic intent into valid, optimized OpenKore eventMacro syntax using the complete EventMacro reference",
            backstory=backstory,
            verbose=True,
            allow_delegation=False,
            llm=llm_chain.get_crewai_llm()
        )
    
    def _load_templates(self) -> Dict:
        """Load macro templates for each type"""
        return {
            'farming': self._farming_template,
            'healing': self._healing_template,
            'resource_management': self._resource_template,
            'escape': self._escape_template,
            'skill_rotation': self._skill_rotation_template
        }
    
    def generate_automacro_tool(self, trigger_conditions: Dict) -> str:
        """
        Generate automacro block from trigger conditions
        
        Args:
            trigger_conditions: Dictionary of trigger conditions
            
        Returns:
            Automacro block syntax
        """
        name = trigger_conditions.get('name', 'generated_macro')
        priority = trigger_conditions.get('priority', 50)
        exclusive = trigger_conditions.get('exclusive', 1)
        timeout = trigger_conditions.get('timeout', 5)
        
        conditions = []
        for cond_type, cond_value in trigger_conditions.get('conditions', {}).items():
            conditions.append(f"    {cond_type} {cond_value}")
        
        automacro = f"""automacro {name} {{
    exclusive {exclusive}
    priority {priority}
    timeout {timeout}
{chr(10).join(conditions)}
    call {name}_sequence
}}"""
        
        return automacro
    
    def validate_syntax_tool(self, macro_text: str) -> Dict:
        """
        Validate macro syntax
        
        Args:
            macro_text: Macro definition text
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        # Check balanced braces
        open_braces = macro_text.count('{')
        close_braces = macro_text.count('}')
        if open_braces != close_braces:
            errors.append(f"Unbalanced braces: {open_braces} open vs {close_braces} close")
        
        # Check for automacro block
        if not re.search(r'automacro\s+\w+\s*\{', macro_text):
            errors.append("Missing automacro block")
        
        # Check for macro block
        if not re.search(r'macro\s+\w+\s*\{', macro_text):
            errors.append("Missing macro block")
        
        # Check for call statement
        if 'call' not in macro_text:
            errors.append("Missing call statement")
        
        # Check for proper indentation (warning only)
        lines = macro_text.split('\n')
        for i, line in enumerate(lines, 1):
            if line.strip() and not (line.startswith(' ') or line.startswith('\t') or line.startswith('#') or 'automacro' in line or 'macro' in line or '}' in line):
                if 'call' not in line and 'exclusive' not in line and 'priority' not in line:
                    warnings.append(f"Line {i}: Poor indentation")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def optimize_conditions_tool(self, conditions: Dict) -> Dict:
        """
        Optimize trigger conditions for performance
        
        Args:
            conditions: Original conditions
            
        Returns:
            Optimized conditions
        """
        optimized = conditions.copy()
        
        # Optimize timeout based on condition type
        if 'hp' in conditions:
            optimized['timeout'] = 2  # Fast response for HP
        elif 'weight' in conditions:
            optimized['timeout'] = 60  # Slower check for weight
        
        # Adjust priority based on urgency
        if any(term in str(conditions) for term in ['hp < 20', 'aggressives > 8']):
            optimized['priority'] = max(optimized.get('priority', 50), 90)
        
        return optimized
    
    def _farming_template(self, params: Dict) -> str:
        """Generate farming macro from parameters"""
        monster_name = params.get('monster_name', 'Monster')
        map_name = params.get('map_name', 'prontera')
        hp_threshold = params.get('hp_threshold', 50)
        priority = params.get('priority', 60)
        
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', monster_name).lower()
        
        return f"""automacro farm_{safe_name} {{
    exclusive 1
    map {map_name}
    monster {monster_name}
    hp > {hp_threshold}%
    priority {priority}
    timeout 5
    run-once 0
    call farm_{safe_name}_sequence
}}

macro farm_{safe_name}_sequence {{
    log [Farming] Engaging {monster_name}...
    do attack "{monster_name}"
    pause 1
    do take
    pause 0.5
    log [Farming] Completed {monster_name} sequence
}}"""
    
    def _healing_template(self, params: Dict) -> str:
        """Generate healing macro from parameters"""
        hp_threshold = params.get('hp_threshold', 30)
        healing_items = params.get('healing_items', ['White Potion', 'Orange Potion'])
        priority = params.get('priority', 95)
        
        healing_actions = []
        for item in healing_items:
            healing_actions.append(f"    do is {item}")
            healing_actions.append("    pause 0.5")
        
        return f"""automacro emergency_heal_{hp_threshold} {{
    exclusive 1
    hp < {hp_threshold}%
    priority {priority}
    timeout 2
    call emergency_heal_sequence
}}

macro emergency_heal_sequence {{
    log [Healing] Emergency healing triggered at {hp_threshold}%
{chr(10).join(healing_actions)}
    log [Healing] Healing complete
}}"""
    
    def _resource_template(self, params: Dict) -> str:
        """Generate resource management macro from parameters"""
        weight_threshold = params.get('weight_threshold', 80)
        action = params.get('action', 'storage')
        priority = params.get('priority', 85)
        
        if action == 'storage':
            action_sequence = """    log [Resource] Opening storage...
    do storage
    pause 2
    log [Resource] Storage opened"""
        else:
            action_sequence = f"""    log [Resource] Performing {action}...
    pause 1"""
        
        return f"""automacro manage_weight_{weight_threshold} {{
    exclusive 1
    weight > {weight_threshold}%
    priority {priority}
    timeout 60
    call manage_weight_sequence
}}

macro manage_weight_sequence {{
    log [Resource] Weight management triggered at {weight_threshold}%
{action_sequence}
    log [Resource] Weight management complete
}}"""
    
    def _escape_template(self, params: Dict) -> str:
        """Generate escape macro from parameters"""
        aggressive_threshold = params.get('aggressive_threshold', 5)
        escape_method = params.get('escape_method', 'fly_wing')
        priority = params.get('priority', 90)
        
        if escape_method == 'fly_wing':
            escape_action = "    do is Fly Wing"
        else:
            escape_action = f"    # {escape_method} not implemented"
        
        return f"""automacro escape_threat_{aggressive_threshold} {{
    exclusive 1
    aggressives > {aggressive_threshold}
    priority {priority}
    timeout 3
    call escape_sequence
}}

macro escape_sequence {{
    log [ESCAPE] Surrounded by hostiles - escaping!
{escape_action}
    pause 1
    log [ESCAPE] Escape attempt complete
}}"""
    
    def _skill_rotation_template(self, params: Dict) -> str:
        """Generate skill rotation macro from parameters"""
        skills = params.get('skills', [])
        monster_target = params.get('target_monster', 'Monster')
        priority = params.get('priority', 50)
        
        skill_actions = []
        for skill in skills:
            skill_actions.append(f"    do ss {skill} \"{monster_target}\"")
            skill_actions.append("    pause 1")
        
        return f"""automacro skill_rotation {{
    exclusive 0
    monster {monster_target}
    sp > 30%
    priority {priority}
    timeout 5
    call skill_rotation_sequence
}}

macro skill_rotation_sequence {{
    log [Combat] Executing skill rotation
{chr(10).join(skill_actions) if skill_actions else "    # No skills defined"}
    log [Combat] Skill rotation complete
}}"""
    
    async def generate_macro(self, strategic_intent: Dict) -> GeneratedMacro:
        """
        Generate macro from strategic intent
        
        Args:
            strategic_intent: Strategic decision from MacroStrategist
            
        Returns:
            Generated macro with validation
        """
        logger.info(f"Generating macro of type: {strategic_intent.get('macro_type')}")
        
        macro_type = strategic_intent.get('macro_type', 'farming')
        parameters = strategic_intent.get('parameters', {})
        priority = strategic_intent.get('priority', 50)
        
        # Add priority to parameters
        parameters['priority'] = priority
        
        # Use template system for fast generation
        template_func = self.templates.get(macro_type)
        if template_func:
            macro_text = template_func(parameters)
            
            # Extract macro name from generated text
            match = re.search(r'automacro\s+(\w+)\s*\{', macro_text)
            macro_name = match.group(1) if match else f"generated_{macro_type}"
        else:
            # Fallback: Use CrewAI for complex generation
            macro_text, macro_name = await self._generate_with_crewai(strategic_intent)
        
        # Validate generated macro
        validation = self.validate_syntax_tool(macro_text)
        
        if not validation['valid']:
            logger.warning(f"Generated macro has validation errors: {validation['errors']}")
            # Attempt automatic fixes
            macro_text = self._attempt_fixes(macro_text, validation['errors'])
            validation = self.validate_syntax_tool(macro_text)
        
        result = GeneratedMacro(
            macro_text=macro_text,
            macro_name=macro_name,
            macro_type=macro_type,
            estimated_performance={
                'expected_execution_time_ms': 2000,
                'estimated_success_rate': 0.85
            },
            validation_result=validation
        )
        
        logger.info(
            f"✓ Generated macro '{macro_name}' "
            f"({'VALID' if validation['valid'] else 'INVALID'})"
        )
        
        return result
    
    async def _generate_with_crewai(self, strategic_intent: Dict) -> tuple:
        """Generate macro using CrewAI when templates are insufficient"""
        task = Task(
            description=f"""
            Generate OpenKore eventMacro syntax for this strategic intent:
            
            Type: {strategic_intent.get('macro_type')}
            Priority: {strategic_intent.get('priority')}
            Reason: {strategic_intent.get('reason')}
            Parameters: {strategic_intent.get('parameters')}
            
            **REQUIREMENTS:**
            1. Generate complete automacro block with appropriate triggers
            2. Generate complete macro block with action sequence
            3. Follow EVENTMACRO_COMPLETE_REFERENCE.md syntax EXACTLY
            4. Use proper formatting, indentation, and structure
            5. Include logging statements for debugging
            6. Add appropriate pause commands for stability
            7. Set correct priority based on macro type
            8. Use exclusive flag appropriately
            
            **REFERENCE:** You have the complete EventMacro reference in your backstory.
            Consult it for exact syntax of conditions, commands, and structure.
            
            Use OpenKore eventMacro DSL syntax exactly as documented.
            """,
            agent=self.agent,
            expected_output="Complete OpenKore macro syntax following EVENTMACRO_COMPLETE_REFERENCE.md"
        )
        
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=True
        )
        
        result = crew.kickoff()
        
        # Extract macro name
        match = re.search(r'automacro\s+(\w+)\s*\{', str(result))
        macro_name = match.group(1) if match else "generated_macro"
        
        return str(result), macro_name
    
    def _attempt_fixes(self, macro_text: str, errors: List[str]) -> str:
        """Attempt automatic fixes for common syntax errors"""
        fixed_text = macro_text
        
        # Fix unbalanced braces
        if any('brace' in error.lower() for error in errors):
            open_count = fixed_text.count('{')
            close_count = fixed_text.count('}')
            if open_count > close_count:
                fixed_text += '\n}' * (open_count - close_count)
            elif close_count > open_count:
                # Remove extra closing braces
                for _ in range(close_count - open_count):
                    fixed_text = fixed_text[::-1].replace('}', '', 1)[::-1]
        
        return fixed_text
