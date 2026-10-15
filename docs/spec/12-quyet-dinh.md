# 12. Nhật ký quyết định

Mỗi quyết định ảnh hưởng đến thiết kế, nghiệp vụ hoặc công nghệ được ghi một mục theo mẫu dưới đây. Quyết định mới thêm vào **cuối file**, không sửa mục cũ. Nếu đổi ý thì viết mục mới và ghi "Thay thế QĐ-xx".

```
## QĐ-xx: <tiêu đề ngắn> (YYYY-MM-DD, task Tx.y)
- Bối cảnh: ...
- Quyết định: ...
- Hệ quả: ... (file spec / code bị ảnh hưởng)
```

## QĐ-01: Phạm vi 3 tác nhân, 1 nhà thuốc = 1 kho (2026-10-15)
- **Bối cảnh:** Đồ án kiểu Long Châu nhưng thu gọn phạm vi.
- **Quyết định:**
  - 3 tác nhân Khách hàng / Nhân viên / Quản trị, chia thành 5 nhóm người dùng.
  - Nhân viên chia vai trò bằng RBAC; mỗi nhân viên có 1 vai trò.
  - Không làm chi nhánh hay chuyển kho.
- **Hệ quả:** spec 00, 03. `nhan_vien.vai_tro_id` giữ quan hệ N-1.

## QĐ-02: ERD đã chỉnh sửa là nguồn sự thật (2026-10-15)
- **Bối cảnh:** ERD gốc có 1 lỗi cú pháp và thiếu chỗ lưu một số nghiệp vụ (biệt trữ, thẻ kho, vận đơn trả hàng, hoàn tiền...).
- **Quyết định:** dùng `docs/database/ERD_da_chinh_sua.dbml` (65 bảng). Mọi thay đổi ghi `[DBxx]`, đối chiếu sheet "Đánh giá Database" trong file Excel.
- **Hệ quả:** spec 02. Lệnh `/doi-schema`.

## QĐ-03: Backend FastAPI + SQLAlchemy async (2026-10-15)
- **Bối cảnh:** Sheet chỉ ghi "Python".
- **Quyết định:**
  - FastAPI, SQLAlchemy 2 async (asyncpg), Alembic, Pydantic v2, `uv`.
  - Job nền: APScheduler ở process riêng.
  - Chat dược sĩ: WebSocket. Chat AI: SSE.
- **Hệ quả:** spec 01, 06; `backend/CLAUDE.md`.

## QĐ-04: Frontend React + Vite + Ant Design (2026-10-15)
- **Quyết định:**
  - TypeScript, Ant Design (`vi_VN`), TanStack Query, React Router, Zustand.
  - Client API sinh từ OpenAPI (`openapi-typescript` + `openapi-fetch`).
  - Một ứng dụng duy nhất chia 3 khu theo đường dẫn.
- **Hệ quả:** spec 09; `frontend/CLAUDE.md`.

## QĐ-05: Claude API cho LLM, BGE-M3 tự host cho embedding (2026-10-15)
- **Quyết định:**
  - Model `claude-opus-5-5` (biến `CLAUDE_MODEL`), đặt `effort` rõ ràng cho từng tác vụ.
  - Bật `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`) để tự chạy lại khi bị bộ lọc an toàn từ chối.
  - Embedding `BAAI/bge-m3`, 1024 chiều, khớp `vector(1024)` của ERD.
- **Hệ quả:** spec 07. Đổi model là quyết định chi phí của nhóm, phải ghi một QĐ mới.

## QĐ-06: Mọi tích hợp ngoài có adapter giả (2026-10-15)
- **Quyết định:**
  - VNPay, MoMo, GHN, SMS/email đi qua interface có bản giả chạy offline.
  - Dev và test mặc định dùng bản giả; sandbox thật bật bằng biến môi trường.
- **Hệ quả:** spec 08. Có thể demo đầy đủ luồng mà không cần tài khoản đối tác.

## QĐ-07: Lịch sử chat gửi lại Claude chỉ gồm text (2026-10-15)
- **Bối cảnh:** `tin_nhan` chỉ lưu nội dung text. Trên Opus 5.5, thinking blocks gắn với đúng hội thoại đã tạo ra chúng.
- **Quyết định:**
  - Giữa các lượt, chỉ gửi lại text của các lượt trước.
  - Trong cùng một lượt có gọi tool, append nguyên `response.content`.
  - System prompt và danh sách tool cố định.
