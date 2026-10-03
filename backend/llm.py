"""LLM 客户端：DeepSeek（OpenAI 兼容）via LangChain。

- 真实模式：Windows 用户级环境变量 DEEPSEEK_API_KEY 自动生效，走 LangChain ChatOpenAI。
- 演示模式：无 key 时结构化生成函数返回 None，由调用方使用规则兜底（保证免 key 也能跑）。
遵循 IMA skills/J（后端 AI 模式）：用 with_structured_output(Pydantic) 做 JSON schema 校验兜底。
"""
import os
from typing import Optional, Type

from pydantic import BaseModel


def has_key() -> bool:
    return bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())


def get_llm(temperature: float = 0.4):
    """返回 LangChain ChatOpenAI（DeepSeek）。无 key 时抛 RuntimeError。"""
    from langchain_openai import ChatOpenAI

    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").strip()
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip()
    if not api_key:
        raise RuntimeError("NO_DEEPSEEK_KEY")
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=2048,
    )


def structured(messages: list, schema: Type[BaseModel], temperature: float = 0.4) -> Optional[BaseModel]:
    """用 LangChain 结构化输出抽取。

    注意：DeepSeek 当前 API 不支持 response_format 的 json_schema（报 400
    "This response_format type is unavailable now"）。故走 function_calling 方式
    （DeepSeek 兼容 OpenAI 工具调用），避免 response_format 限制。
    无 key / 失败返回 None（调用方走规则兜底）。
    """
    try:
        llm = get_llm(temperature=temperature)
        chain = llm.with_structured_output(schema, method="function_calling")
        return chain.invoke(messages)
    except Exception as e:  # 任何失败都降级，绝不让接口崩
        print(f"[llm.structured] 降级: {e}")
        return None
