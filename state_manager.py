"""State Manager for tracking processed Frigate events."""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


class StateManager:
    """Manages state of processed events to prevent duplicates."""
    
    def __init__(self, state_file: str = "state.json"):
        """
        Initialize the state manager.
        
        Args:
            state_file: Path to the JSON state file
        """
        self.state_file = state_file
        self.state: Dict = {
            "processed_events": {},
            "metadata": {
                "created_at": None,
                "last_updated": None
            }
        }
        self._load_state()
    
    def _load_state(self) -> None:
        """Load state from disk if it exists."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
                logger.info(f"Loaded state from {self.state_file} with {len(self.state.get('processed_events', {}))} events")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load state file: {e}. Starting with empty state.")
                self._initialize_empty_state()
        else:
            logger.info(f"State file {self.state_file} does not exist. Starting fresh.")
            self._initialize_empty_state()
    
    def _initialize_empty_state(self) -> None:
        """Initialize an empty state structure."""
        self.state = {
            "processed_events": {},
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
        }
    
    def _save_state(self) -> None:
        """Save state to disk."""
        try:
            self.state["metadata"]["last_updated"] = datetime.now().isoformat()
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug(f"State saved to {self.state_file}")
        except IOError as e:
            logger.error(f"Failed to save state: {e}")
    
    def is_processed(self, event_id: str) -> bool:
        """
        Check if an event has already been processed.
        
        Args:
            event_id: The Frigate event ID
            
        Returns:
            True if event has been processed, False otherwise
        """
        return event_id in self.state.get("processed_events", {})
    
    def mark_processed(
        self,
        event_id: str,
        camera_name: str,
        label: str,
        decision: str,
        corrected_label: Optional[str] = None,
        submission_result: Optional[str] = None
    ) -> None:
        """
        Mark an event as processed.
        
        Args:
            event_id: The Frigate event ID
            camera_name: Camera that captured the event
            label: Original label from Frigate
            decision: Decision made (valid, invalid, corrected)
            corrected_label: Corrected label if different from original
            submission_result: Result of Frigate+ submission
        """
        self.state["processed_events"][event_id] = {
            "timestamp": datetime.now().isoformat(),
            "camera_name": camera_name,
            "original_label": label,
            "decision": decision,
            "corrected_label": corrected_label,
            "submission_result": submission_result
        }
        self._save_state()
        logger.info(f"Marked event {event_id} as processed: {decision}")
    
    def get_processed_count(self) -> int:
        """Get the total number of processed events."""
        return len(self.state.get("processed_events", {}))
    
    def get_processed_event_ids(self) -> Set[str]:
        """Get a set of all processed event IDs."""
        return set(self.state.get("processed_events", {}).keys())
    
    def cleanup_old_entries(self, days: int = 30) -> int:
        """
        Remove entries older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of entries removed
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        events = self.state.get("processed_events", {})
        initial_count = len(events)
        
        events_to_remove = []
        for event_id, data in events.items():
            try:
                event_time = datetime.fromisoformat(data["timestamp"])
                if event_time < cutoff_date:
                    events_to_remove.append(event_id)
            except (KeyError, ValueError):
                # If timestamp is missing or invalid, keep the entry
                continue
        
        for event_id in events_to_remove:
            del events[event_id]
        
        removed_count = initial_count - len(events)
        if removed_count > 0:
            self._save_state()
            logger.info(f"Cleaned up {removed_count} old entries from state")
        
        return removed_count
