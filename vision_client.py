"""Vision Model Client supporting Gemini and OpenAI-compatible endpoints."""

import json
import logging
from typing import Dict, Optional, Union
from io import BytesIO
import base64

from PIL import Image

logger = logging.getLogger(__name__)


class VisionModelResponse:
    """Structured response from vision model."""
    
    def __init__(
        self,
        object_present: bool,
        correct_label: Optional[str],
        confidence: float,
        notes: Optional[str] = None
    ):
        self.object_present = object_present
        self.correct_label = correct_label
        self.confidence = confidence
        self.notes = notes
    
    def __repr__(self):
        return (f"VisionModelResponse(object_present={self.object_present}, "
                f"correct_label={self.correct_label}, confidence={self.confidence})")


class VisionClient:
    """Base client for vision models."""
    
    SYSTEM_PROMPT = """You are reviewing a security camera snapshot from a Frigate NVR system.

Your task is to determine:
1. Whether a real object is present in the image
2. The correct object label for what you see
3. Your confidence in the detection

Respond ONLY in valid JSON using this exact schema:

{
  "object_present": true or false,
  "correct_label": "string or null",
  "confidence": 0.0 to 1.0,
  "notes": "optional brief explanation"
}

Rules:
- object_present: true if you see a real, physical object; false for shadows, reflections, artifacts
- correct_label: the most accurate label (e.g., "person", "car", "dog"), or null if no object
- confidence: 0.0 (not confident) to 1.0 (very confident)
- notes: brief explanation of your decision (optional)

Do not include any text outside the JSON object."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    def analyze_image(
        self,
        image: Union[Image.Image, bytes],
        original_label: str
    ) -> Optional[VisionModelResponse]:
        """
        Analyze an image and return structured response.
        
        Args:
            image: PIL Image or image bytes
            original_label: The original label from Frigate
            
        Returns:
            VisionModelResponse or None if failed
        """
        raise NotImplementedError("Subclass must implement analyze_image")
    
    def _parse_response(self, response_text: str) -> Optional[VisionModelResponse]:
        """
        Parse JSON response from model.
        
        Args:
            response_text: Raw text response from model
            
        Returns:
            VisionModelResponse or None if parsing failed
        """
        try:
            # Try to find JSON in response
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            data = json.loads(response_text)
            
            # Extract fields
            object_present = data.get('object_present', False)
            correct_label = data.get('correct_label')
            confidence = float(data.get('confidence', 0.0))
            notes = data.get('notes')
            
            # Validate
            if not isinstance(object_present, bool):
                logger.error(f"Invalid object_present value: {object_present}")
                return None
            
            if confidence < 0.0 or confidence > 1.0:
                logger.warning(f"Confidence {confidence} out of range, clamping")
                confidence = max(0.0, min(1.0, confidence))
            
            return VisionModelResponse(
                object_present=object_present,
                correct_label=correct_label,
                confidence=confidence,
                notes=notes
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Invalid response format: {e}")
            return None


class GeminiVisionClient(VisionClient):
    """Google Gemini vision model client."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp", timeout: int = 30):
        super().__init__(timeout)
        self.api_key = api_key
        self.model_name = model_name
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            logger.info(f"Initialized Gemini client with model {model_name}")
        except ImportError:
            logger.error("google-generativeai package not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise
    
    def analyze_image(
        self,
        image: Union[Image.Image, bytes],
        original_label: str
    ) -> Optional[VisionModelResponse]:
        """Analyze image using Gemini."""
        try:
            # Convert bytes to PIL Image if needed
            if isinstance(image, bytes):
                image = Image.open(BytesIO(image))
            
            # Build prompt
            user_prompt = f"""The original detection label from Frigate was: "{original_label}"

Please analyze this image and respond with the JSON schema specified."""
            
            # Generate response
            response = self.model.generate_content(
                [self.SYSTEM_PROMPT, user_prompt, image],
                generation_config={
                    'temperature': 0.1,
                    'top_p': 0.95,
                    'top_k': 40,
                    'max_output_tokens': 500,
                }
            )
            
            if not response or not response.text:
                logger.error("Empty response from Gemini")
                return None
            
            logger.debug(f"Gemini response: {response.text[:200]}")
            return self._parse_response(response.text)
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None


class OpenAICompatibleVisionClient(VisionClient):
    """OpenAI-compatible vision model client."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4-vision-preview",
        endpoint_url: str = "https://api.openai.com/v1",
        timeout: int = 30
    ):
        super().__init__(timeout)
        self.api_key = api_key
        self.model_name = model_name
        self.endpoint_url = endpoint_url.rstrip('/')
        
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=api_key,
                base_url=endpoint_url,
                timeout=timeout
            )
            logger.info(f"Initialized OpenAI-compatible client with model {model_name}")
        except ImportError:
            logger.error("openai package not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    def _image_to_base64(self, image: Union[Image.Image, bytes]) -> str:
        """Convert image to base64 string."""
        if isinstance(image, bytes):
            return base64.b64encode(image).decode('utf-8')
        else:
            buffer = BytesIO()
            image.save(buffer, format='JPEG')
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def analyze_image(
        self,
        image: Union[Image.Image, bytes],
        original_label: str
    ) -> Optional[VisionModelResponse]:
        """Analyze image using OpenAI-compatible API."""
        try:
            # Convert image to base64
            image_b64 = self._image_to_base64(image)
            
            # Build prompt
            user_prompt = f"""The original detection label from Frigate was: "{original_label}"

Please analyze this image and respond with the JSON schema specified."""
            
            # Create chat completion
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": self.SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            if not response.choices or not response.choices[0].message.content:
                logger.error("Empty response from OpenAI-compatible API")
                return None
            
            response_text = response.choices[0].message.content
            logger.debug(f"OpenAI response: {response_text[:200]}")
            return self._parse_response(response_text)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None


def create_vision_client(
    provider: str,
    api_key: str,
    model_name: str,
    endpoint_url: Optional[str] = None,
    timeout: int = 30
) -> VisionClient:
    """
    Factory function to create appropriate vision client.
    
    Args:
        provider: "gemini" or "openai_compatible"
        api_key: API key for the service
        model_name: Model name to use
        endpoint_url: Endpoint URL (for OpenAI-compatible only)
        timeout: Request timeout in seconds
        
    Returns:
        VisionClient instance
    """
    if provider.lower() == "gemini":
        return GeminiVisionClient(api_key, model_name, timeout)
    elif provider.lower() == "openai_compatible":
        if not endpoint_url:
            endpoint_url = "https://api.openai.com/v1"
        return OpenAICompatibleVisionClient(api_key, model_name, endpoint_url, timeout)
    else:
        raise ValueError(f"Unknown provider: {provider}")
