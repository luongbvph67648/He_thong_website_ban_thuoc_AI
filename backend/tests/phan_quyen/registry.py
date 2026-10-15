"""Registry route nội bộ: khai báo MỘT LẦN mỗi route `/api/v1/noi-bo/*` thuộc quyền nào, mức nào (spec 10 mục 3).

Thêm route nội bộ mới thì thêm vào `REGISTRY` (hoặc `CONG_KHAI` nếu là route xác thực không cần quyền). Thiếu thì
`test_registry_day_du` fail. Khai báo ở đây phải khớp `Depends(yeu_cau_quyen(ma, muc))` của chính route đó, và mã quyền
phải có trong `docs/spec/data/quyen.yaml`; test ma trận sinh các ca đúng/sai từ đúng bảng này.
"""

TIEN_TO_NOI_BO = "/api/v1/noi-bo"

# {(PHƯƠNG THỨC, đường dẫn mẫu): (mã quyền, mức)}
REGISTRY: dict[tuple[str, str], tuple[str, str]] = {
    # NV01, NV02: mọi nhân viên có `profile.self` ở mức đầy đủ.
    ("GET", f"{TIEN_TO_NOI_BO}/toi"): ("profile.self", "xem"),
    ("PATCH", f"{TIEN_TO_NOI_BO}/toi"): ("profile.self", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/auth/doi-mat-khau"): ("profile.self", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/thong-bao"): ("profile.self", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/thong-bao/so-chua-doc"): ("profile.self", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/thong-bao/da-doc-tat-ca"): ("profile.self", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/thong-bao/{{thong_bao_id}}/da-doc"): ("profile.self", "day_du"),
    # AD01: chỉ Admin có `staff.manage` (day_du).
    ("GET", f"{TIEN_TO_NOI_BO}/nhan-vien"): ("staff.manage", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/nhan-vien"): ("staff.manage", "day_du"),
    ("GET", f"{TIEN_TO_NOI_BO}/nhan-vien/{{nhan_vien_id}}"): ("staff.manage", "xem"),
    ("PATCH", f"{TIEN_TO_NOI_BO}/nhan-vien/{{nhan_vien_id}}"): ("staff.manage", "day_du"),
    ("DELETE", f"{TIEN_TO_NOI_BO}/nhan-vien/{{nhan_vien_id}}"): ("staff.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/nhan-vien/{{nhan_vien_id}}/khoa"): ("staff.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/nhan-vien/{{nhan_vien_id}}/mo-khoa"): ("staff.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/nhan-vien/{{nhan_vien_id}}/dat-lai-mat-khau"): ("staff.manage", "day_du"),
    # AD18: chỉ Admin có `role.manage` (day_du).
    ("GET", f"{TIEN_TO_NOI_BO}/vai-tro"): ("role.manage", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/vai-tro/{{ma}}"): ("role.manage", "xem"),
    ("PUT", f"{TIEN_TO_NOI_BO}/vai-tro/{{ma}}/quyen"): ("role.manage", "day_du"),
    # AD02: chỉ Admin có `customer.manage` (day_du).
    ("GET", f"{TIEN_TO_NOI_BO}/khach-hang"): ("customer.manage", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/khach-hang/{{khach_id}}"): ("customer.manage", "xem"),
    ("GET", f"{TIEN_TO_NOI_BO}/khach-hang/{{khach_id}}/don-hang"): ("customer.manage", "xem"),
    ("POST", f"{TIEN_TO_NOI_BO}/khach-hang/{{khach_id}}/khoa"): ("customer.manage", "day_du"),
    ("POST", f"{TIEN_TO_NOI_BO}/khach-hang/{{khach_id}}/mo-khoa"): ("customer.manage", "day_du"),
}

# Route nội bộ cố ý KHÔNG cần quyền vì chạy trước khi có phiên (đăng nhập) hoặc chỉ dựa vào cookie refresh.
CONG_KHAI: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", f"{TIEN_TO_NOI_BO}/auth/dang-nhap"),
        ("POST", f"{TIEN_TO_NOI_BO}/auth/lam-moi"),
        ("POST", f"{TIEN_TO_NOI_BO}/auth/dang-xuat"),
    }
)

# Chỉ hai route này được dùng khi tài khoản còn bị bắt đổi mật khẩu (`ke_ca_chua_doi_mat_khau=True`):
# đọc hồ sơ để biết phải đổi, và chính việc đổi mật khẩu. Route khác mà bật cờ này là lỗ hổng bỏ qua việc bắt đổi.
CHO_PHEP_KHI_CHUA_DOI_MAT_KHAU: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", f"{TIEN_TO_NOI_BO}/toi"),
        ("POST", f"{TIEN_TO_NOI_BO}/auth/doi-mat-khau"),
    }
)
