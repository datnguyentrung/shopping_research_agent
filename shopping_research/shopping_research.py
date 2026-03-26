import logging
from typing import Any, Callable
from google.adk.memory import InMemoryMemoryService
from google.adk.agents import LlmAgent, SequentialAgent
from tools.playwright_shopee_tool import intercept_shopee_api
from util import load_instruction_from_file

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 1. KHỞI TẠO BỘ NHỚ
# ==========================================
session_memory = InMemoryMemoryService()

# ==========================================
# 2. CẤU HÌNH LLM (LITELLM PROXY)
# ==========================================
# llm_config = {
#     "api_base": "http://localhost:4000",
#     "model": "openai/gemini-2.5-pro",
#     "api_key": "dummy-key"
# }

# ==========================================
# 3. XÂY DỰNG SUB-AGENTS
# ==========================================

# Agent 2: Product URLs Agent - Tìm kiếm URL từ dữ liệu Merchant API cho trước
get_api_data_agent = LlmAgent(
    name="DataTransformationAgent",
    model="gemini-3.1-flash-lite-preview",
    tools=[intercept_shopee_api],  # Sử dụng tool đã map dữ liệu về schema chuẩn
    instruction=load_instruction_from_file("instruction/data_transformation_agent.txt"),
)

# # Agent 3: Generator UI (A2UI Protocol) - Chuyển đổi dữ liệu thành JSON cho React
# ui_generator_agent = LlmAgent(
#     name="ResponseGenerationAgent",
#     model="gemini-3.1-flash-lite-preview",
#     instruction="""
#     Nhận mảng dữ liệu sản phẩm (chuẩn CapturedData) từ Data Transformation Agent.
#     Nhiệm vụ của bạn là ép kiểu dữ liệu đó thành JSON chuẩn để React render theo format sau:
#     {
#       "component": "SwipeableProductCard",
#       "data": [
#          {
#            "name": "Tên sản phẩm",
#            "price": "Giá bán hiện tại (lấy từ price_current, định dạng chuỗi có VNĐ, vd: 285.000đ)",
#            "description": "Tên shop hoặc thông tin thêm",
#            "image_url": "Lấy từ main_image",
#            "checkout_mb": true,
#            "url": "Lấy từ product_url"
#          }
#       ]
#     }
#     Quy tắc:
#     - Chỉ xuất JSON thuần, KHÔNG bọc markdown (không dùng ```json).
#     - Map chính xác các trường từ CapturedData sang format của React UI.
#     """,
# )

# ==========================================
# 4. ORCHESTRATOR - GỘP CÁC AGENT LẠI
# ==========================================
root_agent = SequentialAgent(
    name="Shopping_Research_Agent",
    sub_agents=[get_api_data_agent],
    description="Agent nghiên cứu thị trường cho nền tảng thương mại điện tử. Nhận chủ đề sản phẩm, tìm kiếm dữ liệu từ Google Shopping thông qua API, và chuyển đổi dữ liệu đó thành format JSON chuẩn để UI có thể render.",
)

def _is_transient_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True

    msg = str(exc).lower()
    transient_tokens = (
        "timeout",
        "temporarily",
        "rate limit",
        "429",
        "503",
        "connection reset",
        "connection aborted",
        "deadline exceeded",
    )
    return any(token in msg for token in transient_tokens)


def _normalize_input(keyword_or_payload: Any) -> Any:
    if isinstance(keyword_or_payload, str):
        return {
            "topic": keyword_or_payload,
            "target_platform": "google_shopping",
            "duration_seconds": 45,
        }
    return keyword_or_payload


def _invoke_root_agent(payload: Any) -> Any:
    # ADK versions may expose run() differently; fallback keeps backward compatibility.
    run_fn = getattr(root_agent, "run", None)
    if callable(run_fn):
        return run_fn(payload)
    raise RuntimeError("root_agent does not expose a callable run method in this ADK runtime.")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_is_transient_error),
    before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
    reraise=True,
)
def run_agent_with_retry(keyword_or_payload: Any, invoke_fn: Callable[[Any], Any] | None = None) -> Any:
    payload = _normalize_input(keyword_or_payload)
    logger.info("Đang gọi Agent với retry...")
    runner = invoke_fn or _invoke_root_agent
    return runner(payload)

logger.info("Shopping Research Agent initialized successfully")
