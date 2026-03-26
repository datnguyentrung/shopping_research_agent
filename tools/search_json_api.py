import os
import httpx
from dotenv import load_dotenv


# --------------------- ĐÃ NGỪNG CUNG CẤP ------------------- #
# ----- HÀM GỌI GOOGLE CUSTOM SEARCH API ----- #

def google_search(api_key, search_engine_id, query, **params):
    """Thực hiện tìm kiếm trên Google Custom Search API."""
    # Sửa lại base_url thành endpoint chuẩn trả về JSON
    base_url = "https://customsearch.googleapis.com/customsearch/v1"

    # Định nghĩa các tham số
    request_params = {
        'key': api_key,
        'cx': search_engine_id,
        'q': query,
        **params
    }

    # Gọi API
    response = httpx.get(base_url, params=request_params)

    # Bắt lỗi nếu request thất bại (VD: sai key, hết quota, 403, 400...)
    response.raise_for_status()

    return response.json()


if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("CUSTOM_SEARCH_JSON_API_KEY")
    search_engine_id = os.getenv("CUSTOM_SEARCH_ENGINE_ID")

    print("Đã load biến môi trường:")
    print(f"CUSTOM_SEARCH_JSON_API_KEY: {api_key if api_key else 'Not Loaded'}")
    print(f"CUSTOM_SEARCH_ENGINE_ID: {search_engine_id if search_engine_id else 'Not Loaded'}")

    # # Kiểm tra xem biến môi trường đã load thành công chưa
    # if not api_key or not search_engine_id:
    #     print("Lỗi: Chưa lấy được API Key hoặc Search Engine ID từ file .env")
    #     exit(1)
    #
    # query = "áo khoác"
    #
    # try:
    #     results = google_search(api_key, search_engine_id, query)
    #     print("Gọi API thành công!")
    #     # In thử tiêu đề của kết quả đầu tiên để test
    #     if 'items' in results:
    #         print(f"Kết quả đầu tiên: {results['items'][0]['title']}")
    #         print(f"Link: {results['items'][0]['link']}")
    #     else:
    #         print("Không tìm thấy kết quả nào.")
    #
    # except httpx.HTTPStatusError as exc:
    #     print(f"Lỗi HTTP {exc.response.status_code}: {exc.response.text}")
    # except Exception as e:
    #     print(f"Lỗi hệ thống: {e}")