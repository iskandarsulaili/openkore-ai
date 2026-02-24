"""
State Manager
Thread-safe state management for trigger system with persistence support
"""

import threading
import json
import sqlite3
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger
from datetime import datetime

from .models import LayerPriority


class StateManager:
    """
    Thread-safe state management across trigger layers
    Supports both in-memory and persistent storage
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize state manager
        
        Args:
            db_path: Optional path to SQLite database for persistence
        """
        self._state: Dict[str, Any] = {}
        self._layer_states: Dict[LayerPriority, Dict[str, Any]] = {
            layer: {} for layer in LayerPriority
        }
        self._lock = threading.RLock()
        self._db_path = db_path
        
        # Statistics
        self._get_count = 0
        self._set_count = 0
        
        logger.info("StateManager initialized")
    
    def get(self, key: str, default=None) -> Any:
        """
        Thread-safe state retrieval
        
        Args:
            key: State key to retrieve
            default: Default value if key not found
            
        Returns:
            State value or default
        """
        with self._lock:
            self._get_count += 1
            value = self._state.get(key, default)
            logger.debug(f"State get: {key} = {value}")
            return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Thread-safe state update
        
        Args:
            key: State key to set
            value: Value to store
        """
        with self._lock:
            self._set_count += 1
            self._state[key] = value
            logger.debug(f"State set: {key} = {value}")
    
    def update(self, updates: Dict[str, Any]) -> None:
        """
        Update multiple state values atomically
        
        Args:
            updates: Dictionary of key-value pairs to update
        """
        with self._lock:
            self._state.update(updates)
            self._set_count += len(updates)
            logger.debug(f"State updated with {len(updates)} values")
    
    def delete(self, key: str) -> bool:
        """
        Delete a state key
        
        Args:
            key: Key to delete
            
        Returns:
            bool: True if key existed and was deleted
        """
        with self._lock:
            if key in self._state:
                del self._state[key]
                logger.debug(f"State deleted: {key}")
                return True
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all state values (returns copy for thread safety)
        
        Returns:
            Copy of current state dictionary
        """
        with self._lock:
            return self._state.copy()
    
    def clear(self) -> None:
        """Clear all state"""
        with self._lock:
            self._state.clear()
            logger.info("State cleared")
    
    # ========================================================================
    # LAYER-SPECIFIC STATE MANAGEMENT
    # ========================================================================
    
    def get_layer_state(self, layer: LayerPriority, key: str = None, default=None) -> Any:
        """
        Get layer-specific state
        
        Args:
            layer: Layer to get state from
            key: Optional specific key (if None, returns entire layer state)
            default: Default value if key not found
            
        Returns:
            Layer state value(s)
        """
        with self._lock:
            if key is None:
                return self._layer_states[layer].copy()
            return self._layer_states[layer].get(key, default)
    
    def set_layer_state(self, layer: LayerPriority, key: str, value: Any) -> None:
        """
        Set layer-specific state
        
        Args:
            layer: Layer to set state in
            key: State key
            value: Value to store
        """
        with self._lock:
            self._layer_states[layer][key] = value
            logger.debug(f"Layer state set: {layer.name}.{key} = {value}")
    
    def update_layer_state(self, layer: LayerPriority, updates: Dict[str, Any]) -> None:
        """
        Update multiple layer-specific state values
        
        Args:
            layer: Layer to update
            updates: Dictionary of updates
        """
        with self._lock:
            self._layer_states[layer].update(updates)
            logger.debug(f"Layer {layer.name} state updated with {len(updates)} values")
    
    def clear_layer_state(self, layer: LayerPriority) -> None:
        """
        Clear all state for a specific layer
        
        Args:
            layer: Layer to clear
        """
        with self._lock:
            self._layer_states[layer].clear()
            logger.info(f"Layer {layer.name} state cleared")
    
    # ========================================================================
    # PERSISTENCE
    # ========================================================================
    
    def persist_state(self, db_path: Optional[str] = None) -> bool:
        """
        Persist current state to database
        
        Args:
            db_path: Optional database path (uses init path if not provided)
            
        Returns:
            bool: True if successful
        """
        db_file = db_path or self._db_path
        if not db_file:
            logger.warning("No database path configured for persistence")
            return False
        
        try:
            with self._lock:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                # Create table if not exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trigger_state (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        layer TEXT,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Persist global state
                for key, value in self._state.items():
                    value_json = json.dumps(value)
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO trigger_state (key, value, layer, updated_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (key, value_json, 'GLOBAL', datetime.now().isoformat())
                    )
                
                # Persist layer states
                for layer, layer_state in self._layer_states.items():
                    for key, value in layer_state.items():
                        value_json = json.dumps(value)
                        layer_key = f"{layer.name}.{key}"
                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO trigger_state (key, value, layer, updated_at)
                            VALUES (?, ?, ?, ?)
                            """,
                            (layer_key, value_json, layer.name, datetime.now().isoformat())
                        )
                
                conn.commit()
                conn.close()
                
                logger.success(f"State persisted to database: {db_file}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to persist state: {e}")
            return False
    
    def restore_state(self, db_path: Optional[str] = None) -> bool:
        """
        Restore state from database
        
        Args:
            db_path: Optional database path (uses init path if not provided)
            
        Returns:
            bool: True if successful
        """
        db_file = db_path or self._db_path
        if not db_file:
            logger.warning("No database path configured for restoration")
            return False
        
        if not Path(db_file).exists():
            logger.info(f"Database file does not exist: {db_file}")
            return False
        
        try:
            with self._lock:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                # Check if table exists
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='trigger_state'"
                )
                if not cursor.fetchone():
                    logger.info("No trigger_state table found in database")
                    conn.close()
                    return False
                
                # Restore state
                cursor.execute("SELECT key, value, layer FROM trigger_state")
                rows = cursor.fetchall()
                
                restored_count = 0
                for key, value_json, layer in rows:
                    try:
                        value = json.loads(value_json)
                        
                        if layer == 'GLOBAL':
                            self._state[key] = value
                        else:
                            # Extract layer and key from composite key
                            if '.' in key:
                                _, layer_key = key.split('.', 1)
                                layer_enum = LayerPriority[layer]
                                self._layer_states[layer_enum][layer_key] = value
                        
                        restored_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to restore state key '{key}': {e}")
                        continue
                
                conn.close()
                
                logger.success(f"Restored {restored_count} state values from database")
                return True
                
        except Exception as e:
            logger.error(f"Failed to restore state: {e}")
            return False
    
    # ========================================================================
    # STATISTICS & MONITORING
    # ========================================================================
    
    def get_statistics(self) -> Dict:
        """Get state manager statistics"""
        with self._lock:
            layer_sizes = {
                layer.name: len(state)
                for layer, state in self._layer_states.items()
            }
            
            return {
                "global_state_size": len(self._state),
                "layer_state_sizes": layer_sizes,
                "total_gets": self._get_count,
                "total_sets": self._set_count,
                "has_db_persistence": self._db_path is not None
            }
    
    def get_state_snapshot(self) -> Dict:
        """
        Get complete state snapshot for debugging/analysis
        
        Returns:
            Dictionary containing all state (global + layers)
        """
        with self._lock:
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "global_state": self._state.copy(),
                "layer_states": {
                    layer.name: state.copy()
                    for layer, state in self._layer_states.items()
                },
                "statistics": self.get_statistics()
            }
            return snapshot
    
    def export_state_json(self, filepath: str) -> bool:
        """
        Export state to JSON file
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            bool: True if successful
        """
        try:
            snapshot = self.get_state_snapshot()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, indent=2, default=str)
            
            logger.success(f"State exported to: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export state: {e}")
            return False
    
    def import_state_json(self, filepath: str) -> bool:
        """
        Import state from JSON file
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            bool: True if successful
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)
            
            with self._lock:
                # Import global state
                if 'global_state' in snapshot:
                    self._state = snapshot['global_state']
                
                # Import layer states
                if 'layer_states' in snapshot:
                    for layer_name, state in snapshot['layer_states'].items():
                        try:
                            layer = LayerPriority[layer_name]
                            self._layer_states[layer] = state
                        except KeyError:
                            logger.warning(f"Unknown layer in import: {layer_name}")
            
            logger.success(f"State imported from: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import state: {e}")
            return False


# ============================================================================
# STATE CONTEXT MANAGER
# ============================================================================

class StateContext:
    """
    Context manager for atomic state operations
    Ensures all-or-nothing updates
    """
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.updates = {}
        self.layer_updates = {}
    
    def set(self, key: str, value: Any):
        """Queue a state update"""
        self.updates[key] = value
    
    def set_layer(self, layer: LayerPriority, key: str, value: Any):
        """Queue a layer state update"""
        if layer not in self.layer_updates:
            self.layer_updates[layer] = {}
        self.layer_updates[layer][key] = value
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Apply all updates atomically on successful exit"""
        if exc_type is None:
            # No exception, apply updates
            if self.updates:
                self.state_manager.update(self.updates)
            
            for layer, updates in self.layer_updates.items():
                self.state_manager.update_layer_state(layer, updates)
        
        return False  # Don't suppress exceptions
