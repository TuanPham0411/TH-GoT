# TH-GoT — Game Of Thiên

18 trò chơi và thư viện học tập miễn phí tại **https://got.th.io.vn**. Google login bắt buộc để mở phiên; mỗi phiên mở đủ 18 game trong 10/20/30/40/50/60 phút. Đổi game hoặc reload không kéo dài deadline. Không thanh toán, subscription hay unlock; không gọi backend hoặc tài khoản của website cũ.

## Học từ mẫu giáo đến tiểu học

Bốn nhóm gợi ý: mẫu giáo 3–5 tuổi, lớp 1–2, lớp 3, lớp 4–5. Người lớn chọn nhóm và thời lượng; nhóm tuổi định hướng độ khó, số đáp án, số cặp thẻ và phạm vi số. Cả 18 trò vẫn có sẵn. Mỗi trò có mục tiêu, ba bước chơi, thao tác và gợi ý đồng hành trong `game/education.json`. Đây là hoạt động bổ trợ; người lớn chọn theo mức sẵn sàng thực tế của trẻ.

Phiên mặc định 10 phút, có tổng kết số lượt trong trang đang mở, không xếp hạng trẻ hay thu thập hồ sơ trẻ. Đồng hồ máy chủ vẫn giữ deadline khi đổi trò hoặc tải lại. Trang hướng dẫn mở công khai. Bàn phím, màn hình cảm ứng, tắt âm và giảm chuyển động được hỗ trợ; giọng đọc tùy khả năng thiết bị.

## Ảnh gốc trên Drive, bản hiển thị nhanh trên Pi

- GitHub và Docker image chứa source, JSON cấu hình ban đầu và inventory; không chứa ảnh hoặc gói ảnh.
- Drive là nguồn gốc. App lập ánh xạ bằng logical path, ID, phiên bản và checksum. Quản trị thêm/sửa/xóa tại `/admin/resources` ghi trực tiếp lên Drive.
- `/data/display-cache` giữ **bản hiển thị có thể tạo lại**, mặc định giới hạn 256 MiB, thu hồi theo lần dùng gần nhất. Thumbnail WebP tối đa 480 × 360; ảnh lớn tối đa 1280 × 1280. Bản gốc chỉ được xử lý trong RAM, không lưu gói 1,6 GB xuống Pi.
- Ánh xạ kiểm tra lại mỗi 60 giây khi có yêu cầu. Thay đổi qua quản trị app vô hiệu hóa ánh xạ ngay; đổi nội dung/phiên bản trên Drive tạo khóa cache mới. File chưa có trên Drive trả 404, không hiển thị bản đã xóa khi lần kiểm tra tiếp theo phát hiện xóa.
- Ảnh có ETag và `public, max-age=0, must-revalidate`; trình duyệt xác thực trước khi dùng lại. App không có service worker, IndexedDB hoặc localStorage ảnh. Đường dẫn ảnh là công khai qua app; OAuth token không gửi cho trình duyệt.
- Khi lỗi mạng/quota ngắn hạn, chỉ bản đã xác minh có thể tiếp tục hiển thị tối đa một giờ kể từ lần kiểm tra Drive thành công. Không tạo bản mới từ metadata cũ. Lỗi mất quyền/401/403 xác định sẽ đóng truy cập; `/readyz` vẫn yêu cầu kết nối Drive mới, không coi cache là Drive sẵn sàng.
- Volume `data` giữ tài khoản, phiên, khóa ký, token mã hóa và cache dẫn xuất. Cache có thể bỏ khỏi backup và tạo lại. `MEDIA_CACHE_MAX_BYTES` chỉnh dung lượng; `MEDIA_CACHE_ENABLED=0` dùng bộ đọc tương thích cũ chỉ trong RAM.

## Triển khai AMD64 / ARM64 / Raspberry Pi OS 64 bit

Cần Docker Engine và Compose v2. Không cần Git LFS hoặc source ESP32.

```sh
git clone https://github.com/TuanPham0411/TH-GoT.git
cd TH-GoT
# Chỉ copy nếu chưa có .env; không ghi đè cấu hình hiện tại.
test -e .env || cp .env.example .env
# Điền OAuth và ADMIN_EMAILS; PUBLIC_URL mặc định là https://got.th.io.vn.
docker compose up -d --build --wait --wait-timeout 180
python3 tools/smoke.py
```

