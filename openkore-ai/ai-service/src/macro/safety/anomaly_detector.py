"""
Anomaly Detection System for Macro Behavior

Detects unusual macro execution patterns that may indicate bugs,
exploits, or system issues.
"""

from sklearn.ensemble import IsolationForest
import numpy as np
from typing import Dict, List, Optional
from loguru import logger
import pickle


class MacroAnomalyDetector:
    """Detect anomalous macro behavior patterns using Isolation Forest."""
    
    def __init__(
        self,
        contamination: float = 0.1,
        n_estimators: int = 100,
        random_state: int = 42
    ):
        """
        Initialize anomaly detector.
        
        Args:
            contamination: Expected proportion of anomalies (0.0 to 0.5)
            n_estimators: Number of trees in isolation forest
            random_state: Random seed for reproducibility
        """
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1  # Use all CPU cores
        )
        self.fitted = False
        self.training_data = []
        self.feature_names = [
            'duration',
            'success_rate',
            'actions_count',
            'trigger_frequency',
            'resource_usage',
            'error_rate',
            'hp_variance',
            'sp_variance',
            'movement_distance',
            'combat_intensity'
        ]
        
        # Anomaly tracking
        self.detected_anomalies = []
        self.false_positives = 0
        
        logger.info(
            f"Initialized anomaly detector "
            f"(contamination={contamination}, estimators={n_estimators})"
        )
    
    def fit(self, normal_executions: List[Dict]):
        """
        Train on normal macro execution patterns.
        
        Args:
            normal_executions: List of normal execution records
        """
        if len(normal_executions) < 10:
            logger.warning(
                f"Not enough training data ({len(normal_executions)} samples). "
                "Need at least 10 for reliable anomaly detection."
            )
            return
        
        logger.info(f"Training anomaly detector on {len(normal_executions)} samples...")
        
        features = self._extract_features(normal_executions)
        self.model.fit(features)
        self.fitted = True
        self.training_data = normal_executions
        
        logger.info("Anomaly detector training complete")
    
    def predict_anomaly(self, execution: Dict) -> tuple[bool, float]:
        """
        Detect if execution is anomalous.
        
        Args:
            execution: Execution record to check
            
        Returns:
            (is_anomaly, anomaly_score) tuple
            - is_anomaly: True if execution is anomalous
            - anomaly_score: Anomaly score (-1 to 1, lower = more anomalous)
        """
        if not self.fitted:
            logger.warning("Anomaly detector not trained yet, skipping detection")
            return False, 0.0
        
        features = self._extract_features([execution])
        
        # Predict: -1 for anomaly, 1 for normal
        prediction = self.model.predict(features)[0]
        
        # Get anomaly score (lower = more anomalous)
        anomaly_score = self.model.score_samples(features)[0]
        
        is_anomaly = (prediction == -1)
        
        if is_anomaly:
            self.detected_anomalies.append({
                'execution': execution,
                'score': anomaly_score,
                'features': features[0].tolist()
            })
            logger.warning(
                f"Anomaly detected: {execution.get('macro_name', 'unknown')} "
                f"(score={anomaly_score:.3f})"
            )
        
        return is_anomaly, anomaly_score
    
    def _extract_features(self, executions: List[Dict]) -> np.ndarray:
        """
        Extract numerical features from execution data.
        
        Args:
            executions: List of execution records
            
        Returns:
            Feature matrix (n_samples, n_features)
        """
        features = []
        
        for exec in executions:
            feature_vector = [
                # Duration (seconds)
                exec.get('duration', 0.0),
                
                # Success rate (0-1)
                exec.get('success_rate', 1.0),
                
                # Number of actions executed
                exec.get('actions_count', 0),
                
                # Trigger frequency (per minute)
                exec.get('trigger_frequency', 0.0),
                
                # Resource usage (0-1, normalized)
                exec.get('resource_usage', 0.0),
                
                # Error rate (0-1)
                exec.get('error_rate', 0.0),
                
                # HP variance during execution
                exec.get('hp_variance', 0.0),
                
                # SP variance during execution
                exec.get('sp_variance', 0.0),
                
                # Movement distance (cells)
                exec.get('movement_distance', 0.0),
                
                # Combat intensity (0-1)
                exec.get('combat_intensity', 0.0)
            ]
            
            features.append(feature_vector)
        
        return np.array(features, dtype=np.float32)
    
    def analyze_anomaly(self, execution: Dict) -> Dict:
        """
        Provide detailed analysis of why execution is anomalous.
        
        Args:
            execution: Execution record
            
        Returns:
            Analysis report with anomaly reasons
        """
        if not self.fitted:
            return {'error': 'Detector not trained'}
        
        features = self._extract_features([execution])[0]
        
        # Compare to training data statistics
        training_features = self._extract_features(self.training_data)
        
        anomaly_reasons = []
        
        for i, feature_name in enumerate(self.feature_names):
            value = features[i]
            mean = np.mean(training_features[:, i])
            std = np.std(training_features[:, i])
            
            # Check if value is outside 3 sigma
            if abs(value - mean) > 3 * std:
                anomaly_reasons.append({
                    'feature': feature_name,
                    'value': float(value),
                    'expected_mean': float(mean),
                    'expected_std': float(std),
                    'deviation': float(abs(value - mean) / std) if std > 0 else 0
                })
        
        return {
            'macro_name': execution.get('macro_name', 'unknown'),
            'is_anomaly': self.predict_anomaly(execution)[0],
            'anomaly_score': self.predict_anomaly(execution)[1],
            'reasons': anomaly_reasons,
            'severity': self._calculate_severity(anomaly_reasons)
        }
    
    def _calculate_severity(self, reasons: List[Dict]) -> str:
        """Calculate anomaly severity level."""
        if not reasons:
            return 'none'
        
        max_deviation = max(r['deviation'] for r in reasons)
        
        if max_deviation > 5:
            return 'critical'
        elif max_deviation > 4:
            return 'high'
        elif max_deviation > 3:
            return 'medium'
        else:
            return 'low'
    
    def mark_false_positive(self, execution: Dict):
        """
        Mark detection as false positive and retrain.
        
        Args:
            execution: Execution that was incorrectly flagged
        """
        self.false_positives += 1
        
        # Add to training data
        self.training_data.append(execution)
        
        # Retrain with expanded data
        if len(self.training_data) >= 10:
            logger.info("Retraining detector with false positive feedback...")
            self.fit(self.training_data)
    
    def get_statistics(self) -> Dict:
        """Get anomaly detection statistics."""
        return {
            'fitted': self.fitted,
            'training_samples': len(self.training_data),
            'anomalies_detected': len(self.detected_anomalies),
            'false_positives': self.false_positives,
            'contamination': self.model.contamination,
            'feature_names': self.feature_names
        }
    
    def save_model(self, path: str):
        """Save detector model to disk."""
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'fitted': self.fitted,
                'training_data': self.training_data,
                'feature_names': self.feature_names,
                'detected_anomalies': self.detected_anomalies,
                'false_positives': self.false_positives
            }, f)
        logger.info(f"Saved anomaly detector to {path}")
    
    def load_model(self, path: str):
        """Load detector model from disk."""
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.fitted = data['fitted']
            self.training_data = data['training_data']
            self.feature_names = data['feature_names']
            self.detected_anomalies = data.get('detected_anomalies', [])
            self.false_positives = data.get('false_positives', 0)
        logger.info(f"Loaded anomaly detector from {path}")
    
    def get_recent_anomalies(self, limit: int = 10) -> List[Dict]:
        """
        Get most recent detected anomalies.
        
        Args:
            limit: Maximum number of anomalies to return
            
        Returns:
            List of recent anomaly records
        """
        return self.detected_anomalies[-limit:]


