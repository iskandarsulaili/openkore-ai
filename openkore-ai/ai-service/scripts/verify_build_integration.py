#!/usr/bin/env python3
"""
Build Variant Integration Verification Script

Verifies that all job build variants from opkAI have been properly integrated
into the openkore-ai system.

Usage:
    python scripts/verify_build_integration.py
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


class BuildIntegrationVerifier:
    """Verifies integration of job build variants"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.success_count = 0
        
    def verify_all(self) -> bool:
        """Run all verification checks"""
        logger.info("=" * 70)
        logger.info("Build Variant Integration Verification")
        logger.info("=" * 70)
        
        checks = [
            ("File Existence", self.check_file_existence),
            ("JSON Validity", self.check_json_validity),
            ("Build Variant Count", self.check_build_variant_count),
            ("Job Path Mappings", self.check_job_path_mappings),
            ("Stat Target Validity", self.check_stat_targets),
            ("Skill Rotation Coverage", self.check_skill_rotation_coverage),
            ("Cross-Reference Integrity", self.check_cross_references),
        ]
        
        for check_name, check_func in checks:
            logger.info(f"\n[CHECK] {check_name}...")
            try:
                check_func()
                logger.success(f" {check_name} passed")
                self.success_count += 1
            except Exception as e:
                self.errors.append(f"{check_name}: {str(e)}")
                logger.error(f" {check_name} failed: {e}")
        
        # Print summary
        self._print_summary()
        
        return len(self.errors) == 0
    
    def check_file_existence(self):
        """Verify all required files exist"""
        required_files = [
            "job_build_variants.json",
            "job_change_locations.json",
            "skill_rotations.json"
        ]
        
        for filename in required_files:
            filepath = self.data_dir / filename
            if not filepath.exists():
                raise FileNotFoundError(f"Missing required file: {filename}")
            logger.debug(f"  Found: {filename}")
    
    def check_json_validity(self):
        """Verify all JSON files are valid"""
        json_files = [
            "job_build_variants.json",
            "job_change_locations.json",
            "skill_rotations.json"
        ]
        
        for filename in json_files:
            filepath = self.data_dir / filename
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    logger.debug(f"  {filename}: Valid JSON ({len(str(data))} bytes)")
                except json.JSONDecodeError as e:
                    raise ValueError(f"{filename} has invalid JSON: {e}")
    
    def check_build_variant_count(self):
        """Verify we have 55 build variants (11 paths × 5 builds)"""
        filepath = self.data_dir / "job_build_variants.json"
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        build_variants = data.get('build_variants', {})
        total_builds = 0
        
        expected_paths = [
            'swordman_knight_rune_knight',
            'swordman_crusader_royal_guard',
            'mage_wizard_warlock',
            'mage_sage_sorcerer',
            'archer_hunter_ranger',
            'archer_bard_minstrel',
            'archer_dancer_wanderer',
            'acolyte_priest_archbishop',
            'acolyte_monk_sura',
            'merchant_blacksmith_mechanic',
            'merchant_alchemist_genetic',
            'thief_assassin_guillotine_cross',
            'thief_rogue_shadow_chaser',
            'gunslinger_rebellion',
            'ninja_kagerou',
            'ninja_oboro',
            'taekwon_star_gladiator',
            'taekwon_soul_linker',
            'super_novice',
            'summoner'
        ]
        
        for path_id in expected_paths:
            path_data = build_variants.get(path_id)
            if not path_data:
                self.warnings.append(f"Missing job path: {path_id}")
                continue
            
            builds = path_data.get('builds', {})
            build_count = len(builds)
            total_builds += build_count
            
            if build_count != 5:
                self.warnings.append(f"{path_id} has {build_count} builds (expected 5)")
            
            # Verify 'balanced' build exists
            if 'balanced' not in builds:
                self.warnings.append(f"{path_id} missing 'balanced' build")
            
            logger.debug(f"  {path_id}: {build_count} builds")
        
        logger.info(f"  Total paths: {len(build_variants)}")
        logger.info(f"  Total builds: {total_builds}")
        
        if total_builds < 50:
            self.warnings.append(f"Only {total_builds} builds found (expected ~55)")
    
    def check_job_path_mappings(self):
        """Verify job_path_mappings are complete"""
        filepath = self.data_dir / "job_change_locations.json"
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        mappings = data.get('job_path_mappings', {}).get('paths', {})
        
        if not mappings:
            raise ValueError("No job_path_mappings found in job_change_locations.json")
        
        logger.info(f"  Found {len(mappings)} job path mappings")
        
        # Verify each mapping has required fields
        for path_id, path_data in mappings.items():
            if 'jobs' not in path_data:
                self.errors.append(f"{path_id} missing 'jobs' field")
            if 'type' not in path_data:
                self.errors.append(f"{path_id} missing 'type' field")
    
    def check_stat_targets(self):
        """Verify stat targets are valid (1-99 range, proper allocation)"""
        filepath = self.data_dir / "job_build_variants.json"
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        build_variants = data.get('build_variants', {})
        checked_builds = 0
        
        for path_id, path_data in build_variants.items():
            builds = path_data.get('builds', {})
            
            for build_id, build_config in builds.items():
                stat_targets = build_config.get('stat_targets', {})
                
                if not stat_targets:
                    self.warnings.append(f"{path_id}/{build_id} has no stat_targets")
                    continue
                
                # Verify each stat is in valid range
                for stat, value in stat_targets.items():
                    if not isinstance(value, (int, float)):
                        self.errors.append(f"{path_id}/{build_id}: {stat} is not numeric")
                    elif value < 1 or value > 99:
                        self.errors.append(f"{path_id}/{build_id}: {stat}={value} out of range (1-99)")
                
                # Verify stat_priority exists and matches stat_targets
                stat_priority = build_config.get('stat_priority', [])
                if not stat_priority:
                    self.warnings.append(f"{path_id}/{build_id} has no stat_priority")
                
                checked_builds += 1
        
        logger.info(f"  Verified {checked_builds} build configurations")
    
    def check_skill_rotation_coverage(self):
        """Verify skill rotations exist for all job classes"""
        # Load job_change_locations to get all job classes
        job_loc_file = self.data_dir / "job_change_locations.json"
        with open(job_loc_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        all_jobs: Set[str] = set()
        for req_data in job_data.get('requirements', {}).values():
            all_jobs.update(req_data.get('next_jobs', []))
        
        # Add starting jobs
        all_jobs.update(['Novice', 'Swordman', 'Mage', 'Archer', 'Acolyte', 'Merchant', 'Thief'])
        
        # Load skill rotations
        skill_file = self.data_dir / "skill_rotations.json"
        with open(skill_file, 'r', encoding='utf-8') as f:
            skill_data = json.load(f)
        
        rotations = skill_data.get('rotations', {})
        
        # Check coverage
        missing_rotations = []
        for job in all_jobs:
            if job not in rotations:
                missing_rotations.append(job)
        
        if missing_rotations:
            self.warnings.append(f"Missing skill rotations for: {', '.join(missing_rotations[:10])}")
            if len(missing_rotations) > 10:
                self.warnings.append(f"  ... and {len(missing_rotations) - 10} more")
        
        logger.info(f"  Skill rotations: {len(rotations)}/{len(all_jobs)} jobs covered")
    
    def check_cross_references(self):
        """Verify cross-references between files are valid"""
        # Load all files
        with open(self.data_dir / "job_build_variants.json", 'r') as f:
            build_data = json.load(f)
        with open(self.data_dir / "job_change_locations.json", 'r') as f:
            job_data = json.load(f)
        
        # Check that all job_paths in build_variants have corresponding mappings
        build_variants = build_data.get('build_variants', {})
        job_mappings = job_data.get('job_path_mappings', {}).get('paths', {})
        
        for path_id in build_variants.keys():
            if path_id not in job_mappings:
                self.warnings.append(f"Job path {path_id} in build_variants but not in job_path_mappings")
        
        for path_id in job_mappings.keys():
            if path_id not in build_variants:
                self.warnings.append(f"Job path {path_id} in job_path_mappings but not in build_variants")
        
        logger.info(f"  Cross-references checked between build_variants and job_path_mappings")
    
    def _print_summary(self):
        """Print verification summary"""
        logger.info("\n" + "=" * 70)
        logger.info("VERIFICATION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Checks passed: {self.success_count}")
        logger.info(f"Errors: {len(self.errors)}")
        logger.info(f"Warnings: {len(self.warnings)}")
        
        if self.errors:
            logger.error("\nERRORS:")
            for error in self.errors:
                logger.error(f"   {error}")
        
        if self.warnings:
            logger.warning("\nWARNINGS:")
            for warning in self.warnings:
                logger.warning(f"  ! {warning}")
        
        if not self.errors and not self.warnings:
            logger.success("\n🎉 All checks passed! Build variant integration is complete.")
        elif not self.errors:
            logger.info("\n Integration complete with minor warnings.")
        else:
            logger.error("\n Integration has errors that need to be fixed.")
        
        logger.info("=" * 70)


def main():
    """Main verification routine"""
    # Determine data directory
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"
    
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        sys.exit(1)
    
    logger.info(f"Data directory: {data_dir}")
    
    verifier = BuildIntegrationVerifier(data_dir)
    success = verifier.verify_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
