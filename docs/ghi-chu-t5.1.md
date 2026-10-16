# Ghi chú tạm: kiến trúc hiện tại và lưu ý cho T5.1 (xóa file này khi T5.1 xong)

## Kiến trúc hiện tại (đến hết T4.9)
- **Backend** `backend/app`: `core/` (config, db, lỗi `LoiNghiepVu`, phân quyền `yeu_cau_quyen`, `tien.py`, idempotency), `models/`, `modules/<module>/` (service + router + schemas), `tich_hop/` (VNPay, MoMo, GHN, adapter giả), `jobs/` (APScheduler: HT01, HT02, HT03 mỗi phút, HT08 mỗi 15 phút, dọn lịch sử).
- **Quy ước lớp:** router mỏng → service (không commit; dependency `Db` commit cuối request). API khách ở `/api/v1/toi/*`, `khach_hang_id` lấy từ token, tài nguyên người khác trả 404. API nhân viên ở `/api/v1/noi-bo/*`, mỗi endpoint có `yeu_cau_quyen` và một dòng trong `tests/phan_quyen/registry.py`.
- **Trạng thái đơn:** chỉ qua `ban_hang/trang_thai.py::chuyen_trang_thai()` (bảng chuyển + hook: giữ/nhả hàng, xuất kho, hoàn tiền, trả lượt mã). Đã nối: đặt hàng online, đơn hộ qua điện thoại (DS07), xác nhận/hủy, soạn hàng, vận chuyển, giao tại quầy (DS15), HT03, HT08.
- **Tồn kho:** chỉ qua `kho/ton_kho.py` (khóa lô FOR UPDATE theo id tăng dần, ghi `bien_dong_kho` cùng transaction).
- **Giỏ hàng/đặt hàng:** `gio_hang/dich_vu.py` giữ quy tắc dòng (kê đơn, đơn vị online, hạn mức); `ban_hang/dat_hang.py` tính tiền, dùng chung cho khách, đơn hộ; mua lại dùng `gop_gio`.
- **Chuyên môn:** `chuyen_mon/canh_bao.py` có `kiem_tra_tuong_tac`, `kiem_tra_di_ung` (chỉ trả cảnh báo, không trả `ghi_chu` hay danh sách dị ứng, không log).
- **Frontend** `frontend/src`: `khu/{cua-hang,nhan-vien,quan-tri}`, `api/` (client openapi-fetch, `schema.d.ts` sinh bằng `npm run gen:api` khi backend chạy, `goi()`), `lib/`, `stores/phien`. Trang nhân viên: thêm vào `TRANG_NHAN_VIEN_THAT` (router.tsx), `khu/nhan-vien/menu.ts`, spec 09.
- **Kiểm thử:** backend ~2430 test (~8 phút cả bộ, dùng chung một DB test nên không chạy song song), frontend ~890 test (có 1 test `TrangTimKiem` đôi khi đỏ khi chạy cả bộ, chạy riêng thì qua).

## Lưu ý cho T5.1 (Hồ sơ sức khỏe và dị ứng, KTV11)
- **Đọc trước:** spec 03 mục 5.1 (cổng đọc), 05 mục KTV11, 12-quyet-dinh (QĐ về `kiem_tra_di_ung`), roadmap T5.1 và mục "Việc phát sinh" dòng nói về nơi dùng `kiem_tra_di_ung`.
- **Bảng đã có** (không cần đổi schema): `ho_so_suc_khoe` (khóa chính `khach_hang_id`; `nam_sinh`, `benh_nen`, `dang_mang_thai`, `dang_cho_con_bu`, `dong_y_su_dung`, `dong_y_luc`, `updated_at`), `di_ung` (khóa `khach_hang_id` + `hoat_chat_id`, `ghi_chu` ≤255). Xóa hồ sơ là xóa cứng cả hai bảng.
- **Chưa có:** module `suc_khoe` (spec gọi `suc_khoe.service.duoc_doc_ho_so_suc_khoe`), hàm cổng, mã hóa Fernet (`KHOA_MA_HOA` đã có trong `.env.example`, chưa có code dùng; cần helper mã hóa/giải mã và test khóa thiếu/sai).
- **Quy tắc cứng:**
  - Chỉ lưu khi `dong_y_su_dung = true`, ghi `dong_y_luc`; thu hồi đồng ý thì xóa dữ liệu hoặc cấm lưu tiếp (chốt trong QĐ-32 nếu spec chưa rõ, hỏi người dùng nếu mơ hồ).
  - `benh_nen` mã hóa Fernet ở mức ứng dụng; không bao giờ ghi giá trị rõ vào log, nhật ký, thông báo lỗi.
  - Admin và kho không đọc được (mọi response nội bộ không chứa các trường này, có test). Admin xem khách (`quan_tri_khach`) hiện chỉ có dòng nhắc, giữ nguyên.
  - Dược sĩ chỉ đọc qua `duoc_doc_ho_so_suc_khoe(db, nhan_vien, khach_hang_id) -> bool`: vai trò `PHARMACIST` VÀ `dong_y_su_dung` VÀ (yêu cầu đơn thuốc `dang_tu_van` do chính họ phụ trách HOẶC hội thoại `duoc_si_dang_xu_ly` của họ). Mỗi lần đọc ghi `nhat_ky_he_thong` (`hanh_dong='doc_suc_khoe'`, `bang='ho_so_suc_khoe'`, `ban_ghi_id=khach_hang_id`, không ghi giá trị). Bảng `yeu_cau_don_thuoc` và `hoi_thoai` có sẵn nhưng luồng của chúng là T5.2/T5.3/T7.x, nên test T5.1 tự dựng dữ liệu bằng factory.
- **API khách** `/toi/ho-so-suc-khoe` (xem/sửa/xóa) lấy id từ token. Danh sách hoạt chất để chọn dị ứng: dùng bảng `hoat_chat` (đã seed/CRUD ở T2.3), kiểm hoạt chất tồn tại.
- **Test tối thiểu:** Admin 403/không thấy trường; kho 403; dược sĩ không được gán không đọc được; dược sĩ được gán đọc được và có dòng nhật ký không chứa nội dung; chưa đồng ý thì không lưu và dược sĩ không đọc; `benh_nen` trong DB là bản mã hóa; log không chứa giá trị rõ.
- **Giao diện:** trang hồ sơ sức khỏe ở khu cửa hàng (màn đồng ý trước, rồi form; chọn hoạt chất dị ứng bằng Select tìm kiếm). Thêm vào `/tai-khoan` menu và spec 09.
- **Việc dây chuyền sau T5.1:** nơi gọi `kiem_tra_di_ung` (giỏ hàng cho khách, DS04/DS05, DS07, DS08, lọc gợi ý AI) phải kèm test "không lộ `ghi_chu`"; route dược sĩ gọi nó phải qua cổng trước.
- **Còn nợ chưa làm (không thuộc T5.1):** `nghiep-vu-reviewer` cho P3 và P4; xác nhận của người dùng cho QĐ-13..QĐ-30 (nhất là 16, 18, 21, 22, 24); dọn dữ liệu e2e dev (`e2e.admin@example.com`, `e2e.duocsi@example.com`); GHN chưa thử với sandbox thật; nhả khóa đơn thuốc (T5.3) và đóng chat (T7.4) của HT08.
