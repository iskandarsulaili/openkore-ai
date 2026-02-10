"""
Job Advancement Detector
Detects when character meets job change requirements
Server-agnostic pattern-based detection

Version 2.0: Extended to support all job paths including extended and special classes
"""

import json
from pathlib import Path
from typing import Dict, Optional, List, Any
from loguru import logger
import threading


class JobAdvancementDetector:
    """
    Detects job advancement opportunities based on character state
    Handles multi-step progression: Novice → 1st → 2nd → 3rd → 4th
    
    Version 2.0 Changes:
    - Support for all 11 job paths from job_build_variants.json
    - Extended class support (Gunslinger, Ninja, Taekwon, etc.)
    - Special class support (Super Novice, Summoner)
    - Integration with job_path_mappings
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize job advancement detector
        
        Args:
            data_dir: Directory containing job_change_locations.json and job_build_variants.json
        """
        self.data_dir = data_dir
        self.job_requirements: Dict[str, Any] = {}
        self.job_paths: Dict[str, List[str]] = {}
        self.job_path_mappings: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._load_job_data()
        
        logger.info("JobAdvancementDetector v2.0 initialized with extended class support")
    
    def _load_job_data(self):
        """Load job change requirements and paths from configuration"""
        try:
            job_file = self.data_dir / "job_change_locations.json"
            
            if not job_file.exists():
                logger.warning(f"Job data file not found: {job_file}, using defaults")
                self._load_defaults()
                return
            
            with open(job_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.job_requirements = data.get('requirements', {})
            self.job_paths = data.get('progression_paths', {})
            self.job_path_mappings = data.get('job_path_mappings', {})
            
            logger.success(f"Loaded job data for {len(self.job_requirements)} jobs, "
                         f"{len(self.job_path_mappings.get('paths', {}))} job paths")
            
        except Exception as e:
            logger.error(f"Failed to load job data: {e}")
            self._load_defaults()
    
    def _load_defaults(self):
        """Load default job requirements"""
        self.job_requirements = {
            "Novice": {
                "next_jobs": ["Swordman", "Mage", "Archer", "Acolyte", "Merchant", "Thief"],
                "base_level": 10,
                "job_level": 10
            },
            "Swordman": {
                "next_jobs": ["Knight", "Crusader"],
                "base_level": 40,
                "job_level": 40
            },
            "Mage": {
                "next_jobs": ["Wizard", "Sage"],
                "base_level": 40,
                "job_level": 40
            },
            "Archer": {
                "next_jobs": ["Hunter", "Dancer", "Bard"],
                "base_level": 40,
                "job_level": 40
            },
            "Acolyte": {
                "next_jobs": ["Priest", "Monk"],
                "base_level": 40,
                "job_level": 40
            },
            "Merchant": {
                "next_jobs": ["Blacksmith", "Alchemist"],
                "base_level": 40,
                "job_level": 40
            },
            "Thief": {
                "next_jobs": ["Assassin", "Rogue"],
                "base_level": 40,
                "job_level": 40
            }
        }
        
        self.job_paths = {
            "Novice": ["1st_class"],
            "1st_class": ["2nd_class"],
            "2nd_class": ["Transcendent"],
            "Transcendent": ["3rd_class"]
        }
    
    def check_advancement_ready(self, game_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check if character is ready for job advancement
        
        Args:
            game_state: Current game state with character information
            
        Returns:
            Dictionary with advancement details if ready, None otherwise
        """
        with self._lock:
            try:
                character = game_state.get('character', {})
                current_job = character.get('job_class', 'Novice')
                base_level = character.get('level', 0)
                job_level = character.get('job_level', 0)
                
                # Check if current job has advancement options
                job_info = self.job_requirements.get(current_job)
                
                if not job_info:
                    logger.debug(f"No advancement data for job: {current_job}")
                    return None
                
                # Check level requirements
                required_base = job_info.get('base_level', 99)
                required_job = job_info.get('job_level', 50)
                
                if base_level < required_base or job_level < required_job:
                    logger.debug(
                        f"Job advancement requirements not met: "
                        f"Base {base_level}/{required_base}, Job {job_level}/{required_job}"
                    )
                    return None
                
                # Get available next jobs
                next_jobs = job_info.get('next_jobs', [])
                
                if not next_jobs:
                    logger.info(f"No further advancement available for {current_job}")
                    return None
                
                logger.success(
                    f"Job advancement ready! {current_job} → {next_jobs} "
                    f"(Base: {base_level}, Job: {job_level})"
                )
                
                return {
                    'ready': True,
                    'current_job': current_job,
                    'next_jobs': next_jobs,
                    'base_level': base_level,
                    'job_level': job_level,
                    'recommended_job': self._recommend_job(current_job, next_jobs, character)
                }
                
            except Exception as e:
                logger.error(f"Error checking job advancement: {e}")
                return None
    
    def _recommend_job(self, current_job: str, next_jobs: List[str], character: Dict) -> str:
        """
        Recommend best next job based on character stats and playstyle
        
        Args:
            current_job: Current job class
            next_jobs: Available next jobs
            character: Character information
            
        Returns:
            Recommended job class name
        """
        if len(next_jobs) == 1:
            return next_jobs[0]
        
        # Simple heuristic based on stats
        stats = character.get('stats', {})
        str_stat = stats.get('str', 0)
        agi_stat = stats.get('agi', 0)
        int_stat = stats.get('int', 0)
        dex_stat = stats.get('dex', 0)
        
        # Build score for each job based on stat alignment
        scores = {}
        
        for job in next_jobs:
            score = 0
            job_lower = job.lower()
            
            # Physical damage dealers (STR-based)
            if any(x in job_lower for x in ['knight', 'crusader', 'blacksmith']):
                score = str_stat * 2 + dex_stat
            
            # AGI-based jobs
            elif any(x in job_lower for x in ['assassin', 'rogue', 'hunter']):
                score = agi_stat * 2 + dex_stat
            
            # INT-based jobs
            elif any(x in job_lower for x in ['wizard', 'sage', 'priest']):
                score = int_stat * 2 + dex_stat
            
            # Hybrid jobs
            elif any(x in job_lower for x in ['monk', 'alchemist']):
                score = (str_stat + agi_stat + int_stat) / 3 * 2
            
            # Balanced jobs
            else:
                score = (str_stat + agi_stat + int_stat + dex_stat) / 4
            
            scores[job] = score
        
        # Return job with highest score
        recommended = max(scores.items(), key=lambda x: x[1])[0]
        logger.info(f"Recommended job: {recommended} (scores: {scores})")
        
        return recommended
    
    def get_job_progression_status(self, current_job: str) -> Dict[str, Any]:
        """
        Get current position in job progression path
        
        Args:
            current_job: Current job class
            
        Returns:
            Dictionary with progression status
        """
        with self._lock:
            job_info = self.job_requirements.get(current_job, {})
            
            return {
                'current_job': current_job,
                'tier': self._get_job_tier(current_job),
                'next_jobs': job_info.get('next_jobs', []),
                'required_base_level': job_info.get('base_level', 99),
                'required_job_level': job_info.get('job_level', 50),
                'has_advancement': len(job_info.get('next_jobs', [])) > 0
            }
    
    def _get_job_tier(self, job: str) -> str:
        """Determine job tier (Novice, 1st, 2nd, Trans, 3rd)"""
        if job == "Novice":
            return "novice"
        elif job in ["Swordman", "Mage", "Archer", "Acolyte", "Merchant", "Thief"]:
            return "1st_class"
        elif any(x in job for x in ["Knight", "Crusader", "Wizard", "Sage", "Hunter", 
                                     "Dancer", "Bard", "Priest", "Monk", "Blacksmith", 
                                     "Alchemist", "Assassin", "Rogue"]):
            return "2nd_class"
        elif "Lord" in job or "High" in job or "Paladin" in job:
            return "transcendent"
        else:
            return "3rd_class"
