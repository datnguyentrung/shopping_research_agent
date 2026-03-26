import asyncio
import urllib.parse
import logging
from playwright.sync_api import sync_playwright  # Chuyển sang bản sync

logger = logging.getLogger(__name__)

def _run_shopee_logic(keyword: str):
    """
    Logic chính của Playwright chạy ở chế độ ĐỒNG BỘ (Sync)
    để tránh xung đột Event Loop trên Windows.
    """
    keyword_encoded = urllib.parse.quote(keyword)
    search_url = f"https://shopee.vn/search?keyword={keyword_encoded}"
    extracted_data = []

    # Sử dụng sync_playwright
    with sync_playwright() as p:
        # Khởi chạy trình duyệt
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        # ==========================================
        # HÀM LẮNG NGHE (Sync Version)
        # ==========================================
        def handle_response(response):
            if "api/v4/search/search_items" in response.url and response.status == 200:
                try:
                    # Trong sync mode, .json() không cần await
                    data = response.json()
                    items = data.get('items', [])
                    if items:
                        # Chỉ lấy item_basic và thêm vào list, không map ở đây
                        for item in items[:5]: # Lấy top 5 sản phẩm
                            item_basic = item.get('item_basic')
                            if item_basic:
                                extracted_data.append(item_basic)
                except Exception as e:
                    logger.warning(f"⚠️ Lỗi khi đọc JSON: {e}")

        # Đăng ký sự kiện
        page.on("response", handle_response)

        try:
            logger.info(f"🚀 Đang truy cập Shopee để tìm: {keyword}...")
            # Chờ networkidle ở bản sync
            page.goto(search_url, wait_until="networkidle", timeout=30000)
            # Nghỉ thêm một chút để đảm bảo intercept kịp
            page.wait_for_timeout(3000)
        except Exception as e:
            logger.error(f"❌ Lỗi khi tải trang: {e}")
        finally:
            browser.close()

    return extracted_data

async def intercept_shopee_api(keyword: str):
    """
    Tool tìm kiếm sản phẩm Shopee thông qua kỹ thuật Network Interception.
    Đã được tối ưu để chạy trên Windows.
    """
    # CHÌA KHÓA: Đẩy logic sync vào một thread riêng để né lỗi Event Loop của ADK
    return await asyncio.to_thread(_run_shopee_logic, keyword)

# Block test nhanh
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = asyncio.run(intercept_shopee_api("áo khoác nam"))
    for item in res:
        # Dữ liệu trả về giờ là dict, cần truy cập bằng key
        price = float(item.get('price', 0)) / 100000
        print(f"Product: {item.get('name', 'N/A')} - Price: {price} VND")
