"""Đặt hàng online của khách thành viên (KTV02, spec 04 mục 4, spec 06 mục 3.22).

Một transaction: khóa giỏ, kiểm tra lại giá/giới hạn, dùng mã giảm giá, tính phí ship, tạo đơn qua máy trạng thái rồi
giữ hàng FEFO. Lỗi ở bước nào cũng hoàn tác toàn bộ nên không có đơn nửa chừng, lượt mã hay hàng giữ mồ côi.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import idempotency
from app.core.cau_hinh import doc_cau_hinh
from app.core.loi import LoiNghiepVu
from app.core.ma_chung_tu import ma_don_hang
from app.core.thoi_gian import bay_gio_utc
from app.core.tien import cong, lam_tron_vnd
from app.models.ban_hang import CtDonHang, DonHang, LichSuTrangThai, MaGiamGia, VanDon
from app.models.enums import (
    HinhThucNhan,
    KenhBan,
    LoaiSanPham,
    LoaiVanDon,
    PhuongThucThanhToan,
    TrangThaiDon,
)
from app.models.khach_hang import DiaChi, KhachHang
from app.modules.ban_hang.schemas import DatHangVao, DongDonRa, DonHangRa, MocTrangThai, VanDonRa, XemTruocRa
from app.modules.ban_hang.trang_thai import NGUON_NGUOI_DUNG, TacNhan, khoi_tao_trang_thai
from app.modules.cua_hang.hien_thi import nap_cay_hien_thi
from app.modules.gio_hang import dich_vu as dich_vu_gio
from app.modules.kho import ton_kho
from app.modules.kho.ton_kho import YeuCauGiu
from app.modules.khuyen_mai import ap_dung
from app.tich_hop.van_chuyen import DiaChiGiao, lay_don_vi_van_chuyen

logger = logging.getLogger(__name__)

THAO_TAC = "dat-hang"
PHI_SHIP_MAC_DINH = 30_000
MIEN_PHI_SHIP_TU = 300_000
THOI_HAN_THANH_TOAN_PHUT = 15
GRAM_MOI_DON_VI_CO_SO = 20  # chưa có khối lượng sản phẩm trong schema: ước lượng để gửi cho adapter vận chuyển


def khong_hop_le(truong: str, loi: str) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": truong, "loi": loi}])


def _chuoi(tien: Decimal) -> str:
    """Tiền dạng chuỗi hai chữ số lẻ, cùng dạng với `TienDoc` ở các phản hồi khác."""
    return f"{lam_tron_vnd(tien):.2f}"


def don_ra(don: DonHang, ma_text: str | None, lich_su: Sequence[LichSuTrangThai] = ()) -> DonHangRa:
    return DonHangRa(
        ma_don=don.ma_don,
        trang_thai=don.trang_thai,
        trang_thai_tt=don.trang_thai_tt,
        phuong_thuc_tt=don.phuong_thuc_tt,
        hinh_thuc_nhan=don.hinh_thuc_nhan,
        tam_tinh=don.tam_tinh,
        giam_gia=don.giam_gia,
        phi_van_chuyen=don.phi_van_chuyen,
        tong_tien=don.tong_tien,
        han_thanh_toan=don.han_thanh_toan,
        han_xac_nhan=don.han_xac_nhan,
        ma_giam_gia=ma_text,
        ten_nguoi_nhan=don.ten_nguoi_nhan,
        sdt_nguoi_nhan=don.sdt_nguoi_nhan,
        dia_chi_giao=don.dia_chi_giao,
        ghi_chu=don.ghi_chu,
        ly_do_huy=don.ly_do_huy,
        created_at=don.created_at,
        lich_su=[
            MocTrangThai(
                tu_trang_thai=m.tu_trang_thai,
                den_trang_thai=m.den_trang_thai,
                thoi_diem=m.created_at,
                ghi_chu=m.ghi_chu,
            )
            for m in lich_su
        ],
        dong=[
            DongDonRa(
                id=c.id,
                san_pham_id=c.san_pham_id,
                ten_san_pham=c.ten_san_pham,
                ten_don_vi=c.ten_don_vi,
                so_luong=c.so_luong,
                don_gia=c.don_gia,
                giam_gia_phan_bo=c.giam_gia_phan_bo,
                thanh_tien=c.thanh_tien,
            )
            for c in sorted(don.chi_tiet, key=lambda c: c.id)
        ],
    )


async def tinh_phi_van_chuyen(
    db: AsyncSession, dia_chi: DiaChi | None, so_co_so: int, tam_tinh: Decimal, giam: Decimal
) -> Decimal:
    if dia_chi is None:  # nhận tại nhà thuốc
        return lam_tron_vnd(0)
    mien_phi_tu = Decimal(str(await doc_cau_hinh(db, "mien_phi_ship_tu", MIEN_PHI_SHIP_TU)))
    if tam_tinh - giam >= mien_phi_tu:
        return lam_tron_vnd(0)
    try:
        phi = await lay_don_vi_van_chuyen().tinh_phi(
            DiaChiGiao(
                ma_tinh=dia_chi.ma_tinh, ma_phuong_xa=dia_chi.ma_phuong_xa, dia_chi_chi_tiet=dia_chi.dia_chi_chi_tiet
            ),
            max(so_co_so * GRAM_MOI_DON_VI_CO_SO, GRAM_MOI_DON_VI_CO_SO),
            tam_tinh - giam,
        )
    except Exception:  # noqa: BLE001  adapter lỗi bất kỳ kiểu nào đều quay về phí mặc định (spec 04 mục 4 bước 6)
        logger.warning("Adapter vận chuyển lỗi, dùng phi_ship_mac_dinh", exc_info=True)
        phi = Decimal(str(await doc_cau_hinh(db, "phi_ship_mac_dinh", PHI_SHIP_MAC_DINH)))
    return lam_tron_vnd(phi)


@dataclass
class TinhDon:
    """Kết quả tính tiền của giỏ hiện tại (dùng chung cho xem trước và đặt hàng)."""

    dong_dat: list[dich_vu_gio.DongDat]
    dia_chi: DiaChi | None
    goc: list[Decimal]
    tam_tinh: Decimal
    giam: Decimal
    phan_bo: dict[int, Decimal]
    ma_dung: MaGiamGia | None
    phi: Decimal
    tong_tien: Decimal


async def _tinh_don(db: AsyncSession, khach: KhachHang, vao: DatHangVao, *, dung_luot: bool) -> TinhDon:
    """Khóa giỏ, kiểm tra lại từng dòng, tính tiền theo spec 04 mục 4. `dung_luot=True` khóa và tăng lượt mã (đặt
    hàng); `False` chỉ xem trước nên không ghi gì. Giỏ trống là `400`."""
    dong_dat = await dich_vu_gio.lay_dong_de_dat(db, khach)  # đã khóa giỏ: hai lần đặt của một khách nối đuôi nhau
    if not dong_dat:
        raise khong_hop_le("gio_hang", "Giỏ hàng trống")
    dia_chi: DiaChi | None = None
    if vao.hinh_thuc_nhan == HinhThucNhan.giao_tan_noi:
        if vao.dia_chi_id is None:
            raise khong_hop_le("dia_chi_id", "Cần chọn địa chỉ giao hàng")
        dia_chi = (
            await db.execute(select(DiaChi).where(DiaChi.id == vao.dia_chi_id, DiaChi.khach_hang_id == khach.id))
        ).scalar_one_or_none()
        if dia_chi is None:
            raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy địa chỉ")
    return await tinh_tien(db, khach.id, dong_dat, dia_chi, vao.ma_giam_gia, dung_luot=dung_luot)


async def tinh_tien(
    db: AsyncSession,
    khach_id: int | None,
    dong_dat: list[dich_vu_gio.DongDat],
    dia_chi: DiaChi | None,
    ma_giam_gia: str | None,
    *,
    dung_luot: bool,
) -> TinhDon:
    """Tính tiền các dòng đã kiểm tra (dùng chung đặt hàng online và đơn hộ DS07). Mã giảm giá cần có khách."""
    # Giá luôn lấy lại theo giá hiện tại của đơn vị.
    goc = [lam_tron_vnd(d.dv.gia_ban * d.so_luong) for d in dong_dat]
    tam_tinh = cong(*goc)
    giam, phan_bo, ma_dung = lam_tron_vnd(0), {}, None
    if ma_giam_gia:
        if khach_id is None:
            raise khong_hop_le("ma_giam_gia", "Mã giảm giá chỉ áp dụng cho khách có tài khoản")
        cay = await nap_cay_hien_thi(db)
        dong_giam = [
            ap_dung.DongGio(
                khoa=i,
                san_pham_id=d.sp.id,
                duong_danh_muc=frozenset(x.id for x in cay.duong_dan(d.sp.danh_muc_id)),
                la_ke_don=d.sp.loai_san_pham == LoaiSanPham.thuoc_ke_don,
                thanh_tien_goc=goc[i],
            )
            for i, d in enumerate(dong_dat)
        ]
        cach = ap_dung.dung_ma if dung_luot else ap_dung.kiem_tra_ma
        kq = await cach(db, khach_id, ma_giam_gia, dong_giam)
        if not kq.hop_le:
            assert kq.ma_ly_do is not None
            raise LoiNghiepVu(
                "MA_GIAM_GIA_KHONG_HOP_LE", ap_dung.THONG_DIEP[kq.ma_ly_do], chi_tiet={"ma_ly_do": kq.ma_ly_do.value}
            )
        giam, phan_bo, ma_dung = kq.giam, kq.phan_bo or {}, kq.ma_giam_gia
    so_co_so = sum(d.so_luong * d.dv.he_so for d in dong_dat)
    phi = await tinh_phi_van_chuyen(db, dia_chi, so_co_so, tam_tinh, giam)
    return TinhDon(dong_dat, dia_chi, goc, tam_tinh, giam, phan_bo, ma_dung, phi, tam_tinh - giam + phi)


def ghi_dia_chi_giao(don: DonHang, dia_chi: DiaChi) -> None:
    """Chụp địa chỉ giao vào đơn (bản chụp tại thời điểm đặt)."""
    don.ten_nguoi_nhan, don.sdt_nguoi_nhan = dia_chi.ten_nguoi_nhan, dia_chi.so_dien_thoai
    don.dia_chi_giao = ", ".join(x for x in (dia_chi.dia_chi_chi_tiet, dia_chi.ten_phuong_xa, dia_chi.ten_tinh) if x)
    don.ma_tinh, don.ma_quan_huyen, don.ma_phuong_xa = dia_chi.ma_tinh, dia_chi.ma_quan_huyen, dia_chi.ma_phuong_xa


def dong_cua_don(t: TinhDon) -> list[CtDonHang]:
    return [
        CtDonHang(
            san_pham_id=d.sp.id,
            don_vi_id=d.dv.id,
            ten_san_pham=d.sp.ten,
            ten_don_vi=d.dv.ten_don_vi,
            he_so=d.dv.he_so,
            so_luong=d.so_luong,
            don_gia=lam_tron_vnd(d.dv.gia_ban),
            giam_gia_phan_bo=t.phan_bo.get(i, lam_tron_vnd(0)),
            thanh_tien=t.goc[i] - t.phan_bo.get(i, Decimal(0)),
        )
        for i, d in enumerate(t.dong_dat)
    ]


def _gia_da_thay_doi(t: TinhDon) -> LoiNghiepVu:
    return LoiNghiepVu(
        "GIA_DA_THAY_DOI",
        "Giá hoặc phí đã thay đổi, vui lòng xem lại đơn hàng",
        chi_tiet={
            "tam_tinh": _chuoi(t.tam_tinh),
            "giam_gia": _chuoi(t.giam),
            "phi_van_chuyen": _chuoi(t.phi),
            "tong_tien": _chuoi(t.tong_tien),
            "dong": [
                {
                    "san_pham_id": d.sp.id,
                    "don_vi_id": d.dv.id,
                    "so_luong": d.so_luong,
                    "don_gia": _chuoi(d.dv.gia_ban),
                    "thanh_tien": _chuoi(t.goc[i] - t.phan_bo.get(i, Decimal(0))),
                }
                for i, d in enumerate(t.dong_dat)
            ],
        },
    )


async def xem_truoc(db: AsyncSession, khach: KhachHang, vao: DatHangVao) -> XemTruocRa:
    """Tính thử đơn (phí ship, giảm giá, tổng) cho trang thanh toán; không giữ hàng, không dùng lượt mã."""
    t = await _tinh_don(db, khach, vao, dung_luot=False)
    return XemTruocRa(
        tam_tinh=t.tam_tinh,
        giam_gia=t.giam,
        phi_van_chuyen=t.phi,
        tong_tien=t.tong_tien,
        ma_giam_gia=vao.ma_giam_gia and ap_dung.chuan_hoa_ma(vao.ma_giam_gia),
    )


async def dat_hang(db: AsyncSession, khach: KhachHang, vao: DatHangVao, khoa: str) -> DonHangRa:
    """Tạo đơn từ giỏ của `khach`. `khoa` là `Idempotency-Key` đã kiểm tra dạng UUID."""
    dau_van_tay = idempotency.dau_van_tay(vao.model_dump(mode="json"))
    await dich_vu_gio.khoa_gio(db, khach)  # khóa giỏ TRƯỚC khi tra khóa idempotency
    da_co = idempotency.tra_cuu(THAO_TAC, khach.id, khoa, dau_van_tay)
    if da_co is not None:
        ton_tai = await db.scalar(
            select(DonHang.id).where(DonHang.ma_don == da_co["ma_don"], DonHang.khach_hang_id == khach.id)
        )
        if ton_tai is not None:
            return DonHangRa.model_validate(da_co)
    t = await _tinh_don(db, khach, vao, dung_luot=True)
    dong_dat, dia_chi, ma_dung = t.dong_dat, t.dia_chi, t.ma_dung
    tam_tinh, giam, phi, tong_tien = t.tam_tinh, t.giam, t.phi, t.tong_tien
    if vao.tong_tien_ky_vong is not None and Decimal(vao.tong_tien_ky_vong) != tong_tien:
        raise _gia_da_thay_doi(t)

    truc_tuyen = vao.phuong_thuc_tt != PhuongThucThanhToan.cod
    bay_gio = bay_gio_utc()
    thoi_han = int(await doc_cau_hinh(db, "thoi_han_thanh_toan_phut", THOI_HAN_THANH_TOAN_PHUT))
    don = DonHang(
        ma_don=await ma_don_hang(db),
        khach_hang_id=khach.id,
        kenh_ban=KenhBan.online,
        hinh_thuc_nhan=vao.hinh_thuc_nhan,
        phuong_thuc_tt=vao.phuong_thuc_tt,
        ma_giam_gia_id=ma_dung.id if ma_dung else None,
        tam_tinh=tam_tinh,
        giam_gia=giam,
        phi_van_chuyen=phi,
        tong_tien=tong_tien,
        ghi_chu=vao.ghi_chu,
        han_thanh_toan=bay_gio + timedelta(minutes=thoi_han) if truc_tuyen else None,
    )
    if dia_chi is not None:
        ghi_dia_chi_giao(don, dia_chi)
    else:
        don.ten_nguoi_nhan, don.sdt_nguoi_nhan = khach.ho_ten, khach.so_dien_thoai
    don.chi_tiet = dong_cua_don(t)
    den = TrangThaiDon.cho_thanh_toan if truc_tuyen else TrangThaiDon.cho_xac_nhan
    ls = await khoi_tao_trang_thai(db, don, den, TacNhan.khach(khach.id), NGUON_NGUOI_DUNG)

    # Giữ hàng FEFO trên lô đang bán (không dùng lô cận hạn); thiếu ở bất kỳ dòng nào là HET_HANG, hoàn tác cả đơn.
    thu_tu = sorted(don.chi_tiet, key=lambda c: c.id)
    await ton_kho.giu_hang_nhieu(db, [YeuCauGiu(c.id, c.san_pham_id, c.so_luong * c.he_so) for c in thu_tu])
    await dich_vu_gio.xoa_dong_da_dat(db, [d.dong_id for d in dong_dat])

    await db.refresh(ls)  # created_at do CSDL đặt
    ra = don_ra(don, vao.ma_giam_gia and ap_dung.chuan_hoa_ma(vao.ma_giam_gia), [ls])
    idempotency.ghi_nho(THAO_TAC, khach.id, khoa, dau_van_tay, ra.model_dump(mode="json"))
    return ra


async def van_don_giao_hang(db: AsyncSession, don_id: int) -> list[VanDonRa]:
    ds = (
        await db.execute(
            select(VanDon).where(VanDon.don_hang_id == don_id, VanDon.loai == LoaiVanDon.giao_hang).order_by(VanDon.id)
        )
    ).scalars()
    return [
        VanDonRa(ma_van_don=v.ma_van_don, don_vi_van_chuyen=v.don_vi_van_chuyen, created_at=v.created_at) for v in ds
    ]


async def lich_su_don(db: AsyncSession, don_id: int) -> list[LichSuTrangThai]:
    return list(
        (
            await db.execute(
                select(LichSuTrangThai)
                .where(LichSuTrangThai.don_hang_id == don_id)
                .order_by(LichSuTrangThai.created_at, LichSuTrangThai.id)
            )
        ).scalars()
    )


async def don_ra_day_du(db: AsyncSession, don: DonHang) -> DonHangRa:
    """`DonHangRa` của một đơn đã nạp (kèm dòng hàng, lịch sử, vận đơn); người gọi đã kiểm quyền truy cập đơn."""
    don = (
        await db.execute(
            select(DonHang)
            .where(DonHang.id == don.id)
            .options(selectinload(DonHang.chi_tiet))
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    ma_text = None
    if don.ma_giam_gia_id is not None:
        ma_text = await db.scalar(select(MaGiamGia.ma).where(MaGiamGia.id == don.ma_giam_gia_id))
    ra = don_ra(don, ma_text, await lich_su_don(db, don.id))
    ra.van_don = await van_don_giao_hang(db, don.id)
    return ra


async def don_cua_khach(db: AsyncSession, khach: KhachHang, ma_don: str) -> DonHangRa:
    """Chi tiết một đơn của chính khách; đơn của người khác hoặc không có là `404` (quy tắc 3)."""
    don = (
        await db.execute(
            select(DonHang)
            .where(DonHang.ma_don == ma_don, DonHang.khach_hang_id == khach.id)
            .options(selectinload(DonHang.chi_tiet))
        )
    ).scalar_one_or_none()
    if don is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy đơn hàng")
    ma_text = None
    if don.ma_giam_gia_id is not None:
        ma_text = await db.scalar(select(MaGiamGia.ma).where(MaGiamGia.id == don.ma_giam_gia_id))
    ra = don_ra(don, ma_text, await lich_su_don(db, don.id))
    ra.van_don = await van_don_giao_hang(db, don.id)
    return ra
