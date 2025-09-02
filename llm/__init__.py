#!/usr/bin/env python3
"""
LLM模块 - 大语言模型集成

提供统一的大语言模型调用接口，支持OpenAI和Claude等多种LLM服务
"""

from .base import BaseLLMClient, create_llm_client
from .openai_client import OpenAIClient
from .claude_client import ClaudeClient
from .config import LLMConfig

__all__ = [
    'BaseLLMClient',
    'create_llm_client',
    'OpenAIClient', 
    'ClaudeClient',
    'LLMConfig'
]

__version__ = '1.0.0'