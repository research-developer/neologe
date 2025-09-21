import httpx
import json
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.schemas import LLMResponseData


class LLMService:
    def __init__(self):
        self.providers = {
            "openai": self._call_openai,
            "anthropic": self._call_anthropic, 
            "google": self._call_google
        }
    
    async def get_definitions(self, word: str, user_definition: str, context: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get definitions from all three LLM providers"""
        responses = []
        
        for provider_name, provider_func in self.providers.items():
            try:
                response = await provider_func(word, user_definition, context)
                responses.append({
                    "provider": provider_name,
                    "response": response,
                    "success": True
                })
            except Exception as e:
                responses.append({
                    "provider": provider_name,
                    "error": str(e),
                    "success": False
                })
        
        return responses
    
    def _create_prompt(self, word: str, user_definition: str, context: Optional[str] = None) -> str:
        """Create a standardized prompt for all LLM providers"""
        prompt = f"""Please analyze the neologism "{word}" with the user-provided definition: "{user_definition}"
        
        {"Additional context: " + context if context else ""}
        
        Provide a response in the following JSON format:
        {{
            "word": "{word}",
            "definition": "A concise, dictionary-style definition",
            "part_of_speech": "noun/verb/adjective/etc",
            "etymology": "Likely word origin and formation",
            "variations": {{"plural": "...", "adjective": "...", "verb": "..."}},
            "usage_examples": ["Example sentence 1", "Example sentence 2"],
            "confidence": 0.85
        }}
        
        Rate your confidence in this analysis on a scale of 0.0 to 1.0."""
        
        return prompt
    
    async def _call_openai(self, word: str, user_definition: str, context: Optional[str] = None) -> LLMResponseData:
        """Call OpenAI API"""
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        prompt = self._create_prompt(word, user_definition, context)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "You are a linguistic expert analyzing neologisms. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse JSON response
            try:
                parsed_response = json.loads(content)
                return LLMResponseData(**parsed_response)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return LLMResponseData(
                    word=word,
                    definition=user_definition,
                    part_of_speech="unknown",
                    confidence=0.5
                )
    
    async def _call_anthropic(self, word: str, user_definition: str, context: Optional[str] = None) -> LLMResponseData:
        """Call Anthropic API"""
        if not settings.anthropic_api_key:
            raise ValueError("Anthropic API key not configured")
        
        prompt = self._create_prompt(word, user_definition, context)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1000,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Anthropic API error: {response.status_code} - {response.text}")
            
            result = response.json()
            content = result["content"][0]["text"]
            
            # Parse JSON response
            try:
                parsed_response = json.loads(content)
                return LLMResponseData(**parsed_response)
            except json.JSONDecodeError:
                return LLMResponseData(
                    word=word,
                    definition=user_definition,
                    part_of_speech="unknown",
                    confidence=0.5
                )
    
    async def _call_google(self, word: str, user_definition: str, context: Optional[str] = None) -> LLMResponseData:
        """Call Google Gemini API"""
        if not settings.google_api_key:
            raise ValueError("Google API key not configured")
        
        prompt = self._create_prompt(word, user_definition, context)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={settings.google_api_key}",
                headers={
                    "Content-Type": "application/json"
                },
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 1000
                    }
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Google API error: {response.status_code} - {response.text}")
            
            result = response.json()
            content = result["candidates"][0]["content"]["parts"][0]["text"]
            
            # Parse JSON response
            try:
                parsed_response = json.loads(content)
                return LLMResponseData(**parsed_response)
            except json.JSONDecodeError:
                return LLMResponseData(
                    word=word,
                    definition=user_definition,
                    part_of_speech="unknown",
                    confidence=0.5
                )
    
    async def evaluate_conflicts(self, word: str, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use an LLM to evaluate conflicts between the three responses"""
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key required for conflict evaluation")
        
        # Format the responses for evaluation
        response_text = ""
        for i, resp in enumerate(responses, 1):
            if resp["success"]:
                response_text += f"\nProvider {i} ({resp['provider']}):\n{json.dumps(resp['response'].dict(), indent=2)}\n"
        
        evaluation_prompt = f"""Analyze these three LLM responses for the neologism "{word}":

{response_text}

Identify any significant conflicts or disagreements between the definitions, parts of speech, etymologies, or other aspects. 

Respond with JSON in this format:
{{
    "conflicts_detected": ["Description of conflict 1", "Description of conflict 2"],
    "resolution_required": true/false,
    "overall_confidence": 0.85,
    "recommended_definition": "Best synthesized definition",
    "notes": "Additional observations"
}}

Only flag as requiring resolution if there are major disagreements about meaning or usage."""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "You are an expert linguist evaluating consistency between LLM responses. Always respond with valid JSON."},
                        {"role": "user", "content": evaluation_prompt}
                    ],
                    "temperature": 0.1
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Evaluation API error: {response.status_code} - {response.text}")
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {
                    "conflicts_detected": [],
                    "resolution_required": False,
                    "overall_confidence": 0.5,
                    "recommended_definition": "Unable to evaluate",
                    "notes": "Evaluation parsing failed"
                }


llm_service = LLMService()