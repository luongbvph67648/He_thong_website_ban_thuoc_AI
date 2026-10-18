# Bật AI thật và thanh toán mô phỏng

Mặc định hệ thống chạy với **AI giả** (kịch bản có sẵn, không gọi mạng). Tài liệu này hướng dẫn chuyển sang **Claude thật** cho
mọi tính năng AI, và nói rõ phần **thanh toán online mô phỏng** để demo.

**Lưu ý trung thực:** phần gọi Claude đã được đối chiếu với tài liệu SDK hiện hành và có kiểm thử bằng client giả, nhưng **chưa
được chạy với API thật** trong lúc phát triển. Công cụ kiểm tra ở Bước 3 sẽ cho bạn biết ngay có chỗ nào lệch. Nếu có bước báo
LỖI, chụp màn hình gửi lại để được sửa.

## Phần 1. Những tính năng AI nào cần gì

| Tính năng | Cần Claude thật | Cần embedding thật (BGE-M3) | Cần chạy job nền |
|---|---|---|---|
| Chatbot tư vấn (AI02, AI03), chuyển dược sĩ có tóm tắt (AI04) | Có | Có (tra kho tri thức) | Không |
| Tra cứu thuốc bằng ảnh hộp thuốc (AI05) | Có | Không | Không |
| Đọc ảnh đơn thuốc cho dược sĩ (AI06) | Có | Không | Có (job chạy mỗi phút) |
| Tìm kiếm theo ngữ nghĩa (AI01), gợi ý sản phẩm tương tự (AI07) | Không | Có | Không |
| Luật mua kèm (AI08), dự báo nhu cầu nhập (AI09) | Không (thống kê) | Không | Có (AI08 Chủ nhật, AI09 thứ Hai) |

Nghĩa là: **Claude thật** bật hầu hết tính năng; **embedding thật** (mô hình tải về ~2,3 GB) bật tìm kiếm theo nghĩa và giúp chatbot
tra đúng tri thức. Không có embedding thật thì chatbot và tìm kiếm vẫn chạy, nhưng dùng vector giả (chỉ khớp theo từ).

## Phần 2. Bật Claude thật

### Bước 1. Lấy khóa API

1. Vào https://console.anthropic.com, đăng ký hoặc đăng nhập.
2. Nạp một ít credit ở mục thanh toán (billing). Một buổi demo thường tốn vài chục nghìn đồng.
3. Vào mục **API Keys**, tạo một khóa mới. Khóa có dạng `sk-ant-...`. **Chỉ hiện một lần, hãy sao chép ngay.**

**Giữ bí mật khóa này.** Không gửi cho ai, không dán vào tin nhắn, không commit lên GitHub. Chỉ đặt trong file `backend\.env` (file
này đã được Git bỏ qua).

### Bước 2. Sửa `backend\.env`

Mở bằng Notepad: `notepad backend\.env`. Tìm và sửa các dòng sau:

```
AI_GIA_LAP=false
ANTHROPIC_API_KEY=sk-ant-...khóa-của-bạn...
CLAUDE_MODEL=claude-sonnet-5-5
AI_GIA_INPUT=2
AI_GIA_OUTPUT=10
AI_GIA_CACHE_READ=0.20
AI_NGAN_SACH_NGAY_USD=2
```

Giải thích:
- `CLAUDE_MODEL`: mô hình dùng. `claude-sonnet-5-5` rẻ hơn (2 USD vào / 10 USD ra mỗi triệu token), đủ tốt cho demo.
  `claude-opus-5-5` (mặc định của dự án) mạnh hơn nhưng đắt gấp đôi (4 / 20 USD).
- `AI_GIA_INPUT`, `AI_GIA_OUTPUT`, `AI_GIA_CACHE_READ`: đơn giá (USD cho một triệu token) để hệ thống **ước tính chi phí** hiển thị ở trang
  Giám sát AI. Nếu đổi sang Opus thì đặt `4`, `20`, `0.20`.
- `AI_NGAN_SACH_NGAY_USD`: trần chi phí mỗi ngày. Vượt trần thì chatbot tạm dừng và chuyển khách sang dược sĩ.

Lưu file (Ctrl+S).

### Bước 3. Kiểm tra bằng công cụ có sẵn

Trong PowerShell, ở thư mục `backend`:

```powershell
uv run python -m app.ai.kiem_tra
```

Công cụ gọi Claude thật vài lần (chi phí dưới 0,05 USD) và in từng bước:

```
Model: claude-sonnet-5-5 | AI_GIA_LAP=False | khóa API: có
[ĐẠT] Cấu hình
[ĐẠT] Schema AI02 phân loại câu hỏi: 612 token, ~0.002 USD
[ĐẠT] Schema AI04 tóm tắt hội thoại: ...
[ĐẠT] Schema AI05 đọc hộp thuốc: ...
[ĐẠT] Schema AI06 đọc đơn thuốc: ...
[ĐẠT] Chat có tool + streaming: tool gọi 1 lần, ...
```

- Tất cả **[ĐẠT]**: Claude đã sẵn sàng.
- **[LỖI]**: kèm tên lỗi (ví dụ `AuthenticationError` là sai khóa, `PermissionDeniedError`/`NotFoundError` là khóa không có quyền dùng
  model đó, `RateLimitError` là hết hạn mức). Đổi `CLAUDE_MODEL` sang một model khác trong danh sách mà tài khoản bạn dùng được.

Thử thêm đọc ảnh hộp thuốc thật (chụp hoặc tải ảnh một hộp thuốc về máy):

```powershell
uv run python -m app.ai.kiem_tra --anh C:\duong\dan\den\anh-hop-thuoc.jpg
```

### Bước 4. Khởi động lại backend

Ở cửa sổ đang chạy backend bấm **Ctrl+C** rồi chạy lại `uv run uvicorn app.main:app --reload`. Để dược sĩ nhận kết quả AI đọc đơn
thuốc (AI06), mở thêm một cửa sổ PowerShell chạy job nền:

```powershell
cd $HOME\Documents\He_thong_website_ban_thuoc_AI\backend
uv run python -m app.jobs
```

## Phần 3. Bật embedding thật (BGE-M3), tùy chọn

Bước này tải mô hình khoảng 2,3 GB và thư viện PyTorch (vài GB). Cần ổ đĩa trống khoảng 8 GB và kết nối mạng ổn định. Lần đầu mất
10 đến 30 phút tùy mạng.

1. Cài thư viện (trong thư mục `backend`):
   ```powershell
   uv sync --extra ai-local
   ```
2. Sửa `backend\.env`: `EMBEDDING_GIA_LAP=false` (giữ `EMBEDDING_MODEL=BAAI/bge-m3`).
3. Chạy lại công cụ kiểm tra để tải mô hình về máy (chỉ tải một lần):
   ```powershell
   uv run python -m app.ai.kiem_tra
   ```
   Cuối danh sách phải có `[ĐẠT] Embedding BGE-M3: 1024 chiều, cosine cùng nghĩa 0.xx > khác nghĩa 0.yy`.
4. Khởi động lại backend. Khi chạy với embedding thật, backend nạp mô hình ở nền ngay lúc khởi động (log có dòng
   `Mô hình embedding đã sẵn sàng`).
5. Đăng nhập **Admin**, vào **Tri thức AI**, bấm **Đồng bộ ngay**. Hệ thống tạo lại toàn bộ vector bằng mô hình mới (đổi mô hình
   thì tạo lại tất cả). Với dữ liệu demo mất vài phút trên CPU. Job nền cũng tự đồng bộ lúc 02:30 mỗi ngày.

Nếu tìm kiếm theo nghĩa trả về quá ít hoặc quá nhiều kết quả, ngưỡng độ gần `NGUONG_KHOANG_CACH` trong
`backend/app/modules/cua_hang/tim_kiem_lai.py` (đang là 0,55) được chỉnh theo vector giả; với BGE-M3 thật có thể cần nới hoặc siết nhẹ.

## Phần 4. Thử từng tính năng AI trên giao diện

1. **Chatbot**: bấm nút chat góc dưới bên phải, hỏi "Tôi bị đau đầu nhẹ nên dùng gì?". Chữ hiện dần (streaming), kèm thẻ sản phẩm
   không kê đơn. Hỏi "Tôi bị đau ngực dữ dội" để thấy chatbot dừng tư vấn và khuyên gọi 115 (kiểm bằng luật, trước cả khi gọi AI).
   Hỏi "Cho tôi mua Amoxicillin" để thấy chatbot từ chối gợi ý thuốc kê đơn và mời gặp dược sĩ.
2. **Tra cứu bằng ảnh**: bấm biểu tượng camera cạnh ô tìm kiếm, tải ảnh một hộp thuốc. Hệ thống đọc tên/hoạt chất/số đăng ký và khớp
   với sản phẩm có trong cửa hàng.
3. **Đọc đơn thuốc**: khách gửi ảnh đơn thuốc (chữ in rõ càng tốt). Chờ khoảng 1 phút (job chạy mỗi phút), dược sĩ mở yêu cầu thấy
   danh sách thuốc do AI đọc kèm sản phẩm gợi ý và độ tin cậy; dược sĩ xác nhận hoặc sửa từng dòng.
