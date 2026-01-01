"""Unit tests for StateManager."""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta

from state_manager import StateManager


class TestStateManager(unittest.TestCase):
    """Test cases for StateManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.state_file = self.temp_file.name
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.state_file):
            os.unlink(self.state_file)
    
    def test_initialize_empty_state(self):
        """Test initialization with no existing state file."""
        manager = StateManager(self.state_file)
        
        self.assertEqual(manager.get_processed_count(), 0)
        self.assertIsNotNone(manager.state['metadata']['created_at'])
    
    def test_mark_processed(self):
        """Test marking an event as processed."""
        manager = StateManager(self.state_file)
        
        manager.mark_processed(
            event_id='test-event-1',
            camera_name='front_door',
            label='person',
            decision='valid'
        )
        
        self.assertTrue(manager.is_processed('test-event-1'))
        self.assertEqual(manager.get_processed_count(), 1)
    
    def test_is_not_processed(self):
        """Test checking an event that hasn't been processed."""
        manager = StateManager(self.state_file)
        
        self.assertFalse(manager.is_processed('nonexistent-event'))
    
    def test_persistence(self):
        """Test that state persists across instances."""
        # Create first manager and mark an event
        manager1 = StateManager(self.state_file)
        manager1.mark_processed(
            event_id='persistent-event',
            camera_name='driveway',
            label='car',
            decision='valid'
        )
        
        # Create second manager with same file
        manager2 = StateManager(self.state_file)
        
        self.assertTrue(manager2.is_processed('persistent-event'))
        self.assertEqual(manager2.get_processed_count(), 1)
    
    def test_multiple_events(self):
        """Test processing multiple events."""
        manager = StateManager(self.state_file)
        
        events = [
            ('event-1', 'camera1', 'person', 'valid'),
            ('event-2', 'camera2', 'car', 'corrected'),
            ('event-3', 'camera1', 'dog', 'invalid')
        ]
        
        for event_id, camera, label, decision in events:
            manager.mark_processed(event_id, camera, label, decision)
        
        self.assertEqual(manager.get_processed_count(), 3)
        
        for event_id, _, _, _ in events:
            self.assertTrue(manager.is_processed(event_id))
    
    def test_get_processed_event_ids(self):
        """Test getting set of processed event IDs."""
        manager = StateManager(self.state_file)
        
        event_ids = ['event-1', 'event-2', 'event-3']
        
        for event_id in event_ids:
            manager.mark_processed(event_id, 'camera', 'label', 'valid')
        
        processed_ids = manager.get_processed_event_ids()
        
        self.assertEqual(len(processed_ids), 3)
        for event_id in event_ids:
            self.assertIn(event_id, processed_ids)
    
    def test_cleanup_old_entries(self):
        """Test cleanup of old state entries."""
        manager = StateManager(self.state_file)
        
        # Add recent event
        manager.mark_processed('recent-event', 'camera', 'person', 'valid')
        
        # Manually add old event
        old_timestamp = (datetime.now() - timedelta(days=40)).isoformat()
        manager.state['processed_events']['old-event'] = {
            'timestamp': old_timestamp,
            'camera_name': 'camera',
            'original_label': 'car',
            'decision': 'valid'
        }
        manager._save_state()
        
        # Cleanup entries older than 30 days
        removed = manager.cleanup_old_entries(days=30)
        
        self.assertEqual(removed, 1)
        self.assertTrue(manager.is_processed('recent-event'))
        self.assertFalse(manager.is_processed('old-event'))


if __name__ == '__main__':
    unittest.main()
