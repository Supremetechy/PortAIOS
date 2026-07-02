#!/usr/bin/env python3
"""
PortAIOS AI Learning Engine
Learns user behavior patterns and makes intelligent predictions
Implements local machine learning for privacy-preserving personalization
"""

import logging
import sqlite3
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
import threading

logger = logging.getLogger("AIOS.AILearning")

# Try to import ML libraries
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("NumPy not available - using simplified learning")

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available - using rule-based learning")


@dataclass
class UserAction:
    """Represents a user action for learning"""
    timestamp: float
    action_type: str  # "app_launch", "file_open", "voice_command", "gesture", etc.
    target: str  # App name, file path, command, etc.
    context: Dict[str, Any]  # Hour, day_of_week, current_app, etc.
    input_method: str  # "voice", "gesture", "keyboard", "mouse"
    success: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserAction':
        return cls(**data)


@dataclass
class Prediction:
    """Represents a predicted action"""
    action_type: str
    target: str
    confidence: float
    reasoning: str
    timestamp: float


class BehaviorDatabase:
    """
    SQLite database for storing user behavior
    Privacy-first: all data stored locally, never sent to cloud
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # User actions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                action_type TEXT NOT NULL,
                target TEXT NOT NULL,
                context TEXT NOT NULL,
                input_method TEXT NOT NULL,
                success INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # App launch patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_patterns (
                app_name TEXT PRIMARY KEY,
                launch_count INTEGER DEFAULT 0,
                avg_hour REAL,
                common_days TEXT,
                avg_duration REAL,
                last_launched REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # File access patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_patterns (
                file_path TEXT PRIMARY KEY,
                access_count INTEGER DEFAULT 0,
                last_accessed REAL,
                common_app TEXT,
                avg_session_duration REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Command preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS command_preferences (
                command TEXT PRIMARY KEY,
                voice_count INTEGER DEFAULT 0,
                gesture_count INTEGER DEFAULT 0,
                keyboard_count INTEGER DEFAULT 0,
                preferred_method TEXT,
                avg_response_time REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Contextual patterns (time-based predictions)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS context_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hour INTEGER NOT NULL,
                day_of_week INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                target TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                last_occurred REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(hour, day_of_week, action_type, target)
            )
        ''')
        
        # Sequence patterns (Markov chains)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sequence_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_action TEXT NOT NULL,
                to_action TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                avg_time_delta REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(from_action, to_action)
            )
        ''')
        
        # Create indices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON user_actions(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_actions_type ON user_actions(action_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_context_time ON context_patterns(hour, day_of_week)')
        
        self.conn.commit()
        logger.info(f"Behavior database initialized at {self.db_path}")
    
    def record_action(self, action: UserAction):
        """Record a user action"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO user_actions (timestamp, action_type, target, context, input_method, success)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                action.timestamp,
                action.action_type,
                action.target,
                json.dumps(action.context),
                action.input_method,
                1 if action.success else 0
            ))
            self.conn.commit()
    
    def get_actions(self, limit: int = 1000, action_type: Optional[str] = None) -> List[UserAction]:
        """Get recent user actions"""
        with self.lock:
            cursor = self.conn.cursor()
            
            if action_type:
                cursor.execute('''
                    SELECT * FROM user_actions 
                    WHERE action_type = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (action_type, limit))
            else:
                cursor.execute('''
                    SELECT * FROM user_actions 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
            
            actions = []
            for row in cursor.fetchall():
                actions.append(UserAction(
                    timestamp=row['timestamp'],
                    action_type=row['action_type'],
                    target=row['target'],
                    context=json.loads(row['context']),
                    input_method=row['input_method'],
                    success=bool(row['success'])
                ))
            
            return actions
    
    def update_app_pattern(self, app_name: str, hour: int, day_of_week: int, duration: float):
        """Update app launch pattern"""
        with self.lock:
            cursor = self.conn.cursor()
            
            # Get existing pattern
            cursor.execute('SELECT * FROM app_patterns WHERE app_name = ?', (app_name,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                new_count = existing['launch_count'] + 1
                new_avg_hour = (existing['avg_hour'] * existing['launch_count'] + hour) / new_count
                
                # Update common days
                common_days = json.loads(existing['common_days']) if existing['common_days'] else []
                common_days.append(day_of_week)
                day_counter = Counter(common_days)
                
                cursor.execute('''
                    UPDATE app_patterns 
                    SET launch_count = ?,
                        avg_hour = ?,
                        common_days = ?,
                        avg_duration = ?,
                        last_launched = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE app_name = ?
                ''', (
                    new_count,
                    new_avg_hour,
                    json.dumps(list(day_counter.keys())),
                    duration,
                    time.time(),
                    app_name
                ))
            else:
                # Insert new
                cursor.execute('''
                    INSERT INTO app_patterns (app_name, launch_count, avg_hour, common_days, avg_duration, last_launched)
                    VALUES (?, 1, ?, ?, ?, ?)
                ''', (app_name, hour, json.dumps([day_of_week]), duration, time.time()))
            
            self.conn.commit()
    
    def update_context_pattern(self, hour: int, day_of_week: int, action_type: str, target: str):
        """Update contextual pattern"""
        with self.lock:
            cursor = self.conn.cursor()
            
            cursor.execute('''
                INSERT INTO context_patterns (hour, day_of_week, action_type, target, frequency, last_occurred)
                VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(hour, day_of_week, action_type, target)
                DO UPDATE SET 
                    frequency = frequency + 1,
                    last_occurred = ?,
                    updated_at = CURRENT_TIMESTAMP
            ''', (hour, day_of_week, action_type, target, time.time(), time.time()))
            
            self.conn.commit()
    
    def update_sequence_pattern(self, from_action: str, to_action: str, time_delta: float):
        """Update action sequence pattern"""
        with self.lock:
            cursor = self.conn.cursor()
            
            cursor.execute('SELECT * FROM sequence_patterns WHERE from_action = ? AND to_action = ?', 
                         (from_action, to_action))
            existing = cursor.fetchone()
            
            if existing:
                new_freq = existing['frequency'] + 1
                new_avg = (existing['avg_time_delta'] * existing['frequency'] + time_delta) / new_freq
                
                cursor.execute('''
                    UPDATE sequence_patterns
                    SET frequency = ?,
                        avg_time_delta = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE from_action = ? AND to_action = ?
                ''', (new_freq, new_avg, from_action, to_action))
            else:
                cursor.execute('''
                    INSERT INTO sequence_patterns (from_action, to_action, frequency, avg_time_delta)
                    VALUES (?, ?, 1, ?)
                ''', (from_action, to_action, time_delta))
            
            self.conn.commit()
    
    def get_context_predictions(self, hour: int, day_of_week: int, limit: int = 5) -> List[Tuple[str, str, int]]:
        """Get predictions based on time context"""
        with self.lock:
            cursor = self.conn.cursor()
            
            # Get patterns for this hour and day (exact match)
            cursor.execute('''
                SELECT action_type, target, frequency
                FROM context_patterns
                WHERE hour = ? AND day_of_week = ?
                ORDER BY frequency DESC
                LIMIT ?
            ''', (hour, day_of_week, limit))
            
            exact_matches = cursor.fetchall()
            
            # If not enough exact matches, get patterns for this hour (any day)
            if len(exact_matches) < limit:
                cursor.execute('''
                    SELECT action_type, target, SUM(frequency) as total_freq
                    FROM context_patterns
                    WHERE hour = ?
                    GROUP BY action_type, target
                    ORDER BY total_freq DESC
                    LIMIT ?
                ''', (hour, limit - len(exact_matches)))
                
                hour_matches = cursor.fetchall()
                exact_matches.extend(hour_matches)
            
            return [(row[0], row[1], row[2]) for row in exact_matches]
    
    def get_sequence_predictions(self, last_action: str, limit: int = 5) -> List[Tuple[str, int, float]]:
        """Get predictions based on action sequence"""
        with self.lock:
            cursor = self.conn.cursor()
            
            cursor.execute('''
                SELECT to_action, frequency, avg_time_delta
                FROM sequence_patterns
                WHERE from_action = ?
                ORDER BY frequency DESC
                LIMIT ?
            ''', (last_action, limit))
            
            return [(row[0], row[1], row[2]) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


class AILearningEngine:
    """
    Main AI learning and prediction engine
    Learns from user behavior and makes intelligent predictions
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path.home() / '.portaios' / 'learning'
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.db = BehaviorDatabase(self.data_dir / 'behavior.db')
        
        # Action history for sequence learning
        self.action_history = []
        self.max_history_length = 100
        
        # ML models (if scikit-learn available)
        self.app_predictor = None
        self.file_predictor = None
        
        # Learning enabled flag
        self.learning_enabled = True
        
        # Prediction cache
        self.prediction_cache = {}
        self.cache_timeout = 300  # 5 minutes
        self.last_cache_update = 0
        
        logger.info("AI Learning Engine initialized")
    
    def record_action(self, action: UserAction):
        """Record a user action and learn from it"""
        if not self.learning_enabled:
            return
        
        try:
            # Store in database
            self.db.record_action(action)
            
            # Add to history for sequence learning
            self.action_history.append(action)
            if len(self.action_history) > self.max_history_length:
                self.action_history.pop(0)
            
            # Update patterns
            self._update_patterns(action)
            
            # Learn sequences
            if len(self.action_history) >= 2:
                prev_action = self.action_history[-2]
                time_delta = action.timestamp - prev_action.timestamp
                
                from_key = f"{prev_action.action_type}:{prev_action.target}"
                to_key = f"{action.action_type}:{action.target}"
                
                self.db.update_sequence_pattern(from_key, to_key, time_delta)
            
            # Clear prediction cache
            self.prediction_cache = {}
            
        except Exception as e:
            logger.error(f"Failed to record action: {e}")
    
    def _update_patterns(self, action: UserAction):
        """Update learned patterns based on action"""
        hour = action.context.get('hour', datetime.fromtimestamp(action.timestamp).hour)
        day_of_week = action.context.get('day_of_week', datetime.fromtimestamp(action.timestamp).weekday())
        
        # Update contextual patterns
        self.db.update_context_pattern(hour, day_of_week, action.action_type, action.target)
        
        # Update app patterns
        if action.action_type == 'app_launch':
            duration = action.context.get('duration', 0)
            self.db.update_app_pattern(action.target, hour, day_of_week, duration)
    
    def predict_next_actions(self, context: Optional[Dict[str, Any]] = None, limit: int = 5) -> List[Prediction]:
        """
        Predict what the user is likely to do next
        Returns list of predictions with confidence scores
        """
        if context is None:
            context = self._get_current_context()
        
        # Check cache
        cache_key = json.dumps(context, sort_keys=True)
        if cache_key in self.prediction_cache:
            if time.time() - self.last_cache_update < self.cache_timeout:
                return self.prediction_cache[cache_key]
        
        predictions = []
        
        # Get context-based predictions
        hour = context.get('hour', datetime.now().hour)
        day_of_week = context.get('day_of_week', datetime.now().weekday())
        
        context_preds = self.db.get_context_predictions(hour, day_of_week, limit)
        
        for action_type, target, frequency in context_preds:
            confidence = min(frequency / 100.0, 0.95)  # Cap at 95%
            
            predictions.append(Prediction(
                action_type=action_type,
                target=target,
                confidence=confidence,
                reasoning=f"You usually do this at {hour:02d}:00 on {self._day_name(day_of_week)}",
                timestamp=time.time()
            ))
        
        # Get sequence-based predictions
        if self.action_history:
            last_action = self.action_history[-1]
            last_key = f"{last_action.action_type}:{last_action.target}"
            
            seq_preds = self.db.get_sequence_predictions(last_key, limit)
            
            for to_action, frequency, avg_delta in seq_preds:
                # Parse action key
                parts = to_action.split(':', 1)
                if len(parts) == 2:
                    action_type, target = parts
                    confidence = min(frequency / 50.0, 0.90)
                    
                    predictions.append(Prediction(
                        action_type=action_type,
                        target=target,
                        confidence=confidence,
                        reasoning=f"You often do this after {last_action.target}",
                        timestamp=time.time()
                    ))
        
        # Sort by confidence and deduplicate
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        
        # Remove duplicates
        seen = set()
        unique_predictions = []
        for pred in predictions:
            key = f"{pred.action_type}:{pred.target}"
            if key not in seen:
                seen.add(key)
                unique_predictions.append(pred)
        
        # Limit results
        unique_predictions = unique_predictions[:limit]
        
        # Cache results
        self.prediction_cache[cache_key] = unique_predictions
        self.last_cache_update = time.time()
        
        return unique_predictions
    
    def get_app_suggestions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get app launch suggestions based on patterns"""
        context = self._get_current_context()
        predictions = self.predict_next_actions(context, limit=limit)
        
        app_suggestions = []
        for pred in predictions:
            if pred.action_type == 'app_launch':
                app_suggestions.append({
                    'app_name': pred.target,
                    'confidence': pred.confidence,
                    'reasoning': pred.reasoning
                })
        
        return app_suggestions
    
    def get_file_suggestions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get file access suggestions"""
        context = self._get_current_context()
        predictions = self.predict_next_actions(context, limit=limit)
        
        file_suggestions = []
        for pred in predictions:
            if pred.action_type == 'file_open':
                file_suggestions.append({
                    'file_path': pred.target,
                    'confidence': pred.confidence,
                    'reasoning': pred.reasoning
                })
        
        return file_suggestions
    
    def get_preferred_input_method(self, command: str) -> str:
        """Get user's preferred input method for a command"""
        # Query command preferences from database
        # For now, return simple heuristic
        return "voice"  # Default
    
    def _get_current_context(self) -> Dict[str, Any]:
        """Get current context (time, day, etc.)"""
        now = datetime.now()
        return {
            'hour': now.hour,
            'day_of_week': now.weekday(),
            'timestamp': time.time(),
            'current_app': None  # TODO: Detect current app
        }
    
    def _day_name(self, day_of_week: int) -> str:
        """Get day name from weekday number"""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[day_of_week]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get learning statistics"""
        actions = self.db.get_actions(limit=10000)
        
        return {
            'total_actions': len(actions),
            'actions_last_24h': len([a for a in actions if time.time() - a.timestamp < 86400]),
            'actions_last_week': len([a for a in actions if time.time() - a.timestamp < 604800]),
            'most_used_apps': self._get_most_used_apps(actions),
            'most_used_input': self._get_most_used_input(actions),
            'learning_enabled': self.learning_enabled
        }
    
    def _get_most_used_apps(self, actions: List[UserAction]) -> List[Tuple[str, int]]:
        """Get most frequently used apps"""
        app_actions = [a for a in actions if a.action_type == 'app_launch']
        counter = Counter([a.target for a in app_actions])
        return counter.most_common(5)
    
    def _get_most_used_input(self, actions: List[UserAction]) -> List[Tuple[str, int]]:
        """Get most used input methods"""
        counter = Counter([a.input_method for a in actions])
        return counter.most_common()
    
    def enable_learning(self):
        """Enable learning"""
        self.learning_enabled = True
        logger.info("Learning enabled")
    
    def disable_learning(self):
        """Disable learning"""
        self.learning_enabled = False
        logger.info("Learning disabled")
    
    def clear_data(self):
        """Clear all learned data (for privacy)"""
        logger.warning("Clearing all learned data!")
        self.db.conn.execute('DELETE FROM user_actions')
        self.db.conn.execute('DELETE FROM app_patterns')
        self.db.conn.execute('DELETE FROM file_patterns')
        self.db.conn.execute('DELETE FROM command_preferences')
        self.db.conn.execute('DELETE FROM context_patterns')
        self.db.conn.execute('DELETE FROM sequence_patterns')
        self.db.conn.commit()
        
        self.action_history = []
        self.prediction_cache = {}
        
        logger.info("All learned data cleared")


# Global instance
_ai_learning_engine = None


def get_ai_learning_engine() -> AILearningEngine:
    """Get or create global AI learning engine"""
    global _ai_learning_engine
    if _ai_learning_engine is None:
        _ai_learning_engine = AILearningEngine()
    return _ai_learning_engine


# Eel integration
try:
    import eel
    
    def setup_ai_learning_eel_api():
        """Setup Eel-exposed functions for AI learning"""
        engine = get_ai_learning_engine()
        
        @eel.expose
        def get_predictions(context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
            """Get AI predictions"""
            predictions = engine.predict_next_actions(context)
            return [
                {
                    'action_type': p.action_type,
                    'target': p.target,
                    'confidence': p.confidence,
                    'reasoning': p.reasoning
                }
                for p in predictions
            ]
        
        @eel.expose
        def get_app_suggestions() -> List[Dict[str, Any]]:
            """Get app launch suggestions"""
            return engine.get_app_suggestions()
        
        @eel.expose
        def get_learning_stats() -> Dict[str, Any]:
            """Get learning statistics"""
            return engine.get_statistics()
        
        @eel.expose
        def toggle_learning(enabled: bool) -> Dict[str, Any]:
            """Enable/disable learning"""
            if enabled:
                engine.enable_learning()
            else:
                engine.disable_learning()
            return {'success': True, 'enabled': enabled}
        
        @eel.expose
        def clear_learning_data() -> Dict[str, Any]:
            """Clear all learned data"""
            engine.clear_data()
            return {'success': True, 'message': 'All learning data cleared'}
        
        logger.info("AI Learning Eel API initialized")
        return engine

except ImportError:
    pass


__all__ = [
    'AILearningEngine',
    'UserAction',
    'Prediction',
    'get_ai_learning_engine',
    'setup_ai_learning_eel_api'
]
