"""Chi tiết sản phẩm công khai (KVL03) và ghi lịch sử xem."""

import re
from datetime import timedelta
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import luu_tru
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc, hom_nay_vn
from app.models.ai import LichSuXem
from app.models.enums import LoaiSanPham
from app.models.khach_hang import DanhGia, KhachHang
from app.models.san_pham import AnhSanPham, DonViQuyDoi, HoatChat, NhaSanXuat, SanPham, ThanhPhan, ThuongHieu
from app.modules.chuyen_mon.noi_dung import noi_dung_da_duyet
from app.modules.cua_hang import goi_y
from app.modules.cua_hang.hien_thi import la_hien_thi, nap_cay_hien_thi, ton_kha_dung
from app.modules.cua_hang.schemas import (
    AnhCongKhai,
    DanhGiaCongKhai,
    DonViBan,
    MucDuongDan,
    NoiDungChuyenMonCongKhai,
    SanPhamChiTietCongKhai,
    TenRut,
    ThanhPhanCongKhai,
    TongHopDanhGia,
)

NguonXem = Literal["trang_chu", "danh_muc", "tim_kiem", "goi_y_tuong_tu", "mua_kem", "danh_cho_ban", "chat_ai"]
SO_SAN_PHAM_TUONG_TU = 8
SO_DANH_GIA_HIEN = 10
CUA_SO_GHI_XEM = timedelta(minutes=30)
_MA_PHIEN_HOP_LE = re.compile(r"[A-Za-z0-9_-]{8,64}")


def ten_rut_gon(ho_ten: str) -> str:
    """Rút gọn tên người đánh giá: "Nguyễn Văn An" -> "Nguyễn A."; một từ -> chữ đầu và "…".

    Không lộ họ tên đầy đủ, cũng không lộ số điện thoại hay email người dùng gõ vào ô họ tên (chứa chữ số hoặc "@"
    thì chỉ hiện "Khách hàng").
    """
    tu = ho_ten.split()
    if not tu or any(c.isdigit() or c == "@" for c in ho_ten):
        return "Khách hàng"
    if len(tu) == 1:
        return f"{tu[0][0]}…"
    return f"{tu[0]} {tu[-1][0].upper()}."


def ma_phien_hop_le(gia_tri: str | None) -> str | None:
    return gia_tri if gia_tri is not None and _MA_PHIEN_HOP_LE.fullmatch(gia_tri) else None


async def _ghi_lich_su_xem(
    db: AsyncSession, san_pham_id: int, khach: KhachHang | None, ma_phien: str | None, nguon: NguonXem | None
) -> None:
    """Khách thành viên ghi theo token, vãng lai theo mã phiên; không có cả hai thì không ghi. Cùng người xem lại
    cùng sản phẩm trong 30 phút chỉ giữ một dòng (làm mới trang không làm phình bảng)."""
    if khach is not None:
        dung_chung = LichSuXem.khach_hang_id == khach.id
    elif ma_phien is not None:
        dung_chung = LichSuXem.ma_phien == ma_phien
    else:
        return
    da_co = await db.scalar(
        select(LichSuXem.id)
        .where(dung_chung, LichSuXem.san_pham_id == san_pham_id, LichSuXem.created_at >= bay_gio_utc() - CUA_SO_GHI_XEM)
        .limit(1)
    )
    if da_co is None:
        db.add(
            LichSuXem(
                khach_hang_id=khach.id if khach is not None else None,
                ma_phien=None if khach is not None else ma_phien,
                san_pham_id=san_pham_id,
                nguon=nguon,
            )
        )
        await db.flush()


async def _danh_gia(db: AsyncSession, san_pham_id: int) -> TongHopDanhGia:
    dem = dict(
        (
            await db.execute(
                select(DanhGia.so_sao, func.count())
                .where(DanhGia.san_pham_id == san_pham_id, DanhGia.dang_hien.is_(True))
                .group_by(DanhGia.so_sao)
            )
        ).all()
    )
    phan_bo = [int(dem.get(sao, 0)) for sao in range(1, 6)]
    moi_nhat = (
        await db.execute(
            select(DanhGia, KhachHang.ho_ten)
            .join(KhachHang, KhachHang.id == DanhGia.khach_hang_id)
            .where(DanhGia.san_pham_id == san_pham_id, DanhGia.dang_hien.is_(True))
            .order_by(DanhGia.created_at.desc(), DanhGia.id.desc())
            .limit(SO_DANH_GIA_HIEN)
        )
    ).all()
    return TongHopDanhGia(
        so_luong=sum(phan_bo),
        tong_sao=sum(sao * n for sao, n in enumerate(phan_bo, start=1)),
        phan_bo=phan_bo,
        moi_nhat=[
            DanhGiaCongKhai(
                so_sao=d.so_sao,
                noi_dung=d.noi_dung,
                ten_hien_thi=ten_rut_gon(ho_ten),
                phan_hoi=d.phan_hoi,
                anh=[luu_tru.url_cong_khai(k) for k in d.anh or []],
                created_at=d.created_at,
            )
            for d, ho_ten in moi_nhat
        ],
    )


