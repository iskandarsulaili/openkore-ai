"""
Base validator class for data validation.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    
    entry_id: Any
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.passed = False
    
    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)


class BaseValidator:
    """
    Base class for data validators.
    Provides common validation methods and report generation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the validator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.validation_rules = config.get('validation_rules', {})
    
    def validate_entry(self, entry: Dict[str, Any], rules: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate a single entry against validation rules.
        
        Args:
            entry: Entry to validate
            rules: Optional specific rules (uses default if not provided)
            
        Returns:
            ValidationResult object
        """
        if rules is None:
            rules = self.validation_rules
        
        entry_id = entry.get('id', 'UNKNOWN')
        result = ValidationResult(entry_id=entry_id, passed=True)
        
        # Check required fields
        required_fields = rules.get('required_fields', [])
        missing = self.check_required_fields(entry, required_fields)
        for field in missing:
            result.add_error(f"Missing required field: {field}")
        
        # Check numeric bounds
        numeric_bounds = rules.get('numeric_bounds', {})
        bound_errors = self.check_numeric_bounds(entry, numeric_bounds)
        for error in bound_errors:
            result.add_error(error)
        
        return result
    
    def check_required_fields(self, entry: Dict[str, Any], required: List[str]) -> List[str]:
        """
        Check if all required fields are present.
        
        Args:
            entry: Entry to check
            required: List of required field names
            
        Returns:
            List of missing field names
        """
        missing = []
        for field in required:
            if field not in entry or entry[field] is None:
                missing.append(field)
        return missing
    
    def check_id_uniqueness(self, entries: List[Dict[str, Any]]) -> List[int]:
        """
        Check for duplicate IDs in entries.
        
        Args:
            entries: List of entries to check
            
        Returns:
            List of duplicate IDs
        """
        seen_ids = set()
        duplicates = []
        
        for entry in entries:
            entry_id = entry.get('id')
            if entry_id is not None:
                if entry_id in seen_ids:
                    duplicates.append(entry_id)
                else:
                    seen_ids.add(entry_id)
        
        return duplicates
    
    def check_reference_integrity(
        self,
        entry: Dict[str, Any],
        references: Dict[str, List[Any]]
    ) -> List[str]:
        """
        Check if referenced items exist in reference lists.
        
        Args:
            entry: Entry to check
            references: Dictionary mapping field names to valid value lists
            
        Returns:
            List of integrity error messages
        """
        errors = []
        
        for field, valid_values in references.items():
            if field in entry:
                value = entry[field]
                
                # Handle both single values and lists
                values_to_check = value if isinstance(value, list) else [value]
                
                for v in values_to_check:
                    if v not in valid_values and v is not None:
                        errors.append(f"Invalid reference in {field}: {v} not found")
        
        return errors
    
    def check_numeric_bounds(self, entry: Dict[str, Any], bounds: Dict[str, List[int]]) -> List[str]:
        """
        Check if numeric fields are within valid bounds.
        
        Args:
            entry: Entry to check
            bounds: Dictionary mapping field names to [min, max] bounds
            
        Returns:
            List of bound violation error messages
        """
        errors = []
        
        for field, (min_val, max_val) in bounds.items():
            if field in entry:
                value = entry[field]
                
                # Skip if not numeric
                if not isinstance(value, (int, float)):
                    continue
                
                if value < min_val or value > max_val:
                    errors.append(
                        f"Field {field} value {value} out of bounds [{min_val}, {max_val}]"
                    )
        
        return errors
    
    def validate_all(self, entries: List[Dict[str, Any]]) -> List[ValidationResult]:
        """
        Validate all entries.
        
        Args:
            entries: List of entries to validate
            
        Returns:
            List of ValidationResult objects
        """
        results = []
        
        for entry in entries:
            result = self.validate_entry(entry)
            results.append(result)
        
        return results
    
    def generate_report(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """
        Generate a validation report from results.
        
        Args:
            results: List of ValidationResult objects
            
        Returns:
            Report dictionary
        """
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        
        # Collect all errors and warnings
        all_errors = []
        all_warnings = []
        failed_entries = []
        
        for result in results:
            if not result.passed:
                failed_entries.append({
                    'entry_id': result.entry_id,
                    'errors': result.errors,
                    'warnings': result.warnings
                })
            
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        # Error frequency analysis
        error_frequency = {}
        for error in all_errors:
            # Extract error type (first part before colon)
            error_type = error.split(':')[0] if ':' in error else error
            error_frequency[error_type] = error_frequency.get(error_type, 0) + 1
        
        report = {
            'summary': {
                'total_entries': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': round(passed / total * 100, 2) if total > 0 else 0,
                'total_errors': len(all_errors),
                'total_warnings': len(all_warnings)
            },
            'error_frequency': error_frequency,
            'failed_entries': failed_entries[:100],  # Limit to first 100
            'failed_entries_truncated': len(failed_entries) > 100,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return report
    
    def validate_with_progress(
        self,
        entries: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None,
        batch_size: int = 1000
    ) -> List[ValidationResult]:
        """
        Validate entries with progress reporting.
        
        Args:
            entries: List of entries to validate
            progress_callback: Optional callback function(current, total)
            batch_size: Number of entries to process before progress update
            
        Returns:
            List of ValidationResult objects
        """
        results = []
        total = len(entries)
        
        if progress_callback:
            progress_callback(0, total)
        
        for i, entry in enumerate(entries):
            result = self.validate_entry(entry)
            results.append(result)
            
            if progress_callback and (i + 1) % batch_size == 0:
                progress_callback(i + 1, total)
        
        if progress_callback:
            progress_callback(total, total)
        
        return results
