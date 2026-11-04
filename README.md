# TH-GoT — Game Of Thiên độc lập

18 trò chơi và thư viện học tập miễn phí. Một ứng dụng Flask tự chứa trang giới thiệu, đăng nhập Google, mở phiên và giao diện chơi. Không gọi API, tài khoản, database hay hostname của portal cũ.

- **Bắt buộc đăng nhập Google để mở phiên.** Trẻ có thể dùng đường dẫn phiên do người lớn mở, không cần tài khoản riêng.
- Một phiên mở đủ **18 game**, thời lượng **10/20/30/40/50/60 phút**. Đổi game hay tải lại trang không tăng thời gian.
- Không có mua gói, kích hoạt, mở khóa, giấy phép hay chức năng trả phí.
- Database, khóa phiên và thumbnail được lưu trong volume `/data` của riêng ứng dụng.

## Chạy trên máy mới

Cần Docker Engine và Docker Compose v2. GitHub/image chỉ chứa source, JSON cấu hình và file khóa tài nguyên; thư viện ảnh được tải từ Google Drive xuống thiết bị ở lần chạy đầu. Không cần Git LFS. Hỗ trợ Linux AMD64 và ARM64, bao gồm Raspberry Pi OS/Debian **64 bit**. Không tuyên bố hỗ trợ Pi ARMv6/ARM 32 bit.

```sh
git clone https://github.com/TuanPham0411/TH-GoT.git
cd TH-GoT
cp .env.example .env
# Điền Google OAuth và PUBLIC_URL; nguồn Drive mặc định đã được cấu hình.
docker compose up -d --build --wait --wait-timeout 1800
python3 tools/smoke.py
```

Mặc định phục vụ cổng 5082 trên localhost. Để mở trong LAN, đổi `BIND_ADDRESS=0.0.0.0`; Google OAuth và cookie production phải sử dụng hostname HTTPS. Không cần sửa JavaScript hoặc build lại để đổi hostname.

Nếu chưa cấu hình Google, trang giới thiệu và thư viện vẫn chạy; `/login` báo 503 và không mở phiên trái phép. Không có tài khoản mẫu hay cửa đăng nhập bỏ qua Google trong bản chạy.

## Google/Gmail và hostname mới

1. Tạo OAuth Client loại **Web application** trong Google Cloud Console.
2. Đặt `PUBLIC_URL=https://game.ten-mien-cua-ban.example` trong `.env`.
3. Thêm chính xác `https://game.ten-mien-cua-ban.example/auth/callback` vào **Authorized redirect URIs**, rồi điền `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.
4. Với phát triển tại máy cá nhân, Google cho phép callback `http://localhost:5082/auth/callback`. Địa chỉ IP LAN HTTP không thay thế cho hostname HTTPS trong production.
5. Nếu Google consent screen còn ở Testing, thêm tài khoản thử; chuyển sang Production theo yêu cầu Google để cho phép người dùng công khai.
6. Dùng một reverse proxy như nginx/Caddy/Cloudflare phía trước `127.0.0.1:5082`, bật `TRUST_PROXY=1` chỉ khi có đúng một proxy tin cậy. Tạo lại container sau khi sửa `.env`.

Dùng chung Google Cloud project với ứng dụng khác được, nhưng callback phải thuộc bản triển khai này. Không mang database, cookie hoặc khóa bí mật từ website cũ sang. Khóa ký cookie tự sinh một lần trong volume; cũng có thể cung cấp `FLASK_SECRET_KEY` cố định do bạn tạo và giữ riêng.

## Dùng image đã build

CI kiểm thử source rồi publish image không kèm thư viện ảnh cho AMD64/ARM64:

```sh
APP_IMAGE=ghcr.io/tuanpham0411/th-got:COMMIT_SHA docker compose pull
APP_IMAGE=ghcr.io/tuanpham0411/th-got:COMMIT_SHA docker compose up -d --no-build --wait --wait-timeout 1800
```

Dùng SHA đã kiểm thử thay cho `latest`. Kiểm tra quyền public của GHCR package; nếu package riêng tư thì đăng nhập registry hoặc build tại máy đích.

## Phát triển và kiểm thử

```sh
python3 -m venv .venv
.venv/bin/pip install -r game/requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m unittest discover -s game/tests -v
ASSET_DIR="$PWD/.assets/current" .venv/bin/python game/tools/audit_v88_complete.py
.venv/bin/python game/tools/audit_v89_ui.py
node --test game/tests-js/session-clock.test.cjs
```

Audit ảnh cần cài tài nguyên trước theo [hướng dẫn tài nguyên](docs/ASSETS.md); các test source/auth/asset-manager không cần Drive. CI chạy job integration mặc định với [gói Drive công khai](https://drive.google.com/file/d/1JsQk7-4mWJlmCJDd5TdDy9mnUnEm41U5/view?usp=sharing). Repository variable `TH_GOT_ASSETS_URL` chỉ là override tùy chọn; job tải/xác minh đủ ảnh, audit và smoke test. Build image không tải Drive.

Test Google dùng provider giả lập để xác minh state, nonce, PKCE, audience, issuer, email_verified và expiry; không cần, không chứa credential thật. Đăng nhập Google thật phải kiểm thử với client/callback đã đăng ký. Phần mềm được tách từ GOT, xem [nguồn gốc](docs/PROVENANCE.md).

## Dữ liệu và chuyển máy

Không commit `.env`, `/data`, database hoặc khóa phiên. Đọc [sao lưu và triển khai](docs/DEPLOY.md). Ảnh nằm trong volume `/assets` riêng, không ở Git hay image. Lần đầu tải gói từ Drive, kiểm tra SHA-256 và inventory, giải nén rồi mới chạy web; khởi động lại dùng cache mà không truy cập Drive. Cần giữ volume `assets` hoặc tải lại khi đổi thiết bị. Xem [đóng gói, tải lần đầu, cập nhật và triển khai offline](docs/ASSETS.md).
