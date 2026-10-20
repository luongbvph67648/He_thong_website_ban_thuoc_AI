"""Thu hồi lô: Admin tạo và đóng lệnh (AD13), kho thực hiện (KHO12), dược sĩ liên hệ khách (DS13), T6.6."""

import logging

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.ma_chung_tu import ma_lenh_thu_hoi
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_admin, dam_bao_la_duoc_si
from app.core.phan_trang import ThamSoPhanTrang, Trang, lay_trang, tao_trang
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import CtDonHang, DonHang, PhanBoLo
from app.models.enums import (
    KetQuaLienHeThuHoi,
    TrangThaiLo,
    TrangThaiPhanBo,
    TrangThaiTaiKhoan,
    TrangThaiThuHoi,
)
from app.models.he_thong import NhanVien, VaiTro
from app.models.khach_hang import KhachHang
from app.models.kho import CtLenhThuHoi, LenhThuHoi, LoThuoc
from app.models.san_pham import SanPham
from app.modules.kho import ton_kho
from app.modules.kho.canh_bao import nhan_vien_kho
from app.modules.kho.lo_hang_ngay import KetQuaHt01, _phan_bo_lai
from app.modules.thong_bao import service as thong_bao
from app.modules.thu_hoi.schemas import KhachThuHoi, LenhChiTiet, LenhTao, LenhTomTat, LienHeVao, LoThuHoiRa

logger = logging.getLogger(__name__)
MA_VAI_TRO_DUOC_SI = "PHARMACIST"


def _khong_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy lệnh thu hồi")


async def _id_nhan_vien_theo_vai_tro(db: AsyncSession, ma: str) -> list[int]:
    return list(
        (
            await db.execute(
                select(NhanVien.id)
                .join(VaiTro, VaiTro.id == NhanVien.vai_tro_id)
                .where(
                    VaiTro.ma == ma,
                    NhanVien.trang_thai == TrangThaiTaiKhoan.hoat_dong,
                    NhanVien.deleted_at.is_(None),
                )
                .order_by(NhanVien.id)
            )
        ).scalars()
    )


# --- AD13: tạo lệnh ---


async def tao_lenh(db: AsyncSession, nv: NhanVien, vao: LenhTao, *, ip: str) -> LenhChiTiet:
    await dam_bao_la_admin(db, nv)
    sp = await db.get(SanPham, vao.san_pham_id)
    if sp is None or sp.deleted_at is not None:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": "san_pham_id", "loi": "Không tồn tại"}]
        )
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"thu_hoi:{sp.id}"})
    cau_lo = select(LoThuoc.id).where(LoThuoc.san_pham_id == sp.id)
    if vao.lo_id is not None:
        cau_lo = cau_lo.where(LoThuoc.id == vao.lo_id)
    lo_ids = sorted((await db.execute(cau_lo)).scalars().all())
    if not lo_ids:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "lo_id", "loi": "Lô không tồn tại hoặc không thuộc sản phẩm"}],
        )
    trung = await db.scalar(
        select(LenhThuHoi.ma_lenh).where(
            LenhThuHoi.san_pham_id == sp.id,
            LenhThuHoi.trang_thai == TrangThaiThuHoi.dang_thu_hoi,
            (LenhThuHoi.lo_id.is_(None)) | (LenhThuHoi.lo_id.in_(lo_ids)),
        )
    )
    if trung is not None:
        raise LoiNghiepVu("TRUNG_DU_LIEU", f"Đã có lệnh thu hồi {trung} đang mở cho sản phẩm/lô này")
    lenh = LenhThuHoi(
        ma_lenh=await ma_lenh_thu_hoi(db),
        san_pham_id=sp.id,
        lo_id=vao.lo_id,
        can_cu=vao.can_cu.strip(),
        muc_do=(vao.muc_do or "").strip() or None,
        nguoi_tao_id=nv.id,
    )
    db.add(lenh)
    await db.flush()
    # Khóa theo id tăng (quy tắc tồn kho) rồi đổi trạng thái: không phân bổ cho đơn mới nữa
    het_han_ids: list[int] = []
    for lo in await ton_kho.khoa_cac_lo(db, lo_ids):
        if lo.trang_thai != TrangThaiLo.thu_hoi:
            lo.trang_thai, lo.updated_at = TrangThaiLo.thu_hoi, bay_gio_utc()
            het_han_ids.append(lo.id)
    await db.flush()
    ket_qua = KetQuaHt01()
    await _phan_bo_lai(db, het_han_ids, ket_qua)  # gỡ khỏi đơn chưa xuất, giữ lại từ lô khác (FEFO)
    await _lap_dong_truy_vet(db, lenh, sp, lo_ids)
    await ghi_nhat_ky(
        db,
        nhan_vien_id=nv.id,
        hanh_dong="tao",
        bang="lenh_thu_hoi",
        ban_ghi_id=lenh.id,
        gia_tri_moi={"ma_lenh": lenh.ma_lenh, "san_pham_id": sp.id, "lo_id": vao.lo_id, "so_lo": len(lo_ids)},
        ip=ip,
    )
    await _bao_nhan_vien(db, lenh, sp, ket_qua.don_thieu_hang)
    ct = await chi_tiet(db, lenh.id)
    ct.don_thieu_hang = ket_qua.don_thieu_hang
    return ct


