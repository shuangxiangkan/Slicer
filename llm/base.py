#!/usr/bin/env python3
"""
基础LLM客户端抽象类
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Union
from dataclasses import dataclass
from .config import LLMConfig

logger = logging.getLogger(__name__)


@dataclass
class CostInfo:
    """成本信息数据类"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    requests_count: int = 0
    
    def add(self, other: 'CostInfo') -> 'CostInfo':
        """累加成本信息"""
        return CostInfo(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cost_usd=self.cost_usd + other.cost_usd,
            requests_count=self.requests_count + other.requests_count
        )

class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    def __init__(self, config: Union['LLMConfig', None] = None):
        """
        初始化LLM客户端
        
        Args:
            config: LLM配置对象
        """
        self.config = config or LLMConfig.from_env()
        self.total_cost = CostInfo()  # 总成本统计
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
    
    @abstractmethod
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        计算API调用成本
        
        Args:
            input_tokens: 输入token数量
            output_tokens: 输出token数量
            
        Returns:
            成本（美元）
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        计算文本的token数量
        
        Args:
            text: 输入文本
            
        Returns:
            token数量
        """
        pass
    
    def add_cost(self, cost_info: CostInfo):
        """
        添加成本信息到总统计中
        
        Args:
            cost_info: 成本信息
        """
        self.total_cost = self.total_cost.add(cost_info)
        logger.info(f"Added cost: ${cost_info.cost_usd:.4f}, Total cost: ${self.total_cost.cost_usd:.4f}")
    
    def get_total_cost(self) -> CostInfo:
        """
        获取总成本信息
        
        Returns:
            总成本信息
        """
        return self.total_cost
    
    def reset_cost(self):
        """重置成本统计"""
        self.total_cost = CostInfo()
        logger.info("Cost statistics reset")
    
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
    # 在函数内部导入，避免循环导入
    from .openai_client import OpenAIClient
    from .claude_client import ClaudeClient
    
    if config is None:
        config = LLMConfig.from_env()
    
    # 如果没有指定provider，自动选择可用的（优先使用Claude）
    if provider is None:
        if config.claude_api_key:
            provider = 'claude'
        elif config.openai_api_key:
            provider = 'openai'
        else:
            raise ValueError("No valid API key found. Please set OPENAI_API_KEY or CLAUDE_API_KEY.")
    
    # 创建对应的客户端，_setup_client方法会验证API有效性
    if provider == 'openai':
        return OpenAIClient(config)
    elif provider == 'claude':
        return ClaudeClient(config)
    else:
        raise ValueError(f"Unsupported provider: {provider}. Supported providers: 'openai', 'claude'")