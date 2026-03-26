import requests
from urllib.parse import quote  # Import thêm thư viện này
import os
from dotenv import load_dotenv

def crawl_shopee_direct(keyword,  cookie, token, total_needed=30,):
    url = "https://shopee.vn/api/v4/search/search_items"

    # URL-encode từ khóa để đưa vào Referer an toàn
    encoded_keyword = quote(keyword)

    params = {
        "by": "relevancy",
        "keyword": keyword,  # requests sẽ tự xử lý encoding cho params nên không cần quote ở đây
        "limit": total_needed,
        "newest": 0,
        "order": "desc",
        "page_type": "search",
        "scenario": "PAGE_GLOBAL_SEARCH",
        "version": "2"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        # Sử dụng encoded_keyword ở đây để tránh lỗi Latin-1
        "Referer": f"https://shopee.vn/search?keyword={encoded_keyword}",
        "x-api-source": "pc",
        "x-shopee-language": "vi",
        "Cookie": cookie,
        "af-ac-enc-dat": token
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            json_data = response.json()
            items = json_data.get('items', [])

            if not items:
                print("Không có dữ liệu trả về. Token hoặc Cookie có thể đã hết hạn.")
                return

            for index, item in enumerate(items):
                info = item.get('item_basic')
                if info:
                    name = info.get('name')
                    price = info.get('price') / 100000
                    print(f"[{index + 1}] {name} - Giá: {price:,.0f}đ")
        else:
            print(f"Lỗi {response.status_code}: Có thể bạn đã bị chặn hoặc Header/Cookie sai.")

    except Exception as e:
        print(f"Phát sinh lỗi: {e}")


if __name__ == "__main__":
    load_dotenv()
    # Lấy cookie và token từ biến môi trường
    cookie = os.getenv("SHOPEE_COOKIE")
    token = os.getenv("SHOPEE_TOKEN")
    crawl_shopee_direct("laptop giá rẻ", cookie, token)