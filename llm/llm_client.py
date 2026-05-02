"""
[LLM Client]

OpenAI API 호출 담당 모듈.

역할:
- prompt_builder.py에서 만든 prompt를 OpenAI API로 전달
- raw 응답 텍스트 반환
- API 실패 시 안전하게 None 반환

환경변수:
- OPENAI_API_KEY 필요

설치:
    pip install openai
"""

from __future__ import annotations

import os
from typing import Optional

from openai import OpenAI


DEFAULT_MODEL = "gpt-4o-mini"


class LLMClientError(Exception):
    """LLM 호출 관련 예외"""
    pass


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise LLMClientError(
            "OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다."
        )

    client = OpenAI(
        api_key=api_key,
        timeout=20.0,
    )

    return client


def call_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    max_output_tokens: int = 16,
) -> Optional[str]:
    """
    단건 LLM 호출.

    Args:
        prompt: LLM에 전달할 프롬프트
        model: 사용할 모델명
        temperature: 출력 다양성. 카테고리 분류는 0.0 권장
        max_output_tokens: 카테고리명만 받으므로 작게 설정

    Returns:
        응답 텍스트 또는 실패 시 None
    """

    if not prompt or not str(prompt).strip():
        return None

    try:
        client = get_openai_client()

        response = client.responses.create(
            model=model,
            input=str(prompt).strip(),
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        output_text = getattr(response, "output_text", None)

        if output_text is None:
            return None

        return (
            str(output_text)
            .strip()
            .replace('"', '')
            .replace("'", "")
            .replace(".", "")
        )

    except Exception as exc:
        print(f"[LLM ERROR] {exc}")
        return None


def call_llm_required(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    max_output_tokens: int = 16,
) -> str:
    """
    실패 시 예외를 발생시키는 버전.
    테스트나 디버깅용.
    """

    result = call_llm(
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )

    if result is None:
        raise LLMClientError("LLM 응답을 받지 못했습니다.")

    return result