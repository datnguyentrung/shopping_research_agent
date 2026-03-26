# Cài đặt: pip install playwright && playwright install chromium
import re

from playwright.sync_api import sync_playwright

def extract_with_js(url: str) -> dict:
    """
    Extract nội dung từ bất kỳ trang web nào, kể cả JS-rendered.
    Dùng Playwright để chạy JS như trình duyệt thật.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="vi-VN",
        )

        try:
            # Chặn ảnh/font/media để tăng tốc
            page.route("**/*", lambda route: route.abort()
                if route.request.resource_type in ["image", "font", "media", "stylesheet"]
                else route.continue_()
            )

            page.goto(url, wait_until="domcontentloaded", timeout=20000)

            # Chờ giá xuất hiện — selector tổng quát cho nhiều web
            # Ưu tiên chờ các selector phổ biến chứa giá
            for selector in [
                "[class*='price']",
                "[class*='Price']",
                "[data-testid*='price']",
                "[itemprop='price']",
            ]:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    break  # Tìm thấy thì dừng
                except:
                    continue

            # Lấy toàn bộ text đã render
            full_text = page.inner_text("body")

            # Trích xuất giá bằng regex từ text đã render
            price = _extract_price_from_text(full_text)

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


def _extract_price_from_text(text: str) -> str | None:
    """
    Tìm giá sản phẩm từ text, bỏ qua giá trong các cụm không liên quan.
    """
    # Loại bỏ các dòng chứa context không phải giá sản phẩm
    NOISE_PATTERNS = [
        r'.{0,50}(miễn phí|free shipping|phí giao|vận chuyển|giao hàng|tối thiểu|trở lên|discount|giảm|coupon|voucher).{0,100}',
        r'.{0,50}(thanh toán|payment|order|đơn hàng).{0,100}',
    ]

    cleaned_text = text
    for noise in NOISE_PATTERNS:
        cleaned_text = re.sub(noise, '', cleaned_text, flags=re.IGNORECASE)

    # Tìm giá trong text đã làm sạch
    price_patterns = [
        # VND: 588.000 VNĐ / 588,000đ / 588.000 ₫
        r'[\d]{1,3}(?:[.,]\d{3})+\s*(?:VNĐ|VND|vnđ|đ|₫)',
        # USD
        r'(?:USD|\$)\s*[\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?',
    ]

    candidates = []
    for pattern in price_patterns:
        matches = re.findall(pattern, cleaned_text)
        candidates.extend(matches)

    if not candidates:
        return None

    # Ưu tiên giá lớn nhất (giá sản phẩm thường lớn hơn ngưỡng shipping)
    def parse_value(price_str: str) -> int:
        digits = re.sub(r'[^\d]', '', price_str)
        return int(digits) if digits else 0

    candidates.sort(key=parse_value, reverse=True)
    return candidates[0].strip()