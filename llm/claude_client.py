#!/usr/bin/env python3
"""
Claude API客户端
"""

import time
from typing import Dict, Any
import logging
import anthropic
from .base import BaseLLMClient
from .config import LLMConfig

logger = logging.getLogger(__name__)


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