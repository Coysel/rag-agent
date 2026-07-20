"""
统一 LLM 客户端抽象层

支持:
  - DeepSeek (OpenAI 兼容协议, base_url: https://api.deepseek.com)
  - Anthropic (Claude 模型, 原生协议)
  - 指数退避重试（最多 3 次）

使用方式:
    from src.agent.llm_client import get_llm_client

    client = get_llm_client()
    result = client.create_message(
        system="You are a helpful assistant.",
        messages=[{"role": "user", "content": "Hello"}],
        tools=[...],
        max_tokens=1024,
        temperature=0.3,
    )
    # result = {"text": "...", "tool_calls": [{"id": "...", "name": "...", "input": {...}}]}
"""

import json
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI
from anthropic import Anthropic

from config import (
    LLM_PROVIDER,
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
    DEEPSEEK_BASE_URL,
)


class LLMClient:
    """统一的 LLM 客户端，内部适配 DeepSeek (OpenAI) 和 Anthropic 两种协议"""

    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0  # 指数退避基数 (秒)
    RETRYABLE_ERRORS = (
        "rate_limit", "timeout", "connection", "server_error",
        "internal_server_error", "service_unavailable", "too_many_requests",
    )

    def __init__(self, provider: str = LLM_PROVIDER):
        self.provider = provider

        if provider == "deepseek":
            if not DEEPSEEK_API_KEY:
                raise ValueError("DEEPSEEK_API_KEY 未设置，请在 .env 中配置")
            self._client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
            )
            self._model = DEEPSEEK_MODEL
            self._base_url = DEEPSEEK_BASE_URL
        elif provider == "anthropic":
            if not ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY 未设置，请在 .env 中配置")
            self._client = Anthropic(api_key=ANTHROPIC_API_KEY)
            self._model = CLAUDE_MODEL
            self._base_url = "https://api.anthropic.com"
        else:
            raise ValueError(f"不支持的 LLM provider: {provider}，可选: deepseek, anthropic")

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

    def get_info(self) -> dict:
        """返回 LLM 配置信息（不含 API Key）"""
        return {
            "provider": self.provider,
            "model": self._model,
            "base_url": self._base_url,
        }

    def create_message(
        self,
        system: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[dict]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        统一的消息创建接口（带指数退避重试）

        Args:
            system: 系统提示
            messages: 对话历史
            tools: 工具定义列表
            max_tokens: 最大生成 token 数
            temperature: 采样温度

        Returns: {"text": str, "tool_calls": [...], "usage": {...}}
        """
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                if self.provider == "deepseek":
                    return self._create_message_openai(
                        system=system, messages=messages, tools=tools,
                        max_tokens=max_tokens, temperature=temperature,
                    )
                elif self.provider == "anthropic":
                    return self._create_message_anthropic(
                        system=system, messages=messages, tools=tools,
                        max_tokens=max_tokens, temperature=temperature,
                    )
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                is_retryable = any(
                    keyword in error_str for keyword in self.RETRYABLE_ERRORS
                )
                if not is_retryable or attempt == self.MAX_RETRIES - 1:
                    break
                delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                time.sleep(delay)

        raise last_error

    # ── OpenAI 兼容路径 (DeepSeek) ───────────────────────

    def _create_message_openai(
        self,
        system: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[dict]],
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        """通过 OpenAI SDK 调用 DeepSeek"""

        # 构建消息列表，system prompt 作为第一条消息
        api_messages = []
        if system:
            api_messages.append({"role": "system", "content": system})
        api_messages.extend(messages)

        kwargs = {
            "model": self._model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if tools:
            kwargs["tools"] = tools
#调用api
        response = self._client.chat.completions.create(**kwargs)
        
        choice = response.choices[0]

        result: Dict[str, Any] = {
            "text": choice.message.content or "",
            "tool_calls": [],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        }

        # 解析 tool_calls
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                # function.arguments 是 JSON 字符串，需要解析
                try:
                    tool_input = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    tool_input = {}

                result["tool_calls"].append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": tool_input,
                })

        return result

    # ── Anthropic 原生路径 (保留兼容) ────────────────────

    def _create_message_anthropic(
        self,
        system: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[dict]],
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        """通过 Anthropic SDK 调用 Claude"""

        # Anthropic messages 格式: 需要从历史中分离 system 消息
        api_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            # Anthropic 不允许 role="system" 出现在 messages 中
            if role == "system":
                continue
            api_messages.append({"role": role, "content": msg.get("content", "")})

        # 转换工具格式: OpenAI → Anthropic (兼容 MCP 动态生成的 Anthropic 原生格式)
        anthropic_tools = None
        if tools:
            anthropic_tools = []
            for tool in tools:
                # 检测: MCP 动态生成的已经是 Anthropic 原生格式 (有 input_schema)
                if "input_schema" in tool:
                    anthropic_tools.append(tool)
                else:
                    # 从 OpenAI function-calling 格式转换
                    func = tool.get("function", {})
                    anthropic_tools.append({
                        "name": func.get("name", ""),
                        "description": func.get("description", ""),
                        "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
                    })

        kwargs = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": api_messages,
        }

        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        response = self._client.messages.create(**kwargs)

        result: Dict[str, Any] = {
            "text": "",
            "tool_calls": [],
            "usage": {
                "prompt_tokens": response.usage.input_tokens if hasattr(response, 'usage') and response.usage else 0,
                "completion_tokens": response.usage.output_tokens if hasattr(response, 'usage') and response.usage else 0,
                "total_tokens": (response.usage.input_tokens + response.usage.output_tokens) if hasattr(response, 'usage') and response.usage else 0,
            },
        }

        for block in response.content:
            if block.type == "text":
                result["text"] += block.text
            elif block.type == "tool_use":
                result["tool_calls"].append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        return result


# ── 全局单例 ────────────────────────────────────────────────

_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取全局 LLM 客户端实例 (懒初始化)"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
