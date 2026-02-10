"""
Main orchestrator for data validation and extraction pipeline.

This script:
1. Loads configuration
2. Extracts reference data from rAthena YAML files
3. Validates extracted data
4. Generates coverage reports
5. Performs gap analysis
6. Outputs comprehensive validation results
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init()
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    # Fallback for systems without colorama
    class Fore:
        RED = GREEN = YELLOW = BLUE = CYAN = WHITE = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from extractors import MonsterExtractor, ItemExtractor
from validators import MonsterValidator, ItemValidator
from reports import CoverageReporter, GapAnalyzer


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('output/logs/validation.log', mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ProgressTracker:
    """Track and display progress of long-running operations."""
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.last_percent = -1
    
    def update(self, current: int, total: Optional[int] = None):
        """Update progress."""
        if total is not None:
            self.total = total
        self.current = current
        
        if self.total > 0:
            percent = int((current / self.total) * 100)
            
            # Only print on percent change to reduce output
            if percent != self.last_percent:
                bar_length = 40
                filled = int(bar_length * current / self.total)
                bar = '#' * filled + '-' * (bar_length - filled)
                
                print(f"\r{self.description}: [{bar}] {percent}% ({current:,}/{self.total:,})", end='', flush=True)
                self.last_percent = percent
    
    def complete(self):
        """Mark as complete."""
        self.update(self.total, self.total)
        print()  # New line after progress bar


def print_header(text: str):
    """Print a formatted header."""
    if HAS_COLOR:
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'=' * 80}")
        print(f"{text:^80}")
        print(f"{'=' * 80}{Style.RESET_ALL}\n")
    else:
        print(f"\n{'=' * 80}")
        print(f"{text:^80}")
        print(f"{'=' * 80}\n")


def print_success(text: str):
    """Print success message."""
    if HAS_COLOR:
        print(f"{Fore.GREEN}[OK] {text}{Style.RESET_ALL}")
    else:
        print(f"[OK] {text}")


def print_error(text: str):
    """Print error message."""
    if HAS_COLOR:
        print(f"{Fore.RED}[ERROR] {text}{Style.RESET_ALL}")
    else:
        print(f"[ERROR] {text}")


def print_warning(text: str):
    """Print warning message."""
    if HAS_COLOR:
        print(f"{Fore.YELLOW}[WARNING] {text}{Style.RESET_ALL}")
    else:
        print(f"[WARNING] {text}")


def print_info(text: str):
    """Print info message."""
    if HAS_COLOR:
        print(f"{Fore.BLUE}[INFO] {text}{Style.RESET_ALL}")
    else:
        print(f"[INFO] {text}")


def load_config() -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Load configuration files.
    
    Returns:
        Tuple of (config, field_mappings)
    """
    print_header("LOADING CONFIGURATION")
    
    config_path = Path(__file__).parent / 'config.json'
    mappings_path = Path(__file__).parent / 'field_mappings.json'
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print_success(f"Loaded config from {config_path}")
        
        with open(mappings_path, 'r') as f:
            field_mappings = json.load(f)
        print_success(f"Loaded field mappings from {mappings_path}")
        
        return config, field_mappings
    
    except Exception as e:
        print_error(f"Failed to load configuration: {e}")
        raise


def load_ai_service_data(config: Dict[str, Any], source_key: str) -> Optional[list]:
    """
    Load AI service data if it exists.
    
    Args:
        config: Configuration dictionary
        source_key: Source configuration key
        
    Returns:
        List of entries or None if file doesn't exist
    """
    ai_service_path = config['sources'][source_key].get('ai_service')
    
    if not ai_service_path:
        return None
    
    full_path = Path(config['paths']['ai_service_base']) / ai_service_path
    
    if not full_path.exists():
        print_warning(f"AI service data not found: {full_path}")
        return None
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different data structures
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Try common keys
            for key in ['data', 'items', 'entries', 'monsters']:
                if key in data and isinstance(data[key], list):
                    return data[key]
            # Return as single-item list if it's a dictionary entry
            return [data]
        
        return None
    
    except Exception as e:
        print_error(f"Error loading AI service data from {full_path}: {e}")
        return None


def main():
    """Main validation pipeline."""
    start_time = datetime.now()
    
    print_header("DATA VALIDATION & EXTRACTION FRAMEWORK")
    print_info(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ensure output directories exist
    output_base = Path(__file__).parent / 'output'
    (output_base / 'extracted').mkdir(parents=True, exist_ok=True)
    (output_base / 'reports').mkdir(parents=True, exist_ok=True)
    (output_base / 'logs').mkdir(parents=True, exist_ok=True)
    
    try:
        # Step 1: Load configuration
        config, field_mappings = load_config()
        
        # Step 2: Extract monster data
        print_header("EXTRACTING MONSTER DATA")
        
        monster_extractor = MonsterExtractor(config, field_mappings)
        
        print_info("Parsing monster database (mob_db.yml)...")
        progress = ProgressTracker(0, "Extracting monsters")
        monsters = monster_extractor.extract(progress_callback=progress.update)
        progress.complete()
        
        print_success(f"Extracted {len(monsters):,} monsters")
        
        # Save extracted monsters
        monster_output = output_base / 'extracted' / 'monster_db.json'
        monster_stats = monster_extractor.extract_to_file(str(monster_output))
        print_success(f"Saved to {monster_output} ({monster_stats['file_size_bytes']:,} bytes)")
        
        # Step 3: Extract item data
        print_header("EXTRACTING ITEM DATA")
        
        item_extractor = ItemExtractor(config, field_mappings)
        
        print_info("Parsing item databases (item_db_*.yml)...")
        progress = ProgressTracker(0, "Extracting items")
        items = item_extractor.extract(progress_callback=progress.update)
        progress.complete()
        
        print_success(f"Extracted {len(items):,} items")
        
        # Save extracted items
        item_output = output_base / 'extracted' / 'item_db.json'
        item_stats = item_extractor.extract_to_file(str(item_output))
        print_success(f"Saved to {item_output} ({item_stats['file_size_bytes']:,} bytes)")
        print_info(f"Type distribution: {item_stats['type_distribution']}")
        
        # Step 4: Validate extracted data
        print_header("VALIDATING EXTRACTED DATA")
        
        # Validate monsters
        print_info("Validating monster data...")
        monster_validator = MonsterValidator(config)
        monster_validation = monster_validator.validate(monsters)
        
        print_success(
            f"Monster validation: {monster_validation['summary']['passed']:,}/{monster_validation['summary']['total_entries']:,} passed "
            f"({monster_validation['summary']['pass_rate']:.1f}%)"
        )
        
        if monster_validation['summary']['total_errors'] > 0:
            print_warning(f"Found {monster_validation['summary']['total_errors']:,} errors")
        
        # Validate items
        print_info("Validating item data...")
        item_validator = ItemValidator(config)
        item_validation = item_validator.validate(items)
        
        print_success(
            f"Item validation: {item_validation['summary']['passed']:,}/{item_validation['summary']['total_entries']:,} passed "
            f"({item_validation['summary']['pass_rate']:.1f}%)"
        )
        
        if item_validation['summary']['total_errors'] > 0:
            print_warning(f"Found {item_validation['summary']['total_errors']:,} errors")
        
        # Step 5: Generate coverage reports
        print_header("GENERATING COVERAGE REPORTS")
        
        coverage_reporter = CoverageReporter(config)
        
        # Monster coverage
        print_info("Analyzing monster coverage...")
        ai_monsters = load_ai_service_data(config, 'monsters')
        monster_coverage = coverage_reporter.generate_report(
            'monsters',
            monsters,
            ai_monsters,
            priority='CRITICAL'
        )
        
        coverage_file = output_base / 'reports' / 'monster_coverage.json'
        coverage_reporter.save_report(monster_coverage, str(coverage_file))
        print_success(f"Monster coverage: {monster_coverage['coverage']['percentage']:.2f}%")
        
        # Item coverage
        print_info("Analyzing item coverage...")
        ai_items = load_ai_service_data(config, 'items_etc')
        item_coverage = coverage_reporter.generate_report(
            'items',
            items,
            ai_items,
            priority='CRITICAL'
        )
        
        coverage_file = output_base / 'reports' / 'item_coverage.json'
        coverage_reporter.save_report(item_coverage, str(coverage_file))
        print_success(f"Item coverage: {item_coverage['coverage']['percentage']:.2f}%")
        
        # Step 6: Gap analysis
        print_header("PERFORMING GAP ANALYSIS")
        
        gap_analyzer = GapAnalyzer(config)
        gap_report = gap_analyzer.analyze(monster_coverage, item_coverage)
        
        gap_file = output_base / 'reports' / 'gap_analysis.json'
        gap_analyzer.save_report(gap_report, str(gap_file))
        print_success(f"Gap analysis complete")
        
        # Print summary
        gap_analyzer.print_summary(gap_report)
        
        # Step 7: Generate comprehensive summary
        print_header("GENERATING VALIDATION SUMMARY")
        
        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'execution_time_seconds': (datetime.now() - start_time).total_seconds(),
            'extraction': {
                'monsters': {
                    'total_extracted': len(monsters),
                    'output_file': str(monster_output),
                    'file_size_bytes': monster_stats['file_size_bytes']
                },
                'items': {
                    'total_extracted': len(items),
                    'output_file': str(item_output),
                    'file_size_bytes': item_stats['file_size_bytes'],
                    'type_distribution': item_stats['type_distribution']
                }
            },
            'validation': {
                'monsters': {
                    'total_entries': monster_validation['summary']['total_entries'],
                    'passed': monster_validation['summary']['passed'],
                    'failed': monster_validation['summary']['failed'],
                    'pass_rate': monster_validation['summary']['pass_rate'],
                    'total_errors': monster_validation['summary']['total_errors'],
                    'total_warnings': monster_validation['summary']['total_warnings']
                },
                'items': {
                    'total_entries': item_validation['summary']['total_entries'],
                    'passed': item_validation['summary']['passed'],
                    'failed': item_validation['summary']['failed'],
                    'pass_rate': item_validation['summary']['pass_rate'],
                    'total_errors': item_validation['summary']['total_errors'],
                    'total_warnings': item_validation['summary']['total_warnings']
                }
            },
            'coverage': {
                'monsters': monster_coverage['coverage'],
                'items': item_coverage['coverage']
            },
            'gap_analysis': {
                'overall_coverage_percentage': gap_report['summary']['overall_coverage_percentage'],
                'total_missing_entries': gap_report['summary']['total_missing_entries'],
                'critical_gaps_count': len(gap_report['critical_gaps'])
            }
        }
        
        summary_file = output_base / 'reports' / 'validation_summary.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print_success(f"Validation summary saved to {summary_file}")
        
        # Final summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        print_header("VALIDATION COMPLETE")
        print_info(f"Execution time: {duration.total_seconds():.1f} seconds")
        print_info(f"Overall coverage: {gap_report['summary']['overall_coverage_percentage']:.2f}%")
        print_info(f"Critical gaps: {len(gap_report['critical_gaps'])}")
        
        print("\n" + "=" * 80)
        print("SUMMARY OF GENERATED FILES:")
        print("=" * 80)
        print(f"\nExtracted Data:")
        print(f"  • {monster_output}")
        print(f"  • {item_output}")
        print(f"\nReports:")
        print(f"  • {output_base / 'reports' / 'monster_coverage.json'}")
        print(f"  • {output_base / 'reports' / 'item_coverage.json'}")
        print(f"  • {output_base / 'reports' / 'gap_analysis.json'}")
        print(f"  • {summary_file}")
        print(f"\nLogs:")
        print(f"  • {output_base / 'logs' / 'validation.log'}")
        print("\n" + "=" * 80 + "\n")
        
        return 0
    
    except Exception as e:
        logger.exception("Fatal error during validation")
        print_error(f"Validation failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
