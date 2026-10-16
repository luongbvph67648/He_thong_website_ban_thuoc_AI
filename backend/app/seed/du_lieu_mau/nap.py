"""Nạp dữ liệu mẫu (`catalog.py`) vào DB. Chạy lại an toàn: tìm theo khóa tự nhiên, chưa có mới tạo.

Mọi lô hàng được nhập qua phiếu nhập mẫu và `ton_kho.nhap_kho` nên tồn kho khớp thẻ kho ngay từ đầu (spec 04 mục 3.2).
Hạn sử dụng tính từ ngày chạy seed để luôn có đủ lô còn hạn, cận hạn và hết hạn. Lô đã có thì giữ nguyên (không dịch
hạn theo ngày chạy lại).
"""

from collections import Counter
from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal
from functools import cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bao_mat import bam_mat_khau
from app.core.ma_chung_tu import ma_nhan_vien, ma_phieu
from app.core.slug import tao_slug
from app.core.thoi_gian import bay_gio_utc, hom_nay_vn
from app.core.tien import cong, lam_tron_vnd
from app.models.ban_hang import KhuyenMai, MaGiamGia
from app.models.he_thong import BaiViet, Banner, CauHinh, NhanVien, VaiTro
from app.models.khach_hang import DiaChi, KhachHang
from app.models.kho import CtPhieuNhap, LoThuoc, NhaCungCap, PhieuNhap
from app.models.san_pham import (
    DanhMuc,
    DonViQuyDoi,
    HoatChat,
    NhaSanXuat,
    SanPham,
    ThanhPhan,
    ThongTinChuyenMon,
    ThuongHieu,
    TuongTacHoatChat,
)
from app.modules.kho.lo import trang_thai_theo_han
from app.modules.kho.ton_kho import ChungTu, nhap_kho
from app.seed.co_ban import khoa_seed
from app.seed.du_lieu_mau import catalog
from app.seed.du_lieu_mau.catalog import SanPhamMau

MAT_KHAU_MAU = "Mau@12345"
"""Mật khẩu chung của mọi tài khoản mẫu. Chỉ để demo cục bộ, không dùng `--mau` trên môi trường thật."""

NGUONG_CAN_HAN_MAC_DINH = 90


@cache
def _hash_mat_khau_mau() -> str:
    """Băm một lần cho mọi tài khoản mẫu (mật khẩu công khai nên không cần salt riêng, đỡ tốn thời gian)."""
    return bam_mat_khau(MAT_KHAU_MAU)


NGAY_NHAP_PHIEU_MAU_TRUOC = 45


def trang_thai_lo(han_su_dung: date, hom_nay: date, nguong_can_han_ngay: int) -> str:
    """Trạng thái lô theo hạn (spec 04 mục 1.4); quy tắc ở `modules/kho/lo.py`."""
    return trang_thai_theo_han(han_su_dung, hom_nay, nguong_can_han_ngay).value


async def _lay_hoac_tao(db: AsyncSession, model: type, khoa: dict[str, Any], them: dict[str, Any] | None = None):
    """Trả (đối tượng, vừa tạo?). Tìm theo `khoa`, chưa có thì tạo với `khoa` + `them`."""
    doi_tuong = (await db.execute(select(model).filter_by(**khoa))).scalars().first()
    if doi_tuong is not None:
        return doi_tuong, False
    doi_tuong = model(**khoa, **(them or {}))
    db.add(doi_tuong)
    await db.flush()
    return doi_tuong, True


async def _nap_danh_muc(db: AsyncSession, dem: Counter) -> dict[str, int]:
    id_theo_slug: dict[str, int] = {}
    for thu_tu, (slug, ten, slug_cha) in enumerate(catalog.DANH_MUC):  # cha luôn đứng trước con
        dm, moi = await _lay_hoac_tao(
            db,
            DanhMuc,
            {"slug": slug},
            {"ten": ten, "danh_muc_cha_id": id_theo_slug[slug_cha] if slug_cha else None, "thu_tu": thu_tu},
        )
        id_theo_slug[slug] = dm.id
        dem["danh_muc"] += moi
    return id_theo_slug


async def _nap_danh_muc_phu(db: AsyncSession, dem: Counter) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    thuong_hieu: dict[str, int] = {}
    for ten in catalog.THUONG_HIEU:
        doi_tuong, moi = await _lay_hoac_tao(db, ThuongHieu, {"ten": ten})
        thuong_hieu[ten] = doi_tuong.id
        dem["thuong_hieu"] += moi
    nha_san_xuat: dict[str, int] = {}
    for ten, quoc_gia in catalog.NHA_SAN_XUAT:
        doi_tuong, moi = await _lay_hoac_tao(db, NhaSanXuat, {"ten": ten}, {"quoc_gia": quoc_gia})
        nha_san_xuat[ten] = doi_tuong.id
        dem["nha_san_xuat"] += moi
    hoat_chat: dict[str, int] = {}
    for ten, (ten_khac, mo_ta) in catalog.HOAT_CHAT.items():
        doi_tuong, moi = await _lay_hoac_tao(db, HoatChat, {"ten": ten}, {"ten_khac": ten_khac or None, "mo_ta": mo_ta})
        hoat_chat[ten] = doi_tuong.id
        dem["hoat_chat"] += moi
    return thuong_hieu, nha_san_xuat, hoat_chat


async def _nap_san_pham(
    db: AsyncSession,
    sp: SanPhamMau,
    id_danh_muc: dict[str, int],
    id_thuong_hieu: dict[str, int],
    id_nha_san_xuat: dict[str, int],
    id_hoat_chat: dict[str, int],
    dem: Counter,
) -> SanPham:
    doi_tuong, moi = await _lay_hoac_tao(
        db,
        SanPham,
        {"sku": sp.sku},
        {
            "ten": sp.ten,
            "slug": tao_slug(sp.ten),
            "loai_san_pham": sp.loai,
            "danh_muc_id": id_danh_muc[sp.danh_muc],
            "thuong_hieu_id": id_thuong_hieu[sp.thuong_hieu],
            "nha_san_xuat_id": id_nha_san_xuat[sp.nha_san_xuat],
            "so_dang_ky": sp.so_dang_ky,
            "dang_bao_che": sp.dang_bao_che,
            "quy_cach": sp.quy_cach,
            "doi_tuong_su_dung": sp.doi_tuong,
            "don_vi_co_so": sp.don_vi_co_so,
            "ton_toi_thieu": sp.ton_toi_thieu,
            "dung_dinh_ky": sp.dung_dinh_ky,
            "so_ngay_dung_moi_don_vi": sp.so_ngay_dung_moi_don_vi,
            "so_luong_toi_da_moi_don": sp.so_luong_toi_da_moi_don,
            "la_noi_bat": sp.la_noi_bat,
            "trang_thai": "ngung_kinh_doanh" if sp.ngung_kinh_doanh else "dang_kinh_doanh",
        },
    )
    if moi:
        dem["san_pham"] += 1
        for don_vi in sp.don_vi:
            db.add(
                DonViQuyDoi(
                    san_pham_id=doi_tuong.id,
                    ten_don_vi=don_vi.ten,
                    he_so=don_vi.he_so,
                    gia_ban=don_vi.gia_ban,
                    la_mac_dinh=don_vi.la_mac_dinh,
                    ban_online=don_vi.ban_online,
                )
            )
        for ten_hoat_chat, ham_luong in sp.hoat_chat:
            db.add(
                ThanhPhan(
                    san_pham_id=doi_tuong.id, hoat_chat_id=id_hoat_chat[ten_hoat_chat], ham_luong=ham_luong or None
                )
            )
        await db.flush()
    return doi_tuong


async def _nap_tuong_tac(db: AsyncSession, id_hoat_chat: dict[str, int], dem: Counter) -> None:
    for ten_a, ten_b, muc_do, co_che, khuyen_cao in catalog.TUONG_TAC:
        a, b = sorted((id_hoat_chat[ten_a], id_hoat_chat[ten_b]))  # mỗi cặp lưu một lần với a < b
        _, moi = await _lay_hoac_tao(
            db,
            TuongTacHoatChat,
            {"hoat_chat_a_id": a, "hoat_chat_b_id": b},
            {
                "muc_do": muc_do,
                "co_che": co_che,
                "khuyen_cao": khuyen_cao,
                "nguon_tham_khao": "Dữ liệu mẫu cho demo, chưa được dược sĩ thẩm định",
            },
        )
        dem["tuong_tac_hoat_chat"] += moi


async def _nap_noi_dung_chuyen_mon(
    db: AsyncSession, san_pham: Sequence[tuple[SanPhamMau, SanPham]], duoc_si: NhanVien, dem: Counter
) -> None:
    """Phiên bản 1 đã duyệt cho vài sản phẩm để trang chi tiết có nội dung chuyên môn. Sản phẩm đã có phiên bản nào
    (kể cả nháp do dược sĩ thật soạn) thì bỏ qua, không đè lên công việc của người dùng."""
    for sp_mau, sp in san_pham:
        noi_dung = catalog.NOI_DUNG_CHUYEN_MON.get(sp_mau.ma)
        if noi_dung is None:
            continue
        da_co = await db.scalar(select(ThongTinChuyenMon.id).where(ThongTinChuyenMon.san_pham_id == sp.id).limit(1))
        if da_co is not None:
            continue
        db.add(
            ThongTinChuyenMon(
                san_pham_id=sp.id,
                phien_ban=1,
                trang_thai="da_duyet",
                nguoi_soan_id=duoc_si.id,
                duoc_si_duyet_id=duoc_si.id,
                ngay_duyet=bay_gio_utc(),
                **noi_dung,
            )
        )
        dem["noi_dung_chuyen_mon"] += 1
    await db.flush()


async def _nap_bai_viet(db: AsyncSession, duoc_si: NhanVien, dem: Counter) -> None:
    """Bài sức khỏe (đã duyệt), chính sách và FAQ mẫu. Tìm theo slug: bài đã có (kể cả đã sửa hay gỡ) thì giữ nguyên."""
    for loai, tieu_de, noi_dung, dua_vao_ai in catalog.BAI_VIET_MAU:
        slug = tao_slug(tieu_de, 250)
        _, moi = await _lay_hoac_tao(
            db,
            BaiViet,
            {"slug": slug},
            {
                "tieu_de": tieu_de,
                "noi_dung": noi_dung,
                "loai": loai,
                "tac_gia_id": duoc_si.id,
                "trang_thai": "da_duyet",
                "dua_vao_ai": dua_vao_ai,
                "duoc_si_duyet_id": duoc_si.id if loai == "bai_viet" else None,
                "ngay_duyet": bay_gio_utc(),
            },
        )
        dem["bai_viet"] += moi


async def _nap_banner(db: AsyncSession, dem: Counter) -> None:
    for tieu_de, anh_url, lien_ket, vi_tri, thu_tu in catalog.BANNER_MAU:
        _, moi = await _lay_hoac_tao(
            db,
            Banner,
            {"anh_url": anh_url},
            {"tieu_de": tieu_de, "lien_ket": lien_ket, "vi_tri": vi_tri, "thu_tu": thu_tu},
        )
        dem["banner"] += moi


async def _nap_nhan_vien(db: AsyncSession, vai_tro_id: dict[str, int], dem: Counter) -> dict[str, NhanVien]:
    mau = {
        "PHARMACIST": ("Nguyễn Thị Mai (dược sĩ mẫu)", "duocsi@example.com", "0901000001"),
        "WAREHOUSE": ("Trần Văn Kho (nhân viên kho mẫu)", "kho@example.com", "0901000002"),
    }
    ket_qua: dict[str, NhanVien] = {}
    for ma_vai_tro, (ho_ten, email, sdt) in mau.items():
        nv = (await db.execute(select(NhanVien).where(NhanVien.email == email))).scalars().first()
        if nv is None:
            nv = NhanVien(
                ma_nhan_vien=await ma_nhan_vien(db),
                ho_ten=ho_ten,
                email=email,
                so_dien_thoai=sdt,
                mat_khau_hash=_hash_mat_khau_mau(),
                vai_tro_id=vai_tro_id[ma_vai_tro],
                phai_doi_mat_khau=False,
            )
            db.add(nv)
            await db.flush()
            dem["nhan_vien"] += 1
        ket_qua[ma_vai_tro] = nv
    return ket_qua


async def _nap_khach_hang(db: AsyncSession, dem: Counter) -> None:
    # Mã tỉnh/huyện/xã là mã giả cho adapter vận chuyển giả, chưa đối chiếu danh mục thật của GHN.
    mau = [
        (
            "Lê Minh Anh (khách mẫu)",
            "0900000001",
            "khach1@example.com",
            [
                ("12 Nguyễn Huệ", "202", "TP. Hồ Chí Minh", "1442", "20101", "Phường Bến Nghé", True),
                ("45 Lê Lợi", "202", "TP. Hồ Chí Minh", "1442", "20103", "Phường Bến Thành", False),
            ],
        ),
        (
            "Phạm Quốc Bảo (khách mẫu)",
            "0900000002",
            "khach2@example.com",
            [("8 Hàng Bài", "201", "Hà Nội", "1482", "1A0101", "Phường Hàng Bài", True)],
        ),
    ]
    bay_gio = bay_gio_utc()
    for ho_ten, sdt, email, dia_chi in mau:
        kh, moi = await _lay_hoac_tao(
            db,
            KhachHang,
            {"so_dien_thoai": sdt},
            {
                "ho_ten": ho_ten,
                "email": email,
                "mat_khau_hash": _hash_mat_khau_mau(),
                "dong_y_chinh_sach_luc": bay_gio,
            },
        )
        dem["khach_hang"] += moi
        if not moi:
            continue  # khách đã có (có thể đã sửa sổ địa chỉ): không thêm địa chỉ mẫu nữa
        for chi_tiet, ma_tinh, ten_tinh, ma_quan, ma_xa, ten_xa, mac_dinh in dia_chi:
            _, moi_dc = await _lay_hoac_tao(
                db,
                DiaChi,
                {"khach_hang_id": kh.id, "dia_chi_chi_tiet": chi_tiet},
                {
                    "ten_nguoi_nhan": ho_ten,
                    "so_dien_thoai": sdt,
                    "ma_tinh": ma_tinh,
                    "ten_tinh": ten_tinh,
                    "ma_quan_huyen": ma_quan,
                    "ma_phuong_xa": ma_xa,
                    "ten_phuong_xa": ten_xa,
                    "la_mac_dinh": mac_dinh,
                },
            )
            dem["dia_chi"] += moi_dc


async def _nap_khuyen_mai(db: AsyncSession, dem: Counter) -> None:
    bay_gio = bay_gio_utc()
    mau = [
        # (mã, tên, loại, giá trị, giảm tối đa, đơn tối thiểu, bắt đầu, kết thúc, tổng lượt)
        ("CHAO10", "Chào bạn mới: giảm 10%", "phan_tram", 10, 50000, 200000, -1, 90, 1000),
        ("GIAM30K", "Giảm 30.000đ cho đơn từ 300.000đ", "so_tien", 30000, None, 300000, -1, 60, 500),
        ("HETHAN15", "Khuyến mãi đã kết thúc (dữ liệu thử)", "phan_tram", 15, 100000, 0, -60, -30, 100),
    ]
    for ma, ten, loai, gia_tri, giam_toi_da, don_toi_thieu, bat_dau, ket_thuc, tong_luot in mau:
        if (await db.execute(select(MaGiamGia.id).where(MaGiamGia.ma == ma))).first():
            continue
        km = KhuyenMai(
            ten=ten,
            loai_giam=loai,
            gia_tri=Decimal(gia_tri),
            giam_toi_da=Decimal(giam_toi_da) if giam_toi_da else None,
            don_toi_thieu=Decimal(don_toi_thieu),
            bat_dau=bay_gio + timedelta(days=bat_dau),
            ket_thuc=bay_gio + timedelta(days=ket_thuc),
            tong_luot=tong_luot,
            luot_moi_khach=1,
        )
        db.add(km)
        await db.flush()
        db.add(MaGiamGia(khuyen_mai_id=km.id, ma=ma))
        dem["khuyen_mai"] += 1
        dem["ma_giam_gia"] += 1
    await db.flush()


async def _nap_nha_cung_cap(db: AsyncSession, dem: Counter) -> list[NhaCungCap]:
    ket_qua = []
    for ten, mst, dia_chi, lien_he, sdt, email in catalog.NHA_CUNG_CAP:
        ncc, moi = await _lay_hoac_tao(
            db,
            NhaCungCap,
            {"ma_so_thue": mst},
            {"ten": ten, "dia_chi": dia_chi, "nguoi_lien_he": lien_he, "so_dien_thoai": sdt, "email": email},
        )
        dem["nha_cung_cap"] += moi
        ket_qua.append(ncc)
    return ket_qua


async def _nguong_can_han(db: AsyncSession) -> int:
    gia_tri = (
        await db.execute(select(CauHinh.gia_tri).where(CauHinh.khoa == "nguong_can_han_ngay"))
    ).scalar_one_or_none()
    return int(gia_tri) if gia_tri is not None else NGUONG_CAN_HAN_MAC_DINH


async def _nap_ton_kho(
    db: AsyncSession,
    san_pham: Sequence[tuple[SanPhamMau, SanPham]],
    nha_cung_cap: list[NhaCungCap],
    nv_kho: NhanVien,
    dem: Counter,
    hom_nay: date,
) -> None:
    """Mỗi nhà cung cấp một phiếu nhập mẫu chứa mọi lô của sản phẩm thuộc nó."""
    nguong = await _nguong_can_han(db)
    phieu_theo_ncc: dict[int, PhieuNhap] = {}

    for sp_mau, sp in san_pham:
        lo_mau = sp_mau.lo if sp_mau.lo is not None else catalog.lo_mac_dinh(sp_mau)
        if not lo_mau:
            continue
        don_vi = (await db.execute(select(DonViQuyDoi).where(DonViQuyDoi.san_pham_id == sp.id))).scalars().all()
        mac_dinh = next(d for d in don_vi if d.la_mac_dinh)
        gia_ban_co_so = next(d for d in don_vi if d.he_so == 1).gia_ban
        chi_so_ncc = catalog.NCC_THEO_LOAI[sp_mau.loai]
        ncc = nha_cung_cap[chi_so_ncc]

        for lo in lo_mau:
            so_lo = f"MAU-{sp_mau.ma:04d}{lo.chu_lo}"  # không chứa năm: chạy lại sang năm mới vẫn nhận ra lô cũ
            da_co = (
                await db.execute(select(LoThuoc.id).where(LoThuoc.san_pham_id == sp.id, LoThuoc.so_lo == so_lo))
            ).first()
            if da_co:
                continue
            if ncc.id not in phieu_theo_ncc:
                phieu_theo_ncc[ncc.id] = await _lay_hoac_tao_phieu_nhap(db, ncc, chi_so_ncc, nv_kho, dem)
            phieu = phieu_theo_ncc[ncc.id]

            han = hom_nay + timedelta(days=lo.han_con_lai_ngay)
            gia_von_co_so = lam_tron_vnd(gia_ban_co_so * lo.ty_le_gia_von)
            lo_thuoc = LoThuoc(
                san_pham_id=sp.id,
                so_lo=so_lo,
                ngay_san_xuat=min(han - timedelta(days=730), hom_nay - timedelta(days=30)),  # không ở tương lai
                han_su_dung=han,
                gia_nhap=gia_von_co_so,
                trang_thai=trang_thai_lo(han, hom_nay, nguong),
            )
            db.add(lo_thuoc)
            await db.flush()
            so_luong_co_so = lo.so_luong * mac_dinh.he_so
            db.add(
                CtPhieuNhap(
                    phieu_nhap_id=phieu.id,
                    lo_id=lo_thuoc.id,
                    don_vi_id=mac_dinh.id,
                    so_luong=lo.so_luong,
                    so_luong_co_so=so_luong_co_so,
                    gia_nhap=gia_von_co_so * mac_dinh.he_so,
                )
            )
            await db.flush()
            await nhap_kho(
                db, lo_thuoc, so_luong_co_so, ChungTu("phieu_nhap", phieu.id, nv_kho.id), luc=phieu.ngay_nhap
            )
            dem["lo_thuoc"] += 1

    for phieu in phieu_theo_ncc.values():  # tổng tiền = tổng các dòng, tính lại sau khi thêm lô
        dong = (
            await db.execute(
                select(CtPhieuNhap.so_luong, CtPhieuNhap.gia_nhap).where(CtPhieuNhap.phieu_nhap_id == phieu.id)
            )
        ).all()
        phieu.tong_tien = cong(*[so_luong * gia for so_luong, gia in dong])
    await db.flush()


async def _lay_hoac_tao_phieu_nhap(
    db: AsyncSession, ncc: NhaCungCap, chi_so_ncc: int, nv_kho: NhanVien, dem: Counter
) -> PhieuNhap:
    so_hoa_don = f"MAU-HD-{chi_so_ncc + 1:03d}"
    phieu = (
        (
            await db.execute(
                select(PhieuNhap).where(PhieuNhap.nha_cung_cap_id == ncc.id, PhieuNhap.so_hoa_don_ncc == so_hoa_don)
            )
        )
        .scalars()
        .first()
    )
    if phieu is None:
        phieu = PhieuNhap(
            ma_phieu=await ma_phieu(db, "phieu_nhap"),
            nha_cung_cap_id=ncc.id,
            so_hoa_don_ncc=so_hoa_don,
            nhan_vien_id=nv_kho.id,
            ngay_nhap=bay_gio_utc() - timedelta(days=NGAY_NHAP_PHIEU_MAU_TRUOC),
            ghi_chu="Phiếu nhập mẫu do seed tạo",
        )
        db.add(phieu)
        await db.flush()
        dem["phieu_nhap"] += 1
    return phieu


async def seed_mau(db: AsyncSession, *, hom_nay: date | None = None) -> dict[str, int]:
    """Nạp toàn bộ dữ liệu mẫu. Cần `seed_co_ban` chạy trước (vai trò). Trả số đối tượng MỚI tạo ở lần chạy này.

    `hom_nay` (giờ VN) chỉ để test chạy giả lập ngày khác; mặc định là hôm nay.
    """
    await khoa_seed(db)
    vai_tro_id = {ma: id_ for id_, ma in (await db.execute(select(VaiTro.id, VaiTro.ma))).all()}
    if not {"PHARMACIST", "WAREHOUSE"} <= vai_tro_id.keys():
        raise RuntimeError("Chưa có vai trò: chạy seed_co_ban (uv run python -m app.seed) trước khi nạp dữ liệu mẫu")

    dem: Counter = Counter()
    id_danh_muc = await _nap_danh_muc(db, dem)
    id_thuong_hieu, id_nha_san_xuat, id_hoat_chat = await _nap_danh_muc_phu(db, dem)
    san_pham = [
        (sp, await _nap_san_pham(db, sp, id_danh_muc, id_thuong_hieu, id_nha_san_xuat, id_hoat_chat, dem))
        for sp in catalog.SAN_PHAM
    ]
    await _nap_tuong_tac(db, id_hoat_chat, dem)
    nhan_vien = await _nap_nhan_vien(db, vai_tro_id, dem)
    await _nap_noi_dung_chuyen_mon(db, san_pham, nhan_vien["PHARMACIST"], dem)
    await _nap_banner(db, dem)
    await _nap_bai_viet(db, nhan_vien["PHARMACIST"], dem)
    nha_cung_cap = await _nap_nha_cung_cap(db, dem)
    await _nap_ton_kho(db, san_pham, nha_cung_cap, nhan_vien["WAREHOUSE"], dem, hom_nay or hom_nay_vn())
    await _nap_khach_hang(db, dem)
    await _nap_khuyen_mai(db, dem)
    return {ten: so_luong for ten, so_luong in dem.items() if so_luong}
