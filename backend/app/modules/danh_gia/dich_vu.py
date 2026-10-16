"""Khách đánh giá sản phẩm (KTV10), đặt câu hỏi (KTV15) và dược sĩ kiểm duyệt (DS11), T6.4. Không commit."""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import luu_tru
from app.core.loi import LoiNghiepVu
from app.core.phan_quyen import dam_bao_la_duoc_si
from app.core.phan_trang import ThamSoPhanTrang, Trang, lay_trang, tao_trang
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import CtDonHang, DonHang
from app.models.enums import TrangThaiDon
from app.models.he_thong import NhanVien
from app.models.khach_hang import DanhGia, HoiDap, KhachHang
from app.models.san_pham import SanPham
from app.modules.cua_hang.chi_tiet import ten_rut_gon
from app.modules.cua_hang.hien_thi import la_hien_thi, nap_cay_hien_thi
from app.modules.danh_gia.schemas import (
    DanhGiaCuaToi,
    DanhGiaNoiBo,
    DongCoTheDanhGia,
    HoiDapCongKhai,
    HoiDapCuaToi,
    HoiDapNoiBo,
)
from app.modules.thong_bao import service as thong_bao

SO_ANH_TOI_DA = 3
SO_CAU_HOI_MOI_NGAY = 10
TRANG_THAI_DUOC_DANH_GIA = (TrangThaiDon.da_giao, TrangThaiDon.hoan_tat)


def _loi_du_lieu(truong: str, loi: str) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": truong, "loi": loi}])


def _khong_thay(doi_tuong: str) -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", f"Không tìm thấy {doi_tuong}")


def _url_anh(anh: list[str] | None) -> list[str]:
    return [luu_tru.url_cong_khai(k) for k in anh or []]


# --- Đánh giá (KTV10) ---


async def dong_co_the_danh_gia(db: AsyncSession, khach: KhachHang) -> list[DongCoTheDanhGia]:
    """Dòng thuộc đơn `da_giao`/`hoan_tat` của khách mà chưa đánh giá."""
    ds = (
        await db.execute(
            select(CtDonHang, DonHang, SanPham.slug)
            .join(DonHang, DonHang.id == CtDonHang.don_hang_id)
            .outerjoin(SanPham, SanPham.id == CtDonHang.san_pham_id)
            .outerjoin(DanhGia, DanhGia.ct_don_hang_id == CtDonHang.id)
            .where(
                DonHang.khach_hang_id == khach.id,
                DonHang.trang_thai.in_(TRANG_THAI_DUOC_DANH_GIA),
                DanhGia.id.is_(None),
            )
            .order_by(DonHang.created_at.desc(), CtDonHang.id)
            .limit(100)
        )
    ).all()
    return [
        DongCoTheDanhGia(
            ct_don_hang_id=ct.id,
            ma_don=don.ma_don,
            ten_san_pham=ct.ten_san_pham,
            san_pham_slug=slug,
            created_at=don.created_at,
        )
        for ct, don, slug in ds
    ]


async def tao_danh_gia(
    db: AsyncSession, khach: KhachHang, ct_don_hang_id: int, so_sao: int, noi_dung: str | None, tep: list[bytes]
) -> DanhGiaCuaToi:
    if not 1 <= so_sao <= 5:
        raise _loi_du_lieu("so_sao", "Số sao từ 1 đến 5")
    if len(tep) > SO_ANH_TOI_DA:
        raise _loi_du_lieu("tep", f"Tối đa {SO_ANH_TOI_DA} ảnh")
    kieu = []
    for nd in tep:
        k = luu_tru.nhan_dang_tep(nd)
        if k is None or k == "video/mp4" or len(nd) > luu_tru.TOI_DA_ANH_BYTE:
            raise _loi_du_lieu("tep", "Chỉ nhận ảnh jpeg, png, webp tối đa 5 MB")
        kieu.append(k)
    dong = (
        await db.execute(
            select(CtDonHang, DonHang)
            .join(DonHang, DonHang.id == CtDonHang.don_hang_id)
            .where(CtDonHang.id == ct_don_hang_id, DonHang.khach_hang_id == khach.id)
            .with_for_update(of=CtDonHang)  # hai lần gửi cùng lúc: người sau thấy đánh giá của người trước
        )
    ).first()
    if dong is None:
        raise _khong_thay("dòng đơn hàng")
    ct, don = dong
    if don.trang_thai not in TRANG_THAI_DUOC_DANH_GIA:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Chỉ đánh giá sản phẩm của đơn đã giao hoặc hoàn tất")
    if ct.san_pham_id is None:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Sản phẩm này không còn để đánh giá")
    if await db.scalar(select(DanhGia.id).where(DanhGia.ct_don_hang_id == ct.id)) is not None:
        raise LoiNghiepVu("TRUNG_DU_LIEU", "Bạn đã đánh giá sản phẩm này trong đơn này")
    khoa = [await luu_tru.luu_tru().luu("danh-gia", nd, k) for nd, k in zip(tep, kieu, strict=True)]
    dg = DanhGia(
        san_pham_id=ct.san_pham_id,
        khach_hang_id=khach.id,
        ct_don_hang_id=ct.id,
        so_sao=so_sao,
        noi_dung=(noi_dung or "").strip() or None,
        anh=khoa or None,
    )
    db.add(dg)
    await db.flush()
    return await _cua_toi(db, dg)


async def _cua_toi(db: AsyncSession, dg: DanhGia) -> DanhGiaCuaToi:
    ten, slug = (await db.execute(select(SanPham.ten, SanPham.slug).where(SanPham.id == dg.san_pham_id))).one()
    return DanhGiaCuaToi(
        id=dg.id,
        ct_don_hang_id=dg.ct_don_hang_id,
        san_pham_ten=ten,
        san_pham_slug=slug,
        so_sao=dg.so_sao,
        noi_dung=dg.noi_dung,
        anh=_url_anh(dg.anh),
        dang_hien=dg.dang_hien,
        phan_hoi=dg.phan_hoi,
        created_at=dg.created_at,
    )


async def danh_gia_cua_toi(db: AsyncSession, khach: KhachHang) -> list[DanhGiaCuaToi]:
    ds = (
        (
            await db.execute(
                select(DanhGia)
                .where(DanhGia.khach_hang_id == khach.id)
                .order_by(DanhGia.created_at.desc(), DanhGia.id.desc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )
    return [await _cua_toi(db, d) for d in ds]


# --- Hỏi đáp (KTV15) ---


async def _san_pham_hien_thi(db: AsyncSession, slug: str) -> SanPham:
    cay = await nap_cay_hien_thi(db)
    sp = (await db.execute(select(SanPham).where(SanPham.slug == slug, la_hien_thi(cay.ids)))).scalar_one_or_none()
    if sp is None:
        raise _khong_thay("sản phẩm")
    return sp


async def hoi_dap_cong_khai(db: AsyncSession, slug: str, tp: ThamSoPhanTrang) -> Trang[HoiDapCongKhai]:
    sp = await _san_pham_hien_thi(db, slug)
    cau = (
        select(HoiDap, KhachHang.ho_ten)
        .join(KhachHang, KhachHang.id == HoiDap.khach_hang_id)
        .where(HoiDap.san_pham_id == sp.id, HoiDap.dang_hien.is_(True))
        .order_by(HoiDap.created_at.desc(), HoiDap.id.desc())
    )
    ds, tong = await lay_trang(db, cau, tp, nhieu_cot=True)
    return tao_trang(
        [
            HoiDapCongKhai(
                id=h.id,
                cau_hoi=h.cau_hoi,
                tra_loi=h.tra_loi,
                ten_hien_thi=ten_rut_gon(ho_ten),
                tra_loi_luc=h.tra_loi_luc,
                created_at=h.created_at,
            )
            for h, ho_ten in ds
        ],
        tong,
        tp,
    )


async def dat_cau_hoi(db: AsyncSession, khach: KhachHang, slug: str, cau_hoi: str) -> HoiDapCuaToi:
    sp = await _san_pham_hien_thi(db, slug)
    gan_day = await db.scalar(
        select(func.count()).where(
            HoiDap.khach_hang_id == khach.id, HoiDap.created_at > bay_gio_utc() - timedelta(days=1)
        )
    )
    if (gan_day or 0) >= SO_CAU_HOI_MOI_NGAY:
        raise LoiNghiepVu("QUA_GIOI_HAN", f"Mỗi ngày chỉ đặt tối đa {SO_CAU_HOI_MOI_NGAY} câu hỏi")
    h = HoiDap(san_pham_id=sp.id, khach_hang_id=khach.id, cau_hoi=cau_hoi.strip())
    db.add(h)
    await db.flush()
    return _hoi_dap_cua_toi(h, sp)


def _hoi_dap_cua_toi(h: HoiDap, sp: SanPham) -> HoiDapCuaToi:
    return HoiDapCuaToi(
        id=h.id,
        san_pham_ten=sp.ten,
        san_pham_slug=sp.slug,
        cau_hoi=h.cau_hoi,
        tra_loi=h.tra_loi,
        tra_loi_luc=h.tra_loi_luc,
        dang_hien=h.dang_hien,
        created_at=h.created_at,
    )


async def hoi_dap_cua_toi(db: AsyncSession, khach: KhachHang) -> list[HoiDapCuaToi]:
    ds = (
        await db.execute(
            select(HoiDap, SanPham)
            .join(SanPham, SanPham.id == HoiDap.san_pham_id)
            .where(HoiDap.khach_hang_id == khach.id)
            .order_by(HoiDap.created_at.desc(), HoiDap.id.desc())
            .limit(100)
        )
    ).all()
    return [_hoi_dap_cua_toi(h, sp) for h, sp in ds]


async def _cau_hoi_cua_toi(db: AsyncSession, khach: KhachHang, hoi_id: int) -> tuple[HoiDap, SanPham]:
    dong = (
        await db.execute(
            select(HoiDap, SanPham)
            .join(SanPham, SanPham.id == HoiDap.san_pham_id)
            .where(HoiDap.id == hoi_id, HoiDap.khach_hang_id == khach.id)
            .with_for_update(of=HoiDap)
            .execution_options(populate_existing=True)
        )
    ).first()
    if dong is None:
        raise _khong_thay("câu hỏi")
    return dong[0], dong[1]


async def sua_cau_hoi(db: AsyncSession, khach: KhachHang, hoi_id: int, cau_hoi: str) -> HoiDapCuaToi:
    h, sp = await _cau_hoi_cua_toi(db, khach, hoi_id)
    if h.tra_loi is not None:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Câu hỏi đã được trả lời nên không sửa được")
    h.cau_hoi = cau_hoi.strip()
    await db.flush()
    return _hoi_dap_cua_toi(h, sp)


async def xoa_cau_hoi(db: AsyncSession, khach: KhachHang, hoi_id: int) -> None:
    h, _ = await _cau_hoi_cua_toi(db, khach, hoi_id)
    if h.tra_loi is not None:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Câu hỏi đã được trả lời nên không xóa được")
    await db.delete(h)
    await db.flush()


# --- Kiểm duyệt (DS11) ---


async def ds_danh_gia_noi_bo(
    db: AsyncSession, nv: NhanVien, tp: ThamSoPhanTrang, dang_hien: bool | None, so_sao: int | None
) -> Trang[DanhGiaNoiBo]:
    await dam_bao_la_duoc_si(db, nv)
    cau = (
        select(DanhGia, SanPham.ten, KhachHang.ho_ten)
        .join(SanPham, SanPham.id == DanhGia.san_pham_id)
        .join(KhachHang, KhachHang.id == DanhGia.khach_hang_id)
        .order_by(DanhGia.created_at.desc(), DanhGia.id.desc())
    )
    if dang_hien is not None:
        cau = cau.where(DanhGia.dang_hien.is_(dang_hien))
    if so_sao is not None:
        cau = cau.where(DanhGia.so_sao == so_sao)
    ds, tong = await lay_trang(db, cau, tp, nhieu_cot=True)
    return tao_trang(
        [
            DanhGiaNoiBo(
                id=d.id,
                san_pham_ten=ten,
                ten_khach=ho_ten,
                so_sao=d.so_sao,
                noi_dung=d.noi_dung,
                anh=_url_anh(d.anh),
                dang_hien=d.dang_hien,
                phan_hoi=d.phan_hoi,
                created_at=d.created_at,
            )
            for d, ten, ho_ten in ds
        ],
        tong,
        tp,
    )


async def _lay_danh_gia(db: AsyncSession, dg_id: int) -> DanhGia:
    dg = (
        await db.execute(
            select(DanhGia).where(DanhGia.id == dg_id).with_for_update().execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if dg is None:
        raise _khong_thay("đánh giá")
    return dg


async def _noi_bo_danh_gia(db: AsyncSession, dg: DanhGia) -> DanhGiaNoiBo:
    ten = await db.scalar(select(SanPham.ten).where(SanPham.id == dg.san_pham_id))
    ho_ten = await db.scalar(select(KhachHang.ho_ten).where(KhachHang.id == dg.khach_hang_id))
    return DanhGiaNoiBo(
        id=dg.id,
        san_pham_ten=ten or "",
        ten_khach=ho_ten or "",
        so_sao=dg.so_sao,
        noi_dung=dg.noi_dung,
        anh=_url_anh(dg.anh),
        dang_hien=dg.dang_hien,
        phan_hoi=dg.phan_hoi,
        created_at=dg.created_at,
    )


async def dat_hien_thi_danh_gia(db: AsyncSession, nv: NhanVien, dg_id: int, dang_hien: bool) -> DanhGiaNoiBo:
    await dam_bao_la_duoc_si(db, nv)
    dg = await _lay_danh_gia(db, dg_id)
    dg.dang_hien = dang_hien
    await db.flush()
    return await _noi_bo_danh_gia(db, dg)


async def phan_hoi_danh_gia(db: AsyncSession, nv: NhanVien, dg_id: int, phan_hoi: str) -> DanhGiaNoiBo:
    await dam_bao_la_duoc_si(db, nv)
    dg = await _lay_danh_gia(db, dg_id)
    dg.phan_hoi, dg.nhan_vien_phan_hoi_id = phan_hoi.strip(), nv.id
    await db.flush()
    return await _noi_bo_danh_gia(db, dg)


async def ds_hoi_dap_noi_bo(
    db: AsyncSession, nv: NhanVien, tp: ThamSoPhanTrang, chua_tra_loi: bool | None
) -> Trang[HoiDapNoiBo]:
    await dam_bao_la_duoc_si(db, nv)
    cau = (
        select(HoiDap, SanPham, KhachHang.ho_ten)
        .join(SanPham, SanPham.id == HoiDap.san_pham_id)
        .join(KhachHang, KhachHang.id == HoiDap.khach_hang_id)
        .order_by(HoiDap.created_at, HoiDap.id)
    )
    if chua_tra_loi is not None:
        cau = cau.where(HoiDap.tra_loi.is_(None) if chua_tra_loi else HoiDap.tra_loi.is_not(None))
    ds, tong = await lay_trang(db, cau, tp, nhieu_cot=True)
    return tao_trang([_hoi_dap_noi_bo(h, sp, ten) for h, sp, ten in ds], tong, tp)


def _hoi_dap_noi_bo(h: HoiDap, sp: SanPham, ten_khach: str) -> HoiDapNoiBo:
    return HoiDapNoiBo(
        id=h.id,
        san_pham_ten=sp.ten,
        san_pham_slug=sp.slug,
        ten_khach=ten_khach,
        cau_hoi=h.cau_hoi,
        tra_loi=h.tra_loi,
        tra_loi_luc=h.tra_loi_luc,
        dang_hien=h.dang_hien,
        created_at=h.created_at,
    )


async def _lay_hoi_dap(db: AsyncSession, hoi_id: int) -> tuple[HoiDap, SanPham, str]:
    dong = (
        await db.execute(
            select(HoiDap, SanPham, KhachHang.ho_ten)
            .join(SanPham, SanPham.id == HoiDap.san_pham_id)
            .join(KhachHang, KhachHang.id == HoiDap.khach_hang_id)
            .where(HoiDap.id == hoi_id)
            .with_for_update(of=HoiDap)
            .execution_options(populate_existing=True)
        )
    ).first()
    if dong is None:
        raise _khong_thay("câu hỏi")
    return dong[0], dong[1], dong[2]


async def tra_loi_cau_hoi(db: AsyncSession, nv: NhanVien, hoi_id: int, tra_loi: str) -> HoiDapNoiBo:
    await dam_bao_la_duoc_si(db, nv)
    h, sp, ten = await _lay_hoi_dap(db, hoi_id)
    lan_dau = h.tra_loi is None
    h.tra_loi, h.nhan_vien_tra_loi_id, h.tra_loi_luc = tra_loi.strip(), nv.id, bay_gio_utc()
    await db.flush()
    if lan_dau:
        await thong_bao.gui_cho_khach(
            db,
            h.khach_hang_id,
            loai="hoi_dap",
            tieu_de=f"Dược sĩ đã trả lời câu hỏi của bạn về {sp.ten}",
            noi_dung=None,  # nội dung trả lời xem trên trang sản phẩm, không đưa vào thông báo
            lien_ket=f"/san-pham/{sp.slug}",
        )
    return _hoi_dap_noi_bo(h, sp, ten)


async def dat_hien_thi_hoi_dap(db: AsyncSession, nv: NhanVien, hoi_id: int, dang_hien: bool) -> HoiDapNoiBo:
    await dam_bao_la_duoc_si(db, nv)
    h, sp, ten = await _lay_hoi_dap(db, hoi_id)
    h.dang_hien = dang_hien
    await db.flush()
    return _hoi_dap_noi_bo(h, sp, ten)