4. **Tìm kiếm theo nghĩa** (cần embedding thật): gõ "thuốc hạ sốt giảm đau", kết quả có Paracetamol dù tên không chứa các từ đó.
5. **Chuyển dược sĩ có tóm tắt**: trong chat bấm **Gặp dược sĩ**; dược sĩ thấy bản tóm tắt cuộc trò chuyện do AI viết.
6. **Giám sát**: Admin vào **Giám sát AI** xem số hội thoại, token, chi phí ước tính. Dược sĩ vào **Đánh giá câu trả lời AI** xem các
   câu bị khách báo sai.
7. **Bật/tắt từng mô-đun**: Admin vào **Cấu hình AI**. Tắt một mô-đun thì tính năng đó tự quay về cách không dùng AI.

## Phần 5. Quay về AI giả

Đặt `AI_GIA_LAP=true` (và `EMBEDDING_GIA_LAP=true`) trong `backend\.env`, khởi động lại backend. Dùng khi hết credit hoặc muốn demo
không cần mạng.

---

## Thanh toán online mô phỏng (VNPay, MoMo)

Đây **không phải thanh toán thật**: không có tài khoản VNPay/MoMo thật, không trừ tiền, không kết nối ngân hàng. Hệ thống dựng một
**cổng thanh toán giả lập** có giao diện và luồng giống cổng thật, chạy hoàn toàn trên máy bạn. Cấu hình đã sẵn sàng
(`THANH_TOAN_CHE_DO=gia`), không cần sửa gì.

Trang mô phỏng luôn hiện dòng cảnh báo vàng "Môi trường mô phỏng... Không có tiền thật".

### Luồng giống cổng thật

1. Khách đặt hàng, chọn **VNPay** hoặc **MoMo**. Đơn ở trạng thái "Chờ thanh toán" và có hạn thanh toán (mặc định 15 phút).
2. Hệ thống chuyển khách sang trang cổng thanh toán có số tiền, mã đơn, mã giao dịch và đồng hồ đếm ngược.
3. Khách thanh toán trên trang cổng. Kết quả được báo cho **máy chủ** bằng một IPN có chữ ký (giống cổng thật báo qua server, không
   tin trình duyệt), máy chủ kiểm tra chữ ký, số tiền, chống xử lý trùng rồi mới đổi trạng thái đơn.
4. Khách quay về trang kết quả, trạng thái luôn đọc lại từ máy chủ. Thất bại thì bấm **Thanh toán lại** (giao dịch mới).
5. Quá hạn mà chưa thanh toán, job nền tự hủy đơn và nhả hàng.

### Thanh toán VNPay (mô phỏng)

1. Chọn phương thức **Thẻ nội địa và tài khoản ngân hàng**, bấm **Tiếp tục**.
2. Chọn ngân hàng, nhập thông tin thẻ thử nghiệm (có bảng gợi ý ngay trên trang), bấm **Tiếp tục**.
3. Nhập mã **OTP `123456`**, bấm **Xác nhận**.

Các thẻ thử nghiệm (tên chủ thẻ `NGUYEN VAN A`, ngày phát hành `07/15`, theo bộ thẻ công khai của sandbox VNPay):

| Số thẻ | Kết quả |
|---|---|
| `9704198526191432198` | Thanh toán thành công |
| `9704195798459170488` | Thất bại: thẻ không đủ số dư |
| `9704192181368742` | Thất bại: thẻ chưa đăng ký thanh toán online |
| số khác hoặc sai tên/ngày | Báo "Thông tin thẻ không chính xác", cho nhập lại |

Thêm: nhập sai OTP 3 lần thì giao dịch thất bại; **Hủy giao dịch** thì thất bại; chọn "Ứng dụng Mobile Banking quét mã QR" hiện mã QR
và nút giả lập đã quét.

### Thanh toán MoMo (mô phỏng)

1. Trang hiện **mã QR** và đồng hồ đếm ngược.
2. Bấm **Mô phỏng: mở ứng dụng MoMo và quét mã** (một khung điện thoại giả hiện ra).
3. Nhập mã **PIN `123456`**, bấm **Xác nhận**. Bấm **Từ chối** hoặc nhập sai PIN 3 lần thì giao dịch thất bại.

### Hoàn tiền

Hủy đơn đã thanh toán hoặc đổi trả thì tạo giao dịch hoàn tiền; Admin xác nhận ở trang **Hoàn tiền**. Ở chế độ mô phỏng, việc hoàn
tiền cũng chạy không cần cổng thật.

### Muốn thanh toán thật thì sao?

Dự án đã có sẵn bộ nối VNPay và MoMo thật (`backend/app/tich_hop/thanh_toan/vnpay.py`, `momo.py`, ký HMAC theo tài liệu của hai cổng).
Chỉ cần đăng ký tài khoản **sandbox** của VNPay/MoMo (miễn phí, có tiền thử) rồi đặt `THANH_TOAN_CHE_DO=sandbox` cùng các khóa trong
`backend\.env`. Phần này chưa được chạy thử với sandbox thật.
