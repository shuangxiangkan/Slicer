#!/usr/bin/env python3
"""
DeepSeek API客户端 (兼容OpenAI API)
"""

import logging
import openai
import tiktoken
from .base import BaseLLMClient, CostInfo
from .config import LLMConfig

logger = logging.getLogger(__name__)

# DeepSeek定价 (每百万tokens)
DEEPSEEK_PRICING = {
    'deepseek-chat': {'input': 0.27, 'output': 1.1},
    'deepseek-reasoner': {'input': 0.55, 'output': 2.19},
}


class DeepSeekClient(BaseLLMClient):
    """DeepSeek API客户端 (兼容OpenAI API)"""
    
    def __init__(self, config: LLMConfig = None):
        super().__init__(config)
        self.provider = "deepseek"
        self._setup_client()
        
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except:
            self.tokenizer = None
    
    def _setup_client(self):
        """设置DeepSeek客户端"""
        if not self.config.deepseek_api_key:
            raise ValueError("DeepSeek API密钥未设置")
        
        base_url = self.config.deepseek_base_url or "https://api.deepseek.com"
        
        self.client = openai.OpenAI(
            api_key=self.config.deepseek_api_key,
            base_url=base_url
        )
        logger.info(f"DeepSeek client initialized with base_url: {base_url}")
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """生成响应"""
        messages = [{"role": "user", "content": prompt}]
        
        retry_times = self.config.retry_times or 3
        retry_delay = self.config.retry_delay or 1.0
        
        import time
        for attempt in range(retry_times):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.deepseek_model or "deepseek-chat",
                    messages=messages,
                    temperature=kwargs.get('temperature', self.config.deepseek_temperature or 0.0),
                    max_tokens=kwargs.get('max_tokens', self.config.deepseek_max_tokens or 4096)
                )
                
                # 记录成本
                if hasattr(response, 'usage') and response.usage:
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens
                    cost = self.calculate_cost(input_tokens, output_tokens)
                    self.add_cost(CostInfo(input_tokens, output_tokens, input_tokens + output_tokens, cost, 1))
                
                return response.choices[0].message.content
                
            except Exception as e:
                logger.warning(f"DeepSeek API请求失败 (尝试 {attempt + 1}/{retry_times}): {e}")
                if attempt < retry_times - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                else:
                    raise e
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """计算成本"""
        model = self.config.deepseek_model or "deepseek-chat"
        pricing = DEEPSEEK_PRICING.get(model, DEEPSEEK_PRICING['deepseek-chat'])
        return (input_tokens / 1000000) * pricing['input'] + (output_tokens / 1000000) * pricing['output']
    
    def count_tokens(self, text: str) -> int:
        """计算token数"""
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except:
                pass
        return len(text) // 4