async def _lap_dong_truy_vet(db: AsyncSession, lenh: LenhThuHoi, sp: SanPham, lo_ids: list[int]) -> None:
    """Từ `phan_bo_lo` `da_xuat` của các lô bị thu hồi: mỗi đơn một dòng, báo khách có tài khoản."""
    dong = (
        await db.execute(
            select(DonHang, func.sum(PhanBoLo.so_luong_co_so))
            .join(CtDonHang, CtDonHang.don_hang_id == DonHang.id)
            .join(PhanBoLo, PhanBoLo.ct_don_hang_id == CtDonHang.id)
            .where(PhanBoLo.lo_id.in_(lo_ids), PhanBoLo.trang_thai == TrangThaiPhanBo.da_xuat)
            .group_by(DonHang.id)
            .order_by(DonHang.id)
        )
    ).all()
    lo_ten = {lo.id: lo.so_lo for lo in (await db.execute(select(LoThuoc).where(LoThuoc.id.in_(lo_ids)))).scalars()}
    mo_ta_lo = f"lô {lo_ten[lenh.lo_id]}" if lenh.lo_id else "các lô"
    for don, tong in dong:
        db.add(
            CtLenhThuHoi(
                lenh_thu_hoi_id=lenh.id, don_hang_id=don.id, khach_hang_id=don.khach_hang_id, so_luong_da_ban=tong
            )
        )
        if don.khach_hang_id is not None:
            await thong_bao.gui_cho_khach(
                db,
                don.khach_hang_id,
                loai="thu_hoi",
                tieu_de=f"Thông báo thu hồi thuốc liên quan đến đơn {don.ma_don}",
                noi_dung=(
                    f"Nhà thuốc thu hồi {mo_ta_lo} của sản phẩm {sp.ten} (căn cứ: {lenh.can_cu}). "
                    "Vui lòng ngừng sử dụng và liên hệ nhà thuốc để được hướng dẫn hoàn trả."
                ),
                lien_ket=f"/tai-khoan/don-hang/{don.ma_don}",
            )
        elif don.sdt_nguoi_nhan:
            await thong_bao.gui_sms_khong_tai_khoan(
                don.sdt_nguoi_nhan, f"Thong bao thu hoi thuoc lien quan don {don.ma_don}. Vui long lien he nha thuoc."
            )
    await db.flush()


async def _bao_nhan_vien(db: AsyncSession, lenh: LenhThuHoi, sp: SanPham, don_thieu_hang: list[str]) -> None:
    noi_dung = f"{sp.ten}: {lenh.can_cu}"
    for nv_id in await nhan_vien_kho(db):
        await thong_bao.gui_cho_nhan_vien(
            db,
            nv_id,
            loai="thu_hoi",
            tieu_de=f"Lệnh thu hồi {lenh.ma_lenh}",
            noi_dung=noi_dung
            + (f". Đơn mất hàng giữ, cần xử lý: {', '.join(don_thieu_hang[:20])}" if don_thieu_hang else ""),
            lien_ket="/nhan-vien/thuc-hien-thu-hoi",
        )
    for nv_id in await _id_nhan_vien_theo_vai_tro(db, MA_VAI_TRO_DUOC_SI):
        await thong_bao.gui_cho_nhan_vien(
            db, nv_id, loai="thu_hoi", tieu_de=f"Lệnh thu hồi {lenh.ma_lenh}: liên hệ khách", noi_dung=noi_dung,
            lien_ket="/nhan-vien/thu-hoi",
        )  # fmt: skip


# --- Đọc ---


