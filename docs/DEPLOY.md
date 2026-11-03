# Triển khai và sao lưu

Ứng dụng phục vụ HTTP bên trong container ở cổng 5000; reverse proxy chịu trách nhiệm HTTPS. Cấu hình hostname chỉ qua `PUBLIC_URL` và Google callback, không ghi cứng trong frontend.

Trên Pi mới dùng hệ điều hành ARM64 và Docker/Compose chính thức: https://docs.docker.com/engine/install/debian/. Có thể build trên AMD64 bằng CI rồi pull đúng image ARM64 vào Pi; Pi không cần Node hay compiler để chạy image. Thư viện ảnh nằm trên Drive, tách khỏi image. Lần chạy đầu cần `ASSETS_URL` hoặc import gói offline; xem [ASSETS.md](ASSETS.md). Chừa ít nhất 5 GB trống cho gói tải, giải nén và volume (nhiều hơn nếu giữ nhiều phiên bản). Khi tải lần đầu dùng `--wait-timeout 1800`; kiểm tra log tiến độ nếu đường truyền chậm. Sau đó ứng dụng không cần Drive khi chạy/restart, chỉ khi cài phiên bản tài nguyên mới.

Sao lưu nhất quán:

```sh
docker compose stop web
umask 077
mkdir -p backups
docker compose run --rm -T --no-deps --user 0 --entrypoint tar web -C /data -czf - . > backups/data.tar.gz
# Sao lưu .env riêng vào nơi riêng tư; không đưa lên Git.
docker compose start web
```

Không dùng `docker compose down -v` trừ khi chủ ý xóa toàn bộ người dùng và phiên. Trước khi phục hồi trên máy mới, dừng web, giữ một bản sao volume hiện tại, khôi phục vào volume `/data`, rồi kiểm tra chủ sở hữu UID/GID 10001 và khởi động lại. Khóa `session.key` cần được giữ nếu muốn các cookie đang dùng tiếp tục hợp lệ.

SQLite không được chia sẻ qua NFS hay cho nhiều replica ghi cùng lúc. Một container Gunicorn, một volume riêng là cấu hình được hỗ trợ. Với bind mount thay named volume, tạo thư mục và cấp quyền UID 10001 trước. Giữ replica cũ và backup để rollback; nếu bản mới đã ghi dữ liệu, không đổi về DB cũ mà bỏ mất các thay đổi vừa phát sinh.

Tệp `.env` chỉ nằm trên máy triển khai. Có thể dùng secret manager của nền tảng để đưa các biến tương tự vào process; không cần copy `.env` vào image.

Volume `data` chứa tài khoản/phiên/khóa, còn `assets` chỉ chứa tài nguyên có thể khôi phục từ gói đã pin. Khi chuyển máy, sao lưu volume assets hoặc dùng lại đúng `assets.lock.json` và URL để tải lại. Không xóa data để cập nhật ảnh. Build image không truy cập Drive; entrypoint ánh xạ bộ ảnh đã xác minh vào ứng dụng trên thiết bị triển khai.
