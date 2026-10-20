"""Bán tại quầy POS (DS08, spec 04 mục 1.1 dòng 6 và mục 1.2 dòng 2). Không commit.

Đơn POS hoàn tất ngay trong một transaction: giữ hàng FEFO (được dùng lô cận hạn) rồi xuất kho, ghi giao dịch thanh
toán thành công và đưa đơn thẳng tới `hoan_tat` qua `khoi_tao_trang_thai`. Thuốc kê đơn chỉ bán được khi có yêu cầu đơn
thuốc kênh `tai_quay` do chính dược sĩ lập trước (ảnh + người bệnh); yêu cầu thành `da_su_dung` khi đơn hoàn tất.
"""

import secrets
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import exists, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import idempotency, luu_tru
from app.core.loi import LoiNghiepVu
from app.core.ma_chung_tu import ma_don_hang
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_duoc_si
from app.core.thoi_gian import bay_gio_utc, hom_nay_vn
from app.core.tien import lam_tron_vnd
from app.models.ban_hang import DonHang, ThanhToan, YeuCauDonThuoc
from app.models.enums import (
    HinhThucNhan,
    KenhBan,
    LoaiGiaoDich,
    LoaiSanPham,
    MucDoTuongTac,
    PhuongThucThanhToan,
    TrangThaiDon,
    TrangThaiGiaoDich,
    TrangThaiKinhDoanh,
    TrangThaiLo,
    TrangThaiThanhToan,
    TrangThaiYeuCauDonThuoc,
)
from app.models.he_thong import NhanVien, NhatKyHeThong
from app.models.khach_hang import HoSoSucKhoe, KhachHang
from app.models.kho import LoThuoc
from app.models.san_pham import DonViQuyDoi, HoatChat, SanPham, ThanhPhan
from app.modules.ban_hang import dat_hang
from app.modules.ban_hang.schemas_pos import (
    CanhBaoPosRa,
    CanhBaoPosVao,
    DongHoaDon,
    DonPosRa,
    DonPosVao,
    DonViPos,
    HoaDonRa,
    SanPhamPos,
    YeuCauQuayRa,
    YeuCauQuayVao,
)
from app.modules.ban_hang.trang_thai import NGUON_NGUOI_DUNG, TacNhan, khoi_tao_trang_thai
from app.modules.chuyen_mon import canh_bao
from app.modules.don_thuoc import dich_vu as dich_vu_don_thuoc
from app.modules.gio_hang import dich_vu as dich_vu_gio
from app.modules.kho import ton_kho
from app.modules.kho.ton_kho import ChungTu, YeuCauGiu

THAO_TAC = "pos"
TEN_NHA_THUOC = "Nhà thuốc AI"
TRANG_THAI_LO_QUAY = (TrangThaiLo.dang_ban, TrangThaiLo.can_han)
MUC_NANG = (MucDoTuongTac.nghiem_trong, MucDoTuongTac.chong_chi_dinh)


def _khong_hop_le(truong: str, loi: str) -> LoiNghiepVu:
    return dat_hang.khong_hop_le(truong, loi)


# --- Tìm sản phẩm ---


async def tim_san_pham(db: AsyncSession, nv: NhanVien, q: str) -> list[SanPhamPos]:
    """Tìm theo tên, hoạt chất hoặc mã vạch (khớp đúng). Tối đa 20 sản phẩm, kể cả thuốc kê đơn."""
    from app.core.tim_kiem import mau_tim_like

    await dam_bao_la_duoc_si(db, nv)
    q = q.strip()
    if not q:
        return []
    mau = func.unaccent(mau_tim_like(q))
    co_hoat_chat = exists().where(
        ThanhPhan.san_pham_id == SanPham.id,
        HoatChat.id == ThanhPhan.hoat_chat_id,
        func.unaccent(HoatChat.ten).ilike(mau, escape="\\"),
    )
    theo_ma_vach = exists().where(DonViQuyDoi.san_pham_id == SanPham.id, DonViQuyDoi.ma_vach == q)
    han = hom_nay_vn()
    ton = (
        select(func.coalesce(func.sum(LoThuoc.so_luong_ton - LoThuoc.so_luong_giu), 0))
        .where(
            LoThuoc.san_pham_id == SanPham.id,
            LoThuoc.trang_thai.in_(TRANG_THAI_LO_QUAY),
            LoThuoc.han_su_dung > han,
        )
        .correlate(SanPham)
        .scalar_subquery()
    )
    can_han = (
        exists()
        .where(
            LoThuoc.san_pham_id == SanPham.id,
            LoThuoc.trang_thai == TrangThaiLo.can_han,
            LoThuoc.han_su_dung > han,
            LoThuoc.so_luong_ton - LoThuoc.so_luong_giu > 0,
        )
        .correlate(SanPham)
    )
    ds = (
        await db.execute(
            select(SanPham, ton.label("ton"), can_han.label("can_han"))
            .where(
                SanPham.deleted_at.is_(None),
                SanPham.trang_thai == TrangThaiKinhDoanh.dang_kinh_doanh,
                or_(func.unaccent(SanPham.ten).ilike(mau, escape="\\"), co_hoat_chat, theo_ma_vach),
            )
            .order_by(theo_ma_vach.desc(), SanPham.ten)
            .limit(20)
        )
    ).all()
    ids = [sp.id for sp, _, _ in ds]
    don_vi: dict[int, list[DonViQuyDoi]] = {i: [] for i in ids}
    hoat_chat: dict[int, list[str]] = {i: [] for i in ids}
    if ids:
        for d in (
            (await db.execute(select(DonViQuyDoi).where(DonViQuyDoi.san_pham_id.in_(ids)).order_by("he_so", "id")))
            .scalars()
            .all()
        ):
            don_vi[d.san_pham_id].append(d)
        for sp_id, ten in (
            await db.execute(
                select(ThanhPhan.san_pham_id, HoatChat.ten)
                .join(HoatChat, HoatChat.id == ThanhPhan.hoat_chat_id)
                .where(ThanhPhan.san_pham_id.in_(ids))
                .order_by(HoatChat.ten)
            )
        ).all():
            hoat_chat[sp_id].append(ten)
    return [
        SanPhamPos(
            id=sp.id,
            ten=sp.ten,
            loai_san_pham=sp.loai_san_pham,
            don_vi_co_so=sp.don_vi_co_so,
            ton_quay=max(int(t or 0), 0),
            co_lo_can_han=bool(cb),
            hoat_chat=hoat_chat[sp.id],
            don_vi=[
                DonViPos(id=d.id, ten_don_vi=d.ten_don_vi, he_so=d.he_so, gia_ban=d.gia_ban, ma_vach=d.ma_vach)
                for d in don_vi[sp.id]
            ],
            don_vi_khop_ma_vach=next((d.id for d in don_vi[sp.id] if d.ma_vach == q), None),
        )
        for sp, t, cb in ds
    ]


# --- Yêu cầu đơn thuốc kênh tại quầy (spec 04 mục 1.2 dòng 2) ---


async def tao_yeu_cau_quay(db: AsyncSession, nv: NhanVien, vao: YeuCauQuayVao, ds_anh: list[bytes]) -> YeuCauQuayRa:
    """Dược sĩ nhập đơn của khách ngay tại quầy: ảnh đơn + người bệnh. Vào thẳng `da_tao_don`, gắn dược sĩ."""
    await dam_bao_la_duoc_si(db, nv)
    kieu = dich_vu_don_thuoc.kiem_tra_anh(ds_anh)
    khoa = []
    store = luu_tru.luu_tru()
    for noi_dung, k in zip(ds_anh, kieu, strict=True):
        f = await store.luu("don-thuoc", noi_dung, k, vung="rieng_tu")
        luu_tru.xoa_neu_hoan_tac(db, f, "rieng_tu")
        khoa.append(f)
    ghi_chu = "; ".join(
        x for x in (f"Tuổi/năm sinh: {vao.tuoi_hoac_nam_sinh}" if vao.tuoi_hoac_nam_sinh else None, vao.ghi_chu) if x
    )
    h = dich_vu_don_thuoc.hash_anh(ds_anh)
    yc = YeuCauDonThuoc(
        ma_yeu_cau="YC" + secrets.token_hex(4).upper(),
        khach_hang_id=None,
        kenh=KenhBan.tai_quay,
        ho_ten=vao.ho_ten,
        so_dien_thoai=vao.so_dien_thoai or "",
        anh_don_thuoc=khoa,
        hash_anh=h,
        ghi_chu=ghi_chu or None,
        trang_thai=TrangThaiYeuCauDonThuoc.da_tao_don,
        duoc_si_id=nv.id,
        khoa_luc=bay_gio_utc(),
    )
    db.add(yc)
    await db.flush()
    cu = (
        (
            await db.execute(
                select(YeuCauDonThuoc.ma_yeu_cau).where(
                    YeuCauDonThuoc.hash_anh == h, YeuCauDonThuoc.da_su_dung.is_(True)
                )
            )
        )
        .scalars()
        .all()
    )
    return YeuCauQuayRa(id=yc.id, ma_yeu_cau=yc.ma_yeu_cau, ho_ten=yc.ho_ten, trung_anh=list(cu))


# --- Cảnh báo và bán ---


async def _khach_theo_sdt(db: AsyncSession, sdt: str | None) -> KhachHang | None:
    if not sdt:
        return None
    return (
        await db.execute(select(KhachHang).where(KhachHang.so_dien_thoai == sdt, KhachHang.deleted_at.is_(None)))
    ).scalar_one_or_none()


SO_KHACH_TOI_DA_MOI_GIO = 15
"""Số khách khác nhau một dược sĩ được tra dị ứng qua POS trong một giờ (chống dò hồ sơ theo số điện thoại)."""


async def _di_ung_cua_khach_tai_quay(db: AsyncSession, nv: NhanVien, khach: KhachHang, sp_ids: list[int]):
    """Dị ứng của thành viên đứng tại quầy. Khác cổng đọc hồ sơ (khách không có yêu cầu hay phiên chat với dược sĩ này)
    nên: chỉ khi khách đã đồng ý dùng hồ sơ sức khỏe; mỗi lần tra ghi nhật ký `doc_suc_khoe` (không ghi nội dung); và
    giới hạn số khách khác nhau mỗi giờ để không dò được dị ứng của người lạ bằng cách thử số điện thoại."""
    dong_y = await db.scalar(select(HoSoSucKhoe.dong_y_su_dung).where(HoSoSucKhoe.khach_hang_id == khach.id))
    if not dong_y:
        return []
    mot_gio_truoc = bay_gio_utc() - timedelta(hours=1)
    nhat_ky = (NhatKyHeThong.nhan_vien_id == nv.id, NhatKyHeThong.hanh_dong == "doc_suc_khoe")
    nhat_ky += (NhatKyHeThong.bang == "di_ung", NhatKyHeThong.created_at > mot_gio_truoc)
    da_tra_khach_nay = await db.scalar(select(func.count()).where(*nhat_ky, NhatKyHeThong.ban_ghi_id == str(khach.id)))
    if not da_tra_khach_nay:
        so_khach = await db.scalar(select(func.count(func.distinct(NhatKyHeThong.ban_ghi_id))).where(*nhat_ky))
        if (so_khach or 0) >= SO_KHACH_TOI_DA_MOI_GIO:
            raise LoiNghiepVu("QUA_GIOI_HAN", "Đã tra dị ứng quá nhiều khách trong một giờ, vui lòng thử lại sau")
    await ghi_nhat_ky(db, nhan_vien_id=nv.id, hanh_dong="doc_suc_khoe", bang="di_ung", ban_ghi_id=khach.id)
    return await canh_bao.kiem_tra_di_ung(db, khach.id, sp_ids)


async def _canh_bao(db: AsyncSession, nv: NhanVien, khach: KhachHang | None, sp_ids: list[int]) -> CanhBaoPosRa:
    tuong_tac = await canh_bao.kiem_tra_tuong_tac(db, sp_ids)
    di_ung = [] if khach is None else await _di_ung_cua_khach_tai_quay(db, nv, khach, sp_ids)
    nang = any(c.muc_do in MUC_NANG for c in tuong_tac) or bool(di_ung)
    return CanhBaoPosRa(tuong_tac=tuong_tac, di_ung=di_ung, can_xac_nhan=nang)


async def tinh_canh_bao(db: AsyncSession, nv: NhanVien, vao: CanhBaoPosVao) -> CanhBaoPosRa:
    await dam_bao_la_duoc_si(db, nv)
    khach = await _khach_theo_sdt(db, vao.sdt_khach)
    return await _canh_bao(db, nv, khach, [d.san_pham_id for d in vao.dong])


async def _yeu_cau_quay_hop_le(db: AsyncSession, nv: NhanVien, yc_id: int | None) -> YeuCauDonThuoc:
    if yc_id is None:
        raise _khong_hop_le(
            "yeu_cau_don_thuoc_id", "Thuốc kê đơn cần lập yêu cầu đơn thuốc (ảnh đơn, người bệnh) trước"
        )
    yc = (
        await db.execute(
            select(YeuCauDonThuoc)
            .where(YeuCauDonThuoc.id == yc_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if yc is None or yc.kenh != KenhBan.tai_quay or yc.duoc_si_id != nv.id:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy yêu cầu đơn thuốc tại quầy của bạn")
    da_ban = await db.scalar(select(exists().where(DonHang.yeu_cau_don_thuoc_id == yc.id)))
    if yc.da_su_dung or da_ban:
        raise LoiNghiepVu("TRUNG_DU_LIEU", "Yêu cầu đơn thuốc này đã được dùng cho một đơn khác")
    return yc


async def ban_hang(db: AsyncSession, nv: NhanVien, vao: DonPosVao, khoa: str) -> DonPosRa:
    await dam_bao_la_duoc_si(db, nv)
    dau_van_tay = idempotency.dau_van_tay(vao.model_dump(mode="json"))
    # Hai request cùng khóa chạy song song (bấm đúp, thử lại khi timeout) phải nối đuôi nhau, nếu không cả hai cùng
    # thấy "chưa có" và tạo hai đơn, trừ tồn hai lần
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"{THAO_TAC}:{nv.id}:{khoa}"})
    da_co = idempotency.tra_cuu(THAO_TAC, nv.id, khoa, dau_van_tay)
    if da_co is not None:
        ton_tai = await db.scalar(select(DonHang.id).where(DonHang.id == da_co["don_id"]))
        if ton_tai is not None:
            return DonPosRa.model_validate(da_co)

    gop: dict[tuple[int, int], int] = {}
    for d in vao.dong:
        gop[(d.san_pham_id, d.don_vi_id)] = gop.get((d.san_pham_id, d.don_vi_id), 0) + d.so_luong
    dong_dat = await dich_vu_gio.kiem_tra_dong_de_dat(
        db, [(i, sp, dv, sl) for i, ((sp, dv), sl) in enumerate(gop.items())], cho_phep_ke_don=True
    )
    khach = await _khach_theo_sdt(db, vao.sdt_khach)
    if vao.sdt_khach and khach is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy khách hàng với số điện thoại này")
    co_ke_don = any(d.sp.loai_san_pham == LoaiSanPham.thuoc_ke_don for d in dong_dat)
    yc: YeuCauDonThuoc | None = None
    if co_ke_don:
        yc = await _yeu_cau_quay_hop_le(db, nv, vao.yeu_cau_don_thuoc_id)
        da_dung = (
            (
                await db.execute(
                    select(YeuCauDonThuoc.ma_yeu_cau).where(
                        YeuCauDonThuoc.hash_anh == yc.hash_anh,
                        YeuCauDonThuoc.id != yc.id,
                        YeuCauDonThuoc.da_su_dung.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )
        if da_dung and not vao.xac_nhan_trung_anh:
            raise LoiNghiepVu(
                "CAN_XAC_NHAN_CANH_BAO",
                "Ảnh đơn trùng với đơn đã được sử dụng. Hãy kiểm tra và xác nhận nếu vẫn bán",
                chi_tiet={"loai": "trung_anh", "ma_yeu_cau": list(da_dung)},
            )
    elif vao.yeu_cau_don_thuoc_id is not None:
        raise _khong_hop_le("yeu_cau_don_thuoc_id", "Đơn không có thuốc kê đơn nên không gắn yêu cầu đơn thuốc")
    cb = await _canh_bao(db, nv, khach, [d.sp.id for d in dong_dat])
    if cb.can_xac_nhan and not vao.xac_nhan_canh_bao:
        raise LoiNghiepVu(
            "CAN_XAC_NHAN_CANH_BAO",
            "Có cảnh báo tương tác hoặc dị ứng nghiêm trọng. Hãy tư vấn cho khách rồi xác nhận để bán",
            chi_tiet={"loai": "tuong_tac_di_ung", "so_tuong_tac": len(cb.tuong_tac), "so_di_ung": len(cb.di_ung)},
        )

    # Không mã giảm giá ở quầy; thuốc kê đơn không được giảm giá (CLAUDE.md quy tắc 6).
    t = await dat_hang.tinh_tien(db, None, dong_dat, None, None, dung_luot=False)
    tong = lam_tron_vnd(t.tong_tien)
    khach_dua: Decimal | None = None
    tien_thua: Decimal | None = None
    if vao.phuong_thuc_thu == PhuongThucThanhToan.tien_mat:
        if vao.tien_khach_dua is None or lam_tron_vnd(vao.tien_khach_dua) < tong:
            raise _khong_hop_le("tien_khach_dua", "Tiền khách đưa chưa đủ tổng tiền")
        khach_dua = lam_tron_vnd(vao.tien_khach_dua)
        tien_thua = khach_dua - tong
    elif vao.tien_khach_dua is not None:
        raise _khong_hop_le("tien_khach_dua", "Chỉ nhập tiền khách đưa với thanh toán tiền mặt")

    don = DonHang(
        ma_don=await ma_don_hang(db),
        khach_hang_id=khach.id if khach else None,
        kenh_ban=KenhBan.tai_quay,
        hinh_thuc_nhan=HinhThucNhan.nhan_tai_nha_thuoc,
        phuong_thuc_tt=vao.phuong_thuc_thu,
        trang_thai_tt=TrangThaiThanhToan.da_thanh_toan,
        yeu_cau_don_thuoc_id=yc.id if yc else None,
        tam_tinh=t.tam_tinh,
        giam_gia=t.giam,
        phi_van_chuyen=t.phi,
        tong_tien=t.tong_tien,
        ten_nguoi_nhan=khach.ho_ten if khach else None,
        sdt_nguoi_nhan=khach.so_dien_thoai if khach else None,
    )
    don.chi_tiet = dat_hang.dong_cua_don(t)
    tac_nhan = TacNhan.duoc_si(nv.id)
    await khoi_tao_trang_thai(db, don, TrangThaiDon.hoan_tat, tac_nhan, NGUON_NGUOI_DUNG, "Bán tại quầy")
    thu_tu = sorted(don.chi_tiet, key=lambda c: c.id)
    phan_bo = await ton_kho.giu_hang_nhieu(
        db, [YeuCauGiu(c.id, c.san_pham_id, c.so_luong * c.he_so) for c in thu_tu], cho_phep_can_han=True
    )
    await ton_kho.xuat_theo_phan_bo(db, [p for c in thu_tu for p in phan_bo[c.id]], ChungTu("don_hang", don.id, nv.id))
    db.add(
        ThanhToan(
            don_hang_id=don.id,
            loai=LoaiGiaoDich.thanh_toan,
            cong_thanh_toan=vao.phuong_thuc_thu,
            so_tien=tong,
            trang_thai=TrangThaiGiaoDich.thanh_cong,
            nhan_vien_xu_ly_id=nv.id,
            ghi_chu="Bán tại quầy",
        )
    )
    if yc is not None:
        yc.da_su_dung = True
        yc.updated_at = bay_gio_utc()
    await db.flush()
    ra = DonPosRa(don_id=don.id, hoa_don=await _hoa_don(db, don, nv, khach_dua, tien_thua))
    idempotency.ghi_nho(THAO_TAC, nv.id, khoa, dau_van_tay, ra.model_dump(mode="json"))
    return ra


async def _hoa_don(
    db: AsyncSession, don: DonHang, nv: NhanVien, khach_dua: Decimal | None, tien_thua: Decimal | None
) -> HoaDonRa:
    from app.models.ban_hang import CtDonHang

    dong = (
        (await db.execute(select(CtDonHang).where(CtDonHang.don_hang_id == don.id).order_by(CtDonHang.id)))
        .scalars()
        .all()
    )
    co_ke_don = bool(
        await db.scalar(
            select(
                exists().where(
                    CtDonHang.don_hang_id == don.id,
                    CtDonHang.san_pham_id == SanPham.id,
                    SanPham.loai_san_pham == LoaiSanPham.thuoc_ke_don,
                )
            )
        )
    )
    assert don.phuong_thuc_tt is not None
    await db.refresh(don)  # created_at do CSDL đặt
    nguoi_ban = await db.scalar(select(NhanVien.ho_ten).where(NhanVien.id == don.nhan_vien_tao_id)) or nv.ho_ten
    return HoaDonRa(
        ten_nha_thuoc=TEN_NHA_THUOC,
        ma_don=don.ma_don,
        thoi_diem=don.created_at,
        nhan_vien=nguoi_ban,
        khach=don.ten_nguoi_nhan,
        dong=[
            DongHoaDon(
                ten_san_pham=c.ten_san_pham,
                ten_don_vi=c.ten_don_vi,
                so_luong=c.so_luong,
                don_gia=c.don_gia,
                thanh_tien=c.thanh_tien,
            )
            for c in dong
        ],
        tam_tinh=don.tam_tinh,
        giam_gia=don.giam_gia,
        tong_tien=don.tong_tien,
        phuong_thuc_thu=don.phuong_thuc_tt,
        tien_khach_dua=khach_dua,
        tien_thua=tien_thua,
        co_thuoc_ke_don=co_ke_don,
    )


async def hoa_don(db: AsyncSession, nv: NhanVien, don_id: int) -> HoaDonRa:
    """In lại hóa đơn của đơn POS (không có số tiền khách đưa và tiền thối)."""
    await dam_bao_la_duoc_si(db, nv)
    don = (
        await db.execute(select(DonHang).where(DonHang.id == don_id, DonHang.kenh_ban == KenhBan.tai_quay))
    ).scalar_one_or_none()
    if don is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy đơn bán tại quầy")
    return await _hoa_don(db, don, nv, None, None)
