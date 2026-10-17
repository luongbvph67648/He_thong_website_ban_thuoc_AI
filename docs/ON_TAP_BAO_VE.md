# Tài liệu ôn tập bảo vệ đồ án

Tài liệu này giúp bạn hiểu dự án từ tổng quan đến chi tiết để trả lời câu hỏi của giảng viên. Đọc theo thứ tự. Mỗi phần có **"Mở file nào để xem"** để bạn đối chiếu với code thật, và cuối tài liệu có bộ câu hỏi thường gặp kèm gợi ý trả lời.

Nguồn sự thật của dự án là bộ đặc tả trong `docs/spec/` (00 đến 12). Tài liệu này tóm tắt lại bằng lời dễ hiểu. Khi cần chi tiết hơn, mở đúng file spec được nhắc tới.

---

## Phần 0. Kế hoạch học 7 ngày

Mỗi ngày khoảng 2 đến 3 giờ. Học bằng cách **vừa chạy hệ thống vừa đọc**, không chỉ đọc chữ.

| Ngày | Học gì | Làm gì để nhớ |
|---|---|---|
| 1 | Phần 1, 2 (tổng quan, kiến trúc, công nghệ) | Tự nói lại bài giới thiệu 2 phút (Phần 1) thành tiếng, không nhìn giấy. Vẽ lại sơ đồ kiến trúc ra giấy |
| 2 | Phần 3, 4 (một yêu cầu đi qua hệ thống, cơ sở dữ liệu) | Làm kịch bản 1 trong `HUONG_DAN_DEMO.md`, sau mỗi bước mở database xem bảng nào thay đổi (`don_hang`, `phan_bo_lo`, `lo_thuoc`, `bien_dong_kho`) |
| 3 | Phần 5 (nghiệp vụ lõi: trạng thái đơn, tồn kho, tính tiền) | Vẽ lại sơ đồ trạng thái đơn hàng. Tự giải thích "giữ hàng" khác "xuất kho" như thế nào |
| 4 | Phần 6 (phân quyền, bảo mật) | Thử đăng nhập dược sĩ rồi vào trang quản trị; thử khách A xem đơn của khách B |
| 5 | Phần 7 (AI) | Làm kịch bản chat và đơn thuốc; đọc file `ai/prompts/chat_he_thong.md` |
| 6 | Phần 8, 9, 10 (tích hợp, job nền, kiểm thử) | Chạy `uv run pytest -q tests/phan_quyen` và xem nó kiểm tra gì |
| 7 | Phần 11, 12 (câu hỏi thường gặp, hạn chế) | Nhờ một người bạn (hoặc Claude) hỏi ngẫu nhiên các câu ở Phần 11, bạn trả lời không nhìn tài liệu |

Mẹo: khi đọc một file code, đừng cố hiểu từng dòng. Đọc **tên hàm** và **chuỗi mô tả ngay dưới tên hàm** (docstring, viết bằng tiếng Việt) trước. Chúng nói hàm làm gì.

---

## Phần 1. Giới thiệu dự án trong 2 phút (bài nói mẫu)

> Đề tài của em là website nhà thuốc trực tuyến tích hợp AI, tham khảo mô hình Long Châu và Pharmacity, ở quy mô một nhà thuốc, một kho.
>
> Hệ thống có ba nhóm người dùng: **khách hàng** (vãng lai và thành viên), **nhân viên** (dược sĩ bán hàng và nhân viên kho), và **quản trị viên**. Tổng cộng 92 chức năng.
>
> Về nghiệp vụ, hệ thống bán thuốc và sản phẩm sức khỏe online, quản lý kho **theo lô và hạn sử dụng**, xuất kho theo nguyên tắc **lô hết hạn trước xuất trước (FEFO)**. **Thuốc kê đơn không bán trực tiếp**: khách phải gửi ảnh đơn thuốc để dược sĩ duyệt. Có đổi trả, hoàn tiền, bán tại quầy, và báo cáo.
>
> Về AI, em dùng Claude API cho **chatbot tư vấn** (có chuyển sang dược sĩ khi cần), **đọc ảnh hộp thuốc và ảnh đơn thuốc**, cùng mô hình embedding BGE-M3 cho **tìm kiếm theo ngữ nghĩa**. Ngoài ra có **gợi ý sản phẩm**, **luật mua kèm** và **dự báo nhu cầu nhập hàng** bằng thống kê.
>
> Điểm em chú trọng là **an toàn**: AI không bao giờ gợi ý thuốc kê đơn, và quy tắc này được chặn ngay trong câu truy vấn cơ sở dữ liệu chứ không chỉ dựa vào lời dặn AI; dữ liệu sức khỏe được mã hóa và quản trị viên không đọc được; các thao tác nhạy cảm tách người lập và người duyệt.
>
> Công nghệ: backend Python FastAPI, cơ sở dữ liệu PostgreSQL, frontend React TypeScript. Hệ thống có gần 3.000 test tự động cho backend, gần 1.000 test cho frontend, và 4 kịch bản kiểm thử trên trình duyệt thật.

---

## Phần 2. Kiến trúc và công nghệ

### 2.1 Sơ đồ tổng thể

```
   Trình duyệt (React)
   ├─ Khu cửa hàng       /           (khách)
   ├─ Khu nhân viên      /nhan-vien  (dược sĩ, kho)
   └─ Khu quản trị       /quan-tri   (Admin)
            │  gọi API REST /api/v1, SSE (chat AI), WebSocket (chat dược sĩ)
            ▼
   Backend FastAPI (Python) ──► Claude API (AI), BGE-M3 (embedding)
            │               ──► VNPay, MoMo, GHN, SMS, email (qua "adapter")
            ▼
   PostgreSQL 16 (+ pgvector, unaccent, pg_trgm)
            ▲
   Worker job nền (APScheduler) — tiến trình riêng, chạy việc định kỳ
```

- **Một backend, ba khu giao diện.** Cả ba khu dùng chung một backend. Backend phân biệt khách và nhân viên bằng loại token (Phần 6).
- **Worker job nền** là một chương trình chạy song song với backend, làm các việc định kỳ như hủy đơn quá hạn thanh toán, cập nhật lô hết hạn, dự báo nhập hàng (Phần 9).
- **Adapter**: mỗi dịch vụ bên ngoài (cổng thanh toán, giao hàng, SMS, AI) được bọc trong một lớp trung gian. Mỗi adapter có **bản giả** để chạy demo và test mà không cần mạng hay tài khoản thật.

### 2.2 Công nghệ và lý do chọn

| Công nghệ | Dùng để | Vì sao chọn |
|---|---|---|
| **Python 3.12 + FastAPI** | Backend, viết API | Viết nhanh, tự sinh tài liệu API (trang `/docs`), hỗ trợ bất đồng bộ (async) nên xử lý nhiều yêu cầu cùng lúc tốt; Python mạnh về AI và thống kê |
| **SQLAlchemy 2 (async) + asyncpg** | Làm việc với cơ sở dữ liệu từ Python (ORM) | Viết truy vấn bằng Python an toàn (chống SQL injection), vẫn dùng được SQL thuần khi cần |
| **Alembic** | Quản lý thay đổi cấu trúc CSDL (migration) | Mỗi thay đổi bảng là một file có đánh số, chạy lại được trên máy khác |
| **Pydantic v2** | Kiểm tra dữ liệu vào/ra API | Dữ liệu sai định dạng bị từ chối ngay với thông báo rõ ràng |
| **PostgreSQL 16** | Cơ sở dữ liệu | Có giao dịch (transaction) và khóa dòng (`FOR UPDATE`) cần cho tồn kho; có tiện ích `pgvector` (tìm kiếm vector cho AI), `unaccent` (tìm không dấu), `pg_trgm` (tìm gần đúng, gõ sai chính tả vẫn ra) |
| **React 19 + TypeScript + Vite** | Giao diện | Phổ biến; TypeScript bắt lỗi kiểu dữ liệu khi viết code; Vite chạy nhanh khi phát triển |
| **Ant Design 6** | Bộ thành phần giao diện (bảng, form, nút) | Có sẵn tiếng Việt, hợp với trang quản trị nhiều bảng biểu |
| **TanStack Query** | Gọi API và lưu tạm dữ liệu ở giao diện | Tự quản lý trạng thái đang tải, lỗi, làm mới dữ liệu |
| **Zustand** | Lưu trạng thái đăng nhập, giỏ hàng tạm ở giao diện | Nhẹ, đơn giản |
| **Claude API (Anthropic)** | Chatbot, đọc ảnh hộp thuốc, đọc ảnh đơn thuốc | Trả lời tiếng Việt tốt, đọc được ảnh, hỗ trợ "tool use" (cho AI gọi hàm tra cứu dữ liệu thật) |
| **BGE-M3** | Biến văn bản thành vector 1024 chiều (embedding) để tìm theo nghĩa | Hỗ trợ tiếng Việt, chạy được trên máy, không mất phí mỗi lần gọi |
| **statsmodels** | Dự báo nhu cầu (Holt-Winters) | Thư viện thống kê chuẩn của Python |
| **APScheduler** | Chạy job định kỳ | Đơn giản, chạy trong Python |
| **Docker** | Chạy PostgreSQL và Mailpit | Không phải cài PostgreSQL thủ công, mọi máy giống nhau |
| **pytest, vitest, Playwright** | Kiểm thử backend, frontend, trên trình duyệt thật | Xem Phần 10 |