- **Hệ quả:** spec 07 mục 2. Không cần cột lưu nội dung thô của Claude.

## QĐ-08: Access token chỉ ở bộ nhớ trình duyệt, làm mới bằng cookie refresh (2026-10-15, task T0.6, T0.7)
- **Quyết định:**
  - Frontend giữ access token và hồ sơ trong store Zustand, KHÔNG persist (không localStorage/sessionStorage). Tải lại trang thì lấy lại token bằng refresh token trong cookie httpOnly.
  - Client API gặp 401 thì làm mới đúng một lần (nhiều request lỗi cùng lúc dùng chung một lần làm mới) rồi gọi lại request gốc đúng một lần; gọi lại vẫn 401 hoặc làm mới thất bại thì đăng xuất. Chỉ làm mới khi request gốc có kèm token; các endpoint `dang-nhap`, `dang-ky`, `lam-moi`, `dang-xuat`, `quen-mat-khau`, `otp` không bao giờ kích hoạt làm mới.
  - Thân phản hồi đăng nhập/làm mới là `{"access_token": "<jwt>"}` (spec 06 mục 3).
  - Hàm tạo/kiểm tra JWT (`core/bao_mat.py`) làm ở T0.6 để fixture đăng nhập của test dùng token thật; endpoint đăng nhập và refresh token vẫn ở T1.x.
- **Hệ quả:** spec 06 mục 3; `frontend/CLAUDE.md`; T1.2, T1.3 phải trả đúng thân phản hồi trên.

## QĐ-09: Seed không hoàn tác chỉnh sửa của Admin; Admin đầu tiên cần mật khẩu mạnh (2026-10-15, task T0.5)
- **Bối cảnh:** rà soát nghiệp vụ T0.5 tìm thấy seed ghi đè việc Admin gán/bỏ quyền (AD18) và chấp nhận mật khẩu mẫu công khai của `.env.example` cho Admin.
- **Quyết định:**
  - Seed chỉ cấp mặc định cho quyền MỚI; quyền đã có giữ nguyên cách gán hiện tại. Danh mục `quyen` vẫn đồng bộ theo `quyen.yaml`. `vai_tro` và `cau_hinh` chỉ thêm cái còn thiếu.
  - Admin đầu tiên: mật khẩu tối thiểu 12 ký tự (chặt hơn mức chung 8), không được bắt đầu bằng `doi-` (giá trị mẫu); `JWT_SECRET` cũng không được là giá trị mẫu.
  - `--mau` chỉ chạy với CSDL ở máy cục bộ, trừ khi có `--cho-phep-may-chu-khac`; SKU và số lô mẫu có tiền tố `MAU-`.
- **Hệ quả:** spec 02 mục 6; `backend/CLAUDE.md`.

## QĐ-10: Phân luồng ba khu và guard quyền trên UI (2026-10-15, task T0.7)
- **Quyết định:**
  - Route guard khu nội bộ dùng mức `xem` (quyền chỉ xem vẫn vào được trang xem); nút thao tác bọc `<YeuCauQuyen kieu="nut">` mức đầy đủ và ẩn hẳn khi thiếu.
  - Phiên của khách không được coi là đã đăng nhập nội bộ. Chưa đăng nhập nội bộ thì mọi route `/nhan-vien` và `/quan-tri` chuyển tới `/nhan-vien/dang-nhap`.
  - Admin vào `/nhan-vien` bị chuyển sang `/quan-tri`; không phải Admin vào `/quan-tri` thấy 403. Mỗi trang con vẫn kiểm tra mã quyền riêng.
  - Bảng route và menu nằm ở `khu/nhan-vien/menu.ts`, `khu/quan-tri/menu.ts`, `khu/cua-hang/trang.ts`, có test đối chiếu từng dòng với spec 09 mục 2 và với `quyen.yaml`.
- **Hệ quả:** spec 09; `frontend/CLAUDE.md`.

