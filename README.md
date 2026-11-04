# TH-GoT — Game Of Thiên

18 trò chơi và thư viện học tập miễn phí tại **https://got.th.io.vn**. Google login bắt buộc để mở phiên; mỗi phiên mở đủ 18 game trong 10/20/30/40/50/60 phút. Đổi game hoặc reload không kéo dài deadline. Không thanh toán, subscription hay unlock; không gọi backend hoặc tài khoản của website cũ.

## Ảnh chỉ nằm trên Google Drive

- GitHub và Docker image chứa source, JSON cấu hình ban đầu và inventory, không chứa ảnh hoặc gói ảnh.
- Máy chủ đọc ảnh từ Drive theo yêu cầu, xử lý thumbnail trong RAM và gửi `Cache-Control: no-store`. Không có volume ảnh, file thumbnail, archive tải xuống hay cache ảnh trên đĩa.
- Trình duyệt chỉ giữ dữ liệu cần để hiển thị trong phiên; app không ghi ảnh vào localStorage, IndexedDB, service worker hoặc Cache Storage.
- Quản trị viên thêm/sửa/xóa tại `/admin/resources`: ảnh và nội dung chỉnh sửa được ghi trực tiếp lên Drive. Xóa chuyển ảnh không còn được tài nguyên khác tham chiếu vào thùng rác Drive.
- Cần kết nối Drive khi chơi, kể cả sau khi restart. Không có chế độ chơi bằng bản sao ảnh offline.
- Volume `data` chỉ giữ tài khoản, phiên, khóa ký và refresh token Drive đã mã hóa; không giữ ảnh.

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

Tests Drive dùng provider giả lập để kiểm tra quyền quản trị, CSRF, consent/PKCE, mã hóa token, CRUD trên Drive, ảnh không spool xuống đĩa và migration trong RAM. CI không tải thư viện ảnh hoặc tạo release ảnh. Audit ảnh đầy đủ của bộ chuẩn đã được chạy trong pipeline trước khi chuyển kiến trúc; pipeline hiện tại không thay thế kiểm thử Drive thật sau khi cấp quyền.

Xem [tài nguyên Drive](docs/ASSETS.md), [triển khai/sao lưu](docs/DEPLOY.md) và [nguồn gốc](docs/PROVENANCE.md).