async def _tom_tat(db: AsyncSession, lenh: LenhThuHoi, ten: str, so_lo: str | None) -> LenhTomTat:
    tong = await db.scalar(select(func.count()).where(CtLenhThuHoi.lenh_thu_hoi_id == lenh.id)) or 0
    xong = (
        await db.scalar(
            select(func.count()).where(
                CtLenhThuHoi.lenh_thu_hoi_id == lenh.id, CtLenhThuHoi.ket_qua_lien_he != KetQuaLienHeThuHoi.chua_lien_he
            )
        )
        or 0
    )
    return LenhTomTat(
        id=lenh.id,
        ma_lenh=lenh.ma_lenh,
        san_pham_ten=ten,
        so_lo=so_lo,
        can_cu=lenh.can_cu,
        muc_do=lenh.muc_do,
        trang_thai=lenh.trang_thai,
        so_khach=tong,
        so_khach_da_xu_ly=xong,
        created_at=lenh.created_at,
        dong_luc=lenh.dong_luc,
    )


async def danh_sach(
    db: AsyncSession, tp: ThamSoPhanTrang, trang_thai: TrangThaiThuHoi | None, *, chi_dang_mo: bool = False
) -> Trang[LenhTomTat]:
    cau = (
        select(LenhThuHoi, SanPham.ten, LoThuoc.so_lo)
        .join(SanPham, SanPham.id == LenhThuHoi.san_pham_id)
        .outerjoin(LoThuoc, LoThuoc.id == LenhThuHoi.lo_id)
        .order_by(LenhThuHoi.created_at.desc(), LenhThuHoi.id.desc())
    )
    if chi_dang_mo:
        trang_thai = TrangThaiThuHoi.dang_thu_hoi
    if trang_thai is not None:
        cau = cau.where(LenhThuHoi.trang_thai == trang_thai)
    ds, tong = await lay_trang(db, cau, tp, nhieu_cot=True)
    return tao_trang([await _tom_tat(db, lenh, ten, so_lo) for lenh, ten, so_lo in ds], tong, tp)


async def _lenh_va_lo_ids(db: AsyncSession, lenh_id: int) -> tuple[LenhThuHoi, str, str | None, list[int]]:
    dong = (
        await db.execute(
            select(LenhThuHoi, SanPham.ten, LoThuoc.so_lo)
            .join(SanPham, SanPham.id == LenhThuHoi.san_pham_id)
            .outerjoin(LoThuoc, LoThuoc.id == LenhThuHoi.lo_id)
            .where(LenhThuHoi.id == lenh_id)
        )
    ).first()
    if dong is None:
        raise _khong_thay()
    lenh = dong[0]
    cau = select(LoThuoc.id).where(LoThuoc.san_pham_id == lenh.san_pham_id)
    if lenh.lo_id is not None:
        cau = cau.where(LoThuoc.id == lenh.lo_id)
    else:
        cau = cau.where(LoThuoc.trang_thai == TrangThaiLo.thu_hoi)
    return lenh, dong[1], dong[2], sorted((await db.execute(cau)).scalars().all())


async def chi_tiet(db: AsyncSession, lenh_id: int) -> LenhChiTiet:
    lenh, ten, so_lo, lo_ids = await _lenh_va_lo_ids(db, lenh_id)
    da_ban = dict(
        (
            await db.execute(
                select(PhanBoLo.lo_id, func.sum(PhanBoLo.so_luong_co_so))
                .where(PhanBoLo.lo_id.in_(lo_ids), PhanBoLo.trang_thai == TrangThaiPhanBo.da_xuat)
                .group_by(PhanBoLo.lo_id)
            )
        ).all()
    )
    lo_thuoc = (await db.execute(select(LoThuoc).where(LoThuoc.id.in_(lo_ids)).order_by(LoThuoc.id))).scalars().all()
    lo_ra = [
        LoThuHoiRa(
            lo_id=lo.id,
            so_lo=lo.so_lo,
            han_su_dung=lo.han_su_dung,
            trang_thai=lo.trang_thai,
            so_luong_ton=lo.so_luong_ton,
            so_luong_biet_tru=lo.so_luong_biet_tru,
            so_luong_da_ban=int(da_ban.get(lo.id, 0)),
        )
        for lo in lo_thuoc
    ]
    tt = await _tom_tat(db, lenh, ten, so_lo)
    return LenhChiTiet(
        **tt.model_dump(), lo=lo_ra, ton_con_lai=sum(lo.so_luong_ton + lo.so_luong_biet_tru for lo in lo_thuoc)
    )


# --- AD13: đóng lệnh ---


async def dong_lenh(db: AsyncSession, nv: NhanVien, lenh_id: int, *, ip: str) -> LenhChiTiet:
    await dam_bao_la_admin(db, nv)
    lenh = (
        await db.execute(
            select(LenhThuHoi)
            .where(LenhThuHoi.id == lenh_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if lenh is None:
        raise _khong_thay()
    if lenh.trang_thai != TrangThaiThuHoi.dang_thu_hoi:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Lệnh thu hồi đã đóng")
    ct = await chi_tiet(db, lenh_id)
    chua_lien_he = ct.so_khach - ct.so_khach_da_xu_ly
    if chua_lien_he > 0 or ct.ton_con_lai > 0:
        raise LoiNghiepVu(
            "CHUYEN_TRANG_THAI_KHONG_HOP_LE",
            "Chưa đóng được lệnh: còn khách chưa liên hệ hoặc còn hàng ở các lô bị thu hồi",
            chi_tiet={"khach_chua_lien_he": chua_lien_he, "ton_con_lai": ct.ton_con_lai},
        )
    lenh.trang_thai, lenh.dong_luc = TrangThaiThuHoi.hoan_tat, bay_gio_utc()
    await db.flush()
    await ghi_nhat_ky(
        db, nhan_vien_id=nv.id, hanh_dong="dong", bang="lenh_thu_hoi", ban_ghi_id=lenh.id,
        gia_tri_moi={"ma_lenh": lenh.ma_lenh}, ip=ip,
    )  # fmt: skip
    return await chi_tiet(db, lenh_id)


# --- DS13: liên hệ khách ---


async def danh_sach_khach(db: AsyncSession, nv: NhanVien, lenh_id: int) -> list[KhachThuHoi]:
    """Dược sĩ liên hệ; Admin chỉ xem (`recall.contact` mức `chi_xem`). Vai trò khác bị chặn dù được gán quyền."""
    if await db.scalar(select(VaiTro.ma).where(VaiTro.id == nv.vai_tro_id)) not in (MA_VAI_TRO_DUOC_SI, "ADMIN"):
        raise LoiNghiepVu("KHONG_CO_QUYEN", "Chỉ dược sĩ hoặc Admin mới xem được danh sách khách thu hồi")
    lenh = await db.get(LenhThuHoi, lenh_id)
    if lenh is None or lenh.trang_thai != TrangThaiThuHoi.dang_thu_hoi:
        raise _khong_thay()  # chỉ khách thuộc lệnh đang mở
    ds = (
        await db.execute(
            select(CtLenhThuHoi, DonHang, KhachHang)
            .join(DonHang, DonHang.id == CtLenhThuHoi.don_hang_id)
            .outerjoin(KhachHang, KhachHang.id == CtLenhThuHoi.khach_hang_id)
            .where(CtLenhThuHoi.lenh_thu_hoi_id == lenh_id)
            .order_by(CtLenhThuHoi.id)
        )
    ).all()
    return [
        KhachThuHoi(
            id=ct.id,
            ma_don=don.ma_don,
            ten_khach=khach.ho_ten if khach else don.ten_nguoi_nhan,
            so_dien_thoai=khach.so_dien_thoai if khach else don.sdt_nguoi_nhan,
            so_luong_da_ban=ct.so_luong_da_ban,
            so_luong_da_thu_ve=ct.so_luong_da_thu_ve,
            ket_qua_lien_he=ct.ket_qua_lien_he,
            ghi_chu=ct.ghi_chu,
            cap_nhat_luc=ct.cap_nhat_luc,
        )
        for ct, don, khach in ds
    ]


async def cap_nhat_lien_he(db: AsyncSession, nv: NhanVien, ct_id: int, vao: LienHeVao) -> KhachThuHoi:
    await dam_bao_la_duoc_si(db, nv)
    ct = (
        await db.execute(
            select(CtLenhThuHoi)
            .where(CtLenhThuHoi.id == ct_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    lenh = await db.get(LenhThuHoi, ct.lenh_thu_hoi_id) if ct else None
    if ct is None or lenh is None or lenh.trang_thai != TrangThaiThuHoi.dang_thu_hoi:
        raise _khong_thay()
    if vao.so_luong_da_thu_ve is not None:
        if vao.so_luong_da_thu_ve > ct.so_luong_da_ban:
            raise LoiNghiepVu(
                "DU_LIEU_KHONG_HOP_LE",
                "Dữ liệu không hợp lệ",
                chi_tiet=[{"truong": "so_luong_da_thu_ve", "loi": f"Không vượt số đã bán ({ct.so_luong_da_ban})"}],
            )
        ct.so_luong_da_thu_ve = vao.so_luong_da_thu_ve
    ct.ket_qua_lien_he, ct.nhan_vien_id, ct.cap_nhat_luc = vao.ket_qua_lien_he, nv.id, bay_gio_utc()
    if vao.ghi_chu is not None:
        ct.ghi_chu = vao.ghi_chu.strip() or None
    await db.flush()
    return next(k for k in await danh_sach_khach(db, nv, lenh.id) if k.id == ct.id)
