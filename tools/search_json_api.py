import os
import logging
import json
import re
from typing import List
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def clean_url(url_candidate: str) -> str:
    """Lấy phần URL thuần túy, loại bỏ rác phía sau."""
    # 1. Chỉ lấy phần đầu tiên trước khoảng trắng hoặc dấu xuống dòng
    url = url_candidate.split()[0]

    # 2. Loại bỏ các ký tự bao quanh thường gặp trong Markdown hoặc text
    url = url.strip('()[]<>"\',;\\')

    # 3. Kiểm tra tính hợp lệ cơ bản
    parsed = urlparse(url)
    if parsed.scheme in ('http', 'https') and parsed.netloc:
        return url
    return ""


def parse_product_links(text: str, base_url: str) -> List[str]:
    # Tìm tất cả chuỗi bắt đầu bằng http hoặc /san-pham/
    # Regex này lấy rộng, sau đó sẽ dùng clean_url để bóc tách lại
    potential_urls = re.findall(r'(https?://[^\s"\'<>\]\)]+|/[a-zA-Z0-9\-/]+\.htm)', text)

    product_indicators = ['/p/', '/product/', 'spid=', 'item/', '-p-', '.html', '/san-pham/']
    # Loại bỏ các trang danh mục quá ngắn hoặc chứa từ khóa lọc
    exclude_indicators = ['/category/', '/danh-muc/', '?s=', 'search', 'filter=', 'sort=', 'ban-do', 'chinh-sach']

    final_links = []
    parsed_base = urlparse(base_url)
    domain_root = f"{parsed_base.scheme}://{parsed_base.netloc}"

    for raw_link in potential_urls:
        # Xử lý link tương đối trước khi clean
        if raw_link.startswith('/'):
            full_url_candidate = urljoin(domain_root, raw_link)
        else:
            full_url_candidate = raw_link

        # Làm sạch URL (Chặn đứng lỗi 'Đạp Xe', 'Ô Tô' dính đuôi)
        url = clean_url(full_url_candidate)

        if url:
            url_lower = url.lower()
            # Kiểm tra xem có phải link sản phẩm không
            if any(ind in url_lower for ind in product_indicators):
                if not any(ex in url_lower for ex in exclude_indicators):
                    # Đảm bảo cùng domain để tránh link rác/quảng cáo
                    if urlparse(url).netloc == parsed_base.netloc:
                        final_links.append(url)

    return list(set(final_links))


def deep_search_and_extract_products(keyword: str, max_pages: int = 3):
    try:
        logger.info(f"Đang tìm kiếm nguồn cho: {keyword}")
        # Đổi query để tìm trực tiếp trang sản phẩm hơn là trang danh mục
        search_response = tavily_client.search(
            query=f"chi tiết sản phẩm {keyword}",
            search_depth="advanced",
            include_raw_content=True,
            max_results=max_pages
        )

        all_candidate_urls = []
        for result in search_response.get("results", []):
            links = parse_product_links(result.get("raw_content", ""), result.get("url"))
            all_candidate_urls.extend(links)

        # Lấy 5 link duy nhất
        final_urls = list(set(all_candidate_urls))[:5]

        if not final_urls:
            return {"error": "Không tìm thấy link sản phẩm hợp lệ."}

        logger.info(f"Gửi đi {len(final_urls)} URL sạch: {final_urls}")

        # Bước cuối: Extract
        return tavily_client.extract(urls=final_urls)

    except Exception as e:
        logger.error(f"Lỗi hệ thống: {str(e)}")
        return {"error": str(e)}


if __name__ == "__main__":
    keyword = "áo khoác gió nam chống nước"
    results = deep_search_and_extract_products(keyword)

    if "results" in results:
        print(f"\n✅ TRÍCH XUẤT THÀNH CÔNG {len(results['results'])} SẢN PHẨM")
        for item in results["results"]:
            print(f"- {item.get('title')[:60]}... \n  Link: {item.get('url')}\n")
    else:
        print(json.dumps(results, indent=2, ensure_ascii=False))