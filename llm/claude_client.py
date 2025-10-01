#!/usr/bin/env python3
"""
Claude API客户端
"""

import time
import tiktoken
from typing import Dict, Any
import logging
import anthropic
from .base import BaseLLMClient, CostInfo
from .config import LLMConfig

logger = logging.getLogger(__name__)

# Claude模型定价 (每百万tokens的价格，美元)
CLAUDE_PRICING = {
    # Claude 4 系列 (最新旗舰模型)
    'claude-opus-4-1-20250805': {'input': 15.0, 'output': 75.0},
    'claude-opus-4-1': {'input': 15.0, 'output': 75.0},
    'claude-opus-4-20250514': {'input': 15.0, 'output': 75.0},
    'claude-opus-4-0': {'input': 15.0, 'output': 75.0},
    'claude-sonnet-4-5-20250929': {'input': 3.0, 'output': 15.0},
    'claude-sonnet-4-5': {'input': 3.0, 'output': 15.0},
    'claude-sonnet-4-20250514': {'input': 3.0, 'output': 15.0},
    'claude-sonnet-4-0': {'input': 3.0, 'output': 15.0},
    
    # Claude 3.7 系列
    'claude-3-7-sonnet-20250219': {'input': 3.0, 'output': 15.0},
    'claude-3-7-sonnet-latest': {'input': 3.0, 'output': 15.0},
    
    # Claude 3.5 系列 (高性能模型)
    'claude-3-5-sonnet-20240620': {'input': 3.0, 'output': 15.0},
    'claude-3-5-sonnet-20241022': {'input': 3.0, 'output': 15.0},
    'claude-3-5-sonnet-latest': {'input': 3.0, 'output': 15.0},
    'claude-3-5-haiku-20241022': {'input': 0.8, 'output': 4.0},
    'claude-3-5-haiku-latest': {'input': 0.8, 'output': 4.0},
    
    # Claude 3 系列 (经典模型，部分已弃用但保持兼容)
    'claude-3-opus-20240229': {'input': 15.0, 'output': 75.0},
    'claude-3-sonnet-20240229': {'input': 3.0, 'output': 15.0},
    'claude-3-haiku-20240307': {'input': 0.25, 'output': 1.25},
    
    # 模型别名 (指向最新版本)
    'claude-opus-4': {'input': 15.0, 'output': 75.0},
    'claude-sonnet-4': {'input': 3.0, 'output': 15.0},
    'claude-3-opus': {'input': 15.0, 'output': 75.0},
    'claude-3-sonnet': {'input': 3.0, 'output': 15.0},
    'claude-3-haiku': {'input': 0.25, 'output': 1.25},
    'claude-3-5-sonnet': {'input': 3.0, 'output': 15.0},
    'claude-3-5-haiku': {'input': 0.8, 'output': 4.0},
}


class ClaudeClient(BaseLLMClient):
    """Claude API客户端"""
    
    def __init__(self, config: LLMConfig = None):
        """
        初始化Claude客户端
        
        Args:
            config: LLM配置对象
        """
        super().__init__(config)
        self.provider = "claude"
        self._setup_client()
        
        # 初始化tokenizer (Claude使用类似GPT的tokenizer)
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"Tokenizer初始化失败: {e}")
            self.tokenizer = None
    
    def _setup_client(self):
        """设置Claude客户端"""
        if not self.config.claude_api_key:
            raise ValueError("Claude API密钥未设置")
        
        self.client = anthropic.Anthropic(
            api_key=self.config.claude_api_key
        )
        
        # 验证API密钥有效性
        self._validate_api_key()
    
    def _validate_api_key(self):
        """验证API密钥有效性"""
        try:
            # 尝试发送一个简单的消息来验证API密钥
            response = self.client.messages.create(
                model=self.config.claude_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            logger.info("Claude API密钥验证成功")
        except Exception as e:
            logger.error(f"Claude API密钥验证失败: {e}")
            raise ValueError(f"Claude API密钥无效: {e}")
    
    def _make_request_with_retry(self, messages, **kwargs):
        """带重试的请求"""
        retry_times = self.config.retry_times
        retry_delay = self.config.retry_delay
        
        for attempt in range(retry_times):
            try:
                response = self.client.messages.create(
                    model=self.config.claude_model,
                    messages=messages,
                    temperature=kwargs.get('temperature', self.config.claude_temperature),
                    max_tokens=kwargs.get('max_tokens', self.config.claude_max_tokens)
                )
                
                # 计算成本
                if hasattr(response, 'usage') and response.usage:
                    input_tokens = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens
                    total_tokens = input_tokens + output_tokens
                else:
                    # 如果API没有返回usage信息，手动计算
                    input_text = " ".join([msg["content"] for msg in messages])
                    output_text = response.content[0].text
                    input_tokens = self.count_tokens(input_text)
                    output_tokens = self.count_tokens(output_text)
                    total_tokens = input_tokens + output_tokens
                
                cost_usd = self.calculate_cost(input_tokens, output_tokens)
                
                # 记录成本
                cost_info = CostInfo(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost_usd=cost_usd,
                    requests_count=1
                )
                self.add_cost(cost_info)
                
                return response.content[0].text
            
            except Exception as e:
                logger.warning(f"Claude API请求失败 (尝试 {attempt + 1}/{retry_times}): {e}")
                if attempt < retry_times - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # 指数退避
                else:
                    raise e
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """
        生成响应
        
        Args:
            prompt: 输入提示
            **kwargs: 其他参数
            
        Returns:
            生成的响应文本
        """
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        return self._make_request_with_retry(messages, **kwargs)
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息
        
        Returns:
            模型信息字典
        """
        return {
            'provider': 'claude',
            'model': self.config.claude_model,
            'max_tokens': self.config.claude_max_tokens,
            'temperature': self.config.claude_temperature,
            'supports_json_mode': True,
            'supports_function_calling': True
        }
    
    def count_tokens(self, text: str) -> int:
        """计算文本的token数量
        
        Args:
            text: 输入文本
            
        Returns:
            token数量
        """
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                logger.warning(f"Token计数失败: {e}")
        
        # 简单估算：平均每个token约4个字符
        return len(text) // 4
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """计算API调用成本
        
        Args:
            input_tokens: 输入token数量
            output_tokens: 输出token数量
            
        Returns:
            成本（美元）
        """
        model = self.config.claude_model
        
        # 获取模型定价
        pricing = CLAUDE_PRICING.get(model)
        if not pricing:
            # 如果没有找到确切的模型，尝试匹配前缀
            for model_prefix, model_pricing in CLAUDE_PRICING.items():
                if model.startswith(model_prefix.split('-')[0]):  # 匹配claude-3等前缀
                    pricing = model_pricing
                    break
            
            if not pricing:
                logger.warning(f"未找到模型 {model} 的定价信息，使用claude-3-sonnet的定价")
                pricing = CLAUDE_PRICING['claude-3-sonnet-20240229']
        
        # 计算成本（定价是每百万个token）
        input_cost = (input_tokens / 1000000) * pricing['input']
        output_cost = (output_tokens / 1000000) * pricing['output']
        
        return input_cost + output_cost