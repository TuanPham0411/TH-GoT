# TH-GoT — Thế giới học tập của bé

**https://got.th.io.vn**: học, chơi, đọc truyện và sáng tạo từ mẫu giáo đến lớp 5.

- 48 hoạt động mới trong sáu lĩnh vực, cộng 18 trò kinh điển tại `/play`: toán, tiếng Việt, khoa học, ứng xử, tư duy và sáng tạo. Các cơ chế gồm chọn đáp án, xếp trình tự, robot theo lệnh, nhịp điệu, tranh đối xứng, nhật ký và cầu trên lưới. Đây là hoạt động bổ trợ, không phải chứng nhận hoàn thành chương trình phổ thông.
- Bốn nhóm tuổi điều chỉnh phạm vi số, số lựa chọn và nội dung gợi ý. Đồng hồ 10–60 phút được xác minh trên máy chủ và giữ nguyên khi chuyển vùng hoặc tải lại. Phiên thuộc về tài khoản đã đăng nhập; không dùng phiên của tài khoản khác.
- 16 bản kể ngắn, phỏng tác nhẹ nhàng từ truyện Việt Nam và tác phẩm gốc thuộc phạm vi công cộng; mỗi truyện bốn trang, có câu hỏi suy ngẫm. Không chép bản dịch hiện đại. Một số tình tiết/kết thúc được điều chỉnh và được giải thích trong lời kể; đây không phải bản văn nguyên tác.
- Minh họa dùng ảnh gốc sẵn có trên Drive, khung cảnh chuyển động có nút tắt và hỗ trợ giảm chuyển động. Giọng kể ưu tiên giọng Việt trên thiết bị, có giọng dự phòng trên máy chủ. Xưởng sáng tạo cho phép viết tiếp khung chuyện, vẽ, kể hoặc ghi chép; bản viết và tranh của trẻ không tự gửi lên máy chủ.
- Font Noto Sans tự lưu trữ, gồm đầy đủ chữ tiếng Việt, giấy phép OFL trong `game/static/fonts`. Trình duyệt tải WOFF2; bản TTF phục vụ kiểm tra đầy đủ glyph. Khung ảnh thư viện có kích thước độc lập với khối chữ.

## Quản trị sau đăng nhập

Tài khoản thuộc `ADMIN_EMAILS` mở `/parents`:

1. **Kết nối & AI**: cấu hình OpenAI hoặc Gemini riêng cho GoT. Key được mã hóa bằng khóa riêng của ứng dụng, không trả lại qua API và không gửi cho trẻ. Bật AI rồi bấm tạo bản nháp sẽ gọi nhà cung cấp và có thể phát sinh phí. Trẻ dùng các bài đã duyệt, không có chat AI tự do.
2. **Truyện & bài học**: tự viết hoặc nhờ AI soạn theo nhóm tuổi; sửa bằng biểu mẫu, kiểm tra kiến thức và sự phù hợp, lưu bản nháp rồi xác nhận duyệt. Bản nháp chỉ quản trị viên thấy. Xuất bản/gỡ cần Drive xác nhận trước khi cập nhật bản đang hiển thị. Có thể tiếp tục thêm nội dung, không khóa danh mục ở số lượng trò ban đầu.
3. **Kênh YouTube**: cấu hình YouTube Data API v3 key, thêm link `youtube.com/@handle` hoặc `/channel/UC…`, chọn nhóm tuổi, bật/tắt, sửa tên hay xóa kênh. Đồng bộ tối đa 50 video công khai mới nhất của từng kênh. Chỉ nhận video có ID kênh khớp, cho phép nhúng, không phát trực tiếp và không bị API đánh dấu giới hạn tuổi. Không coi bộ lọc API là đánh giá đầy đủ nội dung cho từng trẻ; quản trị viên chọn kênh phù hợp.

