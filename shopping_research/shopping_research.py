import logging
from google.adk.memory import InMemoryMemoryService
from google.adk.agents import LlmAgent, SequentialAgent
from tools.search_json_api import search_and_extract, extract_from_url, filter_product_urls
from util import load_instruction_from_file

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
product_urls_agent = LlmAgent(
    name="ProductURLsAgent",
    model="gemini-2.5-flash-lite",
    tools=[search_and_extract, extract_from_url, filter_product_urls],
    instruction=load_instruction_from_file("instruction/product_urls_agent_instruction.txt"),
)

# Agent 3: Generator UI (A2UI Protocol) - Chuyển đổi dữ liệu thành JSON cho React
ui_generator_agent = LlmAgent(
    name="ResponseGenerationAgent",
    model="gemini-2.5-flash-lite",
    instruction="""
    Nhận dữ liệu sản phẩm đã có URL từ Product URLs Agent.
    Ép kiểu dữ liệu sản phẩm thành JSON chuẩn để React render:
    {
      "component": "SwipeableProductCard",
      "data": [
         {"name": "...", "price": "...", "description": "...", "image_url": "...", "checkout_mb": true, "url": "..."}
      ]
    }
    Chỉ xuất JSON thuần, không bọc markdown.
    Thêm URL từ dữ liệu vào.
    """,
)

# ==========================================
# 4. ORCHESTRATOR - GỘP CÁC AGENT LẠI
# ==========================================
root_agent = SequentialAgent(
    name="Shopping_Research_Agent",
    sub_agents=[product_urls_agent, ui_generator_agent],
    description="Luồng tuần tự: Nhận dữ liệu từ Merchant API -> Product URLs Agent tìm URL trên web -> UI Generator chuyển thành JSON cho React render.",
)

logger.info("Shopping Research Agent initialized successfully")