## QĐ-11: Đăng nhập khách, phiên và giới hạn đã chấp nhận (2026-10-15, task T1.2)
- **Quyết định:**
  - Refresh token là chuỗi ngẫu nhiên 256 bit, DB chỉ lưu SHA-256; cookie `refresh_token` có `HttpOnly; SameSite=Lax; Secure`, `Path=/api/v1/auth`; xoay vòng mỗi lần làm mới; dùng lại token đã thu hồi thì thu hồi toàn bộ phiên (spec 06 mục 3, 3.2). Khóa dòng phiên bằng `FOR UPDATE` nên hai lần làm mới đồng thời cùng một token chỉ một bên thắng.
  - **Giới hạn đã chấp nhận 1, làm mới đồng thời:** vì quy tắc "dùng lại là bị thu hồi hết", hai lần làm mới cùng lúc bằng một cookie (nhiều tab mở cùng lúc, hoặc trình duyệt khôi phục nhiều tab sau khi khởi động) sẽ làm bên đến sau bị coi là dùng lại và đăng xuất mọi thiết bị. Không thêm "thời gian ân hạn" ở backend (sẽ làm yếu phát hiện trộm token). Thay vào đó frontend tuần tự hóa việc làm mới giữa mọi tab bằng Web Locks API (`api/xacThuc.ts`) và chỉ làm mới một lần khi tải trang (`api/khoiPhuc.ts`). Đã kiểm chứng trên Chromium: 4 tab tải cùng lúc, bật Web Locks thì 4/4 còn đăng nhập, tắt thì 1/4. Trình duyệt không có Web Locks vẫn chịu rủi ro này.
  - **Giới hạn đã chấp nhận 2, dò tài khoản qua khóa tạm:** sai mật khẩu liên tục với số CÓ tài khoản sẽ dẫn tới `403 TAI_KHOAN_BI_KHOA` (khóa tạm) còn số KHÔNG có tài khoản mãi là `401`, nên kẻ thử nhiều lần có thể phân biệt. Khóa tạm là yêu cầu của KVL10 và cần báo người dùng thật biết mình bị khóa, nên chấp nhận; giảm thiểu bằng giới hạn 20 lần mỗi IP mỗi 10 phút và việc khóa tạm không kéo dài thêm khi tiếp tục thử. Mọi phản hồi khác (sai mật khẩu, số lạ, đã xóa) giống hệt nhau.
  - Frontend giữ thêm MỘT khóa `localStorage` là `phien_goi_y` (`khach` hoặc `noi_bo`), không phải token hay hồ sơ: chỉ để biết có nên thử làm mới khi tải trang, nhờ đó khách vãng lai không gọi API thừa. Cập nhật QĐ-08: "không persist token và hồ sơ", vẫn đúng.
  - `?tiep=` sau khi đăng nhập chỉ nhận đường dẫn nội bộ (một dấu `/` đầu, không `//`, `\`, ký tự điều khiển, không về chính trang đăng nhập/đăng ký/quên mật khẩu) để tránh open redirect.
  - Endpoint đặt lại mật khẩu đặt tên `POST /auth/dat-lai-mat-khau` (QĐ-08 ghi `quen-mat-khau` cho danh sách không tự làm mới; frontend dùng `dat-lai-mat-khau`).
- **Hệ quả:** spec 01 (bảng biến môi trường: `COOKIE_SECURE`), spec 06 mục 3.2; `backend/CLAUDE.md`, `frontend/CLAUDE.md`.

## QĐ-12: Xác thực nhân viên, RBAC và nhật ký (2026-10-15, task T1.3)
- **Quyết định:**
  - **Ba route xác thực công khai nằm trong `/api/v1/noi-bo/auth/`** (`dang-nhap`, `lam-moi`, `dang-xuat`): ngoại lệ duy nhất của quy tắc "route `/noi-bo` phải có `yeu_cau_quyen`", khai báo tường minh ở `CONG_KHAI` của registry. `doi-mat-khau` thì cần `profile.self`.
  - **Đổi mật khẩu thu hồi mọi phiên cũ rồi cấp phiên mới cho thiết bị đang đổi** (không đẩy người đang đổi ra màn đăng nhập); mọi thiết bị khác phải đăng nhập lại. Đoán mật khẩu cũ qua chức năng này được đếm như đăng nhập sai và khi khóa thì thu hồi mọi phiên, nên kẻ cầm access token đánh cắp không dò được mật khẩu.
  - **Khóa tạm do đoán mật khẩu KHÔNG thu hồi phiên đang chạy của chủ tài khoản, cả lúc đăng nhập lẫn lúc làm mới** (nếu thu hồi, kẻ chỉ cần gửi sai 5 lần là đăng xuất được người khác). Làm mới lúc đang khóa tạm: `403 TAI_KHOAN_BI_KHOA` kèm `thu_lai_sau_giay`, không xoay vòng, không xóa cookie, hết khóa thì dùng tiếp token cũ. Khóa do Admin (AD01, T1.4) hoặc xóa mềm thì thu hồi mọi phiên và xóa cookie. (Bản đầu của T1.2/T1.3 làm mới xong mới kiểm tra khóa nên khóa tạm cũng làm mất mọi phiên, mâu thuẫn với quyết định này; rà soát nghiệp vụ phát hiện và đã sửa.)
  - **Thứ tự khóa dòng: tài khoản trước, phiên sau** ở mọi luồng đụng cả hai (đăng nhập, làm mới, đổi mật khẩu, đặt lại mật khẩu, khóa tài khoản). Làm mới từng chỉ khóa dòng phiên nên chạy đồng thời với đổi/đặt lại mật khẩu thì hai bên giữ khóa chéo nhau và Postgres báo deadlock (đã tái hiện bằng test).
  - **Access token đã cấp còn dùng được tới khi hết hạn (tối đa `JWT_ACCESS_PHUT` = 15 phút)** sau khi đổi mật khẩu hoặc thu hồi phiên, vì token không tra DB phiên. Chấp nhận để giữ token ngắn hạn không trạng thái; riêng trạng thái tài khoản (khóa, xóa mềm), vai trò và quyền được đọc từ DB mỗi request nên có hiệu lực ngay.
  - **Mức quyền `chi_xem` chỉ cho thao tác đọc:** thao tác ghi luôn đòi `day_du` ngay trong `yeu_cau_quyen`, không phụ thuộc người viết route khai báo đúng `muc`. `gioi_han` lạ coi là chỉ xem.
  - **`ke_ca_chua_doi_mat_khau`**: chỉ `GET /noi-bo/toi` và `POST /noi-bo/auth/doi-mat-khau` được miễn việc bắt đổi mật khẩu; test registry giữ danh sách này cố định.
  - **Nhật ký** (`core/nhat_ky.py`): luôn che giá trị của khóa chứa `mat_khau`, `password`, `otp`, `token`, `secret`, `hash`, `benh_nen`, `di_ung`, `suc_khoe`, `khoa_ma_hoa` (kể cả khi người gọi quên), tiền ghi dạng chuỗi (không qua float), số điện thoại chỉ ghi dạng che. Ghi: đăng nhập thành công, khóa tạm (đúng một lần lúc bị khóa), đổi mật khẩu, sửa hồ sơ. Đăng nhập thất bại thường không ghi để kẻ dò không làm phình bảng.
  - **Giới hạn:** bảng `nhat_ky_he_thong` "chỉ INSERT" hiện chỉ được bảo đảm bằng việc ứng dụng không có route sửa/xóa, chưa có trigger chặn UPDATE/DELETE ở DB (cần migration mới qua `/doi-schema`, ghi ở "Việc phát sinh").
  - Cookie refresh nhân viên tên `refresh_token_noi_bo`, `Path=/api/v1/noi-bo/auth`; đăng nhập nội bộ dùng email; nhân viên không có luồng "quên mật khẩu" tự phục vụ (Admin đặt lại ở T1.4).
- **Hệ quả:** spec 03 mục 8, spec 06 mục 3.3, spec 09 mục 1, spec 10 mục 3; `backend/CLAUDE.md`, `frontend/CLAUDE.md`.

## QĐ-13: Quản lý nhân viên, vai trò và phân quyền (2026-10-15, task T1.4)
- **Quyết định:**
  - **Mã lỗi mới `TU_THAY_DOI_KHONG_DUOC` (403)** cho Admin tự khóa, tự xóa, tự đổi vai trò, tự đặt lại mật khẩu của mình (tách khỏi `TU_DUYET_KHONG_DUOC` của phiếu kho). Mất Admin hoạt động cuối cùng là `409 PHAI_CON_ADMIN`.
  - **Luôn còn ≥ 1 Admin hoạt động được bảo đảm dưới đồng thời:** mỗi thao tác khóa dòng đích và MỌI dòng Admin chưa xóa trong một câu `ORDER BY id FOR UPDATE`, rồi mới đếm. Nếu chỉ khóa dòng đích thì hai Admin cùng khóa nhau vẫn qua được kiểm tra của nhau và hệ thống không còn Admin nào (đã tái hiện và có test hai session thật).
  - **Vai trò ADMIN bất biến qua AD18** (`409 PHAI_CON_ADMIN`); `profile.self` bắt buộc ở mức đầy đủ cho mọi vai trò (nếu không nhân viên không tự đổi mật khẩu được và bị kẹt ở màn bắt đổi); `content.professional.edit` và `content.approve` chỉ gán được cho PHARMACIST (spec 03 mục 7: Admin không sửa nội dung chuyên môn).
  - **18 quyền mà ma trận spec 03 chỉ cấp cho ADMIN không gán được cho vai trò khác qua AD18** (rà soát nghiệp vụ T1.4, M1 và M2). Bản đầu chỉ chặn hai mã `content.*`, nên Admin cấu hình cho kho `staff.manage` thì kho tự tạo tài khoản ADMIN hoặc đặt lại mật khẩu một Admin (đã chạy thử); cấp `role.manage` thì kho tự thêm `stock_doc.approve`/`refund.confirm` cho vai trò của mình; cấp `refund.confirm` cho dược sĩ thì một người vừa duyệt đổi trả vừa xác nhận hoàn tiền, làm giả định "mỗi nhân viên một vai trò nên đã tách nhiệm vụ" ở spec 03 mục 7 không còn đúng. Quy tắc: quyền nào ma trận chỉ cấp cho ADMIN thì chỉ ADMIN giữ (danh sách đọc từ `quyen.yaml`, thiếu file thì lỗi chứ không bỏ qua). Hệ quả: AD18 chỉ điều chỉnh những quyền đã thuộc về vai trò nghiệp vụ (dược sĩ, kho). Muốn ủy quyền một chức năng quản trị cho nhân viên thì phải sửa ma trận ở spec 03 trước.
  - **Lớp phòng thủ thứ hai:** mọi thao tác ghi của AD01 và AD18 còn đòi người thực hiện thuộc vai trò ADMIN (`core.phan_quyen.dam_bao_la_admin`, `403 KHONG_CO_QUYEN`), để dữ liệu cấu hình sai (gán thẳng vào DB, bỏ qua AD18) không thành quyền tạo Admin. Hệ quả: luật "luôn còn ≥ 1 Admin hoạt động" ở AD01 chỉ còn đạt được khi người thực hiện vừa mất hoạt động giữa chừng (đua nhau), vẫn giữ làm bất biến.
  - **Khóa lạc quan khi lưu phân quyền** (rà soát M3): `PUT /vai-tro/{ma}/quyen` thay TOÀN BỘ nên một trang mở từ trước sẽ ngầm cấp lại quyền Admin khác vừa gỡ (hộp xác nhận chỉ liệt kê thay đổi của chính người lưu). Đọc trả `phien_ban`, lưu phải gửi lại, lệch thì `409 DU_LIEU_DA_THAY_DOI`; giao diện tải lại bản mới và giữ các mục người dùng đã đổi. Chọn phiên bản dạng dấu vân tay nội dung (không có cột mới, không cần migration) thay vì cột số thứ tự.
  - **Đổi vai trò của một nhân viên thu hồi mọi phiên của họ; đổi quyền của một vai trò KHÔNG thu hồi phiên.** Quyền được đọc từ DB ở mỗi request nên quyền mới có hiệu lực ở request kế tiếp (cache 60 giây được xóa sau commit); giao diện của người đang đăng nhập cập nhật menu qua `GET /noi-bo/toi` khi focus lại cửa sổ hoặc sau tối đa 5 phút. Không thu hồi phiên hàng loạt chỉ vì chỉnh một quyền để tránh đẩy cả vai trò ra đăng nhập lại.
  - **Mật khẩu tạm** 12 ký tự từ CSPRNG, chỉ trả trong phản hồi tạo/đặt lại mật khẩu, DB chỉ lưu hash, không vào nhật ký, giao diện hiện đúng một lần trong hộp thoại và xóa khỏi DOM khi đóng. Không có cách xem lại; quên thì Admin đặt lại.
  - **Email nhân viên là duy nhất không phân biệt hoa thường, kể cả với tài khoản đã xóa mềm** (tránh người cũ đăng nhập lại hay lẫn nhật ký); hai Admin tạo cùng email cùng lúc: bên thua nhận `409 TRUNG_DU_LIEU` nhờ savepoint chứ không phải 500.
  - Không có xóa cứng nhân viên: chứng từ, phiếu và nhật ký cũ vẫn trỏ tới người lập.
  - Id trong path dùng `IdInt`/`IdBigInt` (`core/tham_so.py`): id ngoài khoảng của cột là 400.
- **Hệ quả:** spec 03 mục 7, 8; spec 06 mục 3.4, 3.5 và bảng mã lỗi; spec 09 mục 2.3; spec 10 mục 3; `backend/CLAUDE.md`, `frontend/CLAUDE.md`.

## QĐ-14: Quản lý khách hàng của Admin (2026-10-15, task T1.5)
- **Quyết định:**
  - **Admin không bao giờ nhận dữ liệu sức khỏe qua AD02, bảo đảm bằng schema chứ không bằng lọc:** `schemas_quan_tri_khach.py` khai báo từng trường (không dùng chung schema của khách hay `model_validate` toàn bộ dòng). Test quét mọi khóa JSON và mọi giá trị (bệnh nền, ghi chú dị ứng, tên hoạt chất) ở danh sách, chi tiết, lịch sử mua và phản hồi khóa với một khách có hồ sơ sức khỏe thật. Thêm trường vào các schema này là quyết định có chủ ý.
  - **Lịch sử mua là bản tóm tắt** (mã đơn, kênh, trạng thái đơn và thanh toán, tổng tiền, ngày đặt), không có người nhận, địa chỉ giao, ghi chú hay token truy cập. Spec 03 mục 6 cho Admin xem mọi đơn, nhưng chi tiết đơn là việc của AD16; trang khách chỉ cần biết khách đã mua gì. Hiện đọc thẳng `don_hang`, khi có API đơn hàng của Admin (T4.x) thì dùng lại.
  - **Khóa khách thu hồi mọi phiên và có hiệu lực ngay** (guard đọc DB mỗi request; QĐ-12). Khóa dòng khách trước, phiên sau, nên không deadlock với đăng nhập, làm mới, đặt lại mật khẩu. Lý do khóa (không bắt buộc, tối đa 300 ký tự) chỉ ghi vào nhật ký hệ thống, không thêm cột vào hồ sơ khách (không đổi schema). Chưa gửi thông báo cho khách bị khóa (KTV13 chưa làm).
  - **Mở khóa gỡ cả khóa tạm** do đoán mật khẩu và xóa bộ đếm sai; khách đặt lại mật khẩu bằng OTP vẫn không tự mở được khóa của Admin (QĐ-11).
  - **Thao tác ghi của AD02 cũng đòi người thực hiện là ADMIN** (`dam_bao_la_admin`, như QĐ-13): `customer.manage` là một trong 18 quyền chỉ ADMIN giữ.
  - **Khách đã xóa (ẩn danh hóa, [DB23]) không hiện và không thao tác được** (404).
  - **Tìm số điện thoại:** chuỗi giống số điện thoại được đưa về dạng lưu (`+84`, `84`, khoảng trắng, gạch) để Admin gõ theo thói quen nào cũng tìm ra; một phần số cũng khớp. Escape LIKE dùng chung `core/tim_kiem.mau_tim_like` với AD01.
  - **Nhãn trạng thái dùng chung** `lib/trangThai.ts` + `NhanTrangThai` (spec 09 mục 3, 4): test đối chiếu từng giá trị enum với `schema.d.ts` sinh từ OpenAPI nên thêm trạng thái ở backend mà quên nhãn thì test báo.
  - **Liên kết trong khu quản trị phải giữ tiền tố `/quan-tri`:** trang AD02 từng viết `to="/khach-hang/1"` nên bấm vào bị đưa ra khu cửa hàng; test đơn vị chạy ở gốc `/` không thấy, chỉ lộ khi chạy trên trình duyệt. Từ nay test trang con của khu phải có ca chạy dưới tiền tố.
- **Hệ quả:** spec 06 mục 3.6; spec 09 mục 2.3; `backend/CLAUDE.md`, `frontend/CLAUDE.md`.

