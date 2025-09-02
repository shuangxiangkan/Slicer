#!/usr/bin/env python3
"""
OpenAI API客户端
"""

import time
from typing import Dict, Any
import logging
import openai
from .base import BaseLLMClient
from .config import LLMConfig

logger = logging.getLogger(__name__)


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