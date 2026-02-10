"""
Gap analysis for identifying data deficiencies and prioritizing remediation.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class GapAnalyzer:
    """
    Analyze data gaps and generate remediation recommendations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the analyzer.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
    
    def analyze(self, *coverage_reports: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze multiple coverage reports and identify critical gaps.
        
        Args:
            *coverage_reports: Variable number of coverage report dictionaries
            
        Returns:
            Gap analysis report with prioritized recommendations
        """
        logger.info(f"Analyzing gaps across {len(coverage_reports)} categories...")
        
        # Aggregate coverage data
        categories = []
        total_reference_entries = 0
        total_ai_service_entries = 0
        total_missing_entries = 0
        
        for report in coverage_reports:
            category_data = {
                'category': report.get('category', 'unknown'),
                'priority': report.get('priority', 'MEDIUM'),
                'coverage_percentage': report.get('coverage', {}).get('percentage', 0),
                'reference_count': report.get('reference_data', {}).get('total_entries', 0),
                'ai_service_count': report.get('ai_service_data', {}).get('total_entries', 0),
                'missing_count': report.get('coverage', {}).get('missing_entries', 0),
                'extra_count': report.get('coverage', {}).get('extra_entries', 0)
            }
            categories.append(category_data)
            
            total_reference_entries += category_data['reference_count']
            total_ai_service_entries += category_data['ai_service_count']
            total_missing_entries += category_data['missing_count']
        
        # Calculate overall coverage
        overall_coverage = (
            (total_ai_service_entries / total_reference_entries * 100)
            if total_reference_entries > 0
            else 0
        )
        
        # Identify critical gaps
        critical_gaps = self._identify_critical_gaps(categories)
        
        # Generate prioritized recommendations
        recommendations = self._generate_prioritized_recommendations(categories, critical_gaps)
        
        # Generate remediation plan
        remediation_plan = self._generate_remediation_plan(categories, critical_gaps)
        
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'summary': {
                'total_categories_analyzed': len(coverage_reports),
                'total_reference_entries': total_reference_entries,
                'total_ai_service_entries': total_ai_service_entries,
                'total_missing_entries': total_missing_entries,
                'overall_coverage_percentage': round(overall_coverage, 2)
            },
            'categories': categories,
            'critical_gaps': critical_gaps,
            'recommendations': recommendations,
            'remediation_plan': remediation_plan
        }
        
        logger.info(f"Gap analysis complete: {overall_coverage:.2f}% overall coverage")
        
        return report
    
    def _identify_critical_gaps(self, categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify critical data gaps requiring immediate attention.
        
        Args:
            categories: List of category data dictionaries
            
        Returns:
            List of critical gap entries
        """
        critical_gaps = []
        
        for category in categories:
            # Critical if:
            # 1. Priority is CRITICAL and coverage < 90%
            # 2. Coverage is 0%
            # 3. Priority is HIGH and coverage < 50%
            
            is_critical = False
            reason = []
            
            if category['coverage_percentage'] == 0:
                is_critical = True
                reason.append("Complete absence of data (0% coverage)")
            
            if category['priority'] == 'CRITICAL' and category['coverage_percentage'] < 90:
                is_critical = True
                reason.append(f"Critical category with insufficient coverage ({category['coverage_percentage']:.2f}%)")
            
            if category['priority'] == 'HIGH' and category['coverage_percentage'] < 50:
                is_critical = True
                reason.append(f"High priority category with low coverage ({category['coverage_percentage']:.2f}%)")
            
            if is_critical:
                critical_gaps.append({
                    'category': category['category'],
                    'priority': category['priority'],
                    'coverage_percentage': category['coverage_percentage'],
                    'missing_entries': category['missing_count'],
                    'reasons': reason
                })
        
        # Sort by priority and coverage (worst first)
        critical_gaps.sort(
            key=lambda x: (
                0 if x['priority'] == 'CRITICAL' else 1 if x['priority'] == 'HIGH' else 2,
                x['coverage_percentage']
            )
        )
        
        return critical_gaps
    
    def _generate_prioritized_recommendations(
        self,
        categories: List[Dict[str, Any]],
        critical_gaps: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate prioritized list of recommendations.
        
        Args:
            categories: List of category data
            critical_gaps: List of critical gaps
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        # Critical gaps first
        for gap in critical_gaps:
            recommendations.append({
                'priority': 'IMMEDIATE',
                'category': gap['category'],
                'action': f"Import {gap['missing_entries']} missing {gap['category']} entries",
                'reason': '; '.join(gap['reasons']),
                'estimated_effort': self._estimate_effort(gap['missing_entries'])
            })
        
        # Medium priority improvements
        for category in categories:
            if category['coverage_percentage'] >= 50 and category['coverage_percentage'] < 95:
                if not any(gap['category'] == category['category'] for gap in critical_gaps):
                    recommendations.append({
                        'priority': 'MEDIUM',
                        'category': category['category'],
                        'action': f"Expand {category['category']} coverage from {category['coverage_percentage']:.1f}% to >95%",
                        'reason': f"Add {category['missing_count']} entries for completeness",
                        'estimated_effort': self._estimate_effort(category['missing_count'])
                    })
        
        # Low priority maintenance
        for category in categories:
            if category['coverage_percentage'] >= 95:
                recommendations.append({
                    'priority': 'LOW',
                    'category': category['category'],
                    'action': f"Maintain {category['category']} database currency",
                    'reason': f"Current coverage is {category['coverage_percentage']:.1f}%",
                    'estimated_effort': 'Low - Periodic updates only'
                })
        
        return recommendations
    
    def _estimate_effort(self, entry_count: int) -> str:
        """
        Estimate effort required for data import.
        
        Args:
            entry_count: Number of entries to import
            
        Returns:
            Effort estimate string
        """
        if entry_count == 0:
            return "None"
        elif entry_count < 100:
            return "Low (< 1 hour)"
        elif entry_count < 1000:
            return "Medium (1-4 hours)"
        elif entry_count < 10000:
            return "High (1-2 days)"
        else:
            return "Very High (3+ days)"
    
    def _generate_remediation_plan(
        self,
        categories: List[Dict[str, Any]],
        critical_gaps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a phased remediation plan.
        
        Args:
            categories: List of category data
            critical_gaps: List of critical gaps
            
        Returns:
            Remediation plan dictionary
        """
        plan = {
            'phase_1_immediate': {
                'description': 'Critical gaps requiring immediate attention',
                'timeline': '1-3 days',
                'actions': []
            },
            'phase_2_high_priority': {
                'description': 'High priority improvements',
                'timeline': '1-2 weeks',
                'actions': []
            },
            'phase_3_completeness': {
                'description': 'Achieve >95% coverage across all categories',
                'timeline': '2-4 weeks',
                'actions': []
            },
            'phase_4_maintenance': {
                'description': 'Ongoing maintenance and updates',
                'timeline': 'Continuous',
                'actions': []
            }
        }
        
        # Phase 1: Critical gaps
        for gap in critical_gaps:
            plan['phase_1_immediate']['actions'].append({
                'category': gap['category'],
                'action': f"Import all {gap['missing_entries']} {gap['category']} entries from reference database",
                'priority': gap['priority']
            })
        
        # Phase 2: High priority but not critical
        for category in categories:
            if category['coverage_percentage'] < 50 and category['priority'] in ['HIGH', 'MEDIUM']:
                if not any(gap['category'] == category['category'] for gap in critical_gaps):
                    plan['phase_2_high_priority']['actions'].append({
                        'category': category['category'],
                        'action': f"Expand {category['category']} from {category['coverage_percentage']:.1f}% to 50%+",
                        'entries_needed': category['missing_count'] // 2
                    })
        
        # Phase 3: Completeness
        for category in categories:
            if 50 <= category['coverage_percentage'] < 95:
                plan['phase_3_completeness']['actions'].append({
                    'category': category['category'],
                    'action': f"Complete {category['category']} to >95% coverage",
                    'entries_needed': category['missing_count']
                })
        
        # Phase 4: Maintenance
        plan['phase_4_maintenance']['actions'] = [
            {
                'action': 'Set up automated validation pipeline',
                'frequency': 'Weekly'
            },
            {
                'action': 'Monitor reference database updates',
                'frequency': 'Weekly'
            },
            {
                'action': 'Sync new entries from reference database',
                'frequency': 'Monthly'
            },
            {
                'action': 'Review and update field mappings',
                'frequency': 'Quarterly'
            }
        ]
        
        return plan
    
    def save_report(self, report: Dict[str, Any], output_path: str):
        """
        Save gap analysis report to file.
        
        Args:
            report: Gap analysis report dictionary
            output_path: Path to output file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved gap analysis report to {output_path}")
    
    def print_summary(self, report: Dict[str, Any]):
        """
        Print a human-readable summary of the gap analysis.
        
        Args:
            report: Gap analysis report dictionary
        """
        print("\n" + "=" * 80)
        print("GAP ANALYSIS SUMMARY")
        print("=" * 80)
        
        summary = report['summary']
        print(f"\nOverall Coverage: {summary['overall_coverage_percentage']:.2f}%")
        print(f"Total Reference Entries: {summary['total_reference_entries']:,}")
        print(f"Total AI Service Entries: {summary['total_ai_service_entries']:,}")
        print(f"Total Missing Entries: {summary['total_missing_entries']:,}")
        
        # Critical gaps
        if report['critical_gaps']:
            print("\n" + "-" * 80)
            print("CRITICAL GAPS (Immediate Action Required)")
            print("-" * 80)
            for gap in report['critical_gaps']:
                print(f"\n• {gap['category'].upper()} [{gap['priority']}]")
                print(f"  Coverage: {gap['coverage_percentage']:.2f}%")
                print(f"  Missing: {gap['missing_entries']:,} entries")
                for reason in gap['reasons']:
                    print(f"  - {reason}")
        
        # Top recommendations
        print("\n" + "-" * 80)
        print("TOP RECOMMENDATIONS")
        print("-" * 80)
        for i, rec in enumerate(report['recommendations'][:5], 1):
            print(f"\n{i}. [{rec['priority']}] {rec['category']}")
            print(f"   Action: {rec['action']}")
            print(f"   Effort: {rec['estimated_effort']}")
        
        print("\n" + "=" * 80)
