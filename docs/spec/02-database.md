# 02. Cơ sở dữ liệu

## 1. Nguồn sự thật và quy trình đổi schema
- **Nguồn sự thật:** `docs/database/ERD_da_chinh_sua.dbml` (65 bảng, 33 enum). `ERD_da_chinh_sua.sql` là DDL sinh từ DBML, đã nạp thử thành công vào PostgreSQL 16.
- **Quy trình đổi schema** (lệnh `/doi-schema`):
  1. Sửa DBML, có chú thích `[DBxx]` hoặc mô tả ngắn.
  2. Sinh lại SQL bằng `npx -y -p @dbml/cli dbml2sql docs/database/ERD_da_chinh_sua.dbml --postgres -o docs/database/ERD_da_chinh_sua.sql`.
  3. Sửa model trong `app/models/`.
  4. Tạo migration mới (`uv run alembic revision --autogenerate -m "..."`) rồi rà lại bằng tay.
  5. Cập nhật spec liên quan (02, 03, 04, 05 nếu ảnh hưởng).
  6. Ghi vào `12-quyet-dinh.md`.
- **Không** sửa migration đã commit. **Không** dùng `Base.metadata.create_all()` ngoài test.

## 2. Migration nền
- **`0001_nen`**
  - `CREATE EXTENSION IF NOT EXISTS vector; ... unaccent; ... pg_trgm;`
  - Toàn bộ enum, bảng, khóa ngoại và index sinh từ model.
- **`0002_rang_buoc`**: SQL viết tay cho mọi thứ ở mục 4.
- **Kiểm tra khớp ERD:** chạy `backend/scripts/so_sanh_schema.py`.
  - Script tạo database tạm, `CREATE EXTENSION vector`, nạp `ERD_da_chinh_sua.sql`.
  - So sánh với database sau `alembic upgrade head` qua `information_schema` và `pg_catalog` theo các tiêu chí: tên bảng, cột, kiểu, nullable, default, khóa ngoại (theo tập cột → bảng đích), unique và index (theo tập cột, bỏ qua tên), giá trị enum theo thứ tự.
  - Bỏ qua: tên ràng buộc/index, comment, và các đối tượng chỉ có ở `0002`.
  - Kết quả phải là **0 lệch**.

## 3. Quy ước
| Chủ đề | Quy ước |
|---|---|
| Khóa chính | `int` tự tăng (`bigint` cho bảng log lớn) đúng như ERD. Không lộ `id` cho khách nếu có mã (`ma_don`, `ma_yeu_cau`) |
| Tiền | `NUMERIC(14,2)` hoặc `(16,2)`; giá trị luôn là số đồng nguyên (phần thập phân `.00`); Python dùng `Decimal`, làm tròn `ROUND_HALF_UP` về 0 chữ số lẻ. Số tiền nhận từ bên ngoài (kiểu `Tien`): không âm, dưới 10^12 (vừa cột NUMERIC(14,2)); `TienCoDau` cho phép âm |
| Thời gian | `timestamptz` lưu UTC; `date` cho HSD/NSX; ngày "hôm nay" tính theo Asia/Ho_Chi_Minh |
| Enum | Enum PostgreSQL native, tên và thứ tự đúng ERD. Thêm giá trị mới bằng `ALTER TYPE ... ADD VALUE` trong migration riêng |
| Xóa mềm | Bảng có `deleted_at` không xóa cứng. Danh sách mặc định lọc `deleted_at IS NULL`. Dữ liệu tài chính và chứng từ không bao giờ xóa |
| Số lượng tồn | Số nguyên theo **đơn vị cơ sở**. Dòng chứng từ theo đơn vị bán/nhập phải lưu thêm `he_so` hoặc `so_luong_co_so` |
| Bản chụp | `ct_don_hang` lưu `ten_san_pham`, `ten_don_vi`, `he_so`, `don_gia`; `don_hang` lưu địa chỉ giao. Không join ngược sang giá hiện tại để tính tiền đơn cũ |
| jsonb | Chỉ cho dữ liệu bán cấu trúc đã ghi trong ERD (ảnh, checklist, payload IPN/webhook, metadata AI). Không dùng jsonb để né thiết kế bảng |

## 4. Ràng buộc bổ sung (migration `0002_rang_buoc`, `0003_nhat_ky_bat_bien`)
Mỗi mục dưới đây cần ít nhất 1 test chứng minh DB từ chối dữ liệu sai (T0.4).

### 4.1 Hàm và index tìm kiếm
```sql
CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$;

CREATE INDEX san_pham_ten_trgm   ON san_pham  USING gin (f_unaccent(lower(ten)) gin_trgm_ops);
CREATE INDEX hoat_chat_ten_trgm  ON hoat_chat USING gin (f_unaccent(lower(ten)) gin_trgm_ops);
CREATE INDEX hoat_chat_khac_trgm ON hoat_chat USING gin (f_unaccent(lower(coalesce(ten_khac, ''))) gin_trgm_ops);
CREATE INDEX tai_lieu_tri_thuc_hnsw ON tai_lieu_tri_thuc USING hnsw (embedding vector_cosine_ops);
CREATE INDEX lich_su_tim_kiem_rong ON lich_su_tim_kiem (created_at) WHERE so_ket_qua = 0;
```
Truy vấn phải dùng **đúng biểu thức** `f_unaccent(lower(...))` thì index mới được dùng.

**Tìm theo tên** dùng toán tử `f_unaccent(lower(:q)) <% f_unaccent(lower(ten))` (word_similarity, ngưỡng mặc định 0.6), **không** dùng `%` (similarity). Lý do: `%` so cả chuỗi nên chuỗi ngắn hoặc đang gõ dở bị điểm thấp. Đo trên dữ liệu thật:

| Từ khóa | `similarity` | `word_similarity` |
|---|---|---|
| "para" | 0.21 | 0.8 |
| "paracetmol" (gõ sai) | 0.45 | 0.64 |

Với tiếng Việt không dấu, "bo phe" khớp "Thuốc ho Bổ phế" với điểm 1.0. Cả hai cách đều dùng được index GIN ở trên.

### 4.2 CHECK
| Bảng | Ràng buộc |
|---|---|
| `don_vi_quy_doi` | `he_so >= 1`, `gia_ban >= 0` |
| `lo_thuoc` | `so_luong_ton >= 0`, `so_luong_giu >= 0`, `so_luong_giu <= so_luong_ton`, `so_luong_biet_tru >= 0`, `han_su_dung > ngay_san_xuat` (khi có NSX) |
| `ct_gio_hang`, `ct_don_hang`, `ct_phieu_nhap`, `ct_phieu_huy`, `ct_phieu_xuat_tra`, `ct_yeu_cau_doi_tra` | `so_luong > 0` |
| `ct_phieu_nhap` | `so_luong_co_so > 0`, `gia_nhap >= 0` |
| `phan_bo_lo` | `so_luong_co_so > 0`, `gia_von >= 0` |
| `ct_phieu_dieu_chinh` | `so_luong_thay_doi <> 0` |
| `don_hang` | `tam_tinh >= 0`, `giam_gia >= 0`, `phi_van_chuyen >= 0`, `tong_tien = tam_tinh - giam_gia + phi_van_chuyen`, `phuong_thuc_tt IS NOT NULL OR trang_thai IN ('cho_khach_xac_nhan','da_huy')` |
| `ct_don_hang` | `giam_gia_phan_bo >= 0`, `thanh_tien = so_luong * don_gia - giam_gia_phan_bo` |
| `thanh_toan` | `so_tien > 0` |
| `van_don` | `(loai = 'tra_hang') = (yeu_cau_doi_tra_id IS NOT NULL)` |
| `khuyen_mai` | `ket_thuc > bat_dau`, `gia_tri > 0`, `loai_giam <> 'phan_tram' OR gia_tri <= 100`, `luot_moi_khach >= 1` |
| `khuyen_mai_pham_vi` | `num_nonnulls(danh_muc_id, san_pham_id) = 1` |
| `thong_bao`, `phien_dang_nhap` | `num_nonnulls(khach_hang_id, nhan_vien_id) = 1` |
| `phieu_dieu_chinh`, `phieu_huy` | `nguoi_duyet_id IS NULL OR nguoi_duyet_id <> nguoi_lap_id` |
| `phieu_xuat_tra` | `nguoi_duyet_id IS NULL OR nguoi_duyet_id <> nhan_vien_id` |
| `danh_gia` | `so_sao BETWEEN 1 AND 5` |
| `tuong_tac_hoat_chat` | `hoat_chat_a_id < hoat_chat_b_id` |
| `ct_yeu_cau_don_thuoc` | `do_tin_cay_ai IS NULL OR do_tin_cay_ai BETWEEN 0 AND 1` |
| `de_xuat_nhap_hang` | `ky_ket_thuc > ky_bat_dau`, `so_luong_de_xuat >= 0` |

### 4.3 Partial unique
```sql
CREATE UNIQUE INDEX dia_chi_mot_mac_dinh   ON dia_chi (khach_hang_id)      WHERE la_mac_dinh;
CREATE UNIQUE INDEX don_vi_mot_co_so       ON don_vi_quy_doi (san_pham_id) WHERE he_so = 1;
CREATE UNIQUE INDEX don_vi_mot_mac_dinh    ON don_vi_quy_doi (san_pham_id) WHERE la_mac_dinh;
CREATE UNIQUE INDEX anh_mot_anh_chinh      ON anh_san_pham (san_pham_id)   WHERE la_anh_chinh;
CREATE UNIQUE INDEX don_thuoc_mot_don_mo   ON don_hang (yeu_cau_don_thuoc_id)
  WHERE yeu_cau_don_thuoc_id IS NOT NULL AND trang_thai <> 'da_huy';
```
Ràng buộc "mỗi đơn có tối đa 1 vận đơn `giao_hang` còn hiệu lực" kiểm tra trong service, vì `trang_thai_doi_tac` là chuỗi tự do của đối tác.

### 4.3b Nhật ký bất biến (migration `0003`, T8.2)
- Trigger `trg_nhat_ky_chi_them` (hàm `nhat_ky_chi_them()`) chặn `UPDATE` và `DELETE` trên `nhat_ky_he_thong` (`integrity_constraint_violation`); chỉ `INSERT`. `TRUNCATE` không bị chặn (quản trị CSDL, test). Index `ix_nhat_ky_he_thong__created_at` cho trang nhật ký và thống kê.

### 4.4 Sequence cho mã chứng từ
`CREATE SEQUENCE seq_<loai>` cho: `phieu_nhap`, `phieu_kiem_ke`, `phieu_dieu_chinh`, `phieu_huy`, `phieu_xuat_tra`, `lenh_thu_hoi`, `nhan_vien`. Định dạng mã ở spec 04 mục 7.

## 5. Khóa và tranh chấp
- **Thứ tự khóa:** mọi thao tác đổi tồn khóa các lô liên quan theo **id tăng dần** trong một câu `SELECT ... FOR UPDATE`, sau đó mới tính toán.
- **Mã giảm giá:** khóa `ma_giam_gia` bằng `FOR UPDATE` khi tạo đơn hoặc hủy đơn.
- **Yêu cầu đơn thuốc:** nhận khóa xử lý bằng `UPDATE ... SET duoc_si_id = :nv, khoa_luc = now() WHERE id = :id AND duoc_si_id IS NULL RETURNING id`. Không trả dòng nào nghĩa là đã có người khác nhận.
- **Mức cô lập:** dùng mặc định `READ COMMITTED`. Không dựa vào kiểm tra trước rồi ghi sau mà không có khóa.

## 6. Seed (`uv run python -m app.seed`)
- **`vai_tro`:**
  - `PHARMACIST` – Dược sĩ bán hàng.
  - `WAREHOUSE` – Nhân viên kho.
  - `ADMIN` – Quản trị.
- **`quyen`, `vai_tro_quyen`:** đọc từ `docs/spec/data/quyen.yaml`. Mức `chi_xem` lưu vào `vai_tro_quyen.gioi_han = 'chi_xem'`; mức `day_du` để `NULL`.
- **Chạy lại seed:** danh mục `quyen` luôn đồng bộ theo yaml (quyền đã bỏ khỏi yaml bị gỡ cùng các cặp của nó). Cách gán `vai_tro_quyen` chỉ được khởi tạo cho quyền MỚI (lần đầu, hoặc quyền mới thêm ở bản phát hành sau); quyền đã có thì giữ nguyên vì Admin được gán/bỏ quyền lúc chạy (AD18). `vai_tro` chỉ thêm vai trò còn thiếu; `cau_hinh` chỉ thêm khóa còn thiếu. Hai tiến trình seed chạy cùng lúc được tuần tự hóa bằng khóa tư vấn PostgreSQL.
- **Admin đầu tiên:** đọc từ `ADMIN_EMAIL`, `ADMIN_MAT_KHAU`, đặt `phai_doi_mat_khau = true`. Mật khẩu tối thiểu 12 ký tự (chặt hơn mức chung 8 của spec 06 vì tài khoản này giữ toàn quyền và được tạo từ file cấu hình) và không được là giá trị mẫu của `.env.example`. Bắt buộc ở lần chạy đầu; khi đã có Admin hoạt động thì có thể để trống. Email trùng nhân viên không phải Admin bị từ chối.
- **Dữ liệu mẫu (`--mau`):** tài khoản mẫu có mật khẩu công khai nên CLI chỉ nạp vào CSDL ở máy cục bộ (`localhost`, `127.0.0.1`, `::1`, `db`), trừ khi thêm `--cho-phep-may-chu-khac`. SKU mẫu có tiền tố `MAU-` và số lô mẫu cũng vậy, để không bao giờ đụng hàng thật.
- **`cau_hinh`:**

| Khóa | Mặc định | Dùng ở |
|---|---|---|
| `nguong_can_han_ngay` | `90` | HT01, KTV02 |
| `han_su_dung_toi_thieu_nhap_ngay` | `180` | KHO02 (cảnh báo) |
| `thoi_han_thanh_toan_phut` | `15` | KTV03, HT03 |
| `thoi_han_khach_xac_nhan_gio` | `24` | DS05, HT03 |
| `thoi_han_doi_tra_ngay` | `7` | KTV09, HT08 |
| `thoi_han_nhan_tai_quay_ngay` | `3` | DS15, HT08 |
| `thoi_gian_khoa_don_thuoc_phut` | `30` | DS04, HT08 |
| `hieu_luc_don_thuoc_ngay` | `5` | DS04 (checklist; kiểm tra lại theo quy định kê đơn hiện hành) |
| `phi_ship_mac_dinh` | `30000` | KTV02 khi adapter vận chuyển lỗi |
| `mien_phi_ship_tu` | `300000` | KTV02 |
| `so_lan_dang_nhap_sai_toi_da` | `5` | KVL10, NV01 |
| `thoi_gian_khoa_dang_nhap_phut` | `15` | KVL10, NV01 |
| `gioi_han_otp` | `{"moi_sdt_moi_gio": 5, "moi_ip_moi_gio": 20}` | KVL08, KVL09 |
| `gioi_han_ai` | `{"chat_moi_phien": 30, "chat_moi_ip_moi_ngay": 100, "tra_anh_moi_ip_moi_ngay": 20}` | KVL05, KVL06 |
| `gio_lam_viec_duoc_si` | `{"bat_dau": "08:00", "ket_thuc": "21:00", "ngay_trong_tuan": [1,2,3,4,5,6,7]}` | AI04 |
| `ai_module` | `{"tim_kiem": true, "chat": true, "tra_anh": true, "doc_don_thuoc": true, "goi_y": true, "du_bao": true}` | AD09 |
| `ai_dau_hieu_nguy_hiem` | danh sách cụm từ: đau ngực, khó thở, co giật, ngất, nôn ra máu, đi ngoài ra máu, yếu liệt nửa người, méo miệng, sốc phản vệ, sưng mặt môi lưỡi, uống quá liều, muốn tự tử, tự làm hại bản thân | AI02 |
| `ai_nguong_chuyen_duoc_si` | `0.6` | AI04 |
| `ai_loi_nhac_bo_sung` | `""` | AD09 (nối vào cuối system prompt khi mở phiên chat mới) |

- **Kiểu và giới hạn (AD08 kiểm tra khi Admin sửa, `core/cau_hinh_khoa.py`):** giá trị là số nguyên thật (không nhận `5.0`, `"5"`, `true`) trong khoảng dưới đây; giá trị tiền là số đồng nguyên. Mọi giá trị mặc định ở bảng trên phải hợp lệ (có test). Bốn khóa `ai_module`, `ai_dau_hieu_nguy_hiem`, `ai_nguong_chuyen_duoc_si`, `ai_loi_nhac_bo_sung` thuộc AD09 (mã quyền `ai.config`): AD08 không liệt kê và không sửa chúng.

| Khóa | Nhóm (chủ đề hiển thị) | Kiểu | Giới hạn |
|---|---|---|---|
| `nguong_can_han_ngay` | Hàng và hạn dùng | số nguyên, ngày | 1 đến 730 |
| `han_su_dung_toi_thieu_nhap_ngay` | Hàng và hạn dùng | số nguyên, ngày | 1 đến 1095 |
| `thoi_han_thanh_toan_phut` | Đơn hàng và thanh toán | số nguyên, phút | 5 đến 1440 |
| `thoi_han_khach_xac_nhan_gio` | Đơn hàng và thanh toán | số nguyên, giờ | 1 đến 168 |
| `thoi_han_doi_tra_ngay` | Đơn hàng và thanh toán | số nguyên, ngày | 1 đến 365 |
| `thoi_han_nhan_tai_quay_ngay` | Đơn hàng và thanh toán | số nguyên, ngày | 1 đến 30 |
| `thoi_gian_khoa_don_thuoc_phut` | Đơn thuốc | số nguyên, phút | 5 đến 240 |
| `hieu_luc_don_thuoc_ngay` | Đơn thuốc | số nguyên, ngày | 1 đến 365 |
| `phi_ship_mac_dinh` | Vận chuyển | tiền (đồng nguyên) | 0 đến 1.000.000 |
| `mien_phi_ship_tu` | Vận chuyển | tiền (đồng nguyên) | 0 đến 100.000.000 (0 là luôn miễn phí) |
| `so_lan_dang_nhap_sai_toi_da` | Bảo mật đăng nhập | số nguyên, lần | 3 đến 20 (dưới 3 thì ai cũng khóa tạm được tài khoản người khác chỉ bằng vài lần thử) |
| `thoi_gian_khoa_dang_nhap_phut` | Bảo mật đăng nhập | số nguyên, phút | 1 đến 1440 |
| `gioi_han_otp` | Bảo mật đăng nhập | đối tượng đúng hai trường | `moi_sdt_moi_gio` 1 đến 20; `moi_ip_moi_gio` 1 đến 200 |
| `gioi_han_ai` | Giới hạn dùng AI | đối tượng đúng ba trường | `chat_moi_phien` 1 đến 500; `chat_moi_ip_moi_ngay` 1 đến 5000; `tra_anh_moi_ip_moi_ngay` 1 đến 500 |
| `gio_lam_viec_duoc_si` | Giờ làm việc | đối tượng `{bat_dau, ket_thuc, ngay_trong_tuan}` | `bat_dau`, `ket_thuc` dạng `HH:MM` (00:00 đến 23:59), `bat_dau` < `ket_thuc` (ca qua nửa đêm chưa hỗ trợ); `ngay_trong_tuan` là danh sách không rỗng, không trùng, mỗi phần tử 1 (thứ hai) đến 7 (chủ nhật) |

- **Dữ liệu mẫu (`--mau`):** xem tiêu chí T0.5 trong lộ trình. Mọi giá trị mẫu phải hợp lệ với mục 4.
