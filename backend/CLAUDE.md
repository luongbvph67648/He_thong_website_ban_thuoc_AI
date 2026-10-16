# Backend: quy ước FastAPI

Đọc kèm `docs/spec/01-kien-truc.md` (cấu trúc), `06-api.md` (API) và `10-kiem-thu.md` (test).

## Phân lớp
```
app/modules/<module>/
  router_cong_khai.py   # route không cần đăng nhập (nếu có)
  router_khach.py       # /api/v1/toi/...       Depends(khach_hien_tai)
  router_noi_bo.py      # /api/v1/noi-bo/...    Depends(yeu_cau_quyen(...))
  schemas.py            # Pydantic: <Ten>Tao, <Ten>Sua, <Ten>Doc, <Ten>Loc
  service.py            # nghiệp vụ, transaction, gọi module khác qua service của module đó
  repo.py               # truy vấn SQLAlchemy dùng lại nhiều nơi (không bắt buộc)
```
- **Router mỏng.** Router chỉ nhận request, gọi service và trả schema. Không viết truy vấn hay logic trong router.
- **Service nhận `db: AsyncSession` và tác nhân** (`KhachHang` hoặc `NhanVien`), trả model hoặc schema.
- **Service không commit.** Route khai báo `db: Db` (`from app.core.db import Db`); session này tự commit khi route trả về thành công và rollback khi có ngoại lệ.
  - `db.commit()` và `db.rollback()` bị chặn và raise `RuntimeError`, vì commit giữa chừng làm phần đã commit ở lại dù sau đó request lỗi.
  - Cần ID của dòng vừa thêm: `await db.flush()`. Cần hoàn tác một phần: `async with db.begin_nested():` (savepoint). Muốn hủy cả request: raise `LoiNghiepVu`.
  - Dependency (ví dụ `khach_hien_tai`) dùng `Db` phải là hàm async thường, không `yield`; dependency có `yield` với scope mặc định mà phụ thuộc `Db` sẽ báo `DependencyScopeError` ngay khi dựng app.
  - Luôn dùng alias `Db`, **không** tự viết `Depends(get_db)`: alias đã đặt `scope="function"` để commit chạy **trước** khi gửi response (mặc định commit chạy sau, client nhận 200 dù commit lỗi).
  - Response streaming (SSE) không dùng `db` của request bên trong generator vì session đã đóng; generator tự mở `AsyncSession(engine)` riêng.
  - Việc phải lưu dù request thất bại (ví dụ ghi payload IPN trước khi xử lý) cũng dùng session riêng.
- **Model dùng chung** đặt ở `app/models/` (theo nhóm ERD). Module không tự khai báo model.
- **Gọi chéo module** chỉ qua hàm public trong `service.py` của module kia. Riêng tồn kho và trạng thái đơn bắt buộc đi qua:
  - `modules/kho/ton_kho.py`
  - `modules/ban_hang/trang_thai.py`
- **Đặt tên:**
  - Thực thể, cột và hàm nghiệp vụ dùng tiếng Việt không dấu, giống ERD (`tao_don_hang`, `xac_nhan_don`).
  - Hạ tầng kỹ thuật dùng tiếng Anh (`get_db`, `settings`).

## Xác thực và phân quyền (`app/core/phan_quyen.py`)
```python
NhanVienXacNhan = Annotated[NhanVien, Depends(yeu_cau_quyen("order.confirm"))]


@router.post("/don-hang/{ma_don}/xac-nhan", response_model=DonHangDoc)
async def xac_nhan(ma_don: str, nv: NhanVienXacNhan, db: Db):
    return await service.xac_nhan_don(db, ma_don, nv)


@router.get("/phieu-nhap")  # Admin chỉ xem: muc="xem"
async def ds_phieu_nhap(nv: Annotated[NhanVien, Depends(yeu_cau_quyen("stock.import", muc="xem"))], db: Db): ...


@router.get("/don-hang/{ma_don}")  # khách: chỉ đơn của mình, không có thì 404
async def don_cua_toi(ma_don: str, kh: Annotated[KhachHang, Depends(khach_hien_tai)], db: Db):
    return await service.lay_don_cua_khach(db, kh.id, ma_don)
```
- **Viết `Annotated[NhanVien, Depends(yeu_cau_quyen(...))]`**, không viết `nv: NhanVien = Depends(yeu_cau_quyen(...))`: ruff B008 cấm gọi hàm trong giá trị mặc định.
- **`muc="xem"`:** vai trò có quyền ở mức `chi_xem` hoặc `day_du` đều qua được, nhưng chỉ có tác dụng với GET: thao tác ghi luôn đòi `day_du` ngay trong `yeu_cau_quyen`.
- **`muc="day_du"` (mặc định):** chỉ vai trò có quyền mức `day_du`.
- **Quyền đọc từ DB, cache 60 giây trong process;** sau khi sửa phân quyền (AD18) gọi `xoa_cache_quyen_sau_commit(db)` (xóa ngay VÀ xóa lại sau commit; chỉ gọi `xoa_cache_quyen()` trước commit thì request chạy giữa chừng nạp lại bản cũ). Trạng thái tài khoản đọc mỗi request, không cache.
- **Id trong path** dùng `IdInt` / `IdBigInt` (`core/tham_so.py`, khoảng của cột INTEGER/BIGINT) thay cho `int` trần: id ngoài khoảng là 400 thay vì 500 `value out of int32 range` của asyncpg.
- **Quyền quản trị chỉ ADMIN:** 18 mã mà `quyen.yaml` chỉ cấp cho ADMIN (`danh_muc_quyen.quyen_chi_cho_admin()`) không gán được cho vai trò khác qua AD18; thao tác ghi của AD01/AD18 gọi `phan_quyen.dam_bao_la_admin(db, actor)` ở đầu hàm service. Thêm chức năng quản trị mới nghĩa là thêm hàng vào ma trận spec 03 (chỉ cột Admin) chứ không sửa danh sách ở code.
- **Danh sách quản trị** (AD01, AD02): tìm kiếm văn bản dùng `core.tim_kiem.mau_tim_like` (thoát `%`, `_`, `\\`) với `.like(..., escape="\\")`; sắp xếp dùng `core.phan_trang.sap_xep_theo` + `SapXepQuery` với bảng trường cho phép riêng của endpoint (tên ngoài bảng là 400, luôn thêm `id` làm khóa phụ).
- **Schema trả cho Admin về khách hàng** (`tai_khoan/schemas_quan_tri_khach.py`) khai báo từng trường; không dùng `model_validate` cả dòng cho schema chung và không thêm trường sức khỏe/mật khẩu. Test `khong_lo_du_lieu_nhay_cam` quét khóa và giá trị.
- **Khóa cấu hình mới** (`cau_hinh`): thêm đồng thời (1) dòng vào bảng ở spec 02 mục 6 (kiểu, giới hạn, nhóm), (2) `core/cau_hinh_khoa.py` nếu do AD08 quản lý (khóa của AD09 thì không), (3) giá trị mặc định ở `seed/co_ban.py`. Test đối chiếu ba nơi. Nơi dùng đọc bằng `core.cau_hinh.doc_cau_hinh` mỗi lần (không cache) và vẫn giữ giá trị mặc định cứng phòng khóa thiếu.
- **Nhật ký:** bảng `ho_so_suc_khoe`, `di_ung` chỉ ghi `bang` + `ban_ghi_id` (`ghi_nhat_ky` tự bỏ giá trị); mọi chỗ ĐỌC nhật ký đi qua `che_khi_doc`. Thêm tên khóa nhạy cảm mới vào `DOAN_KHOA_NHAY_CAM`.
- **Lưu phân quyền** đòi `phien_ban` (khóa lạc quan); test gọi `PUT` dùng helper `dat_quyen` đọc `phien_ban` trước.
- **Thao tác đụng tài khoản nhân viên** (AD01, `modules/nhan_vien/quan_tri.py`): khóa dòng đích và mọi Admin chưa xóa bằng MỘT câu `ORDER BY id FOR UPDATE` rồi mới kiểm tra "luôn còn ≥ 1 Admin" và "không tự thay đổi"; thứ tự khóa luôn là tài khoản trước, phiên sau (QĐ-12). Mật khẩu tạm sinh bằng `core.bao_mat.tao_mat_khau_tam()`, chỉ nằm trong phản hồi tạo/đặt lại.
- **Ngoại lệ về route công khai:** chỉ ba route `/noi-bo/auth/{dang-nhap,lam-moi,dang-xuat}` không có `yeu_cau_quyen`; chúng nằm trong `CONG_KHAI` của registry. `ke_ca_chua_doi_mat_khau=True` chỉ dành cho `GET /noi-bo/toi` và đổi mật khẩu (registry giữ danh sách cố định).
- **Thêm route nội bộ mới:** phải thêm vào `tests/phan_quyen/registry.py` với đúng (mã quyền, mức) route đang dùng. Test registry duyệt cây route + dependency thật và fail nếu thiếu, sai mã/mức hay ghi mà khai mức `xem`; test ma trận sinh ca 3 vai trò từ `quyen.yaml`.
- **Nhật ký:** `core.nhat_ky.ghi_nhat_ky(db, nhan_vien_id=..., hanh_dong=..., bang=..., ban_ghi_id=..., gia_tri_cu/moi=..., ip=...)` trong cùng transaction với thao tác. Khóa nhạy cảm (mật khẩu, OTP, token, hash, sức khỏe) tự bị che; số điện thoại truyền dạng `che_sdt`. Thao tác thất bại mà vẫn cần ghi/đếm thì route TRẢ VỀ lỗi (xem mục "Giữ thay đổi dù trả lỗi").
- **Thông báo:** `modules/thong_bao/service.gui_cho_nhan_vien(db, nhan_vien_id, loai=, tieu_de=, noi_dung=, lien_ket=)`; `lien_ket` chỉ là đường dẫn nội bộ.
- **Kiểm tra ngoài mã quyền** (tách nhiệm vụ, chủ sở hữu, dữ liệu sức khỏe) viết trong service, lỗi trả qua `LoiNghiepVu`.
- **Dữ liệu nhập của Admin** (`core/kieu_du_lieu.py`): `kieu_ten(toi_da)` (gộp khoảng trắng, không rỗng), `DuongDanTuyChon` (chỉ `/...` hoặc `http(s)://...`), `van_ban_tuy_chon(toi_da, nhieu_dong=)` (trống thành `None`); tất cả từ chối ký tự điều khiển vì NUL làm PostgreSQL báo 500. Tham số `q` của route danh sách mới cũng phải chặn NUL.
- **Cây danh mục và dữ liệu dùng chung** (T2.1, QĐ-16): `modules/san_pham/danh_muc.py` tuần tự hóa mọi thao tác ghi cây bằng khóa tư vấn `pg_advisory_xact_lock(hashtext(...))`; xóa khóa dòng `FOR UPDATE` trước khi đếm sản phẩm (tạo sản phẩm giữ khóa FK `KEY SHARE` nên không lọt khe; `san_pham._gan_danh_muc` khóa `FOR SHARE` dòng danh mục chưa xóa trước khi ghi). `du_lieu_chung.py` dựng ba nhóm AD05 từ cấu hình `Nhom`; thương hiệu và nhà sản xuất xóa cứng trong savepoint (`db.begin_nested()`), vi phạm khóa ngoại (`sqlstate 23503`) thành `DU_LIEU_DANG_DUOC_SU_DUNG`. HOẠT CHẤT KHÔNG CÓ XÓA (`cho_phep_xoa=False`, không có route): kết quả xóa sẽ lộ khách nào dị ứng hoạt chất đó. Trùng tên so bằng `f_unaccent(lower(...))`, nên DB unique không đủ: dùng khóa tư vấn theo nhóm.
- **Sản phẩm (AD04, T2.2, QĐ-17)** `modules/san_pham/{san_pham,san_pham_don_vi,san_pham_anh}.py`: mọi thao tác ghi một sản phẩm đi qua `san_pham.khoa_va_kiem_tra(db, id, phien_ban)` (khóa dòng `FOR UPDATE` rồi so `phien_ban`, một dấu vân tay cho cả sản phẩm gồm đơn vị, thành phần, ảnh và tên hiển thị) và trả `san_pham.chi_tiet(...)` (đọc lại dòng từ DB rồi tính `phien_ban`, nên không bao giờ lệch dạng với lần `GET` sau). `phien_ban` tính trên MỌI trường của `SanPhamChiTiet` trừ chính nó, nên thêm trường vào schema đọc là đổi dấu vân tay (người đang sửa nhận 409, chấp nhận được). Gán danh mục dùng `_gan_danh_muc` (`FOR SHARE`, QĐ-16); SKU, slug và mã vạch được tuần tự hóa bằng khóa tư vấn (`khoa_tu_van`) vì DB không đủ unique (mã vạch không có unique, SKU chỉ bắt trùng từng ký tự). Đơn vị thay cả danh sách theo pha (xem docstring `thay_don_vi`); đừng "tối ưu" thứ tự áp hệ số, test hoán đổi đơn vị cơ sở bắt lỗi đó.
- **Tệp công khai** `core/luu_tru.py` (spec 08 mục 6): `luu_tru().luu(thu_muc, noi_dung, kieu)` trả khóa `<thư mục>/<uuid>.<đuôi>`; sau khi ghi tệp gọi `xoa_neu_hoan_tac(db, khoa)` (dọn nếu giao dịch hủy), xóa ảnh gọi `xoa_sau_commit(db, khoa)` (chỉ xóa tệp SAU commit); nhận dạng kiểu bằng `nhan_dang_anh` (magic bytes, không tin `Content-Type`). Route nhận tệp dùng `UploadFile` (cần `python-multipart`) và đọc `TOI_DA_ANH_BYTE + 1` byte để biết có vượt không. Không viết endpoint upload chung: mỗi loại tệp đi kèm bản ghi nghiệp vụ và mã quyền riêng. Test không ghi vào `./storage`: fixture autouse đặt `settings.LUU_TRU_THU_MUC` về thư mục tạm của test. **Route nhận tệp phải khai quy tắc trong `QUY_TAC_THAN_REQUEST` (`app/main.py`)**: middleware `GioiHanKichThuocThan` chặn thân quá lớn TRƯỚC xác thực (Starlette đọc cả multipart vào tệp tạm trước khi chạy dependency); test duyệt OpenAPI đỏ nếu thiếu.
- **Trần thân request** (`GioiHanKichThuocThan`, `QUY_TAC_THAN_REQUEST` + `QUY_TAC_THAN_JSON` ở `app/main.py`): route nhận tệp có quy tắc riêng (test duyệt OpenAPI bắt route multipart thiếu quy tắc); mọi `POST/PUT/PATCH/DELETE` dưới `/api/v1` còn lại bị trần chung 2 MiB (`413 THAN_QUA_LON`) TRƯỚC xác thực. Route mới cần thân JSON lớn hơn 2 MiB thì khai quy tắc riêng đặt trước quy tắc chung.
- **Cửa hàng công khai** (`modules/cua_hang/`, QĐ-19): MỌI truy vấn công khai về sản phẩm phải qua `hien_thi.la_hien_thi(ids)` với `ids` từ `nap_cay_hien_thi` (danh mục và mọi tổ tiên đang hiện, chưa xóa); đừng tự viết điều kiện `deleted_at`/`trang_thai` ở chỗ khác. Giá, còn hàng, bán chạy là biểu thức SQL dùng chung (`gia_hien_thi`, `ton_kha_dung`, `ban_chay_30_ngay` (gộp một lần rồi nối, không dùng truy vấn con tương quan)). Khu quảng bá (nổi bật, bán chạy, tương tự) luôn loại `thuoc_ke_don` trong truy vấn. Nội dung chuyên môn cho khách chỉ lấy từ `noi_dung_da_duyet`.
- **Tìm kiếm** (`modules/cua_hang/tim_kiem.py`, QĐ-20): chỉ dùng `word_similarity` (`<%`) trên đúng `f_unaccent(lower(...))` của index GIN, không dùng `%`; mọi tìm kiếm mới (T7.2 ngữ nghĩa) phải đi qua `la_hien_thi` và `dung_the`, và quay về hàm này khi AI lỗi.
- **Nội dung website** (`modules/noi_dung_web/`, AD07, QĐ-21): mọi hàm GHI gọi `dam_bao_la_admin` ở đầu (mã `cms.manage` chỉ ADMIN giữ). Bài viết đi qua `bai_viet.py`: `loai` bất biến, sửa bài sức khỏe đã duyệt đưa về `nhap` (xóa dấu duyệt), `phien_ban` = `chuyen_mon.bai_viet_duyet.phien_ban_bai_viet` (dùng chung với bước dược sĩ duyệt nên Admin sửa giữa chừng thì duyệt 409); nhật ký bài viết KHÔNG ghi toàn văn, chỉ độ dài. Ảnh tải lên đi qua `anh.tai_anh` (khuôn ảnh sản phẩm) và route mới phải khai quy tắc ở `QUY_TAC_THAN_REQUEST`. Phần công khai (`cong_khai.py`) chỉ trả bài `da_duyet`, không trả người soạn/duyệt/`dua_vao_ai`.
- **Nội dung chuyên môn, tương tác, cảnh báo** (DS10, T2.3, QĐ-18) `modules/chuyen_mon/`: mọi hàm GHI gọi `phan_quyen.dam_bao_la_duoc_si(db, actor)` ở đầu (Admin gán `content.*` cho vai trò khác qua AD18 cũng không sửa được nội dung chuyên môn). Nội dung là lịch sử phiên bản append-only: `noi_dung.tao_phien_ban` khóa dòng sản phẩm `FOR UPDATE`, đòi `phien_ban_co_so` (số phiên bản người soạn đã thấy) khớp số lớn nhất kể cả bản lưu trữ; `noi_dung.duyet` giữ bất biến "tối đa một bản `da_duyet`" và không duyệt lùi. Khách và AI chỉ đọc qua `noi_dung.noi_dung_da_duyet(db, san_pham_id)`, không tự truy vấn bảng. `canh_bao.kiem_tra_tuong_tac(db, ds_san_pham_id)` / `kiem_tra_di_ung(db, khach_hang_id, ds_san_pham_id)` chỉ trả cảnh báo (di ứng KHÔNG kèm `ghi_chu`), dùng chung cho DS04, DS05, DS07, DS08, giỏ hàng và AI; không ghi log chi tiết. `tuong_tac.cap_chuan(a, b)` đưa cặp về thứ tự id tăng dần trước khi đọc/ghi bảng.
- **Đặt hàng** (`modules/ban_hang/dat_hang.py`, T4.4, QĐ-26): `_tinh_don` là chỗ tính tiền duy nhất (xem trước và đặt hàng dùng chung, khác nhau ở `dung_luot`); tạo đơn đi qua `khoi_tao_trang_thai` rồi `ton_kho.giu_hang_nhieu`. Route tạo giao dịch nhận `Idempotency-Key` qua `core.idempotency` (`doc_khoa`, `tra_cuu`, `ghi_nho`): tra khóa SAU khi đã khóa dòng của chủ sở hữu, và kiểm tra bản ghi cũ còn hợp lệ (đơn còn tồn tại) vì bản ghi được đặt trước commit.
- **Thanh toán online** (`modules/thanh_toan/`, `tich_hop/thanh_toan/`, T4.5, QĐ-27): mọi cổng (VNPay, MoMo, giả) đi qua `xu_ly_ipn` (chữ ký, số tiền, chống trùng, rồi `chuyen_trang_thai` dòng 10/11 với nguồn `ipn_thanh_toan`); IPN đến khi đơn không còn chờ thanh toán thì tạo `hoan_tien` chờ xác nhận, không đổi trạng thái. Webhook công khai nằm ở `/api/v1/webhook/*`, xác thực bằng chữ ký. HT03 (`ban_hang/het_han.py`) hủy đơn quá hạn mỗi phút qua `chuyen_trang_thai`.
- **Xử lý đơn** (`modules/ban_hang/dich_vu_don.py`, T4.6, QĐ-28): xác nhận/hủy luôn qua `chuyen_trang_thai`; hủy đơn đã thanh toán tạo `hoan_tien` bằng hook `_tao_hoan_tien_khi_huy` (dòng 14, 15, 19, 21, 27), không tự viết ở route. Kho chỉ thấy đơn từ "Đã xác nhận" trở đi và không thấy giao dịch/khách.
- **Soạn hàng và vận chuyển** (`ban_hang/soan_hang.py`, `modules/van_chuyen/`, `tich_hop/van_chuyen/`, T4.7, QĐ-29): đổi lô chỉ qua `ton_kho.doi_lo` khi đơn còn "Đã xác nhận"; tạo vận đơn gọi đối tác SAU khi khóa đơn và kiểm trạng thái, lỗi ghi thì hủy lại. Webhook vận chuyển đi theo `anh_xa.duong_di` qua `chuyen_trang_thai` (nguồn `webhook_van_chuyen`), chịu được lặp, trễ, sai thứ tự; COD ghi nhận bằng hook dòng 23.
- **Đơn hộ và giao tại quầy** (`ban_hang/dat_ho.py`, `giao_tai_quay.py`, T4.8, QĐ-30): đơn hộ dùng chung `dat_hang.tinh_tien` + `gio_hang.kiem_tra_dong_de_dat` với KTV02 (kê đơn bị chặn ở đó), vào máy trạng thái dòng 4/5; khách tra bằng đúng SĐT, online cần khách có tài khoản. Giao tại quầy đi dòng 20 và ghi `thanh_toan` tiền mặt/chuyển khoản cùng transaction.
- **HT08 và mua lại** (`ban_hang/tu_hoan_tat.py`, `dich_vu_don.mua_lai`, T4.9, QĐ-31): mốc hạn lấy từ `lich_su_trang_thai`, yêu cầu đổi trả mở chặn tự hoàn tất; mọi chuyển trạng thái qua `chuyen_trang_thai`. Mua lại gọi `gio_hang.gop_gio` (không viết lại quy tắc giỏ).

## Lỗi
- Raise `LoiNghiepVu("HET_HANG", "Sản phẩm X chỉ còn 3 viên", chi_tiet={...})`, không raise `HTTPException` thô. HTTP status tự lấy từ bảng mã lỗi.
- Mã lỗi viết HOA_KHONG_DAU. Bảng mã lỗi dùng chung ở `docs/spec/06-api.md` mục 4.
- Mã lỗi mới thì thêm vào **cả** bảng đó **và** `MA_LOI` trong `core/loi.py` (test `test_bang_ma_loi_khop_spec_06` báo nếu lệch).
- Lỗi validate của FastAPI, 404, 405 và lỗi không bắt được đều tự trả đúng định dạng `{ma_loi, thong_diep, chi_tiet}`. Lỗi 500 không lộ chi tiết, chỉ trả `request_id`.

## Log
- Log JSON một dòng (`core/log.py`), mọi dòng tự có `request_id`. Dùng `logging.getLogger(__name__)`, không dùng `print`.
- Thêm trường riêng qua `extra={...}`, ví dụ `logger.info("Đã tạo đơn", extra={"ma_don": ma})`.
- **Không ghi** mật khẩu, OTP, token, dữ liệu sức khỏe, và không ghi query string. Log truy cập chỉ ghi **mẫu route** (`/xac-nhan-don/{token}`), không ghi giá trị trong path; log truy cập của uvicorn bị tắt vì nó in cả query string.
- Tạo engine qua `core.db.tao_engine()` (đã bật `hide_parameters`) để lỗi SQL không ghi tham số. Log lỗi tự che các dòng `DETAIL:`/`HINT:`/`CONTEXT:` của PostgreSQL (chứa giá trị vi phạm).
- Lỗi không bắt được do `RequestIdMiddleware` xử lý (log + trả 500), không ném lại cho uvicorn.

## CSDL
- **SQLAlchemy 2 async:** dùng `select()`, không dùng Query API cũ.
- **Model** ở `app/models/` (7 file theo nhóm ERD, `from app.models import Base` nạp đủ 65 bảng). Model chỉ khai báo cấu trúc, không có logic nghiệp vụ.
- **Enum:** mỗi enum PostgreSQL có một lớp `StrEnum` cùng tên PascalCase trong `app/models/enums.py` (`TrangThaiDon.cho_xac_nhan`, so sánh bằng `is` hoặc `==`) và một kiểu `KIEU_<TEN>` dùng trong `mapped_column`. Giá trị trả về từ DB đã là thành viên enum.
- **Tải quan hệ:** mọi `relationship` đặt `lazy="raise"`, truy cập quan hệ chưa nạp sẽ báo lỗi thay vì âm thầm chạy truy vấn (không dùng được trong async). Phải nạp rõ ràng: `select(DonHang).options(selectinload(DonHang.chi_tiet))`. Tên quan hệ nhiều-một lấy từ cột khóa ngoại bỏ đuôi `_id` (`DonHang.khach_hang`); quan hệ một-nhiều chọn lọc (`DonHang.chi_tiet`, `SanPham.don_vi_quy_doi`...) xem trong model. Khóa ngoại kép (`ct_don_hang.(don_vi_id, san_pham_id)`) không có quan hệ, dùng join tường minh.
- **Khóa chính** dùng `Identity` (như DDL của ERD), không dùng serial. Giá trị mặc định (`created_at`, trạng thái, số lượng 0...) là `server_default`; sau `flush()`/`refresh()` ORM đọc lại từ DB.
- **Cột tên `metadata`** (`tai_lieu_tri_thuc`) có thuộc tính Python là `metadata_`, vì `metadata` bị `DeclarativeBase` giữ riêng.
- **Khóa ghi:** `select(LoThuoc).where(...).order_by(LoThuoc.id).with_for_update()`. Luôn khóa theo thứ tự id tăng để tránh deadlock. Dùng `ton_kho.khoa_cac_lo(db, ids)`: nó khóa theo id tăng, dedupe, báo `LookupError` nếu thiếu lô và dùng `populate_existing` để đối tượng đã nạp từ trước được làm mới theo dòng vừa khóa (nếu không, `+=` trên số cũ làm mất cập nhật của giao dịch khác).
- **Tồn kho:** chỉ đổi qua `modules/kho/ton_kho.py`. Hiện có `nhap_kho(db, lo, so_luong, ChungTu(loai, id, nhan_vien_id))`; mọi hàm TĂNG tồn gọi `kiem_tra_san_pham_chua_xoa(db, lo)` sau khi khóa lô (xóa sản phẩm khóa lô rồi mới đếm tồn, QĐ-17); các hàm còn lại (spec 04 mục 3) thêm ở T3.1/T4.x, cùng một khuôn: khóa lô, đổi số, ghi `bien_dong_kho` với `ton_sau`, flush. `so_luong` phải là `int` dương (float/bool/0 bị từ chối).
- **Xóa mềm:** truy vấn mặc định lọc `deleted_at IS NULL` qua helper `chua_xoa(Model)`.
- **Tiền:** `Decimal`, làm tròn qua `core.tien.lam_tron_vnd()` (half-up). `cong()`/`tru()` cộng trừ rồi làm tròn một lần; hàm tiền từ chối `float`. Trong schema Pydantic dùng kiểu `Tien` cho đầu VÀO (không âm, dưới 10^12, số đồng nguyên, xuất JSON dạng chuỗi `"125000.00"`); chênh lệch có thể âm thì dùng `TienCoDau`; schema ĐỌC (phản hồi) dùng `TienDoc` (chỉ định dạng xuất, không kiểm lại: dòng NUMERIC có phần lẻ nhập ngoài API không được làm cả trang 500).
- **Thời gian:** `core.thoi_gian.bay_gio_utc()`, `hom_nay_vn()`.
- **Giữ thay đổi dù trả lỗi:** `raise LoiNghiepVu` luôn rollback. Cần lưu bộ đếm (lần thử OTP, lần đăng nhập sai, khóa tạm) thì route TRẢ VỀ `core.loi.tra_loi("OTP_SAI", "...", chi_tiet)` (cùng định dạng, route kết thúc bình thường nên `get_db` commit). Service trả kết quả (enum/dataclass) thay vì ném, như `otp.kiem_tra_otp`.
- **Chống dò tài khoản:** API công khai không được cho phép phân biệt tài khoản có hay không qua phản hồi, thời điểm hay bộ đếm; xem `otp.py`. Đoạn nghiệp vụ mà hai nhánh phải giống hệt nhau cần test so sánh chuỗi phản hồi của hai nhánh.
- **Giới hạn tần suất:** `core.gioi_han.GioiHanCuaSoTruot` (bộ nhớ, theo IP), giới hạn đọc từ `cau_hinh` mỗi lần; theo SĐT/tài khoản thì đếm trong DB. Dependency để test thay bằng bộ riêng.
- **Thứ tự khóa dòng: tài khoản trước, phiên sau** ở mọi luồng đụng cả hai (đăng nhập, làm mới, đổi/đặt lại mật khẩu, khóa tài khoản); đảo thứ tự gây deadlock với `FOR UPDATE`/khóa khóa-ngoại của INSERT phiên (đã tái hiện bằng test). Làm mới lúc đang khóa tạm (`khoa_den`) trả 403 mà KHÔNG xoay vòng/thu hồi/xóa cookie; Admin khóa hoặc xóa mềm thì thu hồi tất cả.
- **Phiên đăng nhập:** `modules/tai_khoan/phien.py` (`tao_phien`, `lam_moi_phien`, `thu_hoi_phien`, `thu_hoi_tat_ca`) dùng chung khách và nhân viên (`loai = "khach" | "noi_bo"`). Refresh token là chuỗi ngẫu nhiên, DB chỉ lưu SHA-256, xoay vòng, dùng lại token đã thu hồi thì thu hồi toàn bộ; cookie đặt/xóa qua `tai_khoan/cookie.py` (route nhận cookie bằng `Cookie(alias=TEN_COOKIE_REFRESH_KHACH)`). Đổi/đặt lại mật khẩu, khóa tài khoản phải gọi `thu_hoi_tat_ca`. Đăng nhập: `dang_nhap.kiem_tra_dang_nhap` (khóa tạm, chống dò bằng thời gian).
- **Xác thực nhân viên** (`modules/nhan_vien/`): đăng nhập bằng email, cookie `refresh_token_noi_bo` (Path `/api/v1/noi-bo/auth`). Làm mới/đăng xuất/giới hạn IP dùng chung với khách qua `tai_khoan/phien_http.py` (đừng viết lại). Đổi mật khẩu: thu hồi mọi phiên cũ rồi cấp phiên mới; đoán mật khẩu cũ bị đếm như đăng nhập sai. Admin khóa nhân viên (T1.4) phải gọi `phien.thu_hoi_tat_ca(db, "noi_bo", id)`.
- **Guard khách:** `Depends(khach_hien_tai)` (bắt buộc) hoặc `khach_tuy_chon` (công khai nhưng biết khách nếu có) từ `core/phan_quyen.py`; đọc tài khoản từ DB mỗi request. Route mới dưới `/api/v1/toi` PHẢI dùng `khach_hien_tai` (test duyệt OpenAPI kiểm tra).
- **Tin nhắn:** gửi qua `tich_hop.tin_nhan.KenhTinNhan` (dependency `lay_kenh_tin_nhan`), không tự gọi SMTP/SMS. SĐT chuẩn hóa bằng `core.dien_thoai.chuan_hoa_sdt`, ghi log phải `che_sdt`.
- **Mật khẩu:** `core.bao_mat.bam_mat_khau` / `kiem_tra_mat_khau` (Argon2id; chuỗi băm hỏng trả `False`, không ném lỗi); trong route dùng bản `_async` (`bam_mat_khau_async`, `kiem_tra_mat_khau_async`) vì Argon2 tốn CPU và sẽ chặn vòng lặp sự kiện, `mat_khau_du_manh` (≥ 8 ký tự, có chữ và số). Không tự gọi `argon2` ở nơi khác.
- **Mã chứng từ:** `core.ma_chung_tu.ma_nhan_vien(db)`, `ma_phieu(db, "phieu_nhap")`, `ma_lenh_thu_hoi(db)` lấy số từ sequence (spec 04 mục 7); sequence không rollback nên mã có thể nhảy số, không bao giờ trùng. Mã của khách (`DH...`) dùng ký tự ngẫu nhiên, làm ở T4.x.
- **Slug:** `core.slug.tao_slug("Thuốc ho Bổ phế")` → `thuoc-ho-bo-phe`.
- **Phân trang:** route nhận `tp: PhanTrang`, truy vấn đã có `ORDER BY` thì `dong, tong = await lay_trang(db, stmt, tp)`, trả `tao_trang(dong, tong, tp)` với `response_model=Trang[Schema]`. Truy vấn chọn nhiều cột (thực thể kèm số đếm) truyền `nhieu_cot=True` để mỗi dòng là một `Row`; mặc định `lay_trang` chỉ trả cột đầu (scalars).
- **Schema:** thay đổi phải theo `/doi-schema`. Migration mới đặt tên `NNNN_<mo_ta>.py`. Sau khi sửa model hoặc migration, chạy `uv run python scripts/so_sanh_schema.py` để chắc cả model lẫn kết quả `alembic upgrade head` vẫn khớp DDL của ERD (test `test_model_khop_ddl_cua_erd` và `test_migration_khop_ddl_cua_erd` cũng kiểm tra).
- **Migration (Alembic):** `0001_nen` (bảng, enum, extension) và `0002_rang_buoc` (hàm `f_unaccent`, CHECK, partial unique, index GIN/HNSW, sequence) là bản chụp bất biến, không sửa. Quy ước khi thêm migration mới:
  - Enum tạo bằng `op.execute("CREATE TYPE ...")` và cột dùng `postgresql.ENUM(..., create_type=False)`; autogenerate sinh `sa.Enum` inline sẽ tạo kiểu hai lần.
  - CHECK, partial unique, index biểu thức/GIN/HNSW, hàm và sequence **viết tay bằng SQL** và đặt tên rõ (`ck_<bảng>_<mô tả>`). Model và `alembic check` không biết chúng: `env.py::include_object` bỏ qua index một phần, biểu thức, không phải btree; Alembic không so CHECK/hàm/sequence.
  - Thêm CHECK mới thì thêm một case vào `tests/test_rang_buoc.py` (test `test_moi_check_trong_db_deu_co_test` fail nếu thiếu); thêm partial unique thì thêm vào `CAC_PARTIAL_UNIQUE`.
  - Test chạy Alembic qua `scripts.so_sanh_schema.chay_alembic(engine, "upgrade", "head")` (chạy trong luồng riêng, không ghi đè log). Không gọi `command.upgrade` trực tiếp trong test async vì `env.py` tự dựng vòng lặp asyncio.

## Seed (`app/seed/`)
- `uv run python -m app.seed` (vai trò, quyền, cấu hình mặc định, Admin từ `ADMIN_EMAIL`/`ADMIN_MAT_KHAU`) và `--mau` (dữ liệu mẫu để demo). Chạy lại an toàn.
- `seed_co_ban(db, admin=...)` và `seed_mau(db)` nhận session, **không commit** (CLI bọc transaction). Test dùng trực tiếp hai hàm này.
- Quyền đọc từ `docs/spec/data/quyen.yaml`: danh mục `quyen` đồng bộ theo file (quyền thừa bị gỡ), nhưng cách gán `vai_tro_quyen` chỉ khởi tạo cho quyền MỚI để không hoàn tác chỉnh sửa của Admin (AD18). `cau_hinh` và `vai_tro` chỉ thêm cái còn thiếu. Mọi hàm seed gọi `khoa_seed(db)` (khóa tư vấn) nên hai tiến trình chạy cùng lúc không vi phạm unique. Đổi mặc định ở `seed/co_ban.py::CAU_HINH_MAC_DINH` thì phải khớp bảng ở spec 02 mục 6 (test đối chiếu từng khóa).
- Dữ liệu mẫu ở `seed/du_lieu_mau/catalog.py` (toàn bộ là dữ liệu giả, SKU và số lô có tiền tố `MAU-`); lô hàng luôn nhập qua phiếu nhập + `ton_kho.nhap_kho`, không gán tồn trực tiếp. Tài khoản mẫu dùng chung mật khẩu công khai `MAT_KHAU_MAU`: CLI từ chối `--mau` với CSDL không ở máy cục bộ (trừ `--cho-phep-may-chu-khac`).
- Admin đầu tiên: mật khẩu tối thiểu 12 ký tự, không được là giá trị mẫu (bắt đầu bằng `doi-`); `JWT_SECRET` cũng bị từ chối nếu là giá trị mẫu.
- Ngoại lệ về `print`: CLI `app/seed/__main__.py` in kết quả cho người chạy; không in mật khẩu Admin (chỉ in `MAT_KHAU_MAU`, vốn công khai).

## Job nền (`app/jobs/`)
- Mỗi job là một hàm `async def chay(db)` trong file `htXX_<ten>.py`, đăng ký lịch trong `app/jobs/__main__.py`.
- Bọc bằng `pg_try_advisory_lock(<số cố định của job>)` để không chạy chồng.
- Job phải idempotent: chạy lại không gây sai.

## Test
- Cấu trúc `tests/` giống `app/modules/`. Đọc docstring đầu `tests/conftest.py` để biết đủ fixture.
- **Một event loop cho cả phiên** (`asyncio_default_*_loop_scope = "session"`): fixture async phạm vi phiên dùng chung được với mọi test; không đặt `loop_scope` riêng cho từng module.
- **Database test** ở `DATABASE_URL_TEST` (tên phải có chữ `test`, nếu không `tao_lai_database` từ chối xóa): xóa và tạo lại, `alembic upgrade head`, `seed_co_ban`, một lần mỗi phiên. Cần PostgreSQL với user superuser.
- **Chọn fixture:**
  - `db`: mặc định, session trong transaction ngoài rollback sau test (savepoint, nên `commit()` chỉ giải phóng savepoint). `client`/`app`/`dang_nhap_*` dùng chung transaction đó, request thấy dữ liệu factory đã `flush()`; request lỗi vẫn hoàn tác phần của chính nó như production.
  - `dang_nhap_khach`, `dang_nhap_duoc_si`, `dang_nhap_kho`, `dang_nhap_admin`: client đã gắn access token thật (`aud` đúng) của tài khoản vừa tạo, có thuộc tính `.tai_khoan`. Dùng nhiều fixture trong một test được (mỗi cái một tài khoản riêng).
  - `client_https`: như `client` nhưng gọi qua https, để cookie refresh có cờ `Secure` được lưu và gửi lại. Cookie jar của client giữ cookie không `Secure`; muốn test "không gửi cookie" phải `client.cookies.clear()` (xem `tests/tai_khoan/dung_chung.py`).
  - `thoi_gian`: đồng hồ giả cho OTP, khóa tạm, hạn refresh token (không tua được hạn JWT, do thư viện JWT tính). Thêm module dùng `bay_gio_utc` mới thì thêm vào danh sách trong fixture.
  - `gioi_han_dang_nhap`, `gioi_han_ip`: bộ giới hạn riêng cho mỗi test; autouse `cau_hinh_co_dinh_cho_test` ghim cấu hình ảnh hưởng hành vi (đừng để test phụ thuộc `backend/.env`).
  - `db_that`: test cần commit thật giữa nhiều session (tranh chấp khóa), trả `async_sessionmaker`; sau test TRUNCATE hết, giữ vai trò rồi seed lại quyền, phân quyền và cấu hình về mặc định (seed không ghi đè phân quyền đã có, nên không TRUNCATE thì test sửa phân quyền để lại ma trận lệch cho test sau). Ví dụ `tests/kho/test_ton_kho_tranh_chap.py`.
  - `db_chua_seed`/`engine_migration`: database đã migrate nhưng chưa seed, cho test về seed và migration (`test_rang_buoc.py`, `test_seed.py`). Test dùng `engine_migration` trực tiếp phải tự rollback.
  - `engine_tam`/`engine_co_bang`: database tạm riêng cho một test (có/không có 65 bảng từ `create_all`). `mo_client(app, raise_app_exceptions=False)` gọi vào app dựng riêng, dùng `False` khi test lỗi 500.
- **Factories** `tests/factories.py`: `tao_khach`, `tao_nhan_vien(vai_tro)`, `tao_san_pham(loai, don_vi=[...])`, `tao_lo(san_pham, so_luong, han_su_dung, trang_thai)`, `tao_don(khach, trang_thai, dong=[...])`. Giá trị mặc định hợp lệ, tham số nào cũng ghi đè được. `tao_lo(so_luong=...)` nhập qua `ton_kho.nhap_kho` nên thẻ kho khớp tồn.
- Test API qua HTTP (`AsyncClient`); test bất biến/tranh chấp gọi service trực tiếp với nhiều session. Muốn chèn dòng mà không dựng khóa ngoại: `SET LOCAL session_replication_role = replica` (cần superuser), xem `test_rang_buoc.py`.
- Test có token dùng `settings.JWT_SECRET` do fixture tự đặt (autouse); `tao_access_token`/`giai_ma_access_token` ở `core/bao_mat.py`.
- Không gọi dịch vụ ngoài: `AI_GIA_LAP=true`, adapter tích hợp ở chế độ `gia`.
- Chạy nhanh một phần: `uv run pytest tests/ban_hang -q -x`. CI (`.github/workflows/ci.yml`) chạy ruff, vòng migration lên-xuống-lên + `alembic check`, `scripts/so_sanh_schema.py`, pytest; frontend chạy lint, `tsc`, vitest (khi có script `test`), build.

## Python
- Bật `ruff` (lint + format) cho mọi file. Trước khi push chạy `uv run ruff check --no-cache .` và `uv run ruff format --check --no-cache .`: `.ruff_cache` cục bộ từng che lỗi thứ tự import (I001) khiến CI đỏ hai lần liền (T1.6) dù máy mình báo sạch.
- Type hint đầy đủ cho hàm public.
- Docstring tiếng Việt một dòng cho service public.
- Không dùng `print`; dùng `logging.getLogger(__name__)`.
- **Hồ sơ sức khỏe** (`modules/suc_khoe`, T5.1, QĐ-32): chỉ dược sĩ đọc qua `duoc_doc_ho_so_suc_khoe` / `doc_ho_so_cho_duoc_si` (ghi `doc_suc_khoe`, không ghi nội dung); `benh_nen` qua `core/ma_hoa.py` (Fernet). Thu hồi đồng ý = xóa hồ sơ, DB luôn có `dong_y_su_dung = true`. Test cần `KHOA_MA_HOA` (conftest đã đặt).
- **Đơn thuốc phía khách** (`modules/don_thuoc`, T5.2, QĐ-33): ảnh ở vùng `rieng_tu`, chỉ đọc qua `luu_tru.url_ky` (cấp sau khi kiểm quyền); API khách lấy `khach_hang_id` từ token, yêu cầu của người khác là 404.
- **Duyệt đơn thuốc và đơn từ đơn thuốc** (`don_thuoc/duyet.py`, `xac_nhan.py`, T5.3, QĐ-34): `cho_phep_ke_don=True` chỉ ở `tao_don`; hook dòng 16 bật `da_su_dung`, các dòng hủy trước xuất kho trả yêu cầu về `dang_tu_van`; hồ sơ sức khỏe của khách chỉ qua `duoc_doc_ho_so_suc_khoe`.
- **POS** (`ban_hang/pos.py`, T5.4, QĐ-35): đơn `tai_quay` vào thẳng `hoan_tat` rồi giữ và xuất kho (có lô cận hạn) trong một transaction; thuốc kê đơn bắt buộc yêu cầu `tai_quay` của chính dược sĩ; không mã giảm giá.
- **Đổi trả** (`doi_tra/`, T6.1, QĐ-36): hoàn tiền chỉ qua `thanh_toan` `hoan_tien`; đơn thay thế đi dòng 8 rồi dòng 30 (`khoi_tao_trang_thai(..., so_dong=30)`); mọi route multipart phải có quy tắc trong `QUY_TAC_THAN_REQUEST`.
- **Nhận hàng trả/hoàn** (`doi_tra/kho.py`, T6.2, QĐ-37): hàng khách trả vào biệt trữ qua `ton_kho.vao_biet_tru`; hàng hoàn nguyên niêm phong `hoan_nhap`, rồi `chuyen_trang_thai` dòng 27; hoàn tiền theo số thực nhận.
- **Xác nhận hoàn tiền** (`hoan_tien/`, T6.3, QĐ-38): chỉ Admin; online qua `CongThanhToan.hoan_tien`, thủ công kèm chứng từ `rieng_tu`; người xác nhận ≠ `yeu_cau_doi_tra.duoc_si_id`; ẩn danh hóa tài khoản sau khi xong.
- **Đánh giá/hỏi đáp** (`danh_gia/`, T6.4, QĐ-39): đánh giá khóa dòng `ct_don_hang` rồi kiểm trùng; kiểm duyệt chỉ dược sĩ (`dam_bao_la_duoc_si`).
- **Thông báo khách** (`thong_bao/`, T6.5, QĐ-40): luôn qua `gui_cho_khach` (tự gửi SMS/email theo `KENH_THEO_LOAI`); đổi trạng thái đơn tự báo khách trong `_ghi`; job HT07 `nhac_mua_lai`.
- **Thu hồi lô** (`thu_hoi/`, T6.6, QĐ-41): tạo lệnh khóa lô theo id tăng + khóa advisory theo sản phẩm, gỡ đơn chưa xuất bằng `_phan_bo_lai` của HT01; chỉ dược sĩ xem danh sách khách; đóng lệnh khi hết khách chưa liên hệ và hết tồn.
- **AI** (`app/ai/`, T7.1, QĐ-43): chỉ `ai/claude.py` import `anthropic`; chỉ `ai/embedding.py` tạo vector; test dùng `ai/gia_lap.KICH_BAN` (fixture autouse ghim `AI_GIA_LAP`). Đoạn tri thức chatbot phải lọc `metadata->>'can_ke_don' = 'false'` ngay trong SQL.
- **Chatbot** (`ai/chatbot.py`, `modules/tu_van/`, T7.3, QĐ-44): luật nguy hiểm chạy trước Claude; tool chỉ đọc luôn lọc kê đơn/dị ứng ở SQL và validate input bằng Pydantic; SSE dùng `lay_tao_phien` (không dùng `Db` trong generator); mọi lỗi AI thành `chuyen_duoc_si`.
