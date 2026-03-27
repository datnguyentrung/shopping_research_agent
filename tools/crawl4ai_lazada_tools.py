import asyncio
import urllib.parse
from playwright.async_api import async_playwright
from playwright_stealth import stealth

async def research_lazada(keyword):
    print(f"🕵️‍♂️ Đang dùng chiến thuật 'Đột kích bộ nhớ' để tìm: '{keyword}' trên Lazada...")

    keyword_encoded = urllib.parse.quote(keyword)
    search_url = f"https://www.lazada.vn/catalog/?q={keyword_encoded}"

    extracted_data = []

    async with async_playwright() as p:
        # Launch browser với các tham số giảm thiểu bị chặn
        browser = await p.chromium.launch(headless=False)  # Để False để bạn xem nó chạy, xong việc thì đổi True

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )

        page = await context.new_page()
        # Kích hoạt chế độ tàng hình
        await stealth(page)

        try:
            # Truy cập Lazada
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

            # Đợi một chút để script của Lazada chạy xong
            await page.wait_for_timeout(5000)

            # --- CHIẾN THUẬT QUAN TRỌNG: Lấy dữ liệu từ window.pageData ---
            # Lazada giấu toàn bộ thông tin sản phẩm trong biến này
            page_data = await page.evaluate("() => window.pageData")

            if page_data and 'mods' in page_data:
                items = page_data.get('mods', {}).get('listItems', [])

                for i, item in enumerate(items[:5]):  # Lấy top 5
                    product = {
                        "index": i + 1,
                        "name": item.get('name'),
                        "price": item.get('priceShow'),  # Lazada để giá sẵn dạng chuỗi kèm đ
                        "location": item.get('location'),
                        "image_url": item.get('image'),
                        "rating": item.get('ratingScore'),
                        "shop_name": item.get('sellerName'),
                        "raw_json": item  # Lưu lại bản thô nếu cần
                    }
                    extracted_data.append(product)
            else:
                # Nếu không tìm thấy pageData, có thể bị dính Captcha
                print("⚠️ Không tìm thấy biến pageData. Có thể Lazada đã chặn hoặc yêu cầu Captcha.")
                # Chụp ảnh màn hình để kiểm tra nếu chạy headless
                await page.screenshot(path="lazada_check.png")

        except Exception as e:
            print(f"❌ Lỗi: {e}")
        finally:
            await browser.close()

    # In kết quả đẹp mắt
    if extracted_data:
        print("\n🎉 --- KẾT QUẢ TỪ LAZADA --- 🎉\n")
        for item in extracted_data:
            print(f"{item['index']}. {item['name']}")
            print(f"   💰 Giá: {item['price']} | 📍 Giao từ: {item['location']}")
            print(f"   🏪 Shop: {item['shop_name']} | ⭐ Đánh giá: {item['rating']}")
            print(f"   🖼️ Link ảnh: {item['image_url']}")
            # print(f"   📄 JSON chi tiết: {json.dumps(item['raw_json'], indent=2, ensure_ascii=False)}")
            print("-" * 50)
    else:
        print("\n❌ Thất bại. Hãy kiểm tra file 'lazada_check.png' xem có bị dính thanh trượt Captcha không.")

    return extracted_data


if __name__ == "__main__":
    asyncio.run(research_lazada("áo khoác nam"))