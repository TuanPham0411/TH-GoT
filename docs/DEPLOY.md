# Triển khai và sao lưu

Hostname GoT: **https://got.th.io.vn**. Container phục vụ HTTP ở cổng 5000, Compose bind localhost 5082; reverse proxy cung cấp HTTPS. `PUBLIC_URL=https://got.th.io.vn`, đăng ký callback `/auth/callback` và `/admin/drive/callback`. Chỉ bật `TRUST_PROXY=1` khi có đúng một proxy tin cậy.

Hỗ trợ Linux AMD64 và ARM64, Raspberry Pi OS/Debian **64 bit**. CI build image cho cả hai kiến trúc; Pi không cần Node/compiler khi pull image. Dùng tag commit SHA đã kiểm thử tại `ghcr.io/tuanpham0411/th-got:COMMIT_SHA`.

```sh
test -e .env || cp .env.example .env
# Cấu hình Google OAuth, ADMIN_EMAILS và DRIVE_FOLDER_ID.
docker compose up -d --build --wait --wait-timeout 180
python3 tools/smoke.py
# Sau khi quản trị viên kết nối Drive và chuyển dữ liệu:
python3 tools/smoke.py --media
```

`/healthz` là readiness của web/database, cho phép cấu hình ban đầu. `/readyz` kiểm tra tài nguyên trên Drive; không gọi bản mới là đã chơi được trước khi smoke `--media` qua. Ảnh chỉ ở Drive, kể cả khi restart: cần Internet và quyền Drive còn hiệu lực. Không có volume assets hoặc cache thumbnail. Không chuyển volume ảnh cũ sang bản này và không tự xóa volume cũ khi nâng cấp.

Volume `data` chứa database tài khoản/phiên, khóa phiên và refresh token Drive đã mã hóa bằng khóa phiên. Giữ cả database và khóa khi sao lưu/khôi phục. Nếu đổi khóa hoặc mất token, quản trị viên cần kết nối lại Drive. Không có ảnh trong bản sao lưu `data`.

Sao lưu nhất quán, bằng đúng user ứng dụng có quyền đọc volume:

```sh
docker compose stop web
umask 077
mkdir -p backups
docker compose run --rm -T --no-deps --entrypoint tar web -C /data -czf - . > backups/data.tar.gz
# Sao lưu .env riêng vào nơi riêng tư; không đưa lên Git.
docker compose start web
```

Không dùng `docker compose down -v` trừ khi chủ ý xóa dữ liệu người dùng. Khôi phục vào volume riêng, giữ bản sao hiện tại và bảo đảm UID/GID 10001 sở hữu dữ liệu trước khi chạy. SQLite không chia sẻ qua NFS; cấu hình hỗ trợ là một container Gunicorn, một worker có threads và một volume data riêng.

Bật Google Drive API và dùng OAuth client của triển khai mới; không lấy credential hoặc database của website cũ. Các đích mạng cần cho runtime: `accounts.google.com`, `oauth2.googleapis.com`, `www.googleapis.com` và các endpoint nội dung Google mà Drive trả về. Không tắt TLS để xử lý lỗi proxy; với proxy có CA riêng, cung cấp CA tin cậy cho runtime bằng bind mount read-only và `SSL_CERT_FILE`, không copy CA phiên vào image.
