import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from playwright.sync_api import sync_playwright

from utils.validate import extract_price_from_text


def extract_with_js(url: str) -> dict:
    """
    Extract nội dung từ bất kỳ trang web nào, kể cả JS-rendered.
    Dùng Playwright để chạy JS như trình duyệt thật.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            # Giả lập user agent để tránh bị chặn
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="vi-VN",
        )

        try:
            # Chặn ảnh/font/media để tăng tốc
            # page.route("**/*", lambda route: route.abort()
            #     if route.request.resource_type in ["image", "font", "media", "stylesheet"]
            #     else route.continue_()
            # )

            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            print("⏳ Đang đợi 5 giây để JS tải xong dữ liệu (giá, tên sản phẩm)...")
            # Chờ cứng hẳn 5 giây để chắc chắn các API trả về kết quả và render lên web
            page.wait_for_timeout(5000)

            # Lấy toàn bộ text đã render
            full_text = page.inner_text("body")

            # IN RA TERMINAL ĐỂ BẠN XEM:
            print("\n" + "=" * 50)
            print("👇 NỘI DUNG PLAYWRIGHT CÀO ĐƯỢC 👇")
            print("=" * 50)
            # In 2000 ký tự đầu tiên ra terminal
            print(full_text[:2000])
            print("=" * 50 + "\n")

            # Trích xuất giá bằng regex từ text đã render
            price = extract_price_from_text(full_text)

            # Lấy title
            title = page.title()

            return {
                "url": url,
                "title": title,
                "price": price,
                "raw_text": full_text[:3000],  # Giới hạn để không quá dài
            }

        except Exception as e:
            return {"url": url, "error": str(e)}

        finally:
            browser.close()