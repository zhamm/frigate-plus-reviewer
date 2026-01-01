"""Unit tests for VisionClient."""

import unittest
from unittest.mock import Mock, patch
from PIL import Image

from vision_client import (
    VisionClient,
    VisionModelResponse,
    GeminiVisionClient,
    OpenAICompatibleVisionClient,
    create_vision_client
)


class TestVisionModelResponse(unittest.TestCase):
    """Test cases for VisionModelResponse."""
    
    def test_create_response(self):
        """Test creating a VisionModelResponse."""
        response = VisionModelResponse(
            object_present=True,
            correct_label='person',
            confidence=0.95,
            notes='Clear image'
        )
        
        self.assertTrue(response.object_present)
        self.assertEqual(response.correct_label, 'person')
        self.assertEqual(response.confidence, 0.95)
        self.assertEqual(response.notes, 'Clear image')


class TestVisionClientBase(unittest.TestCase):
    """Test cases for base VisionClient."""
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        client = VisionClient()
        
        response_text = '''
        {
            "object_present": true,
            "correct_label": "car",
            "confidence": 0.85,
            "notes": "Blue sedan"
        }
        '''
        
        response = client._parse_response(response_text)
        
        self.assertIsNotNone(response)
        self.assertTrue(response.object_present)
        self.assertEqual(response.correct_label, 'car')
        self.assertAlmostEqual(response.confidence, 0.85)
        self.assertEqual(response.notes, 'Blue sedan')
    
    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        client = VisionClient()
        
        response_text = '''```json
        {
            "object_present": false,
            "correct_label": null,
            "confidence": 0.9
        }
        ```'''
        
        response = client._parse_response(response_text)
        
        self.assertIsNotNone(response)
        self.assertFalse(response.object_present)
        self.assertIsNone(response.correct_label)
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON returns None."""
        client = VisionClient()
        
        response_text = "This is not JSON"
        
        response = client._parse_response(response_text)
        
        self.assertIsNone(response)
    
    def test_confidence_clamping(self):
        """Test that confidence values are clamped to [0, 1]."""
        client = VisionClient()
        
        # Test over 1.0
        response_text = '{"object_present": true, "correct_label": "test", "confidence": 1.5}'
        response = client._parse_response(response_text)
        self.assertEqual(response.confidence, 1.0)
        
        # Test under 0.0
        response_text = '{"object_present": true, "correct_label": "test", "confidence": -0.5}'
        response = client._parse_response(response_text)
        self.assertEqual(response.confidence, 0.0)


class TestCreateVisionClient(unittest.TestCase):
    """Test cases for vision client factory function."""
    
    @patch('vision_client.genai')
    def test_create_gemini_client(self, mock_genai):
        """Test creating Gemini client."""
        client = create_vision_client(
            provider='gemini',
            api_key='test-key',
            model_name='gemini-2.0-flash-exp'
        )
        
        self.assertIsInstance(client, GeminiVisionClient)
    
    @patch('vision_client.OpenAI')
    def test_create_openai_client(self, mock_openai):
        """Test creating OpenAI-compatible client."""
        client = create_vision_client(
            provider='openai_compatible',
            api_key='test-key',
            model_name='gpt-4-vision-preview',
            endpoint_url='https://api.openai.com/v1'
        )
        
        self.assertIsInstance(client, OpenAICompatibleVisionClient)
    
    def test_create_unknown_provider(self):
        """Test creating client with unknown provider raises error."""
        with self.assertRaises(ValueError):
            create_vision_client(
                provider='unknown',
                api_key='test-key',
                model_name='test-model'
            )


if __name__ == '__main__':
    unittest.main()
