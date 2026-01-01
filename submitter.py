"""Frigate+ Submission Client for submitting reviewed snapshots."""

import logging
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)


class FrigatePlusSubmitter:
    """Client for submitting to Frigate+ API."""
    
    def __init__(self, base_url: str, plus_api_key: str, timeout: int = 30):
        """
        Initialize Frigate+ submitter.
        
        Args:
            base_url: Base URL of Frigate instance
            plus_api_key: Frigate+ API key
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.plus_api_key = plus_api_key
        self.timeout = timeout
        self.session = requests.Session()
    
    def submit_snapshot(
        self,
        camera_name: str,
        frame_time: float,
        label: str,
        include_annotation: bool = True
    ) -> Dict:
        """
        Submit a snapshot to Frigate+ via the snapshot endpoint.
        
        This is the primary submission method for reviewing detections.
        
        Args:
            camera_name: Name of the camera
            frame_time: Timestamp of the frame (Unix timestamp)
            label: Label to submit (can be corrected label)
            include_annotation: Whether to include bounding box annotation
            
        Returns:
            Response dictionary with 'success' and optional 'message' or 'error'
        """
        try:
            # Build endpoint
            endpoint = f"{self.base_url}/api/{camera_name}/plus/{frame_time}"
            
            # Build payload
            payload = {
                'label': label,
                'include_annotation': include_annotation
            }
            
            # Add Frigate+ API key header
            headers = {
                'X-Frigate-Plus-Key': self.plus_api_key
            }
            
            logger.info(f"Submitting snapshot to Frigate+: camera={camera_name}, "
                       f"time={frame_time}, label={label}")
            
            response = self.session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            result = {
                'success': True,
                'status_code': response.status_code,
                'message': 'Snapshot submitted successfully'
            }
            
            # Try to parse response body
            try:
                result['response_data'] = response.json()
            except:
                result['response_data'] = response.text
            
            logger.info(f"Successfully submitted snapshot for {camera_name}")
            return result
            
        except requests.HTTPError as e:
            error_msg = f"HTTP error submitting snapshot: {e}"
            
            # Try to get detailed error message from response
            error_detail = ""
            try:
                if e.response and e.response.text:
                    error_detail = e.response.text
                    logger.error(f"{error_msg} - Response: {error_detail}")
                else:
                    logger.error(error_msg)
            except:
                logger.error(error_msg)
            
            result = {
                'success': False,
                'error': error_msg,
                'status_code': e.response.status_code if e.response else None
            }
            
            # Try to get error details
            try:
                if e.response:
                    result['error_details'] = e.response.json()
            except:
                if error_detail:
                    result['error_details'] = error_detail
            
            return result
            
        except requests.RequestException as e:
            error_msg = f"Request error submitting snapshot: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def submit_event(
        self,
        event_id: str,
        label: str,
        include_annotation: bool = True
    ) -> Dict:
        """
        Submit an event to Frigate+ via the event endpoint.
        
        Alternative method when working with existing Frigate events.
        
        Args:
            event_id: Frigate event ID
            label: Label to submit (can be corrected label)
            include_annotation: Whether to include bounding box annotation
            
        Returns:
            Response dictionary with 'success' and optional 'message' or 'error'
        """
        try:
            # Build endpoint
            endpoint = f"{self.base_url}/api/events/{event_id}/plus"
            
            # Build payload
            payload = {
                'label': label,
                'include_annotation': include_annotation
            }
            
            # Add Frigate+ API key header
            headers = {
                'X-Frigate-Plus-Key': self.plus_api_key
            }
            
            logger.info(f"Submitting event to Frigate+: event_id={event_id}, label={label}")
            
            response = self.session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            result = {
                'success': True,
                'status_code': response.status_code,
                'message': 'Event submitted successfully'
            }
            
            # Try to parse response body
            try:
                result['response_data'] = response.json()
            except:
                result['response_data'] = response.text
            
            logger.info(f"Successfully submitted event {event_id}")
            return result
            
        except requests.HTTPError as e:
            error_msg = f"HTTP error submitting event: {e}"
            
            # Try to get detailed error message from response
            error_detail = ""
            try:
                if e.response and e.response.text:
                    error_detail = e.response.text
                    logger.error(f"{error_msg} - Response: {error_detail}")
                else:
                    logger.error(error_msg)
            except:
                logger.error(error_msg)
            
            result = {
                'success': False,
                'error': error_msg,
                'status_code': e.response.status_code if e.response else None
            }
            
            # Try to get error details
            try:
                if e.response:
                    result['error_details'] = e.response.json()
            except:
                if error_detail:
                    result['error_details'] = error_detail
            
            return result
            
        except requests.RequestException as e:
            error_msg = f"Request error submitting event: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def submit_invalid(
        self,
        camera_name: str,
        frame_time: float
    ) -> Dict:
        """
        Submit a snapshot as invalid (false positive).
        
        Args:
            camera_name: Name of the camera
            frame_time: Timestamp of the frame
            
        Returns:
            Response dictionary
        """
        # Submit with a special "invalid" label or empty label
        # The actual behavior depends on Frigate+ API implementation
        return self.submit_snapshot(
            camera_name=camera_name,
            frame_time=frame_time,
            label='',  # Empty label typically indicates false positive
            include_annotation=False
        )
