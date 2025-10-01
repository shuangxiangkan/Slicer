#!/usr/bin/env python3
"""
OpenAI API客户端
"""

import time
import tiktoken
from typing import Dict, Any
import logging
import openai
from .base import BaseLLMClient, CostInfo
from .config import LLMConfig

logger = logging.getLogger(__name__)

# Prices per 1 million tokens (based on official OpenAI pricing)
OPENAI_PRICING = {
    "gpt-5": {"input": 1.25, "output": 10.0},
    "gpt-4.1": {"input": 2.5, "output": 10.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    "gpt-3.5-turbo-0125": {"input": 0.5, "output": 1.5},
    "gpt-3.5-turbo-1106": {"input": 1.0, "output": 2.0},
    "gpt-3.5-turbo-instruct": {"input": 1.5, "output": 2.0},
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-4-0613": {"input": 30.0, "output": 60.0},
    "gpt-4-32k": {"input": 60.0, "output": 120.0},
    "gpt-4-32k-0613": {"input": 60.0, "output": 120.0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4-turbo-preview": {"input": 10.0, "output": 30.0},
    "gpt-4-0125-preview": {"input": 10.0, "output": 30.0},
    "gpt-4-1106-preview": {"input": 10.0, "output": 30.0},
    "gpt-4-vision-preview": {"input": 10.0, "output": 30.0},
    "gpt-4-1106-vision-preview": {"input": 10.0, "output": 30.0},
}


class OpenAIClient(BaseLLMClient):
    """OpenAI API客户端"""
    
    def __init__(self, config: LLMConfig = None):
        """
        初始化OpenAI客户端
        
        Args:
            config: LLM配置对象
        """
        super().__init__(config)
        self.provider = "openai"
        self._setup_client()
        
        # 初始化tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.config.openai_model)
        except KeyError:
            # 如果模型不支持，使用默认的cl100k_base编码
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            logger.warning(f"Model {self.config.openai_model} not found in tiktoken, using cl100k_base encoding")
    
    def _setup_client(self):
        """设置OpenAI客户端"""
        if not self.config.openai_api_key:
            raise ValueError("OpenAI API密钥未设置")
        
        # 设置OpenAI客户端
        base_url = self.config.openai_base_url or "https://api.openai.com/v1"
        
        self.client = openai.OpenAI(
            api_key=self.config.openai_api_key,
            base_url=base_url
        )
        
        # 验证API密钥有效性
        self._validate_api_key()
    
    def _validate_api_key(self):
        """验证API密钥有效性"""
        try:
            # 尝试获取模型列表来验证API密钥
            response = self.client.models.list()
            logger.info("OpenAI API密钥验证成功")
        except Exception as e:
            logger.error(f"OpenAI API密钥验证失败: {e}")
            raise ValueError(f"OpenAI API密钥无效: {e}")
    
    def _make_request_with_retry(self, messages, **kwargs):
        """带重试的请求"""
        retry_times = self.config.retry_times
        retry_delay = self.config.retry_delay
        
        for attempt in range(retry_times):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.openai_model,
                    messages=messages,
                    temperature=kwargs.get('temperature', self.config.openai_temperature),
                    max_tokens=kwargs.get('max_tokens', self.config.openai_max_tokens),
                    timeout=kwargs.get('timeout', self.config.timeout)
                )
                
                # 计算成本
                if hasattr(response, 'usage') and response.usage:
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens
                    total_tokens = response.usage.total_tokens
                else:
                    # 如果API没有返回usage信息，手动计算
                    input_text = " ".join([msg["content"] for msg in messages])
                    output_text = response.choices[0].message.content
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
                
                return response.choices[0].message.content
            
            except Exception as e:
                logger.warning(f"OpenAI API请求失败 (尝试 {attempt + 1}/{retry_times}): {e}")
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
            'provider': 'openai',
            'model': self.config.openai_model,
            'base_url': self.config.openai_base_url or "https://api.openai.com/v1",
            'max_tokens': self.config.openai_max_tokens,
            'temperature': self.config.openai_temperature,
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
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"Token计数失败: {e}")
            # 简单估算：平均每个token约4个字符
            return len(text) // 4
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        计算API调用成本
        
        Args:
            input_tokens: 输入token数量
            output_tokens: 输出token数量
            
        Returns:
            成本（美元）
        """
        model = self.config.openai_model
        
        # 获取模型定价
        pricing = OPENAI_PRICING.get(model)
        if not pricing:
            # 如果没有找到确切的模型，尝试匹配前缀
            for model_prefix, model_pricing in OPENAI_PRICING.items():
                if model.startswith(model_prefix):
                    pricing = model_pricing
                    break
            
            if not pricing:
                logger.warning(f"未找到模型 {model} 的定价信息，使用gpt-4的定价")
                pricing = OPENAI_PRICING['gpt-4']
        
        # 计算成本（定价是每1000000个token）
        input_cost = (input_tokens / 1000000) * pricing['input']
        output_cost = (output_tokens / 1000000) * pricing['output']
        
        return input_cost + output_cost