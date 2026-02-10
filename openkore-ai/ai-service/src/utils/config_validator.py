"""
Configuration Validation Module

Provides robust validation for all configuration files with:
- Required field checking
- Type validation
- Value range validation
- Schema validation
- Detailed error reporting
"""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import json
import logging
from pydantic import BaseModel, Field, field_validator, ValidationError
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    """Validation severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationResult(BaseModel):
    """Result of a validation check"""
    level: ValidationLevel
    field: str
    message: str
    value: Optional[Any] = None
    expected: Optional[Any] = None


class ConfigValidator:
    """
    Comprehensive configuration validator
    
    Validates configuration files against defined schemas with
    detailed error reporting and suggestions for fixes.
    """
    
    def __init__(self):
        """Initialize validator"""
        self.validation_results: List[ValidationResult] = []
        self.error_count = 0
        self.warning_count = 0
    
    def reset(self) -> None:
        """Reset validation state"""
        self.validation_results.clear()
        self.error_count = 0
        self.warning_count = 0
    
    def add_result(
        self,
        level: ValidationLevel,
        field: str,
        message: str,
        value: Any = None,
        expected: Any = None
    ) -> None:
        """Add validation result"""
        result = ValidationResult(
            level=level,
            field=field,
            message=message,
            value=value,
            expected=expected
        )
        self.validation_results.append(result)
        
        if level == ValidationLevel.ERROR:
            self.error_count += 1
        elif level == ValidationLevel.WARNING:
            self.warning_count += 1
    
    def validate_required_field(
        self,
        config: Dict[str, Any],
        field: str,
        field_type: type = None
    ) -> bool:
        """
        Validate that a required field exists and optionally check its type
        
        Args:
            config: Configuration dictionary
            field: Field name (supports nested fields with dot notation)
            field_type: Optional expected type
            
        Returns:
            True if valid, False otherwise
        """
        # Support nested fields (e.g., "character.level")
        keys = field.split('.')
        value = config
        
        try:
            for key in keys:
                if not isinstance(value, dict):
                    self.add_result(
                        ValidationLevel.ERROR,
                        field,
                        f"Parent field is not a dictionary",
                        value=type(value).__name__
                    )
                    return False
                
                if key not in value:
                    self.add_result(
                        ValidationLevel.ERROR,
                        field,
                        f"Required field '{field}' is missing"
                    )
                    return False
                
                value = value[key]
            
            # Check type if specified
            if field_type is not None and not isinstance(value, field_type):
                self.add_result(
                    ValidationLevel.ERROR,
                    field,
                    f"Invalid type for '{field}'",
                    value=type(value).__name__,
                    expected=field_type.__name__
                )
                return False
            
            return True
            
        except Exception as e:
            self.add_result(
                ValidationLevel.ERROR,
                field,
                f"Validation error: {str(e)}"
            )
            return False
    
    def validate_type(
        self,
        config: Dict[str, Any],
        field: str,
        expected_type: Union[type, List[type]]
    ) -> bool:
        """
        Validate field type
        
        Args:
            config: Configuration dictionary
            field: Field name
            expected_type: Expected type or list of acceptable types
            
        Returns:
            True if valid, False otherwise
        """
        keys = field.split('.')
        value = config
        
        try:
            for key in keys:
                if key not in value:
                    return True  # Field doesn't exist, not a type error
                value = value[key]
            
            # Handle multiple acceptable types
            if isinstance(expected_type, list):
                if not any(isinstance(value, t) for t in expected_type):
                    self.add_result(
                        ValidationLevel.ERROR,
                        field,
                        f"Invalid type for '{field}'",
                        value=type(value).__name__,
                        expected=[t.__name__ for t in expected_type]
                    )
                    return False
            else:
                if not isinstance(value, expected_type):
                    self.add_result(
                        ValidationLevel.ERROR,
                        field,
                        f"Invalid type for '{field}'",
                        value=type(value).__name__,
                        expected=expected_type.__name__
                    )
                    return False
            
            return True
            
        except Exception as e:
            self.add_result(
                ValidationLevel.ERROR,
                field,
                f"Type validation error: {str(e)}"
            )
            return False
    
    def validate_range(
        self,
        config: Dict[str, Any],
        field: str,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None
    ) -> bool:
        """
        Validate that a numeric field is within specified range
        
        Args:
            config: Configuration dictionary
            field: Field name
            min_value: Minimum acceptable value
            max_value: Maximum acceptable value
            
        Returns:
            True if valid, False otherwise
        """
        keys = field.split('.')
        value = config
        
        try:
            for key in keys:
                if key not in value:
                    return True  # Field doesn't exist, not a range error
                value = value[key]
            
            # Check if numeric
            if not isinstance(value, (int, float)):
                return True  # Not our concern, type validation should catch this
            
            if min_value is not None and value < min_value:
                self.add_result(
                    ValidationLevel.ERROR,
                    field,
                    f"Value for '{field}' is below minimum",
                    value=value,
                    expected=f">= {min_value}"
                )
                return False
            
            if max_value is not None and value > max_value:
                self.add_result(
                    ValidationLevel.ERROR,
                    field,
                    f"Value for '{field}' exceeds maximum",
                    value=value,
                    expected=f"<= {max_value}"
                )
                return False
            
            return True
            
        except Exception as e:
            self.add_result(
                ValidationLevel.ERROR,
                field,
                f"Range validation error: {str(e)}"
            )
            return False
    
    def validate_enum(
        self,
        config: Dict[str, Any],
        field: str,
        allowed_values: List[Any]
    ) -> bool:
        """
        Validate that field value is in allowed set
        
        Args:
            config: Configuration dictionary
            field: Field name
            allowed_values: List of acceptable values
            
        Returns:
            True if valid, False otherwise
        """
        keys = field.split('.')
        value = config
        
        try:
            for key in keys:
                if key not in value:
                    return True  # Field doesn't exist, not an enum error
                value = value[key]
            
            if value not in allowed_values:
                self.add_result(
                    ValidationLevel.ERROR,
                    field,
                    f"Invalid value for '{field}'",
                    value=value,
                    expected=allowed_values
                )
                return False
            
            return True
            
        except Exception as e:
            self.add_result(
                ValidationLevel.ERROR,
                field,
                f"Enum validation error: {str(e)}"
            )
            return False
    
    def validate_file_exists(
        self,
        config: Dict[str, Any],
        field: str,
        base_path: Optional[Path] = None
    ) -> bool:
        """
        Validate that a file path exists
        
        Args:
            config: Configuration dictionary
            field: Field name containing file path
            base_path: Optional base directory for relative paths
            
        Returns:
            True if valid, False otherwise
        """
        keys = field.split('.')
        value = config
        
        try:
            for key in keys:
                if key not in value:
                    return True  # Field doesn't exist
                value = value[key]
            
            if not isinstance(value, str):
                return True  # Not a string path
            
            path = Path(value)
            if base_path and not path.is_absolute():
                path = base_path / path
            
            if not path.exists():
                self.add_result(
                    ValidationLevel.WARNING,
                    field,
                    f"File not found: '{value}'",
                    value=str(path)
                )
                return False
            
            return True
            
        except Exception as e:
            self.add_result(
                ValidationLevel.WARNING,
                field,
                f"File validation error: {str(e)}"
            )
            return False
    
    def validate_schema(
        self,
        config: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> bool:
        """
        Validate configuration against a schema definition
        
        Schema format:
        {
            "field_name": {
                "required": True/False,
                "type": type or [type1, type2],
                "min": numeric_min,
                "max": numeric_max,
                "enum": [allowed_values],
                "file_path": True/False
            }
        }
        
        Args:
            config: Configuration to validate
            schema: Schema definition
            
        Returns:
            True if all validations pass, False otherwise
        """
        all_valid = True
        
        for field, constraints in schema.items():
            # Required field check
            if constraints.get('required', False):
                if not self.validate_required_field(config, field):
                    all_valid = False
                    continue
            
            # Type check
            if 'type' in constraints:
                if not self.validate_type(config, field, constraints['type']):
                    all_valid = False
            
            # Range check
            if 'min' in constraints or 'max' in constraints:
                if not self.validate_range(
                    config,
                    field,
                    constraints.get('min'),
                    constraints.get('max')
                ):
                    all_valid = False
            
            # Enum check
            if 'enum' in constraints:
                if not self.validate_enum(config, field, constraints['enum']):
                    all_valid = False
            
            # File path check
            if constraints.get('file_path', False):
                if not self.validate_file_exists(config, field):
                    all_valid = False
        
        return all_valid
    
    def get_report(self) -> Dict[str, Any]:
        """
        Generate validation report
        
        Returns:
            Dictionary containing validation results and statistics
        """
        return {
            'valid': self.error_count == 0,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'total_issues': len(self.validation_results),
            'results': [
                {
                    'level': r.level,
                    'field': r.field,
                    'message': r.message,
                    'value': r.value,
                    'expected': r.expected
                }
                for r in self.validation_results
            ]
        }
    
    def print_report(self) -> None:
        """Print validation report to logger"""
        if self.error_count == 0 and self.warning_count == 0:
            logger.info("✓ Configuration validation passed")
            return
        
        logger.warning("=" * 80)
        logger.warning(f"Configuration Validation Report")
        logger.warning(f"Errors: {self.error_count}, Warnings: {self.warning_count}")
        logger.warning("=" * 80)
        
        for result in self.validation_results:
            if result.level == ValidationLevel.ERROR:
                logger.error(f"[ERROR] {result.field}: {result.message}")
                if result.value is not None:
                    logger.error(f"  Current: {result.value}")
                if result.expected is not None:
                    logger.error(f"  Expected: {result.expected}")
            elif result.level == ValidationLevel.WARNING:
                logger.warning(f"[WARNING] {result.field}: {result.message}")
                if result.value is not None:
                    logger.warning(f"  Current: {result.value}")
        
        logger.warning("=" * 80)


# Predefined schemas for common configurations

GAME_STATE_SCHEMA = {
    "character.level": {
        "required": True,
        "type": int,
        "min": 1,
        "max": 200
    },
    "character.hp": {
        "required": True,
        "type": int,
        "min": 0
    },
    "character.max_hp": {
        "required": True,
        "type": int,
        "min": 1
    },
    "character.sp": {
        "type": int,
        "min": 0
    },
    "character.job_class": {
        "required": True,
        "type": str
    },
    "character.position.map": {
        "required": True,
        "type": str
    }
}

SERVER_CONFIG_SCHEMA = {
    "master": {
        "required": True,
        "type": str
    },
    "username": {
        "type": str
    },
    "password": {
        "type": str
    }
}

AI_CONFIG_SCHEMA = {
    "llm_provider": {
        "type": str,
        "enum": ["deepseek", "openai", "anthropic", "ollama"]
    },
    "temperature": {
        "type": [int, float],
        "min": 0.0,
        "max": 2.0
    },
    "max_tokens": {
        "type": int,
        "min": 1,
        "max": 32000
    },
    "cache_ttl_seconds": {
        "type": int,
        "min": 0,
        "max": 3600
    }
}


# Convenience functions

def validate_game_state(game_state: Dict[str, Any]) -> bool:
    """
    Validate game state dictionary
    
    Args:
        game_state: Game state to validate
        
    Returns:
        True if valid, False otherwise
    """
    validator = ConfigValidator()
    result = validator.validate_schema(game_state, GAME_STATE_SCHEMA)
    
    if not result:
        validator.print_report()
    
    return result


def validate_json_file(file_path: Path, schema: Dict[str, Any]) -> bool:
    """
    Validate JSON configuration file
    
    Args:
        file_path: Path to JSON file
        schema: Schema to validate against
        
    Returns:
        True if valid, False otherwise
    """
    try:
        with open(file_path, 'r') as f:
            config = json.load(f)
        
        validator = ConfigValidator()
        result = validator.validate_schema(config, schema)
        
        if not result:
            logger.error(f"Validation failed for {file_path}")
            validator.print_report()
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to validate {file_path}: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Test game state validation
    test_game_state = {
        "character": {
            "level": 50,
            "hp": 1500,
            "max_hp": 2000,
            "sp": 500,
            "job_class": "Knight",
            "position": {
                "map": "prt_fild08",
                "x": 100,
                "y": 150
            }
        }
    }
    
    print("\n=== Testing Game State Validation ===")
    is_valid = validate_game_state(test_game_state)
    print(f"Validation result: {'PASS' if is_valid else 'FAIL'}")
    
    # Test invalid game state
    invalid_game_state = {
        "character": {
            "level": 250,  # Exceeds max
            "hp": -100,    # Below min
            "max_hp": 2000,
            "job_class": "Knight"
            # Missing position
        }
    }
    
    print("\n=== Testing Invalid Game State ===")
    is_valid = validate_game_state(invalid_game_state)
    print(f"Validation result: {'PASS' if is_valid else 'FAIL'}")