Khu xem chỉ nhận video trong danh sách phía máy chủ và đúng nhóm tuổi của phiên. Không có tìm kiếm/link tùy ý. Khung nhúng `youtube-nocookie` không nhận tương tác trực tiếp, không mở popup/điều hướng trang chính; dùng các nút của GoT. Dừng khi hết phiên, khi phát xong hoặc phát hiện ID video khác lựa chọn. Kiểm tra quyền lại mỗi 15 giây để áp dụng việc tắt/xóa kênh. **YouTube vẫn có thể hiển thị quảng cáo và nội dung từ dịch vụ của họ; GoT không thể cam kết toàn bộ khung hình thuộc kênh đã duyệt hoặc thay thế bộ lọc thiết bị/mạng.** Nếu cần loại bỏ hoàn toàn bên thứ ba, giữ khu video tắt và dùng tài nguyên tự quản trên Drive.

Tài khoản, cấu hình, khóa mã hóa, bản nháp và tiến trình tổng hợp nằm trong volume `/data` cần sao lưu riêng. Nội dung quản trị xuất bản được ghi thêm vào `world/published.json` trên Drive; bản SQLite được cập nhật sau khi Drive xác nhận. Bản vẽ/nhật ký của trẻ không được lưu phía máy chủ; chỉ có số lượt hoàn thành hoạt động theo tài khoản, không có bảng xếp hạng hay hồ sơ định danh riêng của trẻ. Giữ khóa phiên khi khôi phục backup để giải mã cấu hình hiện có.

## Ảnh gốc trên Drive, bản hiển thị nhanh trên Pi

- GitHub và Docker image chứa source, JSON cấu hình ban đầu và inventory; không chứa ảnh hoặc gói ảnh.
- Drive là nguồn gốc. App lập ánh xạ bằng logical path, ID, phiên bản và checksum. Quản trị thêm/sửa/xóa tại `/admin/resources` ghi trực tiếp lên Drive.
- `/data/display-cache` giữ **bản hiển thị có thể tạo lại**, mặc định giới hạn 256 MiB, thu hồi theo lần dùng gần nhất. Thumbnail WebP tối đa 480 × 360; ảnh lớn tối đa 1280 × 1280. Bản gốc chỉ được xử lý trong RAM, không lưu gói 1,6 GB xuống Pi.
- Ánh xạ kiểm tra lại mỗi 60 giây khi có yêu cầu. Thay đổi qua quản trị app vô hiệu hóa ánh xạ ngay; đổi nội dung/phiên bản trên Drive tạo khóa cache mới. File chưa có trên Drive trả 404, không hiển thị bản đã xóa khi lần kiểm tra tiếp theo phát hiện xóa.
- Ảnh có ETag và `private, no-cache, max-age=0, must-revalidate` và chỉ thị CDN `no-store`; trình duyệt xác thực trước khi dùng lại. App không có service worker, IndexedDB hoặc localStorage ảnh. Đường dẫn ảnh là công khai qua app; OAuth token không gửi cho trình duyệt.
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

### Miền Diệu Kỳ — illustrated realm

The child entrance is now a panoramic floating-island map with native touch/mouse panning,
keyboard movement, large landmark portals, a fox guide, a backpack for adult session controls,
and opt-in original WebAudio music. Reduced motion and muting are available at any time.
The library retains its existing Drive documents, bilingual labels and bounded image cache.
The activity engines, server-owned session deadlines, parent-only AI review and verified
YouTube channel allowlist remain in force.

`game/realm-assets.json` pins original commissioned/generated PNG artwork and first-party
8-second 2D motion films by SHA256. Originals live on Drive, not in the application image.
`/world-assets/<id>` verifies a source before generating a disposable WebP or range-capable
MP4 copy; the 96 MiB cache rechecks Drive metadata and never accepts arbitrary paths.
The films use animated painted scenes and an original synthesized score, not recorded footage
or a generative video model. Render with `tools/render_realm_films.cjs` and encode with
`tools/encode_realm_films.py`; source paths are supplied locally and never contain credentials.

Story editions and abridgement notes are visible in the reader. `docs/story-sources.json`
records references checked against the retellings; source type and variant matter. Older tales
with threatening events are assigned to older readers and labelled for reading with adults.
The artwork is a new illustration, not a reproduction from the cited edition.
