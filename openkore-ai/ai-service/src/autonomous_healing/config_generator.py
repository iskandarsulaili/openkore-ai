"""
CrewAI-powered Config Generator for OpenKore
Generates optimal farming configurations based on character state

User requirement: "We should never fix config.txt or macro manually.
If it's config or macro issue, it should be done by the CrewAI or
autonomous self healing with hot reload!"
"""
import logging
from pathlib import Path
from typing import Dict, Optional
from crewai import Agent, Task, Crew

logger = logging.getLogger(__name__)

class ConfigGenerator:
    """
    Uses CrewAI to generate optimal OpenKore configurations
    for autonomous farming gameplay
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config generator
        
        Args:
            config_path: Path to config.txt (default: auto-detect)
        """
        if config_path is None:
            # Auto-detect: openkore-ai/control/config.txt
            config_path = Path(__file__).parent.parent.parent.parent / "control" / "config.txt"
        
        self.config_path = config_path
        logger.info(f"[CONFIG-GEN] Config path: {config_path}")
        
        # Create CrewAI expert agent
        self.config_agent = Agent(
            role='OpenKore Configuration Expert',
            goal='Generate optimal OpenKore config.txt settings for autonomous farming',
            backstory="""You are an expert in OpenKore bot configuration with 
            deep knowledge of optimal farming settings, AI behavior tuning, and 
            server-specific optimizations. You understand how config settings 
            interact with each other and can generate production-ready configurations.""",
            verbose=True,
            allow_delegation=False
        )
    
    def generate_farming_config(
        self,
        character_level: int,
        character_class: str,
        target_map: str = "prt_fild08",
        server_type: str = "rAthena"
    ) -> Dict[str, str]:
        """
        Generate optimal farming configuration using CrewAI
        
        Args:
            character_level: Current character level
            character_class: Current job class (e.g., "Novice", "Swordman")
            target_map: Target farming map
            server_type: Server type for optimization
        
        Returns:
            Dict of config key-value pairs
        """
        logger.info(f"[CONFIG-GEN] Generating farming config for Lv{character_level} {character_class}")
        logger.info(f"[CONFIG-GEN] Target map: {target_map}, Server: {server_type}")
        
        # Create task for CrewAI
        task_description = f"""
        Generate optimal OpenKore config.txt settings for autonomous farming:
        
        Character Info:
        - Level: {character_level}
        - Class: {character_class}
        - Target Map: {target_map}
        - Server: {server_type}
        
        Requirements:
        1. Enable aggressive auto-attack (attackAuto 2)
        2. Enable random walking to find monsters (route_randomWalk 1)
        3. Enable auto-pickup for drops (itemsTakeAuto 1, itemsGatherAuto 2)
        4. Lock to farming map to prevent leaving (lockMap {target_map})
        5. Set appropriate attack distance based on class
        6. Disable buyAuto to prevent infinite town returns
        7. Configure HP/SP recovery thresholds
        8. Set appropriate sit/stand behavior
        
        Output format:
        Return ONLY the config settings as key=value pairs, one per line.
        Example:
        attackAuto 2
        attackAuto_party 1
        route_randomWalk 1
        """
        
        config_task = Task(
            description=task_description,
            agent=self.config_agent,
            expected_output="OpenKore config.txt settings formatted as key=value pairs"
        )
        
        # Execute CrewAI crew
        crew = Crew(
            agents=[self.config_agent],
            tasks=[config_task],
            verbose=True
        )
        
        try:
            result = crew.kickoff()
            logger.info(f"[CONFIG-GEN] CrewAI generated config:\n{result}")
            
            # Parse result into dict
            config_dict = self._parse_config_result(str(result))
            
            # Ensure critical farming settings are present
            config_dict = self._ensure_critical_settings(config_dict, character_class, target_map)
            
            return config_dict
            
        except Exception as e:
            logger.error(f"[CONFIG-GEN] CrewAI generation failed: {e}")
            logger.info(f"[CONFIG-GEN] Falling back to template-based config")
            return self._get_fallback_config(character_class, target_map)
    
    def _parse_config_result(self, result: str) -> Dict[str, str]:
        """Parse CrewAI output into config dict"""
        config_dict = {}
        
        for line in result.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse "key value" or "key=value" format
            if ' ' in line:
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    config_dict[parts[0]] = parts[1]
            elif '=' in line:
                parts = line.split('=', 1)
                if len(parts) == 2:
                    config_dict[parts[0]] = parts[1]
        
        return config_dict
    
    def _ensure_critical_settings(
        self,
        config_dict: Dict[str, str],
        character_class: str,
        target_map: str
    ) -> Dict[str, str]:
        """
        Ensure critical settings are present for autonomous farming
        """
        # Critical settings that MUST be present
        critical_settings = {
            'attackAuto': '2',  # Auto-attack aggressively
            'attackAuto_party': '1',  # Attack in party
            'route_randomWalk': '1',  # Enable random walking
            'route_randomWalk_inTown': '0',  # But not in town
            'itemsTakeAuto': '1',  # Auto-pickup
            'itemsGatherAuto': '2',  # Gather aggressively
            'lockMap': target_map,  # Stay in farming map
            'sitAuto_hp_lower': '50',  # Sit when HP < 50%
            'sitAuto_hp_upper': '90',  # Stand when HP > 90%
            'sitAuto_sp_lower': '0',  # Don't sit for SP
            'attackDistance': '1.5',  # Engage distance
            'attackMaxDistance': '8',  # Max attack range
        }
        
        # Class-specific attack settings
        if character_class.lower() in ['archer', 'hunter', 'bard', 'dancer']:
            critical_settings['attackDistance'] = '4'  # Ranged class
            critical_settings['attackMaxDistance'] = '9'
        elif character_class.lower() in ['magician', 'wizard', 'sage']:
            critical_settings['attackDistance'] = '5'  # Magic class
            critical_settings['attackMaxDistance'] = '10'
        
        # Merge with existing config (critical settings take priority)
        for key, value in critical_settings.items():
            if key not in config_dict:
                config_dict[key] = value
        
        return config_dict
    
    def _get_fallback_config(self, character_class: str, target_map: str) -> Dict[str, str]:
        """
        Fallback configuration if CrewAI fails
        """
        logger.info(f"[CONFIG-GEN] Using fallback config template")
        
        config = {
            'attackAuto': '2',
            'attackAuto_party': '1',
            'route_randomWalk': '1',
            'route_randomWalk_inTown': '0',
            'route_randomWalk_maxRouteTime': '75',
            'itemsTakeAuto': '1',
            'itemsGatherAuto': '2',
            'itemsTakeAuto_new': '1',
            'lockMap': target_map,
            'sitAuto_hp_lower': '50',
            'sitAuto_hp_upper': '90',
            'sitAuto_sp_lower': '0',
            'sitAuto_sp_upper': '0',
            'sitAuto_follow': '0',
            'attackDistance': '1.5',
            'attackMaxDistance': '8',
            'teleportAuto_hp': '0',  # Disable to prevent disrupting farming
            'teleportAuto_sp': '0',
            'teleportAuto_idle': '0',
            'teleportAuto_portal': '0',
        }
        
        # Class-specific adjustments
        if character_class.lower() in ['archer', 'hunter', 'bard', 'dancer']:
            config['attackDistance'] = '4'
            config['attackMaxDistance'] = '9'
        elif character_class.lower() in ['magician', 'wizard', 'sage']:
            config['attackDistance'] = '5'
            config['attackMaxDistance'] = '10'
        elif character_class.lower() in ['acolyte', 'priest', 'monk']:
            config['attackDistance'] = '3'
            config['attackMaxDistance'] = '7'
        
        return config
    
    def write_config_to_file(self, config_dict: Dict[str, str], append: bool = True) -> bool:
        """
        Write generated config to config.txt
        
        Args:
            config_dict: Config settings to write
            append: If True, append to file. If False, overwrite.
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"[CONFIG-GEN] Writing config to {self.config_path}")
            
            mode = 'a' if append else 'w'
            with open(self.config_path, mode, encoding='utf-8') as f:
                if append:
                    f.write("\n\n# === Auto-generated by CrewAI Config Generator ===\n")
                    f.write(f"# Generated at: {Path(__file__).name}\n\n")
                
                for key, value in config_dict.items():
                    f.write(f"{key} {value}\n")
                
                if append:
                    f.write("# === End of auto-generated config ===\n\n")
            
            logger.info(f"[CONFIG-GEN] ✓ Config written successfully ({len(config_dict)} settings)")
            return True
            
        except Exception as e:
            logger.error(f"[CONFIG-GEN] Failed to write config: {e}")
            return False
    
    def signal_config_reload(self) -> bool:
        """
        Signal OpenKore to hot-reload config.txt
        
        This is done by touching a reload trigger file that OpenKore monitors
        """
        try:
            reload_trigger = self.config_path.parent / ".config_reload_trigger"
            reload_trigger.touch()
            logger.info(f"[CONFIG-GEN] ✓ Hot reload signal sent")
            return True
        except Exception as e:
            logger.error(f"[CONFIG-GEN] Failed to signal reload: {e}")
            return False
    
    def generate_and_apply_farming_config(
        self,
        character_level: int,
        character_class: str,
        target_map: str = "prt_fild08"
    ) -> bool:
        """
        Complete workflow: Generate config, write to file, and signal reload
        
        Returns:
            True if successful
        """
        logger.info(f"[CONFIG-GEN] ========================================")
        logger.info(f"[CONFIG-GEN] Starting autonomous config generation")
        logger.info(f"[CONFIG-GEN] Character: Lv{character_level} {character_class}")
        logger.info(f"[CONFIG-GEN] Target: {target_map}")
        logger.info(f"[CONFIG-GEN] ========================================")
        
        # Step 1: Generate config
        config_dict = self.generate_farming_config(
            character_level=character_level,
            character_class=character_class,
            target_map=target_map
        )
        
        if not config_dict:
            logger.error(f"[CONFIG-GEN] Failed to generate config")
            return False
        
        # Step 2: Write to file
        success = self.write_config_to_file(config_dict, append=True)
        if not success:
            return False
        
        # Step 3: Signal hot reload
        self.signal_config_reload()
        
        logger.info(f"[CONFIG-GEN] ========================================")
        logger.info(f"[CONFIG-GEN] ✅ Config generation complete")
        logger.info(f"[CONFIG-GEN] Settings applied: {len(config_dict)}")
        logger.info(f"[CONFIG-GEN] OpenKore will hot-reload within ~5 seconds")
        logger.info(f"[CONFIG-GEN] ========================================")
        
        return True


# Global instance
_config_generator = None

def get_config_generator() -> ConfigGenerator:
    """Get or create global config generator instance"""
    global _config_generator
    if _config_generator is None:
        _config_generator = ConfigGenerator()
    return _config_generator