class AnomalyAlertSystem:
    """Alert system for anomaly detection."""
    
    def __init__(self, severity_thresholds: Optional[Dict[str, int]] = None):
        """
        Initialize alert system.
        
        Args:
            severity_thresholds: Alert thresholds by severity level
        """
        self.thresholds = severity_thresholds or {
            'critical': 1,  # Alert immediately
            'high': 3,      # Alert after 3 occurrences
            'medium': 10,   # Alert after 10 occurrences
            'low': 50       # Alert after 50 occurrences
        }
        
        self.counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }
        
        self.alerts_triggered = []
        
        logger.info(f"Initialized anomaly alert system with thresholds: {self.thresholds}")
    
    def process_anomaly(self, analysis: Dict) -> Optional[Dict]:
        """
        Process anomaly and trigger alert if threshold reached.
        
        Args:
            analysis: Anomaly analysis from detector
            
        Returns:
            Alert dict if triggered, None otherwise
        """
        severity = analysis.get('severity', 'low')
        
        if severity not in self.counts:
            severity = 'low'
        
        self.counts[severity] += 1
        
        # Check if threshold reached
        if self.counts[severity] >= self.thresholds[severity]:
            alert = {
                'severity': severity,
                'count': self.counts[severity],
                'analysis': analysis,
                'message': self._generate_alert_message(severity, analysis)
            }
            
            self.alerts_triggered.append(alert)
            
            # Reset counter after alert
            self.counts[severity] = 0
            
            logger.error(f"ANOMALY ALERT: {alert['message']}")
            
            return alert
        
        return None
    
    def _generate_alert_message(self, severity: str, analysis: Dict) -> str:
        """Generate human-readable alert message."""
        macro_name = analysis.get('macro_name', 'unknown')
        reasons = analysis.get('reasons', [])
        
        if not reasons:
            return f"{severity.upper()}: Anomaly in {macro_name}"
        
        # Get top 3 reasons
        top_reasons = sorted(
            reasons,
            key=lambda r: r['deviation'],
            reverse=True
        )[:3]
        
        reason_text = ', '.join([
            f"{r['feature']} ({r['deviation']:.1f}σ)"
            for r in top_reasons
        ])
        
        return (
            f"{severity.upper()} anomaly in {macro_name}: "
            f"{reason_text}"
        )
    
    def get_alert_history(self) -> List[Dict]:
        """Get history of triggered alerts."""
        return self.alerts_triggered
    
    def reset_counts(self):
        """Reset anomaly counts."""
        for key in self.counts:
            self.counts[key] = 0
        logger.info("Reset anomaly counts")