### 2.3 Cấu trúc thư mục

```
backend/app/
  core/        thành phần dùng chung: cấu hình, kết nối CSDL, bảo mật, phân quyền, tiền, thời gian, lỗi, log
  models/      định nghĩa các bảng CSDL bằng Python
  modules/     mỗi thư mục là một nhóm chức năng (ban_hang, kho, don_thuoc, doi_tra, tu_van, ...)
               thường gồm: router*.py (khai báo API), dich_vu.py (logic nghiệp vụ), schemas.py (dữ liệu vào/ra)
  ai/          mọi thứ về AI: claude.py (cổng duy nhất gọi Claude), chatbot.py, embedding.py, prompts/
  tich_hop/    adapter dịch vụ ngoài: thanh_toan (VNPay, MoMo, giả), van_chuyen (GHN, giả), tin_nhan (SMS, email)
  jobs/        job nền
  seed/        dữ liệu khởi tạo và dữ liệu demo
backend/alembic/versions/   các file migration (0001, 0002, 0003)
backend/tests/              test backend
frontend/src/khu/           giao diện của 3 khu: cua-hang, nhan-vien, quan-tri
frontend/src/api/           gọi API; schema.d.ts được sinh tự động từ backend
frontend/e2e/               4 kịch bản Playwright
docs/spec/                  đặc tả (nguồn sự thật)
docs/database/              sơ đồ CSDL (ERD) dạng DBML và SQL
```

Quy mô: khoảng 34.000 dòng Python ở backend (không tính test), khoảng 18.000 dòng TypeScript ở frontend (không tính test). Khoảng 65 bảng.

---

## Phần 3. Một yêu cầu đi qua hệ thống như thế nào

Lấy ví dụ **khách bấm "Đặt hàng"**. Hiểu được luồng này là hiểu cách mọi chức năng khác hoạt động.

1. **Giao diện** (`frontend/src/khu/cua-hang/...`) gửi `POST /api/v1/toi/don-hang` kèm token đăng nhập (header `Authorization`) và một mã ngẫu nhiên `Idempotency-Key`.
2. **FastAPI nhận yêu cầu**, chạy qua các lớp trung gian (middleware): gắn mã yêu cầu để ghi log, giới hạn kích thước dữ liệu gửi lên, thêm header bảo mật.
3. **Kiểm tra đăng nhập** (`core/phan_quyen.py::khach_hien_tai`): giải mã token, kiểm tra tài khoản còn hoạt động. **Mã khách hàng lấy từ token**, không bao giờ lấy từ dữ liệu khách gửi lên (để khách không giả làm người khác được).
4. **Kiểm tra dữ liệu** bằng Pydantic (`modules/ban_hang/schemas.py::DatHangVao`): hình thức nhận, phương thức thanh toán, địa chỉ.
5. **Mở một giao dịch CSDL** (`core/db.py`, kiểu `Db`): cả yêu cầu chạy trong một transaction. Nếu bất kỳ bước nào lỗi thì **mọi thay đổi bị hủy**, không để dữ liệu dở dang.
6. **Logic nghiệp vụ** (`modules/ban_hang/dat_hang.py`):
   - Đọc giỏ hàng đã lưu của khách (không tin danh sách hàng do giao diện gửi).
   - Tính lại tiền theo giá hiện tại (Phần 5.4), áp mã giảm giá nếu có.
   - **Giữ hàng** theo FEFO (`modules/kho/ton_kho.py::giu_hang`), khóa các lô liên quan.
   - Tạo đơn qua **máy trạng thái** (`modules/ban_hang/trang_thai.py::khoi_tao_trang_thai`), ghi lịch sử trạng thái.
7. **Commit** giao dịch, trả về mã đơn. Nếu khách bấm hai lần với cùng `Idempotency-Key`, lần sau trả lại đúng đơn cũ, không tạo đơn thứ hai.

**Mở file nào để xem:** `backend/app/modules/ban_hang/router_khach.py` (khai báo API), `dat_hang.py` (logic), `trang_thai.py` (máy trạng thái), `backend/app/modules/kho/ton_kho.py` (tồn kho).

---

## Phần 4. Cơ sở dữ liệu

Xem sơ đồ: dán nội dung `docs/database/ERD_da_chinh_sua.dbml` vào trang https://dbdiagram.io để thấy hình. Hoặc mở database bằng DBeaver (xem câu trả lời trước về cách mở).

### 4.1 Các nhóm bảng

| Nhóm | Bảng chính | Ý nghĩa |
|---|---|---|
| Sản phẩm | `san_pham`, `don_vi_quy_doi`, `danh_muc`, `hoat_chat`, `thanh_phan`, `thong_tin_chuyen_mon`, `tuong_tac_hoat_chat` | Thông tin sản phẩm, đơn vị bán (viên/vỉ/hộp), hoạt chất, nội dung chuyên môn do dược sĩ soạn, tương tác giữa các hoạt chất |
| Kho | `lo_thuoc`, `bien_dong_kho`, `phieu_nhap`, `phieu_kiem_ke`, `phieu_dieu_chinh`, `phieu_huy`, `phieu_xuat_tra`, `lenh_thu_hoi` | Lô hàng có hạn dùng, thẻ kho, các loại phiếu kho |
| Bán hàng | `gio_hang`, `don_hang`, `ct_don_hang`, `phan_bo_lo`, `lich_su_trang_thai`, `thanh_toan`, `van_don`, `khuyen_mai`, `ma_giam_gia` | Giỏ, đơn, chi tiết đơn, đơn lấy từ lô nào, thanh toán, vận đơn |
| Đơn thuốc, sau bán | `yeu_cau_don_thuoc`, `ct_yeu_cau_don_thuoc`, `yeu_cau_doi_tra`, `ct_yeu_cau_doi_tra`, `danh_gia`, `hoi_dap` | Yêu cầu duyệt đơn thuốc, đổi trả, đánh giá |
| Tài khoản | `khach_hang`, `nhan_vien`, `vai_tro`, `quyen`, `vai_tro_quyen`, `phien_dang_nhap`, `ma_otp`, `dia_chi` | Người dùng, phân quyền, phiên, OTP |
| Sức khỏe | `ho_so_suc_khoe`, `di_ung` | Bệnh nền (mã hóa), dị ứng hoạt chất |
| AI, tư vấn | `hoi_thoai`, `tin_nhan`, `tai_lieu_tri_thuc`, `lich_su_xem`, `lich_su_tim_kiem`, `luat_mua_kem`, `de_xuat_nhap_hang` | Hội thoại chat, kho tri thức (có cột vector), dữ liệu cho gợi ý và dự báo |
| Hệ thống | `cau_hinh`, `nhat_ky_he_thong`, `thong_bao` | Cấu hình, nhật ký thao tác, thông báo |

### 4.2 Ba ý thiết kế quan trọng cần giải thích được

**a) Đơn vị quy đổi.** Một sản phẩm bán theo nhiều đơn vị: viên, vỉ (10 viên), hộp (10 vỉ = 100 viên). Bảng `don_vi_quy_doi` lưu mỗi đơn vị một dòng với `he_so` (hệ số so với đơn vị nhỏ nhất) và giá bán riêng. **Tồn kho luôn tính theo đơn vị nhỏ nhất** (đơn vị cơ sở). Khách mua 2 hộp thì kho trừ 200 viên.

**b) Lô thuốc.** Cùng một sản phẩm nhưng nhập nhiều đợt, mỗi đợt có số lô, hạn dùng, giá nhập khác nhau. Mỗi đợt là một dòng `lo_thuoc`. Nhờ vậy mới làm được: xuất lô hết hạn trước, cảnh báo cận hạn, thu hồi đúng lô bị lỗi, tính đúng giá vốn.

**c) Phân bổ lô (`phan_bo_lo`).** Một dòng đơn hàng có thể lấy hàng từ nhiều lô (ví dụ lô A còn 30 viên, lô B thêm 20 viên). Bảng này ghi "dòng đơn nào lấy bao nhiêu từ lô nào, giá vốn bao nhiêu". Nó cũng giúp khi thu hồi lô: biết ngay đã bán lô đó cho ai.

### 4.3 Ràng buộc dữ liệu

Ngoài code, CSDL tự chặn dữ liệu sai bằng ràng buộc (CHECK, khóa ngoại, duy nhất). Ví dụ:
- Số lượng giữ không vượt số lượng tồn; tồn không âm.
- Tổng tiền đơn = tạm tính − giảm giá + phí vận chuyển.
- Người duyệt phiếu khác người lập phiếu.
- Nhật ký hệ thống **không sửa, không xóa được** (có trigger trong CSDL chặn lệnh UPDATE và DELETE; migration 0003).

**Tiền** lưu kiểu `NUMERIC` và tính bằng `Decimal` trong Python, **không dùng số thực (float)**, vì float làm sai số tiền (ví dụ 0,1 + 0,2 không bằng đúng 0,3).

**Thời gian** lưu theo giờ UTC (giờ quốc tế), hiển thị theo giờ Việt Nam. Hạn sử dụng là kiểu ngày (`date`), so với ngày hôm nay theo giờ Việt Nam.

---

## Phần 5. Nghiệp vụ lõi

Đây là phần giảng viên hỏi nhiều nhất. Chi tiết đầy đủ ở `docs/spec/04-nghiep-vu.md`.

### 5.1 Máy trạng thái đơn hàng

Đơn hàng đi qua các trạng thái cố định. **Chỉ một hàm duy nhất được đổi trạng thái đơn** (`chuyen_trang_thai` trong `modules/ban_hang/trang_thai.py`), theo đúng một bảng 30 dòng (mỗi dòng: từ trạng thái nào, sang trạng thái nào, ai được làm, điều kiện gì). Chuyển trạng thái không có trong bảng bị từ chối.

Luồng chính:

```
Đặt COD ──────────────► Chờ xác nhận ──(dược sĩ xác nhận)──► Đã xác nhận
Đặt VNPay/MoMo ► Chờ thanh toán ──(IPN thành công)──┘                │
                                                     (kho bắt đầu soạn) ▼
                                                              Đang soạn hàng
                                                     (đóng gói, vận đơn) ▼
                                                               Chờ lấy hàng
                                              (shipper lấy hàng, webhook) ▼
                                                                 Đang giao
                                                   (giao thành công) ▼
                                                                  Đã giao
                                       (hết hạn đổi trả, job nền) ▼
                                                                  Hoàn tất
Ngoài ra: Đã hủy (từ nhiều trạng thái), Giao thất bại, Hoàn về kho.
Đơn thuốc: dược sĩ tạo ► Chờ khách xác nhận ► Đã xác nhận / Chờ thanh toán.
Bán tại quầy: tạo thẳng ở Hoàn tất.
```

Vì sao làm vậy:
- **Một chỗ duy nhất** nên không có đoạn code nào lén đổi trạng thái sai quy trình.
- Mỗi lần chuyển ghi một dòng `lich_su_trang_thai` (từ, đến, lúc nào, nguồn: người dùng / hệ thống / webhook vận chuyển / IPN thanh toán). Khách xem được dòng thời gian của đơn.
- **Chống bấm hai lần**: hàm khóa dòng đơn (`SELECT ... FOR UPDATE`) rồi đọc lại trạng thái. Hai dược sĩ cùng bấm "Xác nhận" thì người thứ hai nhận lỗi, tồn kho không bị trừ hai lần.
- **Sai người** (ví dụ kho bấm xác nhận đơn) trả lỗi 403; **sai trạng thái** trả lỗi 409.

### 5.2 Tồn kho: ba con số trên mỗi lô

| Cột | Nghĩa |
|---|---|
| `so_luong_ton` | Số lượng thật đang có trong khu bán |
| `so_luong_giu` | Số lượng đã được giữ cho đơn chưa xuất kho |
| `so_luong_biet_tru` | Hàng ở khu biệt trữ (khách trả, hư hỏng), không được bán, chờ hủy hoặc trả nhà cung cấp |

**Tồn khả dụng** = `so_luong_ton − so_luong_giu`. Đây là số còn bán được.

Vòng đời hàng trong một đơn:
1. **Giữ hàng** khi khách đặt: tăng `so_luong_giu`. Hàng chưa rời kho nên **chưa ghi thẻ kho**.
2. **Chốt lô / xuất kho** khi kho bắt đầu soạn: trừ cả `so_luong_ton` và `so_luong_giu`, **ghi thẻ kho** loại "xuất bán".
3. **Nhả giữ** nếu đơn hủy trước khi soạn: giảm `so_luong_giu`.
4. **Hoàn nhập** nếu hủy sau khi đã xuất nhưng hàng chưa rời kho, hoặc hàng hoàn còn nguyên: cộng lại `so_luong_ton` đúng lô cũ, ghi thẻ kho.

Vì sao tách "giữ" và "xuất": khách đặt xong có thể hủy, hoặc không thanh toán. Giữ hàng đảm bảo người khác không mua mất phần đó, nhưng chưa coi là đã bán.

**Thẻ kho (`bien_dong_kho`)**: mỗi lần tồn thật thay đổi là một dòng (loại, số lượng có dấu +/−, tồn sau, chứng từ, người làm). Bảng này **chỉ thêm, không sửa**. Báo cáo nhập xuất tồn được tính hoàn toàn từ thẻ kho.

**Chỉ một nơi được đổi tồn**: `modules/kho/ton_kho.py`. Mọi hàm trong đó:
- **Khóa các dòng lô** (`SELECT ... FOR UPDATE`) trước khi đổi, để hai người cùng mua món cuối cùng thì chỉ một người được.
- **Khóa theo thứ tự id tăng dần**, để tránh **deadlock** (hai giao dịch chờ khóa của nhau mãi mãi). Nếu giao dịch 1 khóa lô 5 rồi chờ lô 7, còn giao dịch 2 khóa lô 7 rồi chờ lô 5, cả hai kẹt. Khi ai cũng khóa lô nhỏ trước, chuyện này không xảy ra.
- Ghi thẻ kho **trong cùng giao dịch**, nên tồn và thẻ kho luôn khớp.

**Bất biến** (luôn đúng, có test kiểm tra sau mọi test về kho và đơn):
1. `0 ≤ so_luong_giu ≤ so_luong_ton`, và `so_luong_biet_tru ≥ 0`.
2. `so_luong_giu` của lô = tổng phân bổ đang giữ trên lô đó.
3. `so_luong_ton` của lô = tổng số lượng trên thẻ kho của lô đó.
4. Đơn đã soạn trở đi không còn phân bổ "đang giữ".
5. Tổng phân bổ của mỗi dòng đơn = số lượng × hệ số đơn vị.

### 5.3 FEFO (First Expired, First Out)

