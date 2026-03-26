import asyncio
import urllib.parse
from playwright.async_api import async_playwright


async def intercept_shopee_api(keyword):
    print(f"🕵️‍♂️ Đang dùng chiến thuật 'Persistent Context' tìm: '{keyword}'...")

    keyword_encoded = urllib.parse.quote(keyword)
    search_url = f"https://shopee.vn/search?keyword={keyword_encoded}"
    extracted_data = []

    # Thư mục để lưu thông tin Profile (nó sẽ tự động tạo ở cùng thư mục chứa code)
    user_data_dir = "./shopee_agent_profile"

    async with async_playwright() as p:
        # Khởi chạy trình duyệt VÀ load/lưu profile
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,  # Lần đầu TIÊN QUYẾT phải để False để xem mặt mũi trang web
            args=['--disable-blink-features=AutomationControlled'],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )

        # Với persistent context, Playwright tự tạo sẵn một tab (page) đầu tiên
        page = context.pages[0]

        # ==========================================
        # HÀM LẮNG NGHE
        # ==========================================
        async def handle_response(response):
            if "api/v4/search/search_items" in response.url and response.status == 200:
                try:
                    data = await response.json()
                    if 'items' in data and data['items']:
                        print("\n✅ THÀNH CÔNG: Đã bóc được danh sách sản phẩm!")
                        for index, item in enumerate(data['items'][:5]):
                            info = item.get('item_basic', {})
                            name = info.get('name', 'Không có tên')
                            price = info.get('price', 0) / 100000
                            sold = info.get('historical_sold', 0)
                            extracted_data.append({"name": name, "price": price, "sold": sold})
                    else:
                        print("⚠️ Shopee vẫn trả về lỗi hoặc không có 'items':", str(data)[:100])
                except Exception as e:
                    pass

        page.on("response", handle_response)

        try:
            await page.goto(search_url, wait_until="networkidle", timeout=30000)

            # Để thời gian chờ lâu một chút (10s)
            # để bạn có thời gian tự kéo slide/Captcha bằng tay nếu Shopee bắt xác minh
            print("⏳ Đang đợi 10 giây. NẾU CÓ CAPTCHA, HÃY TỰ GIẢI QUYẾT TRÊN TRÌNH DUYỆT...")
            await page.wait_for_timeout(10000)

        except Exception as e:
            print(f"❌ Lỗi khi tải trang: {e}")
        finally:
            # Đóng context để nó lưu toàn bộ Cookie và Session vào thư mục shopee_agent_profile
            await context.close()

    # In kết quả
    if extracted_data:
        print("\n🎉 --- BÓC TÁCH THÀNH CÔNG --- 🎉\n")
        for i, item in enumerate(extracted_data):
            print(f"{i + 1}. {item['name']}")
            print(f"   💰 Giá: {item['price']:,.0f} đ | 📦 Bán: {item['sold']}")
            print("-" * 40)

    return extracted_data


if __name__ == "__main__":
    asyncio.run(intercept_shopee_api("áo khoác nam"))