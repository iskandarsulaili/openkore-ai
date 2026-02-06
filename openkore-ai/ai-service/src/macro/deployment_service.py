"""
Macro Deployment Service
Handles macro injection into OpenKore via REST API
"""

import httpx
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

logger = logging.getLogger(__name__)


class MacroDefinition(BaseModel):
    """Structured macro definition"""
    name: str = Field(..., description="Unique macro identifier")
    definition: str = Field(..., description="Complete OpenKore macro syntax")
    triggers: List[str] = Field(default_factory=list, description="Trigger conditions")
    actions: List[str] = Field(default_factory=list, description="Action list")
    priority: int = Field(default=50, ge=1, le=100, description="Macro priority")
    timeout: Optional[int] = Field(default=None, description="Timeout in seconds")
    exclusive: bool = Field(default=True, description="Exclusive execution flag")


class MacroDeploymentService:
    """Service for deploying macros to OpenKore via hot-reload plugin"""
    
    def __init__(self, openkore_url: str = "http://127.0.0.1:8765"):
        """
        Initialize deployment service
        
        Args:
            openkore_url: Base URL for MacroHotReload plugin
        """
        self.openkore_url = openkore_url
        self.client = httpx.AsyncClient(timeout=5.0)
        self._injection_history: List[Dict] = []
        
        logger.info(f"MacroDeploymentService initialized with URL: {openkore_url}")
    
    async def inject_macro(self, macro: MacroDefinition) -> Dict:
        """
        Inject macro into OpenKore via REST API
        
        Args:
            macro: Macro definition to inject
            
        Returns:
            Injection result with status and latency
            
        Raises:
            httpx.HTTPError: If injection fails
        """
        try:
            start_time = datetime.now()
            
            payload = {
                "name": macro.name,
                "definition": macro.definition,
                "triggers": macro.triggers,
                "priority": macro.priority
            }
            
            logger.debug(f"Injecting macro '{macro.name}' with priority {macro.priority}")
            
            response = await self.client.post(
                f"{self.openkore_url}/macro/inject",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            result['client_latency_ms'] = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Track injection history
            self._injection_history.append({
                'macro_name': macro.name,
                'timestamp': start_time.isoformat(),
                'success': True,
                'latency_ms': result['injection_time_ms']
            })
            
            logger.success(
                f"✓ Macro '{macro.name}' injected successfully "
                f"(latency: {result['injection_time_ms']}ms)"
            )
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"✗ Macro injection failed: {e.response.status_code} - {e.response.text}")
            self._injection_history.append({
                'macro_name': macro.name,
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'error': str(e)
            })
            raise
        except Exception as e:
            logger.error(f"✗ Macro injection error: {e}")
            raise
    
    async def inject_batch(self, macros: List[MacroDefinition]) -> Dict:
        """
        Inject multiple macros in sequence
        
        Args:
            macros: List of macro definitions
            
        Returns:
            Batch injection results
        """
        results = {
            'successful': [],
            'failed': [],
            'total_time_ms': 0
        }
        
        start_time = datetime.now()
        
        for macro in macros:
            try:
                result = await self.inject_macro(macro)
                results['successful'].append(macro.name)
            except Exception as e:
                results['failed'].append({
                    'macro_name': macro.name,
                    'error': str(e)
                })
        
        results['total_time_ms'] = int((datetime.now() - start_time).total_seconds() * 1000)
        
        logger.info(
            f"Batch injection complete: "
            f"{len(results['successful'])} succeeded, "
            f"{len(results['failed'])} failed "
            f"({results['total_time_ms']}ms total)"
        )
        
        return results
    
    async def list_macros(self) -> List[Dict]:
        """
        Get all active macros from OpenKore
        
        Returns:
            List of active macro information
        """
        try:
            response = await self.client.get(f"{self.openkore_url}/macro/list")
            response.raise_for_status()
            
            data = response.json()
            macros = data.get('macros', [])
            
            logger.debug(f"Retrieved {len(macros)} active macros")
            return macros
            
        except Exception as e:
            logger.error(f"Failed to list macros: {e}")
            raise
    
    async def delete_macro(self, name: str) -> Dict:
        """
        Remove macro by name
        
        Args:
            name: Macro name to delete
            
        Returns:
            Deletion result
        """
        try:
            response = await self.client.delete(
                f"{self.openkore_url}/macro/delete",
                json={"name": name}
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✓ Macro '{name}' deleted successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"✗ Failed to delete macro '{name}': {e}")
            raise
    
    async def get_statistics(self) -> Dict:
        """
        Get macro execution statistics
        
        Returns:
            Statistics for all macros
        """
        try:
            response = await self.client.get(f"{self.openkore_url}/macro/stats")
            response.raise_for_status()
            
            data = response.json()
            stats = data.get('statistics', {})
            
            logger.debug(f"Retrieved statistics for {len(stats)} macros")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            raise
    
    async def health_check(self) -> bool:
        """
        Check if MacroHotReload plugin is accessible
        
        Returns:
            True if plugin is responding, False otherwise
        """
        try:
            response = await self.client.get(
                f"{self.openkore_url}/macro/list",
                timeout=2.0
            )
            return response.status_code == 200
        except:
            return False
    
    def get_injection_history(self) -> List[Dict]:
        """Get history of macro injections"""
        return self._injection_history.copy()
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class MacroValidator:
    """Validates macro definitions before injection"""
    
    @staticmethod
    def validate_syntax(definition: str) -> Dict[str, any]:
        """
        Validate macro syntax
        
        Args:
            definition: Macro definition text
            
        Returns:
            Dictionary with 'valid' (bool) and 'errors' (list) keys
        """
        errors = []
        
        # Check balanced braces
        open_count = definition.count('{')
        close_count = definition.count('}')
        if open_count != close_count:
            errors.append(f"Unbalanced braces: {open_count} open, {close_count} close")
        
        # Check for automacro block
        if 'automacro' not in definition:
            errors.append("Missing 'automacro' block")
        
        # Check for macro block
        if 'macro' not in definition:
            errors.append("Missing 'macro' block")
        
        # Check for call statement
        if 'call' not in definition:
            errors.append("Missing 'call' statement in automacro")
        
        # Check for empty blocks
        if definition.strip() == '':
            errors.append("Empty macro definition")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def validate_macro_object(macro: MacroDefinition) -> Dict[str, any]:
        """
        Validate macro object
        
        Args:
            macro: Macro definition object
            
        Returns:
            Dictionary with 'valid' (bool) and 'errors' (list) keys
        """
        errors = []
        
        # Validate name
        if not macro.name or len(macro.name) < 3:
            errors.append("Macro name must be at least 3 characters")
        
        if not macro.name.replace('_', '').isalnum():
            errors.append("Macro name must be alphanumeric (underscores allowed)")
        
        # Validate priority
        if macro.priority < 1 or macro.priority > 100:
            errors.append("Priority must be between 1 and 100")
        
        # Validate definition
        syntax_result = MacroValidator.validate_syntax(macro.definition)
        if not syntax_result['valid']:
            errors.extend(syntax_result['errors'])
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }


# Convenience function for quick macro injection
async def quick_inject(
    name: str,
    definition: str,
    priority: int = 50,
    openkore_url: str = "http://127.0.0.1:8765"
) -> Dict:
    """
    Quick macro injection helper
    
    Args:
        name: Macro name
        definition: Macro definition
        priority: Macro priority (1-100)
        openkore_url: OpenKore plugin URL
        
    Returns:
        Injection result
    """
    service = MacroDeploymentService(openkore_url)
    try:
        macro = MacroDefinition(
            name=name,
            definition=definition,
            priority=priority
        )
        result = await service.inject_macro(macro)
        return result
    finally:
        await service.close()
