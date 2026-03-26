import logging
from google.adk.memory import InMemoryMemoryService
from google.adk.agents import LlmAgent, SequentialAgent
from tools.playwright_shopee_tool import intercept_shopee_api
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
get_api_data_agent = LlmAgent(
    name="DataTransformationAgent",
    model="gemini-3.1-flash-lite-preview",
    tools=[intercept_shopee_api],
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

logger.info("Shopping Research Agent initialized successfully")

