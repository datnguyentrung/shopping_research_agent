import os
import json
from dotenv import load_dotenv
from tavily import TavilyClient

# 1. Load API Key
load_dotenv()
api_key = os.getenv("TAVILY_API_KEY")

if not api_key:
    print("❌ Lỗi: Chưa tìm thấy TAVILY_API_KEY trong file .env")
    exit()

tavily_client = TavilyClient(api_key=api_key)


def extract(url: str):
    print(f"--- Đang trích xuất dữ liệu từ: {url} ---")

    try:
        # Gọi API Extract của Tavily
        # Chế độ mặc định của extract sẽ trả về nội dung dưới dạng Markdown rất sạch
        response = tavily_client.extract(urls=[url])

        # Kiểm tra nếu có kết quả
        if response and response.get("results"):
            data = response["results"][0]

            # In ra cấu trúc JSON để bạn quan sát các trường thông tin
            print("\n✅ KẾT QUẢ TRẢ VỀ (DẠNG JSON):")
            print(json.dumps(data, indent=4, ensure_ascii=False))

            # In riêng phần Raw Content để bạn xem độ chi tiết của mô tả sản phẩm
            print("\n" + "=" * 50)
            print("📄 NỘI DUNG CHI TIẾT (RAW CONTENT - MARKDOWN):")
            print("=" * 50)
            print(data.get("raw_content", "Không có nội dung thô"))

        else:
            print("❌ Không lấy được dữ liệu. Có thể URL bị chặn hoặc không tồn tại.")

    except Exception as e:
        print(f"❌ Lỗi khi gọi API: {str(e)}")


if __name__ == "__main__":
    target_url = "https://wetrek.vn/san-pham/ao-khoac-gio-da-ngoai-gothiar-windshell-jacket-2-lop-cam.htm"
    extract(target_url)