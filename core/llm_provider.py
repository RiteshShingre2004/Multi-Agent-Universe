import os
import json
import time
from abc import ABC, abstractmethod
from typing import Optional, Type, Dict, Any
from google import genai
from ollama import Client as OllamaClient
from groq import Groq
from pydantic import BaseModel
from .models import AgentOutput

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_instruction: str, response_model: Type[BaseModel]) -> BaseModel:
        pass

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def _clean_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively remove 'additionalProperties' from the JSON schema."""
        if not isinstance(schema, dict):
            return schema
        
        cleaned = schema.copy()
        cleaned.pop('additionalProperties', None)
        cleaned.pop('title', None)
        
        for key, value in cleaned.items():
            if isinstance(value, dict):
                cleaned[key] = self._clean_schema(value)
            elif isinstance(value, list):
                cleaned[key] = [self._clean_schema(item) if isinstance(item, dict) else item for item in value]
        
        return cleaned

    def generate(self, prompt: str, system_instruction: str, response_model: Type[BaseModel]) -> BaseModel:
        raw_schema = response_model.model_json_schema()
        clean_schema = self._clean_schema(raw_schema)
        
        config = {
            "system_instruction": system_instruction,
            "response_mime_type": "application/json",
            "response_schema": clean_schema,
        }
        
        retries = 3
        while retries > 0:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                )
                return response_model.model_validate_json(response.text)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    print(f"Gemini Rate Limit hit. Retrying in 20s... ({retries} retries left)")
                    time.sleep(20)
                    retries -= 1
                else:
                    raise ValueError(f"Gemini error: {e}")
        raise ValueError("Gemini failed after multiple retries due to rate limits.")

class OllamaProvider(LLMProvider):
    def __init__(self, host: str, model_name: str = "llama3"):
        self.client = OllamaClient(host=host)
        self.model_name = model_name

    def generate(self, prompt: str, system_instruction: str, response_model: Type[BaseModel]) -> BaseModel:
        schema_info = json.dumps(response_model.model_json_schema(), indent=2)
        full_system = f"{system_instruction}\nYour output MUST be a valid JSON object matching this schema:\n{schema_info}"
        
        response = self.client.generate(
            model=self.model_name,
            prompt=f"System: {full_system}\n\nTask: {prompt}",
            format="json"
        )
        
        try:
            data = json.loads(response['response'])
            return response_model(**data)
        except Exception as e:
            raise ValueError(f"Failed to parse Ollama response: {e}\nRaw response: {response['response']}")

class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str = "llama-3.1-8b-instant"):
        self.client = Groq(api_key=api_key)
        self.model_name = model_name

    def generate(self, prompt: str, system_instruction: str, response_model: Type[BaseModel]) -> BaseModel:
        retries = 3
        while retries > 0:
            try:
                schema_info = json.dumps(response_model.model_json_schema(), indent=2)
                json_system_instruction = f"{system_instruction}\nReturn the output as a JSON object matching this schema:\n{schema_info}"
                
                chat_completion = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": json_system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    model=self.model_name,
                    response_format={"type": "json_object"}
                )
                content = chat_completion.choices[0].message.content
                return response_model.model_validate_json(content)
            except Exception as e:
                if "429" in str(e) or "rate_limit_exceeded" in str(e):
                    print(f"Groq Rate Limit hit. Retrying in 20s... ({retries} retries left)")
                    time.sleep(20)
                    retries -= 1
                else:
                    err_msg = str(e)
                    if "400" in err_msg and ("json_validate_failed" in err_msg or "Failed to generate JSON" in err_msg):
                        print(f"Groq JSON Validation Error. Retrying once with strict warning... ({retries} retries left)")
                        retries -= 1
                        time.sleep(2)
                        # Append a strict JSON reminder to the prompt for the retry
                        prompt += "\n\nCRITICAL: Your previous response failed JSON validation. Ensure you use DOUBLE QUOTES and NO PYTHON SETS (use [] for lists)."
                        continue

                    if "403" in err_msg or "Access denied" in err_msg:
                        raise ValueError(
                            "Groq Access Denied (403): Your network is being blocked by Groq/Cloudflare.\n"
                            "TIPS: 1. Disable any VPN/Proxy. 2. Check if your IP is in a restricted region. "
                            "3. Verify your API key in the Groq Console."
                        )
                    raise ValueError(f"Groq error: {e}")
        raise ValueError("Groq failed after multiple retries due to rate limits or validation errors.")

class LLMFactory:
    @staticmethod
    def get_provider(provider_type: str, config: Dict[str, Any]) -> LLMProvider:
        provider_type = provider_type.lower()
        if provider_type == "gemini":
            return GeminiProvider(api_key=config["api_key"], model_name=config.get("model_name", "gemini-2.0-flash"))
        elif provider_type == "ollama":
            return OllamaProvider(host=config.get("host", "http://localhost:11434"), model_name=config.get("model_name", "llama3"))
        elif provider_type == "groq":
            return GroqProvider(api_key=config["api_key"], model_name=config.get("model_name", "llama-3.1-8b-instant"))
        else:
            raise ValueError(f"Unsupported provider: {provider_type}")
