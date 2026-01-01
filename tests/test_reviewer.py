"""Unit tests for EventReviewer decision logic."""

import unittest
from unittest.mock import Mock

from reviewer import ReviewDecision, EventReviewer
from vision_client import VisionModelResponse


class TestReviewDecision(unittest.TestCase):
    """Test cases for ReviewDecision."""
    
    def test_create_decision(self):
        """Test creating a ReviewDecision."""
        decision = ReviewDecision(
            decision=ReviewDecision.VALID,
            original_label='person',
            confidence=0.9
        )
        
        self.assertEqual(decision.decision, ReviewDecision.VALID)
        self.assertEqual(decision.original_label, 'person')
        self.assertEqual(decision.confidence, 0.9)


class TestEventReviewerDecisionLogic(unittest.TestCase):
    """Test cases for EventReviewer decision logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock clients
        self.frigate_client = Mock()
        self.vision_client = Mock()
        self.submitter = Mock()
        self.state_manager = Mock()
        
        # Create reviewer
        self.reviewer = EventReviewer(
            frigate_client=self.frigate_client,
            vision_client=self.vision_client,
            submitter=self.submitter,
            state_manager=self.state_manager,
            min_confidence=0.5,
            dry_run=False,
            submission_method='snapshot'
        )
    
    def test_decision_invalid_no_object(self):
        """Test decision when no object is present."""
        vision_response = VisionModelResponse(
            object_present=False,
            correct_label=None,
            confidence=0.95
        )
        
        decision = self.reviewer.make_decision(vision_response, 'person')
        
        self.assertEqual(decision.decision, ReviewDecision.INVALID)
    
    def test_decision_valid_same_label(self):
        """Test decision when label matches."""
        vision_response = VisionModelResponse(
            object_present=True,
            correct_label='person',
            confidence=0.9
        )
        
        decision = self.reviewer.make_decision(vision_response, 'person')
        
        self.assertEqual(decision.decision, ReviewDecision.VALID)
    
    def test_decision_corrected_different_label(self):
        """Test decision when label needs correction."""
        vision_response = VisionModelResponse(
            object_present=True,
            correct_label='cat',
            confidence=0.85
        )
        
        decision = self.reviewer.make_decision(vision_response, 'dog')
        
        self.assertEqual(decision.decision, ReviewDecision.CORRECTED)
        self.assertEqual(decision.corrected_label, 'cat')
    
    def test_decision_skipped_low_confidence(self):
        """Test decision when confidence is too low."""
        vision_response = VisionModelResponse(
            object_present=True,
            correct_label='person',
            confidence=0.3
        )
        
        decision = self.reviewer.make_decision(vision_response, 'person')
        
        self.assertEqual(decision.decision, ReviewDecision.SKIPPED)
    
    def test_decision_case_insensitive_labels(self):
        """Test that label comparison is case-insensitive."""
        vision_response = VisionModelResponse(
            object_present=True,
            correct_label='Person',
            confidence=0.9
        )
        
        decision = self.reviewer.make_decision(vision_response, 'person')
        
        self.assertEqual(decision.decision, ReviewDecision.VALID)


if __name__ == '__main__':
    unittest.main()