async def chi_tiet(
    db: AsyncSession,
    slug: str,
    *,
    khach: KhachHang | None,
    ma_phien: str | None,
    nguon: NguonXem | None,
    duoc_ghi: bool = True,
) -> SanPhamChiTietCongKhai:
    cay = await nap_cay_hien_thi(db)
    sp = (await db.execute(select(SanPham).where(SanPham.slug == slug, la_hien_thi(cay.ids)))).scalar_one_or_none()
    if sp is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy sản phẩm")
    ton = int(await db.scalar(select(ton_kha_dung(hom_nay_vn())).where(SanPham.id == sp.id)) or 0)

    don_vi = (
        (
            await db.execute(
                select(DonViQuyDoi)
                .where(DonViQuyDoi.san_pham_id == sp.id, DonViQuyDoi.ban_online.is_(True))
                .order_by(DonViQuyDoi.he_so, DonViQuyDoi.id)
            )
        )
        .scalars()
        .all()
    )
    anh = (
        (
            await db.execute(
                select(AnhSanPham).where(AnhSanPham.san_pham_id == sp.id).order_by(AnhSanPham.thu_tu, AnhSanPham.id)
            )
        )
        .scalars()
        .all()
    )
    thanh_phan = (
        await db.execute(
            select(ThanhPhan.hoat_chat_id, HoatChat.ten, ThanhPhan.ham_luong)
            .join(HoatChat, HoatChat.id == ThanhPhan.hoat_chat_id)
            .where(ThanhPhan.san_pham_id == sp.id)
            .order_by(HoatChat.ten, HoatChat.id)
        )
    ).all()
    thuong_hieu = await db.get(ThuongHieu, sp.thuong_hieu_id) if sp.thuong_hieu_id else None
    nha_san_xuat = await db.get(NhaSanXuat, sp.nha_san_xuat_id) if sp.nha_san_xuat_id else None
    nd = await noi_dung_da_duyet(db, sp.id)

    if duoc_ghi:
        await _ghi_lich_su_xem(db, sp.id, khach, ma_phien, nguon)
    return SanPhamChiTietCongKhai(
        id=sp.id,
        sku=sp.sku,
        ten=sp.ten,
        slug=sp.slug,
        loai_san_pham=sp.loai_san_pham,
        can_tu_van=sp.loai_san_pham == LoaiSanPham.thuoc_ke_don,
        luu_y_khong_phai_thuoc=sp.loai_san_pham == LoaiSanPham.thuc_pham_chuc_nang,
        chi_ban_tai_quay=not don_vi,
        thuong_hieu=TenRut(id=thuong_hieu.id, ten=thuong_hieu.ten) if thuong_hieu else None,
        nha_san_xuat=nha_san_xuat.ten if nha_san_xuat else None,
        so_dang_ky=sp.so_dang_ky,
        dang_bao_che=sp.dang_bao_che,
        quy_cach=sp.quy_cach,
        doi_tuong_su_dung=sp.doi_tuong_su_dung,
        duong_dan_danh_muc=[MucDuongDan(ten=m.ten, slug=m.slug) for m in cay.duong_dan(sp.danh_muc_id)],
        don_vi=[
            DonViBan(
                id=d.id,
                ten_don_vi=d.ten_don_vi,
                he_so=d.he_so,
                gia_ban=d.gia_ban,
                la_mac_dinh=d.la_mac_dinh,
                con_hang=ton >= d.he_so,
            )
            for d in don_vi
        ],
        anh=[AnhCongKhai(url=a.url, la_anh_chinh=a.la_anh_chinh) for a in anh],
        thanh_phan=[ThanhPhanCongKhai(hoat_chat_id=i, ten=ten, ham_luong=hl) for i, ten, hl in thanh_phan],
        noi_dung_chuyen_mon=NoiDungChuyenMonCongKhai(
            phien_ban=nd.phien_ban,
            ngay_duyet=nd.ngay_duyet,
            chi_dinh=nd.chi_dinh,
            chong_chi_dinh=nd.chong_chi_dinh,
            lieu_dung_tham_khao=nd.lieu_dung_tham_khao,
            tac_dung_phu=nd.tac_dung_phu,
            than_trong=nd.than_trong,
            tuong_tac_thuoc=nd.tuong_tac_thuoc,
            phu_nu_co_thai_cho_con_bu=nd.phu_nu_co_thai_cho_con_bu,
            tre_em=nd.tre_em,
            qua_lieu_xu_tri=nd.qua_lieu_xu_tri,
            bao_quan=nd.bao_quan,
            file_hdsd_url=nd.file_hdsd_url,
        )
        if nd
        else None,
        con_hang=ton > 0,
        danh_gia=await _danh_gia(db, sp.id),
        tuong_tu=await goi_y.san_pham_tuong_tu(
            db, sp, [h for h, _, _ in thanh_phan], khach, gioi_han=SO_SAN_PHAM_TUONG_TU
        ),
    )
