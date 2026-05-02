"""
[LLM Category Normalization Package]

Semantic 결과의 상품 객체에 대해
LLM 기반 카테고리 정규화를 수행하는 패키지.
"""

from llm.category_schema import (
    PRIMARY_CATEGORIES,
    CATEGORY_DESCRIPTIONS,
    get_allowed_categories,
    is_allowed_category,
    normalize_category,
)

from llm.prompt_builder import (
    build_category_prompt,
    build_batch_category_prompt,
)

from llm.llm_client import (
    call_llm,
    call_llm_required,
    LLMClientError,
)

from llm.response_parser import (
    parse_category_response,
    parse_batch_category_response,
)

from llm.category_manager import (
    categorize_receipt_items,
    categorize_items_only,
    build_category_summary,
)

from llm.metrics import (
    build_category_metrics,
    build_category_metrics_for_many,
    build_consumption_metrics_from_amounts,
    compare_consumption_metrics,
    attach_category_metrics,
)

__all__ = [
    "PRIMARY_CATEGORIES",
    "CATEGORY_DESCRIPTIONS",
    "get_allowed_categories",
    "is_allowed_category",
    "normalize_category",
    "build_category_prompt",
    "build_batch_category_prompt",
    "call_llm",
    "call_llm_required",
    "LLMClientError",
    "parse_category_response",
    "parse_batch_category_response",
    "categorize_receipt_items",
    "categorize_items_only",
    "build_category_summary",
]