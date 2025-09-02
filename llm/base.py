#!/usr/bin/env python3
"""
基础LLM客户端抽象类
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Union
from .config import LLMConfig

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    def __init__(self, config: Union['LLMConfig', None] = None):
        """
        初始化LLM客户端
        
        Args:
            config: LLM配置对象
        """
        self.config = config or LLMConfig.from_env()
        self._setup_client()
    
    @abstractmethod
    def _setup_client(self):
        """设置客户端"""
        pass
    
    @abstractmethod
    def generate_response(self, prompt: str, **kwargs) -> str:
        """
        生成响应
        
        Args:
            prompt: 输入提示
            **kwargs: 其他参数
            
        Returns:
            生成的响应文本
        """
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            模型信息字典
        """
        return {
            'provider': self.provider,
            'model': getattr(self.config, f'{self.provider}_model', 'unknown'),
            'config': self.config
        }


def create_llm_client(provider: str = None, config: LLMConfig = None) -> BaseLLMClient:
    """
    创建LLM客户端的统一接口
    
    Args:
        provider: 提供商名称 ('openai' 或 'claude')，如果为None则自动选择
        config: LLM配置对象，如果为None则从环境变量加载
        
    Returns:
        LLM客户端实例
        
    Raises:
        ValueError: 当指定的提供商不可用或没有可用的提供商时
    """
    if config is None:
        config = LLMConfig.from_env()
    
    # 如果没有指定provider，自动选择可用的
    if provider is None:
        if config.openai_api_key:
            provider = 'openai'
        elif config.claude_api_key:
            provider = 'claude'
        else:
            raise ValueError("No valid API key found. Please set OPENAI_API_KEY or CLAUDE_API_KEY.")
    
    # 创建对应的客户端，_setup_client方法会验证API有效性
    if provider == 'openai':
        from .openai_client import OpenAIClient
        return OpenAIClient(config)
    elif provider == 'claude':
        from .claude_client import ClaudeClient
        return ClaudeClient(config)
    else:
        raise ValueError(f"Unsupported provider: {provider}. Supported providers: 'openai', 'claude'")