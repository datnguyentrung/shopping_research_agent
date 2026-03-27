import asyncio
import json

from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# 1. Đổi thành hàm đồng bộ bình thường (bỏ async)
def get_crawl4ai_config():
    browser_config = BrowserConfig(
        headless=True,
        light_mode=True, # Chỉ tải HTML, bỏ qua CSS/JS để tăng tốc độ và giảm tài nguyên, phù hợp với mục đích chỉ lấy dữ liệu JSON trong __NEXT_DATA__
        verbose=False # Tắt log chi tiết của crawl4ai để terminal gọn hơn, chỉ in kết quả cuối thôi
    )

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        magic=True,
        wait_for="js:() => document.readyState === 'complete'",
        page_timeout=20000
    )

    return browser_config, run_config


async def extract_by_crawl4ai(target_url: str):
    print(f"🚀 Khởi động cào dữ liệu: {target_url}")

    # Lấy cấu hình từ hàm đồng bộ
    browser_config, run_config = get_crawl4ai_config()

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=target_url, config=run_config)

        if not result.success:
            return {"error": result.error_message}

        raw_html = result.html

        soup = BeautifulSoup(raw_html, "html.parser")
        next_data_script = soup.find("script", id="__NEXT_DATA__", type="application/json")
        if not next_data_script:
            return {"error": "Không tìm thấy script __NEXT_DATA__ trong HTML"}

        try:
            next_data_json = json.loads(next_data_script.string)
            return next_data_json
        except Exception as e:
            return {"error": f"Lỗi parse JSON từ __NEXT_DATA__: {e}", "raw": next_data_script.string}

        # # Dữ liệu JSON đẹp như mơ nằm ở đây
        # extracted_json = result.extracted_content
        #
        # try:
        #     # Parse chuỗi JSON trả về thành list object Python
        #     data = json.loads(extracted_json)
        #     return data
        # except Exception as e:
        #     return {"error": f"Lỗi parse JSON từ LLM: {e}", "raw": extracted_json}


if __name__ == "__main__":
    target_url = "https://tokyolife.vn/nu-giay-the-thao-em-chan-40004372"

    # Chạy duy nhất 1 Event Loop ở ngoài cùng
    result_data = asyncio.run(extract_by_crawl4ai(target_url))

    # In ra JSON đẹp
    print("\n✅ KẾT QUẢ CUỐI CÙNG:\n")
    # print(json.dumps(result_data, indent=2, ensure_ascii=False))
    print(result_data)