import asyncio

from config.init_clients import tavily_client
from tools.extract.crawl4ai_extract_tools import extract_by_crawl4ai
from tools.extract.playwright_tools import extract_price_from_text, extract_with_js


async def extract(url: str):
    print(f"--- Đang trích xuất dữ liệu từ: {url} ---")

    try:
        response = tavily_client.extract(urls=[url])
        if response and response.get("results"):
            data = response["results"][0]
            raw_text = data.get("raw_content", "")

            # Kiểm tra có giá trong nội dung không
            price = extract_price_from_text(raw_text)

            if price:
                print(f"✅ Tavily lấy được giá: {price}")
                return {**data, "price": price, "source": "tavily"}
            else:
                print("⚠️ Tavily không có giá → fallback Crawl4Ai...")
    except Exception as e:
        print(f"❌ Lỗi khi gọi API: {str(e)}")

    result = await extract_by_crawl4ai(url)

    # print(
    #     f"{'✅' if 'price' in result else '❌'} Playwright: {result.get('price', result.get('error', 'Không tìm thấy giá'))}"
    #     f"{result}"
    # )
    return result


if __name__ == "__main__":
    target_url = "https://tokyolife.vn/nu-giay-the-thao-em-chan-40004372"
    asyncio.run(extract(target_url))