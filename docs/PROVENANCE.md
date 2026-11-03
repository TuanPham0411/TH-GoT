# Nguồn gốc

Tách game và các thành phần giới thiệu cần thiết từ `TuanPham0411/GOT`, commit `4a7de663b0bf16427b7c51e88ea3d8c1426cda73`, theo yêu cầu chủ repository. Không nhập người dùng, đơn hàng, API key, khóa Cloudflare hay dữ liệu của SIKA.

Lịch sử phát triển game được giữ trong các CHANGELOG trong `game/`. Đây là repository độc lập; không cần checkout GOT, không chạy portal cũ, không dùng hostname của portal cũ. Ảnh gốc được giữ nguyên byte và đóng thành gói tài nguyên ngoài GitHub, có inventory và SHA-256 trong assets.lock.json; các audit dữ liệu vẫn được giữ. Lịch sử TH-GoT chưa xuất bản được gom vào một commit dựa trên README ban đầu của repository đích, để không đưa pointer hoặc binary LFS vào lịch sử GitHub. Bản sao lịch sử cũ được giữ ngoài checkout; không sửa lịch sử GOT gốc.

Các tệp nguồn/asset có điều kiện cấp phép riêng vẫn giữ nguyên điều kiện đó. Việc website công khai, miễn phí không tự cấp thêm quyền tái cấp phép các thành phần bên thứ ba.