Docker bind localhost cổng 5082. Đặt reverse proxy HTTPS cho `got.th.io.vn`, bật `TRUST_PROXY=1` khi có đúng một proxy tin cậy. Có thể dùng image `ghcr.io/tuanpham0411/th-got:COMMIT_SHA` qua `APP_IMAGE`; CI build cả `linux/amd64` và `linux/arm64`. Không tuyên bố hỗ trợ ARMv6/ARM 32 bit.

`/healthz` kiểm tra web/database để có thể cấu hình Drive sau khi khởi động; **không chứng minh ảnh đã sẵn sàng**. `/readyz` kiểm tra tài nguyên Drive sau khi chuyển dữ liệu. Dùng `python3 tools/smoke.py --media` để kiểm tra thêm ảnh thật, thumbnail và readiness.

## Google login và quyền quản trị Drive

1. Bật Google Drive API trong Google Cloud project của bạn. Tạo OAuth Client loại **Web application**.
2. Đăng ký hai redirect URI chính xác:
   - `https://got.th.io.vn/auth/callback` — đăng nhập người chơi.
   - `https://got.th.io.vn/admin/drive/callback` — cấp quyền Drive cho quản trị viên.
3. Điền `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ADMIN_EMAILS` và `DRIVE_FOLDER_ID` trong cấu hình riêng; không commit credentials.
4. Người chơi chỉ xin `openid email profile`. Quản trị viên đăng nhập rồi mở `/admin/resources`, bấm **Kết nối Google Drive** và đồng ý quyền Drive bằng chính tài khoản đó. Tài khoản phải có quyền chỉnh sửa thư mục đã cấu hình.
5. Bấm **Chuyển bộ ảnh có sẵn thành tài nguyên Drive** một lần. App xác minh gói chuẩn trên Drive, đọc từng ảnh trong RAM và upload từng tệp vào Drive; không lưu gói hay ảnh trên máy chủ. Nội dung JSON được khởi tạo trên Drive. Theo dõi tiến độ ngay trên trang quản trị.
6. Khi hoàn tất, chạy smoke test `--media`. Các thao tác thêm/sửa/xóa từ app sẽ tác động tới dữ liệu Drive đang được sử dụng.

Nếu chưa cấu hình OAuth, web vẫn khởi động và `/login` báo 503; không có đăng nhập giả. Nếu chưa cấp quyền Drive hoặc chuyển dữ liệu, ảnh chưa hoạt động. Không được coi các kiểm thử provider giả lập là đã xác minh OAuth/Drive thật.

Quyền Drive dùng scope `https://www.googleapis.com/auth/drive` để quản lý tệp sẵn có trong thư mục. API của app chỉ thao tác thư mục được cấu hình. Cấu hình consent screen và xác minh ứng dụng theo yêu cầu Google. Ở chế độ Testing, thêm tài khoản quản trị làm test user; refresh token có thể hết hạn sau 7 ngày, cần kết nối lại. Không dùng service account không có storage quota để thay thế chủ sở hữu My Drive.

## Phát triển và kiểm thử

```sh
python3 -m venv .venv
.venv/bin/pip install -r game/requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m unittest discover -s game/tests -v
.venv/bin/python game/tools/audit_v89_ui.py
node --test game/tests-js/session-clock.test.cjs
```

Tests Drive dùng provider giả lập để kiểm tra quyền quản trị, CSRF, consent/PKCE, mã hóa token, CRUD trên Drive, cache có phiên bản/ETag, cập nhật/xóa/mất quyền, và migration trong RAM. CI không tải thư viện ảnh hoặc tạo release ảnh. Audit ảnh đầy đủ của bộ chuẩn đã được chạy trong pipeline trước khi chuyển kiến trúc; pipeline hiện tại không thay thế kiểm thử Drive thật sau khi cấp quyền.

Xem [tài nguyên Drive](docs/ASSETS.md), [triển khai/sao lưu](docs/DEPLOY.md) và [nguồn gốc](docs/PROVENANCE.md).
