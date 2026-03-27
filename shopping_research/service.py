import asyncio
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

from tools.extract.tavily_extract import extract

# Tool nội bộ
from tools.search_and_extract.tiki_tools import fetch_tiki_direct
from tools.search_and_extract.playwright_shopee_tool import intercept_shopee_api
from tools.search.tavily_tools import deep_search_and_extract_products

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _resolve_instruction_file(file_name: str) -> Path:
    """Resolve instruction files regardless of current working directory."""
    module_dir = Path(__file__).resolve().parent
    project_root = module_dir.parent

    candidates = [
        project_root / "instruction" / file_name,
        Path.cwd() / "instruction" / file_name,
    ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(
        f"Instruction file '{file_name}' not found. Checked: {', '.join(str(p) for p in candidates)}"
    )


# ==========================================
# 1. QUẢN LÝ TRẠNG THÁI TOÀN CỤC (GLOBAL STATE)
# ==========================================
class AppState:
    def __init__(self):
        self.big_data = []  # Chứa các sản phẩm đã cào thành công
        self.filter_map = {}  # dict: map<thuộc tính> = [giá trị]
        self.whitelist = set()
        self.blacklist = set()
        self.is_extracting = True  # Cờ báo hiệu quá trình cào nền còn chạy không
        self.ui_phase_1_done = False  # Cờ báo hiệu người dùng đã chọn xong filter sơ bộ chưa


state = AppState()


# ==========================================
# 2. CÁC HÀM CÀO DỮ LIỆU NỀN (BACKGROUND WORKERS)
# ==========================================

async def worker_fast_apis(keyword: str):
    """Worker này chạy cực nhanh, lấy data từ Shopee/Tiki ném ngay vào big_data"""
    logger.info("[WORKER] Đang chạy API siêu tốc (Tiki/Shopee)...")

    loop = asyncio.get_running_loop()

    # 1. Ném cả 2 hàm vào ThreadPool để nó chạy nền NGAY LẬP TỨC
    task_tiki = loop.run_in_executor(None, fetch_tiki_direct, keyword, 20)

    # 2. Shopee của bạn ĐÃ LÀ hàm async -> Gọi thẳng
    task_shopee = intercept_shopee_api(keyword)

    # 3. GATHER: Chạy đua song song cả 2 sàn!
    # return_exceptions=True giúp hệ thống KHÔNG BỊ SẬP nếu 1 trong 2 trang web bị lỗi mạng
    results = await asyncio.gather(task_tiki, task_shopee, return_exceptions=True)

    tiki_data = results[0]
    shopee_data = results[1]

    # 4. Kiểm tra và bơm data vào kho chứa (State)
    if isinstance(shopee_data, list):
        logger.info(f"[WORKER] Nhận được {len(shopee_data)} sản phẩm từ Shopee.")
        for item in shopee_data:
            add_to_big_data_if_valid(item)
    else:
        logger.error(f"[WORKER] Lỗi luồng Shopee: {shopee_data}")

    if isinstance(tiki_data, list):
        logger.info(f"[WORKER] Nhận được {len(tiki_data)} sản phẩm từ Tiki.")
        for item in tiki_data:
            add_to_big_data_if_valid(item)
    else:
        logger.error(f"[WORKER] Lỗi luồng Tiki: {tiki_data}")

    logger.info(f"[WORKER] Đã gom xong! Hiện kho big_data đang có {len(state.big_data)} sản phẩm hợp lệ.")


async def process_and_save_background(url: str):
    try:
        result = await extract(url)
        if not result or "error" in result: return

        prod_to_save = None

        # Phương án 1: Bóc theo JSON cấu trúc (dành cho TokyoLife)
        if "tokyolife.vn" in url:
            detail = result.get('props', {}).get('pageProps', {}).get('data', {}).get('productDetail', {})
            if detail:
                prod_to_save = {
                    "name": detail.get("name"),
                    "price_current": detail.get("price"),
                    "main_image": detail.get("image_link"),
                    "url": url,
                    "key_features": {"Nguồn": "TokyoLife"}
                }

        # Phương án 2: Fallback dùng Metadata (Dành cho Tiki, Lazada và các trang khác)
        if not prod_to_save:
            # result lúc này là giá trị trả về từ hàm extract_by_crawl4ai
            # Nếu hàm extract_by_crawl4ai của bạn chỉ return json_data, hãy sửa nó
            # để return toàn bộ result object hoặc ít nhất là kèm metadata.

            # Giả sử ta lấy từ Metadata mà Crawl4AI đã trích xuất sẵn:
            meta = result.get('metadata', {})
            price = result.get('price')  # Giá bóc bằng regex trong hàm extract() của bạn

            if meta.get('og:title') and price:
                prod_to_save = {
                    "name": meta.get('og:title'),
                    "price_current": price,
                    "main_image": meta.get('og:image'),
                    "url": url,
                    "key_features": {"Nguồn": "Generic Crawl"}
                }

        if prod_to_save and prod_to_save.get("price_current"):
            add_to_big_data_if_valid(prod_to_save)
            logger.info(f"✅ [CRAWL4AI] Đã thêm: {prod_to_save['name']}")

    except Exception as e:
        logger.error(f"💥 Lỗi luồng ngầm URL {url}: {e}")


async def worker_deep_crawl4ai(keyword: str):
    logger.info("[WORKER] Bắt đầu luồng Tavily + Crawl4AI (Chậm, sâu)...")

    # 1. Tìm link (giữ nguyên)
    loop = asyncio.get_running_loop()
    tavily_response = await loop.run_in_executor(None, deep_search_and_extract_products, keyword, 20)
    results_list = tavily_response.get("results", [])
    search_urls = [item.get("url") for item in results_list if item.get("url")]

    if not search_urls:
        logger.warning("[TAVILY] Không tìm thấy URL nào hợp lệ!")
        return

    # === CẢI TIẾN 1: DÙNG SEMAPHORE GIỚI HẠN 3 TRÌNH DUYỆT CÙNG LÚC ===
    sem = asyncio.Semaphore(3)  # Số 3 hoặc 5 tùy máy bạn khỏe hay yếu

    async def sem_task(url):
        async with sem:  # Chỉ khi nào có "vé" trống thì mới chạy
            return await process_and_save_background(url)

    logger.info(f"[TAVILY] Đã tìm thấy {len(search_urls)} URLs. Đang cào cuốn chiếu (3 links/lượt)...")

    # 2. Tạo danh sách task
    tasks = []
    for url in search_urls:
        if not state.is_extracting:
            break
        # Dùng hàm sem_task để kiểm soát lưu lượng
        tasks.append(asyncio.create_task(sem_task(url)))

    # 3. Đợi tất cả xong
    if tasks:
        await asyncio.gather(*tasks)

    # === CẢI TIẾN 2: SỬA LẠI LOG CHO ĐÚNG THỰC TẾ ===
    logger.info(f"✅ [CRAWL4AI] Đã hoàn thành bóc tách toàn bộ {len(tasks)} URLs vào Big Data.")

# ==========================================
# 3. LOGIC CẬP NHẬT TRẠNG THÁI VÀ BỘ LỌC
# ==========================================

def add_to_big_data_if_valid(product: dict):
    """Kiểm tra whitelist/blacklist trước khi nhét vào kho"""
    # 1. Kiểm tra tồn tại ảnh và giá
    if not product.get("price_current") or not product.get("main_image"):
        return

    # 2. Thuật toán Blacklist: Nếu tên chứa từ khóa blacklist -> Vứt
    product_str = json.dumps(product).lower()
    for bad_word in state.blacklist:
        if bad_word.lower() in product_str:
            return  # Bỏ qua sản phẩm này

    # 3. Thêm vào Big Data
    state.big_data.append(product)

    # 4. Cập nhật Filter Map (Map<biến> = []) để UI hiển thị cho User
    features = product.get("key_features", {})
    for key, value in features.items():
        if key not in state.filter_map:
            state.filter_map[key] = set()
        state.filter_map[key].add(value)


# ==========================================
# 4. ORCHESTRATOR & UI SIMULATION
# ==========================================

async def simulate_ui_interaction():
    """Giả lập luồng hoạt động của Frontend (React)"""

    # PHASE 1: Đợi cho đến khi big_data có ít nhất 15 sản phẩm
    timeout_counter = 0
    # Chờ gom đủ 15 sản phẩm, nhưng KHÔNG CHỜ QUÁ 15 GIÂY
    while len(state.big_data) < 15 and timeout_counter < 15:
        await asyncio.sleep(1)
        timeout_counter += 1

    if len(state.big_data) == 0:
        logger.error("[UI] Đã hết thời gian chờ nhưng không có data. Hủy luồng!")
        state.is_extracting = False
        return

    logger.info(f"[UI] Bắt đầu với {len(state.big_data)} sản phẩm. Kích hoạt Popup chọn Đặc điểm!")
    logger.info(f"[UI] Các đặc điểm hệ thống vừa gom được: {state.filter_map}")

    # Giả lập User thao tác mất 5 giây, trong lúc đó background cào vẫn chạy
    await asyncio.sleep(5)

    # Giả lập User đưa ra quyết định
    logger.info("[UI] User đã chọn xong đặc điểm!")
    state.whitelist.add("chống nước")
    state.blacklist.add("giá cao")
    state.ui_phase_1_done = True

    # PHASE 2: Bật giao diện Tinder Swipe
    logger.info("[UI] Đang hiển thị giao diện Quẹt thẻ (Tinder Swipe)...")

    # Lọc lại toàn bộ big_data hiện tại bằng Agent Logic (Sử dụng google.adk)
    # (Tại đây bạn sẽ gọi swipe_logic_agent với state.big_data, blacklist, whitelist)

    await asyncio.sleep(5)  # Giả lập user quẹt xong

    # PHASE 3: Dừng background và gọi Agent chốt sale
    # state.is_extracting = False  # Tắt worker
    logger.info("[UI] User đã chốt được 5 sản phẩm. Gọi Shopping Closer Agent viết báo cáo!")

    # (Gọi shopping_closer_agent ở đây)
    print("\n🎉 HOÀN THÀNH QUY TRÌNH!")


async def main_orchestrator(keyword: str):
    logger.info("=== KHỞI ĐỘNG SHOPPING RESEARCH AGENT ===")

    # Tạo các task chạy nền
    task_fast = asyncio.create_task(worker_fast_apis(keyword))
    task_slow = asyncio.create_task(worker_deep_crawl4ai(keyword))
    task_ui = asyncio.create_task(simulate_ui_interaction())

    # Đợi task UI hoàn thành là kết thúc phiên làm việc
    # await task_ui
    await asyncio.gather(task_fast, task_slow, task_ui)

    # IN KẾT QUẢ RA MÀN HÌNH SAU KHI CÀO XONG
    logger.info("==================================================")
    logger.info(f"🎉 TỔNG KẾT: Đã thu thập được {len(state.big_data)} sản phẩm vào Big Data")
    logger.info("==================================================")

    # In JSON đẹp mắt
    print(json.dumps(state.big_data, indent=2, ensure_ascii=False))

    # Dọn dẹp
    # task_fast.cancel()
    # task_slow.cancel()


if __name__ == "__main__":
    asyncio.run(main_orchestrator("áo khoác nam bomber"))