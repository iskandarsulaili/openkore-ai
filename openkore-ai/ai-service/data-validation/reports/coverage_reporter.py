"""
Coverage reporting for data completeness analysis.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class CoverageReporter:
    """
    Generate coverage reports comparing reference data to AI service data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the reporter.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
    
    def generate_report(
        self,
        category: str,
        reference_data: List[Dict[str, Any]],
        ai_service_data: Optional[List[Dict[str, Any]]],
        priority: str = "MEDIUM"
    ) -> Dict[str, Any]:
        """
        Generate a coverage report for a data category.
        
        Args:
            category: Data category name (e.g., 'monsters', 'items')
            reference_data: Reference database entries
            ai_service_data: AI service data entries (or None if not exists)
            priority: Priority level (CRITICAL, HIGH, MEDIUM, LOW)
            
        Returns:
            Coverage report dictionary
        """
        logger.info(f"Generating coverage report for {category}...")
        
        total_reference = len(reference_data)
        total_ai_service = len(ai_service_data) if ai_service_data else 0
        
        # Calculate coverage percentage
        coverage_percentage = (total_ai_service / total_reference * 100) if total_reference > 0 else 0
        
        # Identify missing and extra entries
        missing_entries = []
        extra_entries = []
        matched_entries = []
        
        if ai_service_data:
            reference_ids = {entry.get('id') for entry in reference_data}
            ai_service_ids = {entry.get('id') for entry in ai_service_data}
            
            missing_ids = reference_ids - ai_service_ids
            extra_ids = ai_service_ids - reference_ids
            matched_ids = reference_ids & ai_service_ids
            
            # Get entry details for missing items (limited to first 100)
            for entry in reference_data[:1000]:  # Check first 1000 for missing
                if entry.get('id') in missing_ids and len(missing_entries) < 100:
                    missing_entries.append({
                        'id': entry.get('id'),
                        'name': entry.get('name', 'UNKNOWN'),
                        'aegis_name': entry.get('aegis_name', 'UNKNOWN')
                    })
            
            # Get entry details for extra items
            for entry in ai_service_data:
                if entry.get('id') in extra_ids and len(extra_entries) < 100:
                    extra_entries.append({
                        'id': entry.get('id'),
                        'name': entry.get('name', 'UNKNOWN')
                    })
            
            matched_entries = list(matched_ids)
        else:
            # No AI service data exists
            missing_ids_count = total_reference
            for entry in reference_data[:100]:  # First 100 missing
                missing_entries.append({
                    'id': entry.get('id'),
                    'name': entry.get('name', 'UNKNOWN'),
                    'aegis_name': entry.get('aegis_name', 'UNKNOWN')
                })
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            category,
            coverage_percentage,
            total_reference,
            total_ai_service,
            priority
        )
        
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'category': category,
            'priority': priority,
            'reference_data': {
                'total_entries': total_reference,
                'source': 'rathena-AI-world'
            },
            'ai_service_data': {
                'total_entries': total_ai_service,
                'exists': ai_service_data is not None
            },
            'coverage': {
                'percentage': round(coverage_percentage, 2),
                'matched_entries': len(matched_entries),
                'missing_entries': len(missing_entries) if ai_service_data else total_reference,
                'extra_entries': len(extra_entries)
            },
            'details': {
                'missing_entries_sample': missing_entries,
                'missing_entries_truncated': len(missing_entries) >= 100,
                'extra_entries_sample': extra_entries,
                'extra_entries_truncated': len(extra_entries) >= 100
            },
            'recommendations': recommendations
        }
        
        return report
    
    def _generate_recommendations(
        self,
        category: str,
        coverage_percentage: float,
        total_reference: int,
        total_ai_service: int,
        priority: str
    ) -> List[str]:
        """
        Generate actionable recommendations based on coverage.
        
        Args:
            category: Data category
            coverage_percentage: Current coverage percentage
            total_reference: Total reference entries
            total_ai_service: Total AI service entries
            priority: Priority level
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if coverage_percentage == 0:
            recommendations.append(
                f"IMMEDIATE ACTION: {category} data is completely missing (0% coverage). "
                f"Import all {total_reference} entries from reference database."
            )
        elif coverage_percentage < 1:
            missing_count = total_reference - total_ai_service
            recommendations.append(
                f"CRITICAL: {category} has only {coverage_percentage:.2f}% coverage. "
                f"Add {missing_count} missing entries."
            )
        elif coverage_percentage < 50:
            missing_count = total_reference - total_ai_service
            recommendations.append(
                f"HIGH PRIORITY: {category} coverage is {coverage_percentage:.2f}%. "
                f"Expand database by {missing_count} entries."
            )
        elif coverage_percentage < 95:
            missing_count = total_reference - total_ai_service
            recommendations.append(
                f"MEDIUM PRIORITY: {category} coverage is {coverage_percentage:.2f}%. "
                f"Add remaining {missing_count} entries for completeness."
            )
        else:
            recommendations.append(
                f"GOOD: {category} has {coverage_percentage:.2f}% coverage. "
                "Perform periodic updates to maintain currency."
            )
        
        # Priority-specific recommendations
        if priority == "CRITICAL" and coverage_percentage < 90:
            recommendations.append(
                f"This is a CRITICAL data category. Prioritize completing {category} database immediately."
            )
        
        return recommendations
    
    def save_report(self, report: Dict[str, Any], output_path: str):
        """
        Save coverage report to file.
        
        Args:
            report: Coverage report dictionary
            output_path: Path to output file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved coverage report to {output_path}")


def generate_coverage_report(
    reference_data: List[Dict[str, Any]],
    ai_service_data: Optional[List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Quick function to generate a coverage report.
    
    Args:
        reference_data: Reference database entries
        ai_service_data: AI service data entries
        
    Returns:
        Coverage report dictionary
    """
    reporter = CoverageReporter({})
    return reporter.generate_report(
        category='generic',
        reference_data=reference_data,
        ai_service_data=ai_service_data
    )
