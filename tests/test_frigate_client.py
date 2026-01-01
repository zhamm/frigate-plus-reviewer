"""Unit tests for FrigateClient event filtering."""

import unittest
from frigate_client import FrigateClient


class TestFrigateClientFiltering(unittest.TestCase):
    """Test cases for event filtering logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = FrigateClient(base_url='http://localhost:5000')
        
        # Sample events for testing
        self.events = [
            {
                'id': 'event-1',
                'camera': 'front_door',
                'label': 'person',
                'has_snapshot': True,
                'data': {'score': 0.9}
            },
            {
                'id': 'event-2',
                'camera': 'driveway',
                'label': 'car',
                'has_snapshot': True,
                'data': {'score': 0.85}
            },
            {
                'id': 'event-3',
                'camera': 'backyard',
                'label': 'dog',
                'has_snapshot': False,
                'data': {'score': 0.7}
            },
            {
                'id': 'event-4',
                'camera': 'front_door',
                'label': 'person',
                'has_snapshot': True,
                'data': {'score': 0.3}
            },
            {
                'id': 'event-5',
                'camera': 'garage',
                'label': 'shadow',
                'has_snapshot': True,
                'data': {'score': 0.6}
            }
        ]
    
    def test_filter_no_snapshot(self):
        """Test filtering events without snapshots."""
        filtered = self.client.filter_events(self.events)
        
        # event-3 should be filtered out (no snapshot)
        event_ids = [e['id'] for e in filtered]
        self.assertNotIn('event-3', event_ids)
    
    def test_filter_min_confidence(self):
        """Test filtering by minimum confidence."""
        filtered = self.client.filter_events(
            self.events,
            min_confidence=0.5
        )
        
        # event-4 should be filtered out (confidence 0.3)
        event_ids = [e['id'] for e in filtered]
        self.assertNotIn('event-4', event_ids)
    
    def test_filter_allowed_labels(self):
        """Test filtering by allowed labels."""
        filtered = self.client.filter_events(
            self.events,
            allowed_labels=['person', 'car']
        )
        
        # Only person and car events should remain
        labels = [e['label'] for e in filtered]
        self.assertIn('person', labels)
        self.assertIn('car', labels)
        self.assertNotIn('dog', labels)
        self.assertNotIn('shadow', labels)
    
    def test_filter_reject_labels(self):
        """Test filtering by rejected labels."""
        filtered = self.client.filter_events(
            self.events,
            reject_labels=['shadow']
        )
        
        # event-5 should be filtered out (shadow)
        labels = [e['label'] for e in filtered]
        self.assertNotIn('shadow', labels)
    
    def test_filter_include_cameras(self):
        """Test filtering by included cameras."""
        filtered = self.client.filter_events(
            self.events,
            include_cameras=['front_door']
        )
        
        # Only front_door events should remain
        cameras = [e['camera'] for e in filtered]
        self.assertTrue(all(c == 'front_door' for c in cameras))
    
    def test_filter_exclude_cameras(self):
        """Test filtering by excluded cameras."""
        filtered = self.client.filter_events(
            self.events,
            exclude_cameras=['backyard']
        )
        
        # backyard events should be filtered out
        cameras = [e['camera'] for e in filtered]
        self.assertNotIn('backyard', cameras)
    
    def test_filter_combined(self):
        """Test combined filtering rules."""
        filtered = self.client.filter_events(
            self.events,
            min_confidence=0.5,
            allowed_labels=['person', 'car'],
            reject_labels=['shadow'],
            exclude_cameras=['backyard']
        )
        
        # Should only have event-1 and event-2
        event_ids = [e['id'] for e in filtered]
        self.assertEqual(len(event_ids), 2)
        self.assertIn('event-1', event_ids)
        self.assertIn('event-2', event_ids)


if __name__ == '__main__':
    unittest.main()
