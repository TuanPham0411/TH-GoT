# Tài nguyên trên Google Drive

GitHub chứa mã, HTML/CSS/JS, JSON cấu hình/chủ đề và `assets.lock.json`. Image build hoàn toàn không tải/kèm thư viện ảnh. Toàn bộ `game/resource/images/` và `game/static/images/` (gồm ảnh trang giới thiệu) được đóng thành một gói `.tar.gz` và đưa lên Drive. Thiết bị tải gói khi chạy lần đầu, xác minh SHA-256 của gói lẫn từng tệp, giải nén vào volume `assets`, rồi mới mở web.

## Nguồn Drive mặc định

Gói chuẩn đã được upload và cấu hình trong `assets.lock.json` và `.env.example`:

https://drive.google.com/file/d/1JsQk7-4mWJlmCJDd5TdDy9mnUnEm41U5/view?usp=sharing

- Tệp: `th-got-assets-5b878953c7227f78.tar.gz`.
- Kích thước: **1626348552 bytes**, **1274 tệp**, gồm ảnh trang giới thiệu.
- SHA-256: `5b878953c7227f788d3da7167cb297f013fdf6977d80c6bb00c8b9e8a3191462`.

Không cần upload lại hoặc điền URL khi cài mới. `ASSETS_URL` có thể override nguồn mặc định bằng link tệp Drive hoặc mirror HTTPS chứa cùng byte; không dùng link thư mục. Downloader xử lý URL chia sẻ, resourcekey và trang xác nhận tệp lớn của Drive. URL không phải credential.

CI chạy integration mặc định với nguồn trên. Repository variable `TH_GOT_ASSETS_URL` là override tùy chọn. Job tải/xác minh archive và inventory, audit ảnh và smoke test; build/publish image không tải Drive.

Drive có giới hạn lượt tải/băng thông. Nếu bị yêu cầu đăng nhập hoặc hết quota, bootstrap dừng với lỗi; không chạy ứng dụng thiếu ảnh. Có thể đổi `ASSETS_URL` sang mirror HTTPS chứa **cùng byte** và cùng SHA-256, hoặc import offline. Không mount Drive bằng FUSE; lúc chơi mọi ảnh được phục vụ từ đĩa thiết bị, không hotlink tới Drive.

## Thiết bị mới

```sh
git clone https://github.com/TuanPham0411/TH-GoT.git
cd TH-GoT
cp .env.example .env
# Điền PUBLIC_URL và Google OAuth; nguồn Drive mặc định đã được cấu hình.
docker compose up -d --build --wait --wait-timeout 1800
python3 tools/smoke.py
```

Dùng image GHCR thay build tại chỗ cũng có cùng quy trình tải lần đầu. Image/source tương ứng luôn mang file khóa đã pin; URL không được tự quyết định checksum. Cần mạng để tải lần đầu và dung lượng ít nhất 5 GB trống. Tải lỗi hoặc mất điện không tạo bản cài “ready”; chạy lại sẽ cài lại. Không hỗ trợ tiếp tục tải byte từ tệp dở. Một khóa cài đặt ngăn hai process đồng thời cài cùng volume. Web chỉ bắt đầu sau khi toàn bộ gói được xác minh.

Volume có `releases/<SHA-256>/` và `current` trỏ tới bản sẵn sàng. Phiên bản cũ được giữ khi nâng cấp để có thể rollback. Không tự xóa volume khi restart. Mỗi lần start kiểm tra marker và sự hiện diện/kích thước của các tệp; xác minh đầy đủ khi cần:

```sh
docker compose run --rm --no-deps --entrypoint python web /app/assets.py verify
```

Lệnh trên đọc hash mọi tệp, không dùng mạng. Nếu phát hiện hỏng nội dung cùng kích thước, dừng web, xóa **chỉ marker `.verified` của bản tài nguyên đó** trong volume rồi chạy lại để cài lại; không xóa volume data.

## Import gói offline trên thiết bị

Copy đúng gói nén lên thiết bị, rồi:

```sh
docker compose build
docker compose run --rm --no-deps \
  -v /duong/dan/tuyet/doi/th-got-assets-HASH.tar.gz:/import.tar.gz:ro \
  --entrypoint python web /app/assets.py install --archive /import.tar.gz
docker compose up -d --no-build --wait --wait-timeout 180
```

Gói import cũng phải khớp file khóa, không có chế độ bỏ kiểm tra checksum. Có thể để ASSETS_URL trống sau khi import. Volume named được Docker khởi tạo với chủ sở hữu UID 10001; nếu bind-mount, cấp quyền thư mục cho UID/GID 10001 trước.

## Phát triển, thêm hoặc cập nhật ảnh

Tải/cài bộ ảnh hiện tại ngoài source tree:

```sh
python3 tools/assets.py install --root .assets
# Hoặc: python3 tools/assets.py install --root .assets --archive /path/to/archive.tar.gz
ASSET_DIR="$PWD/.assets/current" .venv/bin/python game/app.py
ASSET_DIR="$PWD/.assets/current" .venv/bin/python game/tools/audit_v88_complete.py
```

Khi sửa ảnh, dùng một thư mục staging riêng có cấu trúc `resource/images/` và `static/images/`, không chỉnh trực tiếp cache bản đã xác minh:

```sh
python3 tools/assets.py pack --source /path/to/staging --output /path/to/output --lock assets.lock.json
```

Lệnh tạo tar deterministic, kiểm tra không còn pointer LFS, tạo inventory từng tệp và pin SHA-256/size. Upload gói mới lên Drive, điền URL mới vào lock, commit lock và JSON cấu hình nếu thay đổi. Build/deploy source mới; thiết bị chỉ tải bản mới khi SHA thay đổi. Không commit tar, ảnh hay thư mục cache. Đổi URL gói mà không đổi hash không thể đưa nội dung khác vào bản chạy.
