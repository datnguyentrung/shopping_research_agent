import os
import logging
import json
import re
import requests
from typing import List
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from dotenv import load_dotenv
from tavily import TavilyClient

from tools.playwright_tools import _extract_price_from_text, extract_with_js

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

ASSET_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".bmp",
    ".ico", ".mp4", ".webm", ".pdf", ".css", ".js", ".xml", ".json"
)
ASSET_PATH_HINTS = ("/cdn/", "/static/", "/assets/", "/files/")
PRODUCT_PATH_HINTS = ("/san-pham/", "/product/", "/products/", "/p/")
CATEGORY_PATH_HINTS = ("/collection", "/collections", "/danh-muc", "/category", "/search")

def get_uniqlo_price_via_api(product_url: str) -> dict:
    """
    UNIQLO VN có API nội bộ trả về giá dạng JSON.
    URL mẫu: /vn/vi/products/E483281-000/00?colorDisplayCode=12
    → product_id = E483281-000, priceGroup = 00
    """
    # Parse product_id và priceGroup từ URL
    match = re.search(r'/products/([A-Z0-9\-]+)/(\d+)', product_url)
    if not match:
        return {"error": "Không parse được product ID"}

    product_id, price_group = match.group(1), match.group(2)

    api_url = (
        f"https://www.uniqlo.com/vn/api/commerce/v5/vn/products"
        f"/{product_id}/price-groups/{price_group}/l2s"
        f"?includeModelSize=false&httpFailure=true"
    )

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": product_url,
    }

    try:
        resp = requests.get(api_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Cấu trúc thường là: data["result"]["l2s"][...]["prices"]["base"]["value"]
        prices = []
        for item in data.get("result", {}).get("l2s", []):
            price_info = item.get("prices", {})
            base_price = price_info.get("base", {}).get("value")
            promo_price = price_info.get("promo", {}).get("value")
            if base_price:
                prices.append({
                    "l2Id": item.get("l2Id"),
                    "base_price": base_price,
                    "promo_price": promo_price,
                })

        return {"product_id": product_id, "prices": prices}

    except Exception as e:
        return {"error": str(e)}

def clean_tracking_url(url: str) -> str:
    """Loại bỏ các tham số tracking quảng cáo (Google Ads, Facebook) để làm sạch URL."""
    if not isinstance(url, str) or not url.strip():
        return ""

    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # Danh sách các tham số quảng cáo cần loại bỏ
    # Đã bổ sung srsltid
    tracking_params = ['gclid', 'gad_source', 'gad_campaignid', 'gbraid', 'utm_source', 'utm_medium', 'utm_campaign',
                       'fbclid', 'srsltid']

    # Giữ lại các tham số không nằm trong blacklist
    clean_query = {k: v for k, v in query_params.items() if k not in tracking_params}

    new_query = urlencode(clean_query, doseq=True)
    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    return clean_url

def clean_url(url_candidate: str) -> str:
    """Lấy phần URL thuần túy, loại bỏ rác phía sau."""
    if not isinstance(url_candidate, str) or not url_candidate.strip():
        return ""

    url = url_candidate.split()[0]
    url = url.strip('()[]<>"\',;\\')
    parsed = urlparse(url)
    if parsed.scheme in ('http', 'https') and parsed.netloc:
        return url
    return ""


def _is_asset_url(url: str) -> bool:
    parsed = urlparse(url)
    path = (parsed.path or "").lower()
    if any(hint in path for hint in ASSET_PATH_HINTS):
        return True
    if any(path.endswith(ext) for ext in ASSET_EXTENSIONS):
        return True

    query_params = parse_qs(parsed.query)
    if any(key in query_params for key in ("width", "height", "format", "quality")):
        return True
    return False


def _score_url(url: str) -> int:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return -1

    if _is_asset_url(url):
        return -1

    path = (parsed.path or "").lower()
    query_params = parse_qs(parsed.query)

    score = 0
    if any(hint in path for hint in PRODUCT_PATH_HINTS):
        score += 5
    if path.endswith(".htm") or path.endswith(".html"):
        score += 2
    if any(hint in path for hint in CATEGORY_PATH_HINTS):
        score += 1
    if any(key in query_params for key in ("sku", "variant", "product_id")):
        score += 2

    # Tránh ưu tiên homepage/rỗng.
    if path in ("", "/"):
        score -= 2

    return score


def parse_product_links(text: str, base_url: str) -> List[str]:
    if not isinstance(text, str) or not text.strip():
        return []

    # Bắt URL tuyệt đối và URL tương đối có dấu hiệu là trang sản phẩm.
    potential_urls = re.findall(
        r'(https?://[^\s"\'<>\])]+|/(?:san-pham|product|products|p)/[a-zA-Z0-9\-/_\.%]+)',
        text,
        flags=re.IGNORECASE,
    )

    final_links = []
    seen = set()
    parsed_base = urlparse(base_url if isinstance(base_url, str) else "")
    domain_root = f"{parsed_base.scheme}://{parsed_base.netloc}" if parsed_base.netloc else ""

    for raw_link in potential_urls:
        if raw_link.startswith('/') and domain_root:
            full_url_candidate = urljoin(domain_root, raw_link)
        else:
            full_url_candidate = raw_link

        # Bước 1: Cắt bỏ ký tự rác Markdown
        url = clean_url(full_url_candidate)

        if not url:
            continue

        # Bước 2: Rửa sạch tham số tracking quảng cáo
        clean_url_final = clean_tracking_url(url)

        # Bước 3: Đảm bảo cùng domain (tránh link ra ngoài Facebook, Youtube, v.v.)
        # Nếu không có base domain hợp lệ thì không lọc theo domain.
        same_domain = (not parsed_base.netloc) or (urlparse(clean_url_final).netloc == parsed_base.netloc)
        if same_domain and clean_url_final not in seen and _score_url(clean_url_final) >= 1:
            seen.add(clean_url_final)
            final_links.append(clean_url_final)

    return final_links


def deep_search_and_extract_products(keyword: str, max_pages: int = 3):
    try:
        logger.info(f"Đang tìm kiếm nguồn cho: {keyword}")
        # Đổi query để tìm trực tiếp trang sản phẩm hơn là trang danh mục
        search_response = tavily_client.search(
            query=f"mua {keyword} chính hãng giá",
            search_depth="advanced",
            include_raw_content=True,
            max_results=max_pages
        )

        primary_urls = []
        secondary_urls = []

        results = search_response.get("results") if isinstance(search_response, dict) else []
        if not isinstance(results, list):
            results = []

        for result in results:
            if not isinstance(result, dict):
                continue

            main_url = result.get("url") or ""
            if main_url:
                clean_main_url = clean_tracking_url(main_url)
                if _score_url(clean_main_url) >= 0:
                    primary_urls.append(clean_main_url)

            # Vẫn cào thêm link bên trong, nhưng xếp vào nhóm ưu tiên thấp
            links = parse_product_links(result.get("raw_content") or "", main_url)
            secondary_urls.extend(links)

        all_candidate_urls = primary_urls + secondary_urls

        # Lọc trùng theo thứ tự xuất hiện, sau đó xếp hạng để ưu tiên trang giống sản phẩm.
        seen = set()
        scored_candidates = []
        for idx, u in enumerate(all_candidate_urls):
            if not u or u in seen:
                continue
            seen.add(u)

            score = _score_url(u)
            if score < 0:
                continue
            scored_candidates.append((score, idx, u))

        scored_candidates.sort(key=lambda x: (-x[0], x[1]))
        final_urls = [url for _, __, url in scored_candidates[:20]] # Giới hạn tối đa 20 URL để tránh quá tải

        if not final_urls:
            return {"error": "Không tìm thấy link sản phẩm hợp lệ."}

        logger.info(f"Gửi đi {len(final_urls)} URL sạch: {final_urls}")

        results = []
        batch_size = 20  # Chia thành từng lô tối đa 20 URLs

        for i in range(0, len(final_urls), batch_size):
            batch_urls = final_urls[i:i + batch_size]
            try:
                logger.info(f"Đang extract lô từ {i} đến {i + len(batch_urls)}...")
                extracted = tavily_client.extract(urls=batch_urls)

                # Tùy thuộc vào cấu trúc trả về của Tavily, thường nó là 1 dict có list results bên trong
                # Bạn có thể append nguyên cụm hoặc dùng extend để gom chung thành 1 list phẳng
                results.extend(extracted.get("results", []) if isinstance(extracted, dict) else [])
            except Exception as e:
                logger.error(f"Lỗi khi extract lô URL: {e}")

        return {"results": results}  # ← Luôn trả về dict

    except Exception as e:
        logger.error(f"Lỗi hệ thống: {str(e)}")
        return {"error": str(e)}

def extract(url: str):
    print(f"--- Đang trích xuất dữ liệu từ: {url} ---")

    try:
        response = tavily_client.extract(urls=[url])
        if response and response.get("results"):
            data = response["results"][0]
            raw_text = data.get("raw_content", "")

            # Kiểm tra có giá trong nội dung không
            price = _extract_price_from_text(raw_text)

            if price:
                print(f"✅ Tavily lấy được giá: {price}")
                return {**data, "price": price, "source": "tavily"}
            else:
                print("⚠️ Tavily không có giá → fallback Playwright...")
    except Exception as e:
        print(f"❌ Lỗi khi gọi API: {str(e)}")

    result = extract_with_js(url)
    result["source"] = "playwright"

    print(
        f"{'✅' if 'price' in result else '❌'} Playwright: {result.get('price', result.get('error', 'Không tìm thấy giá'))}")
    return result

# def tavily_search_and_extract(keyword: str):
#     search_results = deep_search_and_extract_products(keyword)
#
#     if "results" in search_results:
#         print(f"\n✅ TRÍCH XUẤT THÀNH CÔNG {len(search_results['results'])} SẢN PHẨM")
#         for item in search_results["results"]:
#             if not isinstance(item, dict):
#                 continue
#             title = str(item.get("title") or "Không có tiêu đề")
#             link = str(item.get("url") or "")
#             print(f"- {title[:60]}... \n  Link: {link}\n")
#     else:
#         print(json.dumps(search_results, indent=2, ensure_ascii=False))

# if __name__ == "__main__":
#     keyword = "áo khoác nữ"
#     results = deep_search_and_extract_products(keyword)
#
#     if "results" in results:
#         print(f"\n✅ TRÍCH XUẤT THÀNH CÔNG {len(results['results'])} SẢN PHẨM")
#         for item in results["results"]:
#             if not isinstance(item, dict):
#                 continue
#             title = str(item.get("title") or "Không có tiêu đề")
#             link = str(item.get("url") or "")
#             print(f"- {title[:60]}... \n  Link: {link}\n")
#     else:
#         print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    target_url = "https://tiki.vn/ta-quan-cao-cap-moony-nhat-ban-be-gai-l44-44-mieng-p412767.html?spid=115706"
    extract(target_url)