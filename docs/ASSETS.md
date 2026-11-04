# Drive là nơi lưu ảnh duy nhất

App không tải gói ảnh về volume, không cài `.assets`, không ghi thumbnail xuống đĩa và không chơi bằng cache offline. Ảnh được đọc từ Drive khi hiển thị. Thumbnail và upload chỉ được xử lý trong RAM, tối đa 32 MB cho mỗi ảnh; phản hồi ảnh dùng `Cache-Control: no-store`. App không có service worker, IndexedDB hay Cache Storage để lưu ảnh.

## Thư mục và dữ liệu ban đầu

Thư mục mặc định: https://drive.google.com/drive/folders/1hueCpVN5ez5aFRGAxbjc2hjK-Yaw3rA0

Gói chuẩn **đã có trên Drive**, không cần upload lại:
https://drive.google.com/file/d/1JsQk7-4mWJlmCJDd5TdDy9mnUnEm41U5/view

- Tên: `th-got-assets-5b878953c7227f78.tar.gz`.
- Kích thước: **1626348552 bytes**, **1274 tệp**, gồm ảnh trang giới thiệu.
- SHA-256: `5b878953c7227f788d3da7167cb297f013fdf6977d80c6bb00c8b9e8a3191462`.

Gói nén chỉ là nguồn chuyển dữ liệu một lần. App cần ảnh riêng lẻ trên Drive để đọc và sửa trực tiếp. Inventory trong `assets.lock.json` giữ nguyên để xác minh dữ liệu ban đầu; nó không đóng băng tài nguyên sau khi quản trị viên chỉnh sửa.

## Kết nối và chuyển dữ liệu

Cấu hình Google OAuth, hai callback và `ADMIN_EMAILS` theo README. Đăng nhập bằng tài khoản quản trị có quyền chỉnh sửa thư mục, mở `/admin/resources` rồi kết nối Drive. Public share URL không cấp quyền ghi; phải hoàn tất consent của chủ tài khoản.

Bấm chuyển dữ liệu trên trang quản trị. Tác vụ chạy nền trong process web:

1. Đọc gói trực tiếp từ Drive API, tính size/SHA-256 theo chunk trong RAM; không ghi archive xuống đĩa.
2. Đọc lượt thứ hai, kiểm tra đường dẫn, loại entry, size và hash từng ảnh, rồi upload từng tệp vào thư mục Drive. Từ chối symlink, traversal, tệp lặp hoặc ngoài inventory.
3. Khởi tạo các tài liệu JSON trên Drive và ghi marker hoàn tất chỉ sau khi đủ 1274 ảnh.

Tác vụ có thể tốn thời gian và quota Drive. Nếu container restart hoặc mạng lỗi, chạy lại: ảnh đã có được so hash, không ghi đè ảnh khác nội dung; JSON đã có không bị ghi đè. Sau khi có marker hoàn tất, chạy migration lại không ghi đè tài nguyên đã sửa. Không chạy nhiều replica cùng quản lý một thư mục trong khi chuyển dữ liệu.

Ảnh được định danh bằng logical path trong metadata Drive; app không tạo public permission hoặc tự mở rộng chia sẻ thư mục. Trình duyệt đọc qua app, không nhận access token hoặc refresh token Drive.

## Thêm, sửa và xóa từ app

Ở `/admin/resources`, chọn chủ đề rồi thêm ảnh PNG/JPEG/WebP, tên và mô tả song ngữ. Khi sửa có thể thay ảnh hoặc giữ ảnh cũ. App kiểm tra ảnh và gửi dữ liệu trực tiếp đến Drive. Metadata của chủ đề được cập nhật trên Drive, không sửa source trong container.

Khi xóa, app bỏ tài nguyên khỏi chủ đề trên Drive rồi chuyển ảnh không còn được tài liệu khác tham chiếu vào thùng rác Drive. Tệp đang dùng ở tài liệu khác được giữ. Drive không có transaction bao trùm nhiều tệp: nếu một bước gặp lỗi mạng, kiểm tra trạng thái trên trang quản trị trước khi thử lại; app không xóa ảnh cũ trước khi ghi tài liệu mới.

Dữ liệu ảnh, tài liệu đang sửa và marker đều nằm trên Drive. Volume `data` chỉ chứa dữ liệu tài khoản, phiên và kết nối OAuth đã mã hóa. Không mount volume ảnh cũ vào bản mới. Chỉ xóa volume ảnh cũ sau khi đã xác minh Drive và sao lưu phù hợp; không tự xóa volume người dùng.

Mất quyền Drive, hết quota hoặc mất mạng: API trả lỗi 503; không phục vụ ảnh cũ từ đĩa. Kết nối lại Drive bằng tài khoản quản trị để khôi phục quyền truy cập.