Khi giữ hàng, hệ thống chọn **lô có hạn dùng gần nhất trước** trong các lô được phép bán, lấy dần đến khi đủ số lượng. Câu SQL (spec 04 mục 3.1):

```sql
SELECT id, so_luong_ton - so_luong_giu AS kha_dung FROM lo_thuoc
WHERE san_pham_id = :sp AND trang_thai = ANY(:duoc_ban) AND han_su_dung > :hom_nay
  AND so_luong_ton - so_luong_giu > 0
ORDER BY han_su_dung, id
FOR UPDATE;
```

- **Đơn online** chỉ dùng lô "Đang bán". **Bán tại quầy** dùng được cả lô "Cận hạn" (dược sĩ trao tận tay, nói rõ hạn dùng).
- Không đủ hàng thì báo lỗi `HET_HANG` và **hủy toàn bộ đơn** (không tạo đơn thiếu).
- Kho được **đổi lô** khi soạn (ví dụ lô gợi ý bị móp hộp) nhưng phải ghi lý do.

Trạng thái lô: Đang bán → Cận hạn (còn dưới ngưỡng ngày cấu hình) → Hết hạn. Job nền chạy lúc 00:05 mỗi ngày để cập nhật. Admin có thể Khóa lô nghi vấn hoặc ra lệnh Thu hồi.

### 5.4 Tính tiền và mã giảm giá

Thứ tự (spec 04 mục 4):
1. **Tạm tính** = tổng (số lượng × đơn giá hiện tại) của các dòng.
2. **Dòng được giảm giá**: không phải thuốc kê đơn, và thuộc phạm vi khuyến mãi (toàn bộ / danh mục / sản phẩm).
3. **Điều kiện áp mã**: còn hạn, còn lượt, mỗi khách chưa dùng quá số lần, đạt giá trị đơn tối thiểu.
4. **Số tiền giảm**: theo phần trăm (có trần tối đa) hoặc số tiền cố định.
5. **Phân bổ phần giảm vào từng dòng** theo tỷ lệ tiền, làm tròn xuống đồng, phần dư dồn vào dòng cuối. Để khi trả hàng một phần, biết chính xác dòng đó được giảm bao nhiêu và hoàn đúng số tiền.
6. **Phí vận chuyển**: nhận tại nhà thuốc thì 0; giao tận nơi thì miễn phí nếu đủ ngưỡng, không thì lấy từ đơn vị vận chuyển.
7. **Tổng** = tạm tính − giảm giá + phí vận chuyển.

Quy tắc an toàn:
- **Server luôn tự tính lại giá**, không tin giá do giao diện gửi. Nếu giá đã đổi so với lúc khách xem, báo `GIA_DA_THAY_DOI` để khách xác nhận lại.
- **Thuốc kê đơn không được giảm giá** (luật về quảng cáo thuốc).
- Mã giảm giá cũng khóa dòng khi dùng, nên còn 1 lượt mà 2 người dùng cùng lúc thì chỉ 1 người được. Đơn bị hủy thì trả lại lượt.

### 5.5 Đơn thuốc kê đơn

Quy tắc: **thuốc kê đơn không vào giỏ hàng, không được giảm giá, không bán qua kênh điện thoại, và AI không được gợi ý**. Chặn ở tầng service và SQL, không chỉ ẩn nút.

Luồng:
1. Khách gửi ảnh đơn thuốc. Khách vãng lai phải xác thực số điện thoại bằng OTP.
2. AI (nếu bật) đọc ảnh, gợi ý danh sách thuốc. **AI chỉ gợi ý, dược sĩ quyết định.**
3. Dược sĩ **nhận xử lý** (yêu cầu bị khóa cho người đó; hai dược sĩ cùng nhận thì người sau bị từ chối).
4. Dược sĩ nhập/sửa danh sách thuốc, chọn sản phẩm, đánh dấu **checklist 5 mục**: có thông tin người bệnh; có thông tin bác sĩ; ngày kê còn hiệu lực; đơn chưa dùng (so ảnh trùng bằng mã băm); đã xem cảnh báo tương tác và dị ứng.
5. Hệ thống **tự cảnh báo tương tác thuốc** (bảng `tuong_tac_hoat_chat`) và **dị ứng** của khách. Mức nghiêm trọng bắt buộc ghi chú tư vấn.
6. Dược sĩ tạo đơn ("Chờ khách xác nhận"), khách xác nhận và thanh toán.
7. Khi đơn sang "Đang soạn hàng", đơn thuốc bị đánh dấu **đã sử dụng**, không dùng lại được.

### 5.6 Đổi trả và hoàn tiền

1. Khách gửi yêu cầu cho đơn **Đã giao**, trong thời hạn đổi trả, chọn dòng và số lượng, kèm ảnh/video. Chỉ nhận đổi trả **do lỗi nhà thuốc** (giao sai, hư hỏng, hết hạn, cận hạn) vì thuốc là hàng đặc biệt.
2. **Dược sĩ** xác minh, duyệt (chọn hướng: hoàn tiền hoặc gửi hàng thay thế), hệ thống tạo vận đơn trả hàng.
3. **Kho** nhận hàng, kiểm tra. Hàng trả vào **khu biệt trữ** (không bán lại), sau đó xử lý bằng phiếu hủy hoặc trả nhà cung cấp.
4. Hướng hoàn tiền: dược sĩ tạo giao dịch hoàn. Số tiền = thành tiền các dòng trả (đã trừ phần giảm giá phân bổ). Khách COD thì khai tài khoản ngân hàng nhận hoàn.
5. **Admin** xác nhận đã hoàn tiền (kèm chứng từ chuyển khoản). Thanh toán online thì hoàn qua cổng.

**Tách nhiệm vụ**: người duyệt đổi trả (dược sĩ) khác người xác nhận hoàn tiền (Admin). Tổng tiền hoàn không bao giờ vượt tổng đã thanh toán.

### 5.7 Tách nhiệm vụ trong kho

Phiếu điều chỉnh tồn, phiếu hủy, phiếu xuất trả nhà cung cấp: **nhân viên kho lập, Admin duyệt, người duyệt khác người lập**. Phiếu chỉ làm đổi tồn sau khi được duyệt. Chặn cả ở code và bằng ràng buộc CHECK trong CSDL. Mục đích: một người không thể tự ý xóa hàng khỏi kho để che mất mát.

---

## Phần 6. Phân quyền và bảo mật

### 6.1 Đăng nhập và token

- **Mật khẩu** băm bằng **Argon2id** (thuật toán chuyên cho mật khẩu, chậm có chủ đích để chống dò). Không ai đọc ngược được mật khẩu.
- Đăng nhập thành công nhận **access token** (JWT, hạn 15 phút) và **refresh token** (chuỗi ngẫu nhiên 256 bit, để trong cookie `HttpOnly` nên JavaScript không đọc được, chống bị đánh cắp qua XSS).
- **Refresh token xoay vòng**: mỗi lần làm mới cấp token mới, hủy token cũ. Nếu ai đó dùng lại token cũ (dấu hiệu bị đánh cắp), hệ thống **hủy toàn bộ phiên** của tài khoản đó.
- CSDL chỉ lưu mã băm SHA-256 của refresh token, lộ CSDL cũng không dùng được token.
- **Hai loại token**: khách (`aud = khach`) và nhân viên (`aud = noi_bo`). Token khách không dùng được cho API nội bộ và ngược lại.
- **Khóa tạm** sau 5 lần đăng nhập sai (15 phút). Số điện thoại không tồn tại cũng bị khóa giống hệt, để kẻ xấu không dò được số nào đã đăng ký.
- **OTP**: 6 số, lưu mã băm, hết hạn 5 phút, tối đa 5 lần thử, giới hạn số lần xin mã.

### 6.2 Phân quyền nhân viên (RBAC)

- Ba vai trò: `PHARMACIST` (dược sĩ), `WAREHOUSE` (kho), `ADMIN`.
- Danh sách quyền (ví dụ `order.confirm`, `stock.import`) nằm ở `docs/spec/data/quyen.yaml`, nạp vào bảng `quyen`. Mỗi vai trò được gán quyền ở mức **đầy đủ** hoặc **chỉ xem** (bảng `vai_tro_quyen`).
- **Mọi API nội bộ** (`/api/v1/noi-bo/...`) phải khai báo quyền cần có, ví dụ `Depends(yeu_cau_quyen("order.confirm"))`. Thiếu quyền trả 403.
- Quyền đọc từ CSDL mỗi yêu cầu (có lưu tạm 60 giây), nên Admin đổi phân quyền thì có hiệu lực gần như ngay. Khóa tài khoản có hiệu lực ngay lập tức.
- Admin chỉ **xem** đơn hàng và chứng từ kho, không thao tác. Admin không sửa được nội dung chuyên môn của dược sĩ. Admin không tự khóa hay tự hạ quyền của chính mình, và hệ thống luôn còn ít nhất một Admin.

### 6.3 Quyền của khách

- Khách chỉ thấy dữ liệu của mình. Mã khách luôn lấy từ token.
- Khách A truy cập đơn của khách B nhận **404 (Không tìm thấy)**, không phải 403. Lý do: trả 403 sẽ tiết lộ "đơn này có tồn tại".

### 6.4 Dữ liệu sức khỏe (theo Nghị định 13/2023 về bảo vệ dữ liệu cá nhân)

- **Bệnh nền được mã hóa** bằng Fernet (khóa `KHOA_MA_HOA`). Xem trực tiếp CSDL chỉ thấy chuỗi lộn xộn.
- **Admin và kho không bao giờ đọc được.** Có test khẳng định mọi phản hồi API cho họ không chứa các trường này.
- **Dược sĩ chỉ đọc qua một "hàm cổng"** (`modules/suc_khoe/dich_vu.py::duoc_doc_ho_so_suc_khoe`), khi đồng thời: là dược sĩ, khách đã đồng ý chia sẻ, và dược sĩ đang trực tiếp tư vấn cho khách đó (đang xử lý đơn thuốc hoặc đang chat). Mỗi lần đọc ghi nhật ký.
- Các kiểm tra tự động (cảnh báo dị ứng) chỉ trả **cảnh báo**, không trả hồ sơ.
- Không gửi tên, số điện thoại của khách cho AI.

### 6.5 Các biện pháp bảo mật khác

| Biện pháp | Chống lại |
|---|---|
| Truy vấn tham số hóa qua SQLAlchemy | SQL injection |
| Header bảo mật (CSP, X-Frame-Options, nosniff...) | XSS, nhúng trang vào iframe (clickjacking) |
| Không hiển thị nội dung HTML thô do người dùng nhập | XSS |
| Kiểm tra loại tệp bằng nội dung (magic bytes), đặt tên tệp ngẫu nhiên, giới hạn kích thước | Tải lên tệp độc hại |
| Ảnh đơn thuốc lưu khu riêng tư, chỉ xem qua đường dẫn có chữ ký và có hạn | Lộ ảnh đơn thuốc |
| Giới hạn tần suất (đăng nhập, OTP, chat, tra cứu ảnh) | Dò mật khẩu, spam, đốt tiền AI |
| Chữ ký HMAC trên IPN thanh toán | Giả mạo thông báo "đã thanh toán" |
| Nhật ký hệ thống không sửa/xóa được | Xóa dấu vết |
| Lỗi 500 trả thông báo chung kèm mã yêu cầu, không lộ chi tiết | Lộ thông tin hệ thống |
| `MOI_TRUONG=production` từ chối khởi động nếu còn cổng giả, thiếu khóa bí mật | Triển khai nhầm cấu hình demo |

---

## Phần 7. AI

Chi tiết ở `docs/spec/07-ai.md`. Hệ thống có 9 mô-đun AI (AI01 đến AI09). Mỗi mô-đun bật/tắt được ở trang Cấu hình AI. **Khi AI tắt hoặc lỗi, chức năng tự quay về cách thường** (tìm kiếm dùng từ khóa, chat chuyển dược sĩ, tra ảnh báo tạm không khả dụng).

| Mã | Chức năng | Kỹ thuật |
|---|---|---|
| AI01 | Tìm kiếm lai | Ghép tìm từ khóa (trigram, gõ sai vẫn ra) với tìm theo nghĩa (vector) bằng Reciprocal Rank Fusion |
| AI02 | Phân loại ý định câu hỏi | Claude trả JSON: ý định, có nguy hiểm không, có cần dược sĩ không, độ tự tin |
| AI03 | Chatbot trả lời | Claude với các "tool" chỉ đọc dữ liệu thật |
| AI04 | Chuyển dược sĩ | Tóm tắt hội thoại cho dược sĩ, chat trực tiếp qua WebSocket |
| AI05 | Đọc ảnh hộp thuốc | Claude đọc ảnh, khớp sản phẩm theo số đăng ký hoặc tên |
| AI06 | Đọc ảnh đơn thuốc | Claude trích danh sách thuốc, gợi ý sản phẩm; dược sĩ quyết định |
| AI07 | Gợi ý sản phẩm | Cùng hoạt chất, cùng danh mục, gần nhau theo vector; "dành cho bạn" theo lịch sử xem |
| AI08 | Luật mua kèm | Thống kê: support, confidence, lift trên đơn 180 ngày |
| AI09 | Dự báo nhu cầu nhập | Holt-Winters khi đủ 12 tuần dữ liệu, ít hơn thì trung bình trượt có trọng số |

### 7.1 Chatbot hoạt động thế nào

Mỗi tin nhắn của khách (`POST /api/v1/tu-van/chat`, trả lời dạng luồng SSE để chữ hiện dần):
1. Kiểm tra giới hạn tần suất và **ngân sách tiền AI mỗi ngày**.
2. **Kiểm tra dấu hiệu nguy hiểm bằng luật** (ví dụ "đau ngực", "khó thở", "co giật") **trước khi gọi AI**. Trùng thì trả câu cố định: dừng tư vấn, khuyên đi khám ngay hoặc gọi 115. Không gọi Claude. (`ai/dau_hieu.py`)
3. **AI02** phân loại ý định. Nguy hiểm thì như bước 2; cần dược sĩ hoặc AI không tự tin thì đề nghị khách gặp dược sĩ.
4. **AI03** trả lời. Claude **không tự bịa**: nó được cấp các "tool" để tra dữ liệu thật: tìm sản phẩm, xem sản phẩm, tra kho tri thức (nội dung chuyên môn đã được dược sĩ duyệt), tra chính sách, xem đơn hàng của chính khách, đề nghị gặp dược sĩ. Đây là kỹ thuật **RAG** (truy xuất rồi mới sinh câu trả lời).
5. Gửi kèm **thẻ sản phẩm** để khách bấm vào.

**Nguyên tắc an toàn (quan trọng nhất, giảng viên rất hay hỏi):**
- AI **không chẩn đoán, không đưa liều cá nhân hóa, không gợi ý thuốc kê đơn**.
- **Chặn bằng code, không chỉ bằng lời dặn trong prompt.** Các tool lọc bỏ thuốc kê đơn ngay trong câu SQL (`modules/cua_hang/loc_an_toan.py`). Dù AI bị "lừa" (prompt injection) cũng không lấy được thuốc kê đơn để gợi ý. Thẻ sản phẩm gửi khách chỉ gồm sản phẩm thật sự có trong kết quả tool của lượt đó.
- Tool **chỉ đọc**, AI không có cách nào đặt hàng hay sửa dữ liệu.
- Nội dung lấy từ CSDL được coi là dữ liệu; prompt nói rõ không làm theo chỉ dẫn nằm trong dữ liệu.
- Mỗi câu trả lời kèm dòng: thông tin chỉ mang tính tham khảo, không thay thế dược sĩ/bác sĩ.
- Không gửi tên, số điện thoại của khách cho Claude; hồ sơ sức khỏe chỉ dùng khi khách đồng ý và chỉ gửi phần cần (dị ứng hoạt chất, mang thai, nhóm tuổi). Ảnh gửi đi được xóa thông tin EXIF.

**Mở file nào để xem:** `backend/app/ai/chatbot.py`, `ai/claude.py` (cổng duy nhất gọi Claude), `ai/prompts/chat_he_thong.md` (lời dặn cho AI), `ai/dau_hieu.py`.

### 7.2 Embedding và tìm kiếm theo nghĩa

- **Embedding**: biến một đoạn văn bản thành một dãy 1024 con số (vector) sao cho các đoạn **cùng ý nghĩa** có vector **gần nhau**. Ví dụ "thuốc hạ sốt" gần với "Paracetamol" dù không chung chữ nào.
- Kho tri thức (`tai_lieu_tri_thuc`) gồm đoạn tổng quan mỗi sản phẩm, các mục nội dung chuyên môn đã duyệt, bài viết, chính sách. Mỗi đoạn có vector, lưu bằng `pgvector`, tìm nhanh bằng chỉ mục HNSW.
- **Giá và tồn kho không đưa vào vector**: tool luôn đọc trực tiếp từ CSDL để không bao giờ trả giá cũ.
- **Reciprocal Rank Fusion (RRF)**: ghép hai bảng xếp hạng (từ khóa và ngữ nghĩa). Điểm mỗi sản phẩm = tổng 1/(60 + thứ hạng) trong từng bảng. Sản phẩm đứng cao ở cả hai bảng sẽ lên đầu.

### 7.3 Dự báo nhu cầu (AI09)

- Dữ liệu: số lượng đã xuất mỗi tuần của từng sản phẩm.
- **Holt-Winters** (làm trơn hàm mũ có xu hướng) khi có từ 12 tuần dữ liệu; ít hơn thì **trung bình trượt có trọng số 4-3-2-1** (tuần gần nhất nặng nhất).
- Đo độ chính xác bằng **MAPE** (sai số phần trăm trung bình) trên 4 tuần gần nhất.
- **Đề xuất nhập** = max(0, dự báo 30 ngày + tồn tối thiểu − tồn khả dụng).
- Chạy tự động mỗi thứ Hai lúc 04:00; kho xem ở trang "Đề xuất nhập từ AI".

### 7.4 Luật mua kèm (AI08)

Với mỗi cặp sản phẩm A, B trong các đơn hoàn tất 180 ngày:
- **support** = số đơn có cả A và B / tổng số đơn.
- **confidence** = support(A, B) / support(A): mua A thì bao nhiêu phần trăm mua B.
- **lift** = confidence / support(B): lớn hơn 1 nghĩa là A và B thật sự hay đi cùng nhau, không phải ngẫu nhiên.
- Giữ cặp có support ≥ 0,005, confidence ≥ 0,1, lift > 1. Hiện ở giỏ hàng ("thường mua kèm").

### 7.5 Bản giả khi chạy demo

`AI_GIA_LAP=true` dùng một client giả trả lời theo kịch bản, không gọi mạng; `EMBEDDING_GIA_LAP=true` dùng vector giả sinh từ mã băm. Lý do: test và demo chạy được mọi lúc, không tốn tiền, kết quả lặp lại được. Muốn dùng thật thì đặt hai biến về `false` và có khóa API.

---

## Phần 8. Tích hợp bên ngoài

- **VNPay, MoMo**: khách được chuyển sang cổng thanh toán. Cổng báo kết quả về server qua **IPN** (một yêu cầu từ server cổng gọi về). Server **kiểm tra chữ ký HMAC** (VNPay dùng SHA-512, MoMo dùng SHA-256) bằng khóa bí mật, kiểm tra số tiền khớp, và **chống xử lý trùng** bằng mã giao dịch của cổng. Không tin trang kết quả hiển thị cho khách, vì khách có thể sửa đường dẫn.
- **GHN** (giao hàng): tạo vận đơn khi đóng gói; GHN báo trạng thái qua **webhook** (lấy hàng, đang giao, giao thành công, thất bại, hoàn hàng), có token xác thực.
- **SMS, email**: gửi OTP và thông báo. Bản demo ghi SMS ra log và gửi email tới Mailpit.
- **Idempotency-Key**: đặt hàng và tạo thanh toán nhận một mã ngẫu nhiên do giao diện tạo; gửi lại cùng mã (mạng chập chờn, bấm hai lần) thì trả đúng kết quả cũ, không tạo đơn trùng.

**Mở file nào để xem:** `backend/app/tich_hop/thanh_toan/vnpay.py`, `momo.py`, `backend/app/modules/thanh_toan/dich_vu.py::xu_ly_ipn`.

---

## Phần 9. Job nền

Chạy bằng `uv run python -m app.jobs` (process riêng). Mỗi job có khóa (advisory lock của PostgreSQL) để không chạy chồng hai bản cùng lúc.

| Job | Lịch | Việc |
|---|---|---|
| HT01 | 00:05 mỗi ngày | Cập nhật trạng thái lô (cận hạn, hết hạn) |
| HT02 | sau HT01 | Cảnh báo tồn thấp, cận hạn cho kho |
| HT03 | mỗi phút | Hủy đơn quá hạn thanh toán hoặc quá hạn khách xác nhận, nhả hàng đã giữ |
| HT08 | mỗi phút | Tự hoàn tất đơn đã giao quá hạn đổi trả; hủy đơn quá hạn nhận tại quầy; nhả khóa yêu cầu đơn thuốc bị bỏ dở; đóng chat không hoạt động |
| AI06 | mỗi phút | AI đọc ảnh đơn thuốc mới gửi |
| AI08 | Chủ nhật 03:00 | Tính luật mua kèm |
| AI09 | Thứ Hai 04:00 | Dự báo nhu cầu, đề xuất nhập |

---

## Phần 10. Kiểm thử

| Loại | Số lượng | Công cụ | Kiểm tra gì |
|---|---|---|---|
| Backend | khoảng 2.950 test | pytest, chạy trên PostgreSQL thật | Mọi tiêu chí chấp nhận, nghiệp vụ, phân quyền, bảo mật |
| Frontend | 988 test | vitest + Testing Library | Logic giao diện, form, điều hướng, ẩn hiện theo quyền |
| Trên trình duyệt thật | 4 kịch bản | Playwright | 4 luồng chính từ đầu đến cuối qua nhiều vai trò |

Các loại test đáng nói:
- **Test ma trận phân quyền** (`tests/phan_quyen/`): tự đọc `quyen.yaml`, thử **mọi API nội bộ với mọi vai trò**. Vai trò không có quyền phải nhận 403. Có test bắt lỗi nếu ai đó thêm API nội bộ mà quên khai báo quyền.
- **Test bất biến tồn kho** (`tests/bat_bien/`): sau mọi test về kho và đơn, kiểm tra 5 bất biến ở Phần 5.2.
- **Test tranh chấp**: hai người cùng mua món cuối cùng → đúng một người được; hai dược sĩ cùng nhận một đơn thuốc → một người được; không deadlock.
- **Test không lộ dữ liệu**: phản hồi cho Admin không chứa dữ liệu sức khỏe; phản hồi cho dược sĩ không chứa giá vốn.
- **Test không gọi mạng**: AI, cổng thanh toán, GHN, SMS đều dùng bản giả.

Mỗi test chạy trong một giao dịch rồi hủy (rollback), nên test không ảnh hưởng nhau và chạy theo thứ tự nào cũng được.

---

## Phần 11. Câu hỏi giảng viên thường hỏi (kèm gợi ý trả lời)

Đừng học thuộc nguyên văn. Hiểu ý rồi trả lời bằng lời của bạn.

### Tổng quan và quy trình

**1. Em làm dự án này theo quy trình nào?**
Viết đặc tả trước (`docs/spec/`), gồm schema CSDL, phân quyền, bảng chuyển trạng thái, API, quy tắc AI. Sau đó chia thành 56 task trong 9 giai đoạn (P0 nền tảng đến P8 hoàn thiện) ở `docs/spec/11-lo-trinh.md`, mỗi task có tiêu chí chấp nhận và test tương ứng. Quyết định thiết kế ghi lại ở `docs/spec/12-quyet-dinh.md`.

**2. Phạm vi không làm những gì?**
Nhiều chi nhánh/nhiều kho, kế toán và hóa đơn điện tử, tích điểm, kết nối cổng dữ liệu dược quốc gia, khám bệnh từ xa, ứng dụng di động.

**3. Vì sao chọn FastAPI chứ không phải Django, Spring hay Node?**
Python mạnh về AI và thống kê (statsmodels, sentence-transformers, SDK Claude), dùng chung một ngôn ngữ cho cả API và AI. FastAPI nhẹ, hỗ trợ async, tự sinh tài liệu API, kiểm tra dữ liệu bằng Pydantic. Django mạnh về trang quản trị có sẵn nhưng nặng hơn và giao diện em tách riêng bằng React.

**4. Vì sao PostgreSQL mà không MySQL hay MongoDB?**
Cần giao dịch và khóa dòng chặt chẽ cho tồn kho và tiền, cần ràng buộc CHECK, cần `pgvector` để lưu vector cho AI ngay trong cùng CSDL (không phải dựng thêm một CSDL vector riêng), cần `pg_trgm` và `unaccent` để tìm kiếm tiếng Việt không dấu, gõ sai vẫn ra. MongoDB không hợp với dữ liệu quan hệ nhiều ràng buộc như đơn hàng.

### Nghiệp vụ và CSDL

**5. Hai khách cùng mua hộp thuốc cuối cùng thì sao?**
Hàm giữ hàng khóa dòng lô bằng `SELECT ... FOR UPDATE`. Giao dịch thứ hai phải chờ giao dịch thứ nhất xong, đọc lại thấy hết hàng và nhận lỗi `HET_HANG`. Có test chạy hai đơn song song thật để chứng minh đúng một đơn thành công.

**6. Deadlock là gì, em tránh thế nào?**
Hai giao dịch giữ khóa mà mỗi bên chờ khóa của bên kia nên kẹt mãi. Em luôn khóa các lô **theo id tăng dần**, nên mọi giao dịch khóa theo cùng một thứ tự, không thể tạo vòng chờ. Có test giữ hàng song song trên hai lô theo thứ tự ngược nhau.

**7. Vì sao tách "giữ hàng" và "xuất kho"?**
Khách đặt xong có thể không thanh toán hoặc hủy. Giữ hàng đảm bảo người khác không mua mất, nhưng chưa trừ tồn thật và chưa ghi thẻ kho. Chỉ khi kho bắt đầu soạn mới trừ tồn thật. Như vậy thẻ kho phản ánh đúng hàng thực sự rời kệ.

**8. FEFO là gì, vì sao không FIFO?**
FEFO: lô hết hạn sớm nhất xuất trước. Với thuốc, hạn dùng quan trọng hơn ngày nhập; lô nhập sau vẫn có thể hết hạn sớm hơn. FEFO giảm hàng hết hạn phải hủy.

**9. Làm sao em biết tồn kho luôn đúng?**
Có 5 bất biến (Phần 5.2), ví dụ tồn của lô bằng tổng thẻ kho của lô đó. Test kiểm tra các bất biến này sau mọi test liên quan kho và đơn. Thêm nữa, chỉ một module được đổi tồn và mọi thay đổi ghi thẻ kho trong cùng giao dịch.

**10. Tại sao tiền không dùng float?**
Float là số nhị phân xấp xỉ, ví dụ 0,1 + 0,2 = 0,30000000000000004. Cộng dồn nhiều đơn sẽ lệch tiền. Em dùng `Decimal` trong Python và `NUMERIC` trong CSDL, làm tròn về đồng ở một chỗ duy nhất (`core/tien.py`).

**11. Mã giảm giá áp cho đơn có thuốc kê đơn thế nào?**
Dòng thuốc kê đơn không được giảm (quy định về quảng cáo, khuyến mãi thuốc). Phần giảm chỉ tính trên các dòng hợp lệ và phân bổ vào từng dòng để khi trả hàng một phần thì hoàn đúng số tiền.

**12. Máy trạng thái có lợi gì?**
Một chỗ duy nhất đổi trạng thái, theo bảng 30 dòng. Không thể nhảy cóc (ví dụ từ "Chờ xác nhận" sang "Đã giao"), mỗi bước kiểm tra đúng người, đúng điều kiện, và ghi lịch sử. Dễ kiểm thử: mỗi dòng của bảng có test.

**13. Đơn thuốc đã dùng rồi, khách gửi lại ảnh cũ thì sao?**
Ảnh được tính mã băm. Ảnh trùng với đơn đã sử dụng thì hệ thống cảnh báo dược sĩ. Đơn liên kết sang "Đang soạn hàng" thì đơn thuốc bị đánh dấu đã sử dụng.

**14. Thu hồi lô hoạt động thế nào?**
Admin ra lệnh thu hồi một lô. Hệ thống gỡ lô đó khỏi các đơn chưa xuất, và nhờ bảng `phan_bo_lo` liệt kê được mọi đơn đã giao có hàng từ lô đó để dược sĩ liên hệ khách. Kho thực hiện thu hồi hàng còn trong kho.

### Phân quyền và bảo mật

**15. Phân biệt xác thực và phân quyền?**
Xác thực: bạn là ai (đăng nhập, token). Phân quyền: bạn được làm gì (vai trò, mã quyền). Mỗi API nội bộ khai báo quyền cần có; backend kiểm tra mỗi yêu cầu.

**16. Nếu người dùng sửa giao diện để hiện nút ẩn thì sao?**
Ẩn nút chỉ là lớp phụ cho tiện. Backend vẫn kiểm tra quyền ở mọi API, gọi trực tiếp API mà không có quyền thì nhận 403. Test ma trận phân quyền thử mọi API với mọi vai trò.

**17. Vì sao truy cập đơn của người khác trả 404 chứ không phải 403?**
403 ngụ ý "đơn này có tồn tại nhưng bạn không được xem", giúp kẻ xấu dò mã đơn. 404 không tiết lộ gì.

**18. JWT là gì? Sao cần cả refresh token?**
JWT là token có chữ ký, server kiểm tra chữ ký là biết token hợp lệ mà không cần tra CSDL. Access token sống ngắn (15 phút) để nếu bị lộ thì thiệt hại ít. Refresh token sống lâu hơn, nằm trong cookie HttpOnly (JavaScript không đọc được), dùng để xin access token mới, và xoay vòng để phát hiện bị đánh cắp.

**19. Dữ liệu sức khỏe được bảo vệ thế nào?**
Mã hóa bệnh nền; Admin và kho không đọc được; dược sĩ chỉ đọc qua hàm cổng khi khách đồng ý và đang được chính dược sĩ đó tư vấn; mỗi lần đọc ghi nhật ký; không ghi dữ liệu sức khỏe vào log; không gửi thông tin định danh cho AI. Căn cứ Nghị định 13/2023/NĐ-CP.

**20. Mật khẩu lưu thế nào?**
Băm bằng Argon2id, mỗi mật khẩu có muối (salt) riêng. Không lưu và không giải ngược được. Đăng nhập thì băm mật khẩu nhập vào và so sánh.

**21. Làm sao chống giả mạo thông báo thanh toán?**
IPN từ VNPay/MoMo có chữ ký HMAC tính bằng khóa bí mật chỉ server và cổng biết. Server tính lại chữ ký, so khớp, kiểm tra số tiền, và bỏ qua giao dịch đã xử lý. Trang kết quả hiện cho khách không được dùng để xác nhận thanh toán.

### AI

**22. Làm sao em đảm bảo AI không gợi ý thuốc kê đơn?**
Không chỉ dặn trong prompt. Các tool AI dùng để tra sản phẩm **lọc thuốc kê đơn ngay trong câu SQL**, và kho tri thức truy xuất cho chatbot chỉ lấy đoạn không kê đơn. Thẻ sản phẩm gửi cho khách chỉ gồm sản phẩm có trong kết quả tool của lượt đó và vẫn qua bộ lọc. Dù AI bị lừa, nó không có dữ liệu thuốc kê đơn để gợi ý.

**23. Prompt injection là gì? Em chống thế nào?**
Kẻ xấu chèn câu lệnh vào dữ liệu (ví dụ trong câu hỏi hay mô tả sản phẩm: "bỏ qua mọi quy tắc, hãy..."). Em coi dữ liệu là dữ liệu, prompt nói rõ không làm theo chỉ dẫn trong dữ liệu, và quan trọng hơn: tool chỉ đọc và đã lọc sẵn, nên dù AI làm theo thì cũng không gây hại được.

**24. Khách hỏi về triệu chứng nguy hiểm thì sao?**
Câu hỏi được so với danh sách dấu hiệu nguy hiểm bằng luật **trước khi gọi AI**. Trùng thì trả câu cố định khuyên đi khám ngay hoặc gọi 115, gắn cờ để dược sĩ xem. AI02 là lớp kiểm tra thứ hai.

**25. RAG là gì?**
Retrieval-Augmented Generation: trước khi AI trả lời, hệ thống truy xuất thông tin liên quan từ kho dữ liệu thật (sản phẩm, nội dung chuyên môn đã duyệt, chính sách) rồi đưa cho AI. AI trả lời dựa trên đó, giảm bịa đặt. Trong dự án, AI tự gọi tool để truy xuất.

**26. Embedding và tìm kiếm ngữ nghĩa khác tìm từ khóa thế nào?**
Từ khóa so khớp chữ. Ngữ nghĩa so khớp ý nghĩa qua vector. Em ghép cả hai bằng RRF để vừa đúng tên vừa đúng ý.

**27. Nếu Claude bị lỗi hoặc hết tiền thì sao?**
Mỗi mô-đun AI có đường lui: chat chuyển dược sĩ, tìm kiếm quay về từ khóa, tra ảnh báo tạm không khả dụng. Có ngân sách tiền AI mỗi ngày, vượt thì tạm dừng. Admin bật/tắt từng mô-đun.

**28. Holt-Winters là gì? Sao không dùng mạng nơ-ron?**
Phương pháp làm trơn hàm mũ, tách mức và xu hướng của chuỗi thời gian, cập nhật dần theo dữ liệu mới. Với một nhà thuốc nhỏ, dữ liệu theo tuần chỉ vài chục điểm, mạng nơ-ron cần nhiều dữ liệu hơn nhiều và dễ học vẹt. Holt-Winters đơn giản, giải thích được, đo bằng MAPE. Ít hơn 12 tuần thì dùng trung bình trượt có trọng số.

**29. AI có tự duyệt đơn thuốc không?**
Không. AI chỉ đọc ảnh và gợi ý danh sách thuốc. Dược sĩ xác nhận hoặc sửa từng dòng, đánh dấu checklist, và quyết định tạo đơn hay từ chối.

**30. Chi phí dùng Claude?**
Tính theo số token vào/ra. Hệ thống đếm token và chi phí cho từng lượt, có ngân sách mỗi ngày cấu hình được. Prompt hệ thống cố định nên dùng được cache để giảm chi phí.

### Kiểm thử và triển khai

**31. Em kiểm thử thế nào?**
Xem Phần 10. Nhấn mạnh: test chạy trên PostgreSQL thật (không giả lập bằng SQLite) để kiểm được khóa dòng và ràng buộc; có test ma trận phân quyền, bất biến tồn kho, tranh chấp; 4 kịch bản Playwright trên trình duyệt thật.

**32. Sao test không gọi Claude thật?**
Để test nhanh, miễn phí, kết quả lặp lại được, và không phụ thuộc mạng. Mỗi dịch vụ ngoài có adapter giả với cùng giao diện.

**33. Triển khai lên máy chủ thế nào?**
Có `docker-compose.prod.yml`: CSDL, migration, backend, worker, và nginx phục vụ giao diện và chuyển tiếp API. Cần HTTPS phía trước, khóa bí mật thật, và tài khoản thật của cổng thanh toán, giao hàng, SMS. Xem README mục Triển khai.

### Câu hỏi khó

**34. Hệ thống chịu được bao nhiêu người dùng?**
Em đã đo với dữ liệu gấp khoảng 100 lần dữ liệu mẫu (5.000 sản phẩm, 50.000 đơn, 400.000 dòng nhật ký): các trang chính trả lời trong khoảng 15 đến 140 mili giây. Chưa làm kiểm thử tải nhiều người dùng đồng thời. Một số bộ đếm (giới hạn tần suất, idempotency) đang lưu trong bộ nhớ một tiến trình; chạy nhiều máy chủ thì cần chuyển sang Redis.

**35. Nếu cần nhiều chi nhánh thì phải sửa gì?**
Thêm bảng chi nhánh/kho, gắn lô và tồn theo kho, phiếu chuyển kho, chọn kho khi giữ hàng. Hiện thiết kế giả định một kho nên đây là thay đổi lớn ở module kho và đơn hàng.

---

## Phần 12. Hạn chế và hướng phát triển (nói thật khi được hỏi)

Giảng viên đánh giá cao việc bạn biết hệ thống mình còn thiếu gì. Đừng giấu:
- Chưa chạy thử với Claude API thật, mô hình BGE-M3 thật, VNPay/MoMo/GHN sandbox thật; test và demo dùng bản giả.
- Chưa tích hợp nhà cung cấp SMS thật.
- Chưa đánh giá chất lượng chatbot với Claude thật trên bộ câu hỏi chuẩn.
- Một số bộ đếm lưu trong bộ nhớ một tiến trình, chưa hợp khi chạy nhiều máy chủ.
- Kẻ xấu vẫn có thể cố tình đăng nhập sai để khóa tạm tài khoản người khác (cần CAPTCHA).
- Cấu hình Docker cho triển khai chưa được chạy thử.

Hướng phát triển: nhiều chi nhánh, tích điểm, hóa đơn điện tử, ứng dụng di động, kết nối cổng dữ liệu dược quốc gia, đánh giá chatbot định kỳ.

---

## Phần 13. Bảng tra nhanh: giảng viên hỏi "chỉ code chỗ đó" thì mở file nào

| Giảng viên hỏi | Mở file |
|---|---|
| Máy trạng thái đơn hàng | `backend/app/modules/ban_hang/trang_thai.py` (bảng `BANG_CHUYEN`) |
| Đặt hàng | `backend/app/modules/ban_hang/dat_hang.py` |
| Giữ hàng, FEFO, khóa lô | `backend/app/modules/kho/ton_kho.py` |
| Tính tiền, làm tròn | `backend/app/core/tien.py`, module `khuyen_mai` |
| Phân quyền | `backend/app/core/phan_quyen.py`, `docs/spec/data/quyen.yaml` |
| Đăng nhập, JWT, mật khẩu | `backend/app/core/bao_mat.py`, `backend/app/modules/tai_khoan/dang_nhap.py` |
| Mã hóa dữ liệu sức khỏe | `backend/app/core/ma_hoa.py`, `backend/app/modules/suc_khoe/dich_vu.py` |
| Chatbot | `backend/app/ai/chatbot.py`, `backend/app/ai/prompts/chat_he_thong.md` |
| Lọc thuốc kê đơn cho AI | `backend/app/modules/cua_hang/loc_an_toan.py` |
| Tìm kiếm lai | `backend/app/modules/cua_hang/tim_kiem_lai.py` |
| Dự báo | `backend/app/modules/du_bao/mo_hinh.py` |
| Thanh toán, chữ ký IPN | `backend/app/tich_hop/thanh_toan/vnpay.py`, `backend/app/modules/thanh_toan/dich_vu.py` |
| Cấu trúc bảng | `backend/app/models/`, `docs/database/ERD_da_chinh_sua.dbml` |
| Test phân quyền | `backend/tests/phan_quyen/` |
| Test bất biến tồn kho | `backend/tests/bat_bien/` |
| Kịch bản trình duyệt | `frontend/e2e/` |

Mở file trong VS Code (cài từ https://code.visualstudio.com, rồi mở thư mục dự án). Bấm **Ctrl+P** và gõ tên file để mở nhanh; bấm **Ctrl+Shift+F** để tìm một chữ trong toàn dự án.
