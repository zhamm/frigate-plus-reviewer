"""Core review logic orchestrating the entire workflow."""

import logging
from typing import Dict, List, Optional

from frigate_client import FrigateClient
from vision_client import VisionClient, VisionModelResponse
from submitter import FrigatePlusSubmitter
from state_manager import StateManager

logger = logging.getLogger(__name__)


class ReviewDecision:
    """Represents a review decision."""
    
    VALID = "valid"
    INVALID = "invalid"
    CORRECTED = "corrected"
    SKIPPED = "skipped"
    ERROR = "error"
    
    def __init__(
        self,
        decision: str,
        original_label: str,
        corrected_label: Optional[str] = None,
        confidence: float = 0.0,
        notes: Optional[str] = None
    ):
        self.decision = decision
        self.original_label = original_label
        self.corrected_label = corrected_label
        self.confidence = confidence
        self.notes = notes
    
    def __repr__(self):
        return (f"ReviewDecision(decision={self.decision}, "
                f"original={self.original_label}, "
                f"corrected={self.corrected_label}, "
                f"confidence={self.confidence})")


class EventReviewer:
    """Orchestrates the review workflow for Frigate events."""
    
    def __init__(
        self,
        frigate_client: FrigateClient,
        vision_client: VisionClient,
        submitter: FrigatePlusSubmitter,
        state_manager: StateManager,
        min_confidence: float = 0.5,
        dry_run: bool = False,
        submission_method: str = "snapshot"
    ):
        """
        Initialize the event reviewer.
        
        Args:
            frigate_client: Client for Frigate API
            vision_client: Client for vision model
            submitter: Client for Frigate+ submissions
            state_manager: State manager for tracking processed events
            min_confidence: Minimum confidence to accept a decision
            dry_run: If True, don't actually submit to Frigate+
            submission_method: "snapshot" or "event"
        """
        self.frigate_client = frigate_client
        self.vision_client = vision_client
        self.submitter = submitter
        self.state_manager = state_manager
        self.min_confidence = min_confidence
        self.dry_run = dry_run
        self.submission_method = submission_method
    
    def make_decision(
        self,
        vision_response: VisionModelResponse,
        original_label: str
    ) -> ReviewDecision:
        """
        Make a review decision based on vision model response.
        
        Args:
            vision_response: Response from vision model
            original_label: Original label from Frigate
            
        Returns:
            ReviewDecision
        """
        # Check confidence threshold
        if vision_response.confidence < self.min_confidence:
            logger.info(f"Low confidence ({vision_response.confidence}), skipping")
            return ReviewDecision(
                decision=ReviewDecision.SKIPPED,
                original_label=original_label,
                confidence=vision_response.confidence,
                notes="Confidence below threshold"
            )
        
        # No object present -> invalid
        if not vision_response.object_present:
            logger.info("No object present, marking as invalid")
            return ReviewDecision(
                decision=ReviewDecision.INVALID,
                original_label=original_label,
                confidence=vision_response.confidence,
                notes=vision_response.notes
            )
        
        # Object present with same label -> valid
        if vision_response.correct_label and \
           vision_response.correct_label.lower() == original_label.lower():
            logger.info(f"Label confirmed: {original_label}")
            return ReviewDecision(
                decision=ReviewDecision.VALID,
                original_label=original_label,
                confidence=vision_response.confidence,
                notes=vision_response.notes
            )
        
        # Object present with different label -> corrected
        if vision_response.correct_label and \
           vision_response.correct_label.lower() != original_label.lower():
            logger.info(f"Label corrected: {original_label} -> {vision_response.correct_label}")
            return ReviewDecision(
                decision=ReviewDecision.CORRECTED,
                original_label=original_label,
                corrected_label=vision_response.correct_label,
                confidence=vision_response.confidence,
                notes=vision_response.notes
            )
        
        # Object present but no label provided
        logger.warning("Object present but no label provided by vision model")
        return ReviewDecision(
            decision=ReviewDecision.VALID,
            original_label=original_label,
            confidence=vision_response.confidence,
            notes="Object present but label unclear"
        )
    
    def review_event(self, event: Dict) -> Optional[ReviewDecision]:
        """
        Review a single event.
        
        Args:
            event: Event dictionary from Frigate
            
        Returns:
            ReviewDecision or None if review failed
        """
        event_id = event.get('id')
        camera_name = event.get('camera')
        original_label = event.get('label')
        
        logger.info(f"Reviewing event {event_id}: {camera_name}/{original_label}")
        
        # Get snapshot
        snapshot = self.frigate_client.get_snapshot(event_id, clean=True)
        if not snapshot:
            logger.error(f"Failed to retrieve snapshot for event {event_id}")
            return ReviewDecision(
                decision=ReviewDecision.ERROR,
                original_label=original_label,
                notes="Failed to retrieve snapshot"
            )
        
        # Analyze with vision model
        vision_response = self.vision_client.analyze_image(snapshot, original_label)
        if not vision_response:
            logger.error(f"Failed to get vision model response for event {event_id}")
            return ReviewDecision(
                decision=ReviewDecision.ERROR,
                original_label=original_label,
                notes="Vision model failed"
            )
        
        # Make decision
        decision = self.make_decision(vision_response, original_label)
        logger.info(f"Decision for event {event_id}: {decision}")
        
        return decision
    
    def submit_decision(
        self,
        event: Dict,
        decision: ReviewDecision
    ) -> Dict:
        """
        Submit decision to Frigate+.
        
        Args:
            event: Event dictionary from Frigate
            decision: Review decision
            
        Returns:
            Submission result dictionary
        """
        event_id = event.get('id')
        camera_name = event.get('camera')
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would submit event {event_id}: {decision.decision}")
            return {
                'success': True,
                'message': 'Dry run - no actual submission',
                'dry_run': True
            }
        
        # Determine submission parameters
        if decision.decision == ReviewDecision.INVALID:
            # Submit as invalid (false positive)
            frame_time = self.frigate_client.get_snapshot_timestamp(event)
            if not frame_time:
                logger.error(f"Cannot submit invalid - no frame time for event {event_id}")
                return {'success': False, 'error': 'No frame time'}
            
            return self.submitter.submit_invalid(camera_name, frame_time)
        
        elif decision.decision in [ReviewDecision.VALID, ReviewDecision.CORRECTED]:
            # Determine label to submit
            label = decision.corrected_label if decision.corrected_label else decision.original_label
            
            # Choose submission method
            if self.submission_method == "event":
                return self.submitter.submit_event(
                    event_id=event_id,
                    label=label,
                    include_annotation=True
                )
            else:  # snapshot method (default/preferred)
                frame_time = self.frigate_client.get_snapshot_timestamp(event)
                if not frame_time:
                    logger.error(f"Cannot submit snapshot - no frame time for event {event_id}")
                    return {'success': False, 'error': 'No frame time'}
                
                return self.submitter.submit_snapshot(
                    camera_name=camera_name,
                    frame_time=frame_time,
                    label=label,
                    include_annotation=True
                )
        
        else:
            # SKIPPED or ERROR - don't submit
            logger.info(f"Not submitting event {event_id}: {decision.decision}")
            return {
                'success': False,
                'message': f'Not submitted: {decision.decision}'
            }
    
    def review_and_submit(self, event: Dict) -> bool:
        """
        Review an event and submit the decision.
        
        Args:
            event: Event dictionary from Frigate
            
        Returns:
            True if successful, False otherwise
        """
        event_id = event.get('id')
        camera_name = event.get('camera')
        original_label = event.get('label')
        
        try:
            # Review the event
            decision = self.review_event(event)
            if not decision:
                logger.error(f"Failed to review event {event_id}")
                return False
            
            # Submit the decision
            submission_result = self.submit_decision(event, decision)
            
            # Mark as processed (only if not in dry-run mode)
            if not submission_result.get('dry_run', False):
                self.state_manager.mark_processed(
                    event_id=event_id,
                    camera_name=camera_name,
                    label=original_label,
                    decision=decision.decision,
                    corrected_label=decision.corrected_label,
                    submission_result=str(submission_result.get('success', False))
                )
            else:
                logger.info(f"[DRY RUN] Not marking event {event_id} as processed")
            
            return submission_result.get('success', False)
            
        except Exception as e:
            logger.error(f"Error reviewing event {event_id}: {e}", exc_info=True)
            return False
    
    def review_batch(self, events: List[Dict]) -> Dict[str, int]:
        """
        Review a batch of events.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'total': len(events),
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
        
        for event in events:
            event_id = event.get('id')
            
            # Check if already processed
            if self.state_manager.is_processed(event_id):
                logger.debug(f"Event {event_id} already processed, skipping")
                stats['skipped'] += 1
                continue
            
            # Review and submit
            success = self.review_and_submit(event)
            
            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1
        
        logger.info(f"Batch review complete: {stats}")
        return stats
