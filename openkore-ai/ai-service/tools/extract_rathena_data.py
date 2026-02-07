"""
Extract game mechanics data from rathena-AI-world for OpenKore AI.

This script extracts:
1. Skill database from skill_db.yml
2. Status effects from status.hpp
3. Skill tree from skill_tree.yml

Updates OpenKore tables for client-side use.
"""

import yaml
import re
from pathlib import Path
from typing import Dict, List, Tuple


class RathenaDataExtractor:
    """Extract data from rathena-AI-world for OpenKore."""
    
    def __init__(self):
        self.base_path = Path(__file__).parent.parent.parent.parent
        self.rathena_path = self.base_path / "external-references" / "rathena-AI-world"
        self.openkore_tables_path = self.base_path / "openkore-ai" / "tables"
        
    def extract_skill_database(self) -> List[Dict]:
        """
        Extract skill database from rathena skill_db.yml.
        
        Returns:
            List of skill dictionaries
        """
        skill_db_path = self.rathena_path / "db" / "skill_db.yml"
        
        if not skill_db_path.exists():
            print(f"Warning: Skill DB not found at {skill_db_path}")
            return []
        
        print(f"Reading skill database from {skill_db_path}")
        
        try:
            with open(skill_db_path, 'r', encoding='utf-8') as f:
                skill_data = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading skill_db.yml: {e}")
            return []
        
        skills = []
        body = skill_data.get('Body', [])
        
        for skill in body:
            skill_id = skill.get('Id')
            skill_name = skill.get('Name')
            description = skill.get('Description', '')
            max_level = skill.get('MaxLevel', 10)
            
            skills.append({
                'id': skill_id,
                'name': skill_name,
                'description': description,
                'max_level': max_level,
                'type': skill.get('Type'),
                'target': skill.get('TargetType'),
                'range': skill.get('Range', [0])[0] if isinstance(skill.get('Range'), list) else skill.get('Range', 0),
                'sp_cost': skill.get('Requires', {}).get('SpCost', [0]),
                'cast_time': skill.get('CastTime', [0]),
                'cooldown': skill.get('Cooldown', [0])
            })
        
        print(f"Extracted {len(skills)} skills")
        return skills
    
    def extract_status_effects(self) -> List[Tuple[int, str]]:
        """
        Extract status effects from rathena status.hpp.
        
        Returns:
            List of (status_id, status_name) tuples
        """
        status_hpp_path = self.rathena_path / "src" / "map" / "status.hpp"
        
        if not status_hpp_path.exists():
            print(f"Warning: status.hpp not found at {status_hpp_path}")
            return []
        
        print(f"Reading status effects from {status_hpp_path}")
        
        try:
            with open(status_hpp_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading status.hpp: {e}")
            return []
        
        # Parse enum e_sc_type (sc_type)
        # Pattern: SC_NAME = value or SC_NAME,
        sc_pattern = r'SC_([A-Z_0-9]+)\s*(?:=\s*(\d+)|,)'
        matches = re.findall(sc_pattern, content)
        
        status_effects = []
        last_value = -1
        
        for name, explicit_value in matches:
            if name in ['NONE', 'MAX', 'COMMON_MIN', 'COMMON_MAX']:
                continue
            
            if explicit_value:
                value = int(explicit_value)
                last_value = value
            else:
                last_value += 1
                value = last_value
            
            status_effects.append((value, f"SC_{name}"))
        
        print(f"Extracted {len(status_effects)} status effects")
        return status_effects
    
    def write_skill_table(self, skills: List[Dict]):
        """Write SKILL_id_handle.txt for OpenKore."""
        output_path = self.openkore_tables_path / "SKILL_id_handle.txt"
        
        print(f"Writing skill table to {output_path}")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# Skill ID to Name mapping\n")
                f.write("# Extracted from rathena-AI-world/db/skill_db.yml\n")
                f.write("# Format: <skill_id> <skill_name>\n\n")
                
                for skill in sorted(skills, key=lambda x: x['id']):
                    f.write(f"{skill['id']} {skill['name']}\n")
            
            print(f"Successfully wrote {len(skills)} skills to {output_path}")
        except Exception as e:
            print(f"Error writing skill table: {e}")
    
    def write_status_table(self, status_effects: List[Tuple[int, str]]):
        """Write STATUS_id_handle.txt for OpenKore."""
        output_path = self.openkore_tables_path / "STATUS_id_handle.txt"
        
        print(f"Writing status table to {output_path}")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# Status Effect ID to Name mapping\n")
                f.write("# Extracted from rathena-AI-world/src/map/status.hpp\n")
                f.write("# Format: <status_id> <status_name>\n\n")
                
                for value, name in sorted(status_effects):
                    f.write(f"{value} {name}\n")
            
            print(f"Successfully wrote {len(status_effects)} status effects to {output_path}")
        except Exception as e:
            print(f"Error writing status table: {e}")
    
    def extract_skill_tree(self) -> Dict:
        """
        Extract skill tree from rathena skill_tree.yml.
        
        Returns:
            Dictionary of job -> skill tree
        """
        skill_tree_path = self.rathena_path / "db" / "skill_tree.yml"
        
        if not skill_tree_path.exists():
            print(f"Warning: Skill tree not found at {skill_tree_path}")
            return {}
        
        print(f"Reading skill tree from {skill_tree_path}")
        
        try:
            with open(skill_tree_path, 'r', encoding='utf-8') as f:
                tree_data = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading skill_tree.yml: {e}")
            return {}
        
        skill_trees = {}
        body = tree_data.get('Body', [])
        
        for entry in body:
            job = entry.get('Job')
            tree = []
            
            for skill_entry in entry.get('Tree', []):
                tree.append({
                    'name': skill_entry.get('Name'),
                    'max_level': skill_entry.get('MaxLevel'),
                    'min_job_level': skill_entry.get('JobLevel', 0),
                    'requires': skill_entry.get('Requires', [])
                })
            
            skill_trees[job] = tree
        
        print(f"Extracted skill trees for {len(skill_trees)} jobs")
        return skill_trees
    
    def run_extraction(self):
        """Run complete data extraction."""
        print("=" * 60)
        print("rathena Data Extraction for OpenKore AI")
        print("=" * 60)
        print()
        
        # Extract skill database
        print("Step 1: Extracting skill database...")
        skills = self.extract_skill_database()
        if skills:
            self.write_skill_table(skills)
        print()
        
        # Extract status effects
        print("Step 2: Extracting status effects...")
        status_effects = self.extract_status_effects()
        if status_effects:
            self.write_status_table(status_effects)
        print()
        
        # Extract skill tree
        print("Step 3: Extracting skill tree...")
        skill_trees = self.extract_skill_tree()
        if skill_trees:
            print(f"Skill trees extracted for: {', '.join(skill_trees.keys())}")
        print()
        
        print("=" * 60)
        print("Extraction complete!")
        print("=" * 60)
        print()
        print("Summary:")
        print(f"  - {len(skills)} skills extracted")
        print(f"  - {len(status_effects)} status effects extracted")
        print(f"  - {len(skill_trees)} job skill trees extracted")
        print()
        print("Updated OpenKore tables:")
        print(f"  - {self.openkore_tables_path / 'SKILL_id_handle.txt'}")
        print(f"  - {self.openkore_tables_path / 'STATUS_id_handle.txt'}")
        print()


if __name__ == "__main__":
    extractor = RathenaDataExtractor()
    extractor.run_extraction()
