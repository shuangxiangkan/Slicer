#!/usr/bin/env python3
"""
LLM配置管理模块
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging
from pathlib import Path

# 加载.env文件
try:
    from dotenv import load_dotenv
    # 获取当前文件所在目录的.env文件
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)  # override=True 让.env文件中的值覆盖环境变量
    else:
        raise FileNotFoundError(f".env文件不存在: {env_path}")
except ImportError:
    raise ImportError("请安装python-dotenv库: pip install python-dotenv")

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM配置类"""
    
    # OpenAI配置
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_temperature: Optional[float] = None
    openai_max_tokens: Optional[int] = None
    
    # Claude配置
    claude_api_key: Optional[str] = None
    claude_model: Optional[str] = None
    claude_base_url: Optional[str] = None
    claude_temperature: Optional[float] = None
    claude_max_tokens: Optional[int] = None
    
    # 通用配置
    timeout: Optional[int] = None
    retry_times: Optional[int] = None
    retry_delay: Optional[float] = None
     
    @classmethod
    def from_env(cls) -> 'LLMConfig':
        """从.env文件创建配置"""
        # 确保.env文件已加载
        env_path = Path(__file__).parent / '.env'
        if not env_path.exists():
            raise FileNotFoundError(f".env文件不存在: {env_path}")
        
        # 重新加载.env文件，覆盖环境变量
        from dotenv import load_dotenv
        load_dotenv(env_path, override=True)
        
        # 从.env文件读取配置，不提供默认值，确保所有配置都在.env中定义
        config = cls()
        
        # OpenAI配置
        if os.getenv('OPENAI_API_KEY'):
            config.openai_api_key = os.getenv('OPENAI_API_KEY')
        if os.getenv('OPENAI_MODEL'):
            config.openai_model = os.getenv('OPENAI_MODEL')
        if os.getenv('OPENAI_BASE_URL'):
            config.openai_base_url = os.getenv('OPENAI_BASE_URL')
        if os.getenv('OPENAI_TEMPERATURE'):
            config.openai_temperature = float(os.getenv('OPENAI_TEMPERATURE'))
        if os.getenv('OPENAI_MAX_TOKENS'):
            config.openai_max_tokens = int(os.getenv('OPENAI_MAX_TOKENS'))
        
        # Claude配置
        if os.getenv('CLAUDE_API_KEY'):
            config.claude_api_key = os.getenv('CLAUDE_API_KEY')
        if os.getenv('CLAUDE_MODEL'):
            config.claude_model = os.getenv('CLAUDE_MODEL')
        if os.getenv('CLAUDE_BASE_URL'):
            config.claude_base_url = os.getenv('CLAUDE_BASE_URL')
        if os.getenv('CLAUDE_TEMPERATURE'):
            config.claude_temperature = float(os.getenv('CLAUDE_TEMPERATURE'))
        if os.getenv('CLAUDE_MAX_TOKENS'):
            config.claude_max_tokens = int(os.getenv('CLAUDE_MAX_TOKENS'))
        
        # 通用配置
        if os.getenv('LLM_TIMEOUT'):
            config.timeout = int(os.getenv('LLM_TIMEOUT'))
        if os.getenv('LLM_RETRY_TIMES'):
            config.retry_times = int(os.getenv('LLM_RETRY_TIMES'))
        if os.getenv('LLM_RETRY_DELAY'):
            config.retry_delay = float(os.getenv('LLM_RETRY_DELAY'))
        
        return config
    
    @classmethod
    def from_file(cls, config_path: str) -> 'LLMConfig':
        """从配置文件创建配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            return cls(**config_data)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return cls()
    
    def to_file(self, config_path: str):
        """保存配置到文件"""
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self), f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存到: {config_path}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def validate(self) -> bool:
        """验证配置"""
        # 检查是否至少有一个提供商的API密钥可用
        if not self.openai_api_key and not self.claude_api_key:
            logger.error("至少需要设置一个LLM提供商的API密钥（OpenAI或Claude）")
            return False
        
        return True
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """获取指定提供商的配置"""
        if provider == "openai":
            return {
                'api_key': self.openai_api_key,
                'model': self.openai_model,
                'base_url': self.openai_base_url,
                'temperature': self.openai_temperature,
                'max_tokens': self.openai_max_tokens,
                'timeout': self.timeout,
                'retry_times': self.retry_times,
                'retry_delay': self.retry_delay
            }
        elif provider == "claude":
            return {
                'api_key': self.claude_api_key,
                'model': self.claude_model,
                'temperature': self.claude_temperature,
                'max_tokens': self.claude_max_tokens,
                'timeout': self.timeout,
                'retry_times': self.retry_times,
                'retry_delay': self.retry_delay
            }
        else:
            raise ValueError(f"不支持的提供商: {provider}")


# 默认配置实例
default_config = LLMConfig.from_env()