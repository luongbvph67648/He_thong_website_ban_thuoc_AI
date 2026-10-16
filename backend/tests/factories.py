"""Hàm dựng dữ liệu cho test (spec 10 mục 2). Giá trị mặc định hợp lệ, tham số nào cũng ghi đè được.

Chỉ dựng qua ORM và `ton_kho.nhap_kho`, không đi qua các dịch vụ nghiệp vụ khác, để test dịch vụ không phụ thuộc vào
chính nó. Mọi hàm `flush()` nhưng không commit.
"""

import secrets
from datetime import date, timedelta
from decimal import Decimal
from functools import cache
from itertools import count

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bao_mat import bam_mat_khau
from app.core.ma_chung_tu import ma_nhan_vien
from app.core.thoi_gian import bay_gio_utc, hom_nay_vn
from app.core.tien import cong
from app.models.ban_hang import CtDonHang, DonHang
from app.models.he_thong import NhanVien, VaiTro
from app.models.khach_hang import KhachHang
from app.models.kho import LoThuoc
from app.models.san_pham import DanhMuc, DonViQuyDoi, SanPham
from app.modules.kho.ton_kho import ChungTu, nhap_kho
from app.seed.du_lieu_mau import trang_thai_lo

MAT_KHAU_TEST = "Mat-khau-test-1"

_dem = count(1)


@cache
def _hash_mat_khau_test() -> str:
    """Băm một lần cho cả phiên test (Argon2 chậm có chủ đích); dùng cho mọi tài khoản dựng bằng factory."""
    return bam_mat_khau(MAT_KHAU_TEST)


async def tao_khach(db: AsyncSession, **truong) -> KhachHang:
    n = next(_dem)
    gia_tri = {
        "ho_ten": f"Khách {n}",
        "email": f"khach{n}@example.com",
        "so_dien_thoai": f"09{n:08d}",
        "mat_khau_hash": _hash_mat_khau_test(),
        "dong_y_chinh_sach_luc": bay_gio_utc(),
        **truong,
    }
    khach = KhachHang(**gia_tri)
    db.add(khach)
    await db.flush()
    return khach


async def tao_danh_muc(db: AsyncSession, ten: str | None = None, cha: DanhMuc | None = None, **truong) -> DanhMuc:
    """Danh mục chèn thẳng (không qua service AD03): `cha` là danh mục cha, `thu_tu` mặc định theo thứ tự tạo."""
    n = next(_dem)
    danh_muc = DanhMuc(
        ten=ten or f"Danh mục {n}",
        danh_muc_cha_id=None if cha is None else cha.id,
        **{"slug": f"dm-{n}-{secrets.token_hex(3)}", "thu_tu": n, **truong},
    )
    db.add(danh_muc)
    await db.flush()
    return danh_muc


async def tao_nhan_vien(db: AsyncSession, vai_tro: str = "PHARMACIST", **truong) -> NhanVien:
    """`vai_tro` là mã vai trò (`PHARMACIST`, `WAREHOUSE`, `ADMIN`); database test đã seed sẵn."""
    vai_tro_id = (await db.execute(select(VaiTro.id).where(VaiTro.ma == vai_tro))).scalar_one_or_none()
    if vai_tro_id is None:
        raise LookupError(f"Chưa có vai trò {vai_tro}: database này chưa chạy seed_co_ban")
    n = next(_dem)
    gia_tri = {
        "ma_nhan_vien": await ma_nhan_vien(db),
        "ho_ten": f"Nhân viên {n}",
        "email": f"nhanvien{n}@example.com",
        "mat_khau_hash": _hash_mat_khau_test(),
        "vai_tro_id": vai_tro_id,
        "phai_doi_mat_khau": False,
        **truong,
    }
    nhan_vien = NhanVien(**gia_tri)
    db.add(nhan_vien)
    await db.flush()
    return nhan_vien


DON_VI_MAC_DINH = [{"ten_don_vi": "viên", "he_so": 1, "gia_ban": 1000, "la_mac_dinh": True}]


async def tao_san_pham(
    db: AsyncSession, loai: str = "thuoc_khong_ke_don", don_vi: list[dict] | None = None, **truong
) -> SanPham:
    """`don_vi`: danh sách `{ten_don_vi, he_so, gia_ban, la_mac_dinh}`; mặc định một đơn vị cơ sở "viên" giá 1.000.

    Trả `SanPham` kèm thuộc tính phụ `don_vi_theo_ten` (tên đơn vị -> `DonViQuyDoi`) vì quan hệ model không tự nạp.
    """
    n = next(_dem)
    danh_muc = DanhMuc(ten=f"Danh mục {n}", slug=f"danh-muc-{n}-{secrets.token_hex(3)}")
    db.add(danh_muc)
    await db.flush()
    gia_tri = {
        "sku": f"SKU-{n}-{secrets.token_hex(3)}",
        "ten": f"Sản phẩm {n}",
        "slug": f"san-pham-{n}-{secrets.token_hex(3)}",
        "loai_san_pham": loai,
        "danh_muc_id": danh_muc.id,
        "don_vi_co_so": "viên",
        **truong,
    }
    san_pham = SanPham(**gia_tri)
    db.add(san_pham)
    await db.flush()
    san_pham.don_vi_theo_ten = {}
    for d in don_vi or DON_VI_MAC_DINH:
        dong = DonViQuyDoi(san_pham_id=san_pham.id, **{"la_mac_dinh": False, **d})
        db.add(dong)
        san_pham.don_vi_theo_ten[dong.ten_don_vi] = dong
    await db.flush()
    return san_pham


async def tao_lo(
    db: AsyncSession,
    san_pham: SanPham | None = None,
    so_luong: int = 0,
    han_su_dung: date | None = None,
    trang_thai: str | None = None,
    **truong,
) -> LoThuoc:
    """Lô của `san_pham` (tạo sản phẩm mới nếu bỏ trống). `so_luong` (đơn vị cơ sở) được nhập qua `ton_kho.nhap_kho`
    nên thẻ kho khớp tồn; muốn tồn "có sẵn" không có thẻ kho thì truyền thẳng `so_luong_ton=...`.

    `trang_thai` mặc định suy ra từ hạn sử dụng (ngưỡng cận hạn 90 ngày) như job HT01 sẽ làm.
    """
    if san_pham is None:
        san_pham = await tao_san_pham(db)
    han = han_su_dung or hom_nay_vn() + timedelta(days=365)
    gia_tri = {
        "san_pham_id": san_pham.id,
        "so_lo": f"L{next(_dem):04d}",
        "han_su_dung": han,
        "gia_nhap": 1000,
        "trang_thai": trang_thai or trang_thai_lo(han, hom_nay_vn(), 90),
        **truong,
    }
    lo = LoThuoc(**gia_tri)
    db.add(lo)
    await db.flush()
    if so_luong:
        await nhap_kho(db, lo, so_luong, ChungTu("phieu_nhap", 0))  # chứng từ giả: test không cần phiếu nhập thật
    return lo


async def tao_don(
    db: AsyncSession,
    khach: KhachHang | None = None,
    trang_thai: str = "cho_xac_nhan",
    dong: list[dict] | None = None,
    **truong,
) -> DonHang:
    """Đơn hàng với các dòng `{san_pham, so_luong, don_vi=None}` (mặc định đơn vị mặc định của sản phẩm). Tổng tiền
    khớp công thức ở CHECK. KHÔNG giữ hàng/phân bổ lô: test cần thì tạo thêm `phan_bo_lo`.

    Đây là cách duy nhất ngoài `chuyen_trang_thai()` được tạo đơn ở trạng thái bất kỳ, chỉ dành cho test.
    """
    if dong is None:
        dong = [{"san_pham": await tao_san_pham(db), "so_luong": 1}]
    chi_tiet = []
    for d in dong:
        san_pham: SanPham = d["san_pham"]
        don_vi = (
            san_pham.don_vi_theo_ten[d["don_vi"]]
            if d.get("don_vi")
            else next(x for x in san_pham.don_vi_theo_ten.values() if x.la_mac_dinh)
        )
        chi_tiet.append((san_pham, don_vi, d["so_luong"]))
    tam_tinh = cong(*[Decimal(so_luong) * don_vi.gia_ban for _, don_vi, so_luong in chi_tiet])
    giam_gia, phi = Decimal(truong.pop("giam_gia", 0)), Decimal(truong.pop("phi_van_chuyen", 0))
    gia_tri = {
        "ma_don": f"DH{next(_dem):08d}",
        "khach_hang_id": khach.id if khach else None,
        "trang_thai": trang_thai,
        "phuong_thuc_tt": "cod",
        "tam_tinh": tam_tinh,
        "giam_gia": giam_gia,
        "phi_van_chuyen": phi,
        "tong_tien": tam_tinh - giam_gia + phi,
        **truong,
    }
    don = DonHang(**gia_tri)
    db.add(don)
    await db.flush()
    for san_pham, don_vi, so_luong in chi_tiet:
        db.add(
            CtDonHang(
                don_hang_id=don.id,
                san_pham_id=san_pham.id,
                don_vi_id=don_vi.id,
                ten_san_pham=san_pham.ten,
                ten_don_vi=don_vi.ten_don_vi,
                he_so=don_vi.he_so,
                so_luong=so_luong,
                don_gia=don_vi.gia_ban,
                thanh_tien=Decimal(so_luong) * don_vi.gia_ban,
            )
        )
    await db.flush()
    return don
