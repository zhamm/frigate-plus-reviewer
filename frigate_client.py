"""Frigate API Client for retrieving events and snapshots."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from io import BytesIO

import requests
from PIL import Image

logger = logging.getLogger(__name__)


class FrigateClient:
    """Client for interacting with Frigate API."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize Frigate client.
        
        Args:
            base_url: Base URL of Frigate instance (e.g., http://localhost:5000)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
    
    def test_connection(self) -> bool:
        """
        Test connection to Frigate.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/stats",
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info("Successfully connected to Frigate")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to connect to Frigate: {e}")
            return False
    
    def get_events(
        self,
        lookback_minutes: int = 10,
        cameras: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
        has_snapshot: bool = True
    ) -> List[Dict]:
        """
        Retrieve recent events from Frigate.
        
        Args:
            lookback_minutes: How far back to look for events
            cameras: Filter by specific cameras (None = all)
            labels: Filter by specific labels (None = all)
            has_snapshot: Only return events with snapshots
            
        Returns:
            List of event dictionaries
        """
        try:
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=lookback_minutes)
            
            # Build query parameters
            params = {
                'before': int(end_time.timestamp()),
                'after': int(start_time.timestamp()),
            }
            
            if cameras:
                params['cameras'] = ','.join(cameras)
            
            if labels:
                params['labels'] = ','.join(labels)
            
            if has_snapshot:
                params['has_snapshot'] = 1
            
            response = self.session.get(
                f"{self.base_url}/api/events",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            events = response.json()
            logger.info(f"Retrieved {len(events)} events from Frigate")
            return events
            
        except requests.RequestException as e:
            logger.error(f"Failed to retrieve events: {e}")
            return []
    
    def get_event_by_id(self, event_id: str) -> Optional[Dict]:
        """
        Get a specific event by ID.
        
        Args:
            event_id: The event ID
            
        Returns:
            Event dictionary or None if not found
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/events/{event_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to retrieve event {event_id}: {e}")
            return None
    
    def get_snapshot(
        self,
        event_id: str,
        clean: bool = True
    ) -> Optional[Image.Image]:
        """
        Get snapshot image for an event.
        
        Args:
            event_id: The event ID
            clean: Use clean snapshot without bounding boxes (recommended for vision models)
            
        Returns:
            PIL Image object or None if failed
        """
        try:
            # Frigate snapshot endpoint
            endpoint = f"{self.base_url}/api/events/{event_id}/snapshot.jpg"
            if clean:
                endpoint += "?clean=true"
            
            response = self.session.get(endpoint, timeout=self.timeout)
            response.raise_for_status()
            
            # Load image
            image = Image.open(BytesIO(response.content))
            logger.debug(f"Retrieved snapshot for event {event_id}: {image.size}")
            return image
            
        except requests.RequestException as e:
            logger.error(f"Failed to retrieve snapshot for event {event_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load snapshot image: {e}")
            return None
    
    def get_snapshot_bytes(
        self,
        event_id: str,
        clean: bool = True
    ) -> Optional[bytes]:
        """
        Get snapshot image bytes for an event.
        
        Args:
            event_id: The event ID
            clean: Use clean snapshot without bounding boxes
            
        Returns:
            Image bytes or None if failed
        """
        try:
            endpoint = f"{self.base_url}/api/events/{event_id}/snapshot.jpg"
            if clean:
                endpoint += "?clean=true"
            
            response = self.session.get(endpoint, timeout=self.timeout)
            response.raise_for_status()
            
            logger.debug(f"Retrieved snapshot bytes for event {event_id}: {len(response.content)} bytes")
            return response.content
            
        except requests.RequestException as e:
            logger.error(f"Failed to retrieve snapshot bytes for event {event_id}: {e}")
            return None
    
    def get_snapshot_timestamp(self, event: Dict) -> Optional[float]:
        """
        Extract the snapshot timestamp from an event.
        
        Args:
            event: Event dictionary from Frigate
            
        Returns:
            Timestamp as float or None
        """
        try:
            # Try different possible fields
            if 'snapshot' in event and 'frame_time' in event['snapshot']:
                return event['snapshot']['frame_time']
            elif 'start_time' in event:
                return event['start_time']
            else:
                logger.warning(f"Could not find snapshot timestamp in event {event.get('id', 'unknown')}")
                return None
        except Exception as e:
            logger.error(f"Error extracting snapshot timestamp: {e}")
            return None
    
    def filter_events(
        self,
        events: List[Dict],
        min_confidence: float = 0.0,
        allowed_labels: Optional[List[str]] = None,
        reject_labels: Optional[List[str]] = None,
        exclude_cameras: Optional[List[str]] = None,
        include_cameras: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Filter events based on rules.
        
        Args:
            events: List of events to filter
            min_confidence: Minimum confidence threshold
            allowed_labels: Only these labels (None = all)
            reject_labels: Exclude these labels
            exclude_cameras: Exclude these cameras
            include_cameras: Only these cameras (None = all)
            
        Returns:
            Filtered list of events
        """
        filtered = []
        
        for event in events:
            # Check snapshot exists
            if not event.get('has_snapshot'):
                logger.debug(f"Event {event['id']} has no snapshot, skipping")
                continue
            
            # Check confidence
            if event.get('data', {}).get('score', 1.0) < min_confidence:
                logger.debug(f"Event {event['id']} below confidence threshold, skipping")
                continue
            
            label = event.get('label', '')
            camera = event.get('camera', '')
            
            # Check reject labels
            if reject_labels and label in reject_labels:
                logger.debug(f"Event {event['id']} has rejected label '{label}', skipping")
                continue
            
            # Check allowed labels
            if allowed_labels and label not in allowed_labels:
                logger.debug(f"Event {event['id']} label '{label}' not in allowed list, skipping")
                continue
            
            # Check cameras
            if include_cameras and camera not in include_cameras:
                logger.debug(f"Event {event['id']} camera '{camera}' not in include list, skipping")
                continue
            
            if exclude_cameras and camera in exclude_cameras:
                logger.debug(f"Event {event['id']} camera '{camera}' in exclude list, skipping")
                continue
            
            filtered.append(event)
        
        logger.info(f"Filtered {len(events)} events down to {len(filtered)}")
        return filtered
