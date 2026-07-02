"""
Inference Engine - Local LLM inference using quantized models

Designed for llama.cpp integration with GGUF models
Optimized for lightweight, local execution
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("MiniKernel.Inference")


@dataclass
class InferenceConfig:
    """Configuration for LLM inference"""
    model_path: str
    context_size: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_tokens: int = 512
    threads: int = 4
    gpu_layers: int = 0  # Number of layers to offload to GPU
    
    # Quantization
    quantization: str = "Q4_K_M"  # 4-bit quantization (medium)


class InferenceEngine:
    """
    Inference Engine for quantized LLMs
    
    Designed to work with:
    - Llama-3-8B (quantized to 3-4 bit)
    - Mistral-7B (quantized)
    - Phi-3 (small models)
    
    Uses llama.cpp bindings for efficient inference
    """
    
    def __init__(self, config: Optional[InferenceConfig] = None):
        self.config = config or InferenceConfig(
            model_path="models/llama-3-8b-q4.gguf"
        )
        
        self.model = None
        self.context = []
        self.system_prompt = self._default_system_prompt()
        
        logger.info(f"Inference Engine created (model={Path(self.config.model_path).name})")
    
    def initialize(self) -> bool:
        """
        Load the model
        
        Returns:
            True if successful
        """
        try:
            # Try to import llama-cpp-python
            try:
                from llama_cpp import Llama
                
                logger.info(f"Loading model: {self.config.model_path}")
                
                self.model = Llama(
                    model_path=self.config.model_path,
                    n_ctx=self.config.context_size,
                    n_threads=self.config.threads,
                    n_gpu_layers=self.config.gpu_layers,
                    verbose=False
                )
                
                logger.info("Model loaded successfully")
                return True
                
            except ImportError:
                logger.warning("llama-cpp-python not installed, using mock inference")
                self.model = "mock"  # Fallback for testing
                return True
                
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    def infer(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """
        Run inference on a prompt
        
        Args:
            prompt: Input text
            max_tokens: Override max tokens
            
        Returns:
            Generated text
        """
        if not self.model:
            logger.error("Model not initialized")
            return ""
        
        try:
            # Build full prompt with system context
            full_prompt = self._build_prompt(prompt)
            
            # Mock inference if llama.cpp not available
            if self.model == "mock":
                return self._mock_inference(prompt)
            
            # Real inference
            max_tokens = max_tokens or self.config.max_tokens
            
            output = self.model(
                full_prompt,
                max_tokens=max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                stop=["</s>", "Human:", "User:"],
                echo=False
            )
            
            response = output["choices"][0]["text"].strip()
            
            # Update context
            self.context.append({"role": "user", "content": prompt})
            self.context.append({"role": "assistant", "content": response})
            
            return response
            
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return ""
    
    def parse_intent(self, natural_language: str) -> Dict[str, Any]:
        """
        Use LLM to parse natural language into structured intent
        
        This is the LLM fallback for the intent parser
        """
        prompt = f"""Parse this command into a structured format:
Command: "{natural_language}"

Respond with JSON:
{{
  "intent_type": "file_operation|process_control|system_info|package_management",
  "action": "specific_action",
  "parameters": {{}},
  "confidence": 0.0-1.0
}}

JSON:"""
        
        response = self.infer(prompt, max_tokens=256)
        
        # Parse JSON from response
        try:
            import json
            # Extract JSON from response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
        
        return {
            "intent_type": "unknown",
            "action": "unknown",
            "parameters": {},
            "confidence": 0.0
        }
    
    def _build_prompt(self, user_prompt: str) -> str:
        """Build complete prompt with system context"""
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.context[-4:])  # Last 4 turns for context
        messages.append({"role": "user", "content": user_prompt})
        
        # Format for llama.cpp
        prompt = ""
        for msg in messages:
            if msg["role"] == "system":
                prompt += f"System: {msg['content']}\n\n"
            elif msg["role"] == "user":
                prompt += f"User: {msg['content']}\n"
            elif msg["role"] == "assistant":
                prompt += f"Assistant: {msg['content']}\n"
        
        prompt += "Assistant:"
        return prompt
    
    def _default_system_prompt(self) -> str:
        """Default system prompt for OS assistant"""
        return """You are an AI assistant for MiniKernel, a voice-controlled operating system.
Your role is to help users control their system through natural language.

You can:
- Manage files (find, move, copy, delete)
- Control processes (start, stop, list)
- Query system information (memory, CPU, disk)
- Manage packages (install, uninstall, update)

Respond concisely and accurately. When parsing commands, extract the intent and parameters clearly."""
    
    def _mock_inference(self, prompt: str) -> str:
        """Mock inference for testing without llama.cpp"""
        # Simple keyword-based responses for testing
        prompt_lower = prompt.lower()
        
        if "parse this command" in prompt_lower:
            if "find" in prompt_lower or "search" in prompt_lower:
                return '{"intent_type": "file_operation", "action": "find", "parameters": {"query": "file"}, "confidence": 0.8}'
            elif "install" in prompt_lower:
                return '{"intent_type": "package_management", "action": "install", "parameters": {"package": "vim"}, "confidence": 0.9}'
            else:
                return '{"intent_type": "unknown", "action": "unknown", "parameters": {}, "confidence": 0.0}'
        
        return "I understand. How can I help you?"
    
    def clear_context(self) -> None:
        """Clear conversation context"""
        self.context = []
        logger.debug("Cleared conversation context")
    
    def set_system_prompt(self, prompt: str) -> None:
        """Update system prompt"""
        self.system_prompt = prompt
        logger.debug("Updated system prompt")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get inference statistics"""
        return {
            "model_path": self.config.model_path,
            "context_size": self.config.context_size,
            "context_turns": len(self.context) // 2,
            "model_loaded": self.model is not None
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # Create inference engine
    config = InferenceConfig(
        model_path="models/llama-3-8b-q4.gguf",
        context_size=2048,
        threads=4
    )
    
    engine = InferenceEngine(config)
    
    # Initialize (will use mock if llama.cpp not available)
    if engine.initialize():
        # Test intent parsing
        intent = engine.parse_intent("find the file I downloaded yesterday")
        print(f"Parsed intent: {intent}")
        
        # Test general inference
        response = engine.infer("What can you help me with?")
        print(f"Response: {response}")
