"""
DeepSeek / MIMO 推理模型专用 ChatModel 包装器

推理模型在响应中返回 reasoning_content 字段，多轮对话时必须回传。
标准 ChatOpenAI 不处理此字段，导致 API 返回 400 错误。

根因：OpenAI Python SDK 的 Pydantic 模型使用 extra='ignore'，
会静默丢弃 reasoning_content 等非 OpenAI 标准字段。

解决方案：
- 重写 _get_request_payload：将 additional_kwargs["reasoning_content"] 注入请求体
- 重写 _generate/_agenerate：从 with_raw_response 获取原始 JSON 提取 reasoning_content
- 流式：使用 httpx 直接请求 API，逐行解析 SSE 事件
"""

import json
import logging
from typing import Any, Dict, Iterator, List, Optional

import httpx
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

_REASONING_MODEL_PATTERNS = (
    "deepseek-reasoner",
    "deepseek-r1",
    "ds-r1",
    "reasoner",
    "mimo",  # 小米 MIMO 推理模型
)


def is_reasoning_model(model_name: str) -> bool:
    """判断模型是否为推理模型（基于名称匹配）"""
    name_lower = (model_name or "").lower()
    return any(p in name_lower for p in _REASONING_MODEL_PATTERNS)


class ChatDeepSeek(ChatOpenAI):
    """
    推理模型专用 ChatModel

    通过 _get_request_payload 注入 reasoning_content，
    通过 with_raw_response / httpx 绕过 Pydantic 解析。
    """

    class Config:
        arbitrary_types_allowed = True

    # ── 请求侧：注入 reasoning_content ──

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)

        # 将 additional_kwargs 中的 reasoning_content 注入到 assistant 消息中
        messages = self._convert_input(input_).to_messages()
        api_messages = payload.get("messages", [])
        for msg, api_msg in zip(messages, api_messages):
            if isinstance(msg, AIMessage) and api_msg.get("role") == "assistant":
                rc = msg.additional_kwargs.get("reasoning_content")
                if rc:
                    api_msg["reasoning_content"] = rc

        return payload

    # ── 非流式：从原始 JSON 提取 reasoning_content ──

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self._ensure_sync_client_available()
        payload = self._get_request_payload(messages, stop=stop, **kwargs)

        raw_response = self.root_client.chat.completions.with_raw_response.create(**payload)
        data = raw_response.json()
        reasoning = self._extract_rc_from_json(data)
        result = self._json_to_chat_result(data)

        if reasoning:
            for g in result.generations:
                if isinstance(g, ChatGeneration) and isinstance(g.message, AIMessage):
                    g.message.additional_kwargs["reasoning_content"] = reasoning
                    logger.info("ChatDeepSeek: 保存 reasoning_content (长度=%d)", len(reasoning))
        return result

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        payload = self._get_request_payload(messages, stop=stop, **kwargs)

        raw_response = await self.root_async_client.chat.completions.with_raw_response.create(**payload)
        data = raw_response.json()
        reasoning = self._extract_rc_from_json(data)
        result = self._json_to_chat_result(data)

        if reasoning:
            for g in result.generations:
                if isinstance(g, ChatGeneration) and isinstance(g.message, AIMessage):
                    g.message.additional_kwargs["reasoning_content"] = reasoning
                    logger.info("ChatDeepSeek: 保存 reasoning_content (长度=%d)", len(reasoning))
        return result

    # ── 流式：httpx 直接请求 ──

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        payload["stream"] = True
        yield from self._stream_via_httpx(payload)

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        payload["stream"] = True
        async for chunk in self._astream_via_httpx(payload):
            yield chunk

    def _stream_via_httpx(self, params: dict) -> Iterator[ChatGenerationChunk]:
        url = str(self.root_client.base_url).rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.root_client.api_key}",
            "Content-Type": "application/json",
        }
        accumulated_reasoning = ""

        with httpx.Client(timeout=self.request_timeout or 120) as client:
            with client.stream("POST", url, json=params, headers=headers) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    rc = self._extract_rc_from_stream_json(chunk_data)
                    if rc:
                        accumulated_reasoning = rc

                    yield self._stream_json_to_generation_chunk(
                        chunk_data,
                        reasoning_content=accumulated_reasoning,
                    )

    async def _astream_via_httpx(self, params: dict):
        url = str(self.root_client.base_url).rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.root_client.api_key}",
            "Content-Type": "application/json",
        }
        accumulated_reasoning = ""

        async with httpx.AsyncClient(timeout=self.request_timeout or 120) as client:
            async with client.stream("POST", url, json=params, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    rc = self._extract_rc_from_stream_json(chunk_data)
                    if rc:
                        accumulated_reasoning = rc

                    yield self._stream_json_to_generation_chunk(
                        chunk_data,
                        reasoning_content=accumulated_reasoning,
                    )

    # ── 辅助方法 ──

    @staticmethod
    def _extract_rc_from_json(data: dict) -> Optional[str]:
        try:
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("reasoning_content")
        except (KeyError, IndexError, TypeError):
            pass
        return None

    @staticmethod
    def _extract_rc_from_stream_json(chunk: dict) -> Optional[str]:
        try:
            choices = chunk.get("choices", [])
            if choices:
                return choices[0].get("delta", {}).get("reasoning_content")
        except (KeyError, IndexError, TypeError):
            pass
        return None

    def _json_to_chat_result(self, data: dict) -> ChatResult:
        generations = []
        for choice in data.get("choices", []):
            msg_data = choice.get("message", {})
            content = msg_data.get("content") or ""
            additional_kwargs = {}
            if msg_data.get("tool_calls"):
                additional_kwargs["tool_calls"] = msg_data["tool_calls"]

            usage = data.get("usage", {})
            msg = AIMessage(
                content=content,
                additional_kwargs=additional_kwargs,
                response_metadata={
                    "model_name": data.get("model", ""),
                    "finish_reason": choice.get("finish_reason"),
                },
            )
            if usage:
                msg.usage_metadata = {
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }
            generations.append(
                ChatGeneration(
                    message=msg,
                    generation_info={"finish_reason": choice.get("finish_reason")},
                )
            )
        return ChatResult(generations=generations)

    def _stream_json_to_generation_chunk(
        self, data: dict, reasoning_content: str = ""
    ) -> ChatGenerationChunk:
        content = ""
        additional_kwargs = {}
        finish_reason = None
        choices = data.get("choices", [])
        if choices:
            choice = choices[0]
            delta = choice.get("delta", {})
            content = delta.get("content") or ""
            finish_reason = choice.get("finish_reason")
            if delta.get("tool_calls"):
                additional_kwargs["tool_calls"] = delta["tool_calls"]
        if reasoning_content:
            additional_kwargs["reasoning_content"] = reasoning_content

        message_chunk = AIMessageChunk(
            content=content,
            additional_kwargs=additional_kwargs,
            response_metadata={
                "model_name": data.get("model", ""),
                "finish_reason": finish_reason,
            },
        )
        usage = data.get("usage")
        if usage:
            message_chunk.usage_metadata = {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }

        generation_info = {}
        if finish_reason is not None:
            generation_info["finish_reason"] = finish_reason
        return ChatGenerationChunk(
            message=message_chunk,
            generation_info=generation_info or None,
        )
