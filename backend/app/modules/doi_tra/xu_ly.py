"""Dược sĩ xử lý yêu cầu đổi trả (DS09, T6.1). Không commit.

Duyệt/từ chối (dòng 2, 3, 5), tạo giao dịch hoàn tiền (dòng 6) hoặc đơn thay thế 0đ (dòng 8, đơn dòng 30). Xác nhận
chuyển tiền thuộc Admin (AD17, T6.3) nên người duyệt không thể tự xác nhận. Kho nhận hàng ở T6.2 (dòng 4).
"""

import logging
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.ma_chung_tu import ma_don_hang
from app.core.phan_quyen import dam_bao_la_duoc_si
from app.core.thoi_gian import bay_gio_utc
from app.core.tien import lam_tron_vnd
from app.models.ban_hang import CtDonHang, CtYeuCauDoiTra, DonHang, ThanhToan, VanDon, YeuCauDoiTra
from app.models.enums import (
    HinhThucNhan,
    HuongXuLyDoiTra,
    KenhBan,
    LoaiGiaoDich,
    LoaiVanDon,
    PhuongThucThanhToan,
    TrangThaiDoiTra,
    TrangThaiDon,
    TrangThaiGiaoDich,
    TrangThaiThanhToan,
)
from app.models.he_thong import NhanVien
from app.models.khach_hang import KhachHang
from app.modules.ban_hang import dat_hang
from app.modules.ban_hang.trang_thai import NGUON_NGUOI_DUNG, TacNhan, khoi_tao_trang_thai
from app.modules.doi_tra import dich_vu
from app.modules.doi_tra.schemas import DoiTraNoiBoChiTiet, DoiTraNoiBoTom
from app.modules.kho import ton_kho
from app.modules.kho.ton_kho import YeuCauGiu
from app.modules.thong_bao import service as thong_bao
from app.tich_hop.van_chuyen import lay_don_vi_van_chuyen

logger = logging.getLogger(__name__)
TT = TrangThaiDoiTra
GRAM_MOI_DON_VI_CO_SO = 100


async def _lay(db: AsyncSession, nv: NhanVien, yc_id: int, *, khoa: bool = False):
    await dam_bao_la_duoc_si(db, nv)  # Admin được gán quyền cho vai trò khác cũng không duyệt đổi trả
    cau = (
        select(YeuCauDoiTra, DonHang, KhachHang)
        .join(DonHang, DonHang.id == YeuCauDoiTra.don_hang_id)
        .join(KhachHang, KhachHang.id == YeuCauDoiTra.khach_hang_id)
        .where(YeuCauDoiTra.id == yc_id)
    )
    if khoa:
        cau = cau.with_for_update(of=YeuCauDoiTra).execution_options(populate_existing=True)
    dong = (await db.execute(cau)).first()
    if dong is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy yêu cầu đổi trả")
    return dong[0], dong[1], dong[2]


def _sai_trang_thai(thong_diep: str) -> LoiNghiepVu:
    return LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", thong_diep)


async def danh_sach(db: AsyncSession, nv: NhanVien, trang_thai: TrangThaiDoiTra | None) -> list[DoiTraNoiBoTom]:
    await dam_bao_la_duoc_si(db, nv)
    cau = (
        select(YeuCauDoiTra, DonHang.ma_don, KhachHang)
        .join(DonHang, DonHang.id == YeuCauDoiTra.don_hang_id)
        .join(KhachHang, KhachHang.id == YeuCauDoiTra.khach_hang_id)
        .order_by(YeuCauDoiTra.created_at, YeuCauDoiTra.id)
        .limit(200)
    )
    cau = (
        cau.where(YeuCauDoiTra.trang_thai == trang_thai)
        if trang_thai
        else cau.where(YeuCauDoiTra.trang_thai.in_((TT.cho_duyet, TT.da_duyet, TT.kho_da_nhan)))
    )
    return [
        DoiTraNoiBoTom(
            **(await dich_vu.tom_tat(db, yc, ma)).model_dump(),
            id=yc.id,
            ten_khach=k.ho_ten,
            so_dien_thoai_khach=k.so_dien_thoai,
            duoc_si_duyet_toi=yc.duoc_si_id == nv.id,
        )
        for yc, ma, k in (await db.execute(cau)).all()
    ]


async def tong_da_thanh_toan(db: AsyncSession, don_id: int) -> Decimal:
    return await db.scalar(
        select(func.coalesce(func.sum(ThanhToan.so_tien), 0)).where(
            ThanhToan.don_hang_id == don_id,
            ThanhToan.loai == LoaiGiaoDich.thanh_toan,
            ThanhToan.trang_thai == TrangThaiGiaoDich.thanh_cong,
        )
    ) or Decimal(0)


async def _tong_hoan(db: AsyncSession, don_id: int, bo_qua_yc: int | None = None) -> Decimal:
    cau = select(func.coalesce(func.sum(ThanhToan.so_tien), 0)).where(
        ThanhToan.don_hang_id == don_id,
        ThanhToan.loai == LoaiGiaoDich.hoan_tien,
        ThanhToan.trang_thai.in_((TrangThaiGiaoDich.khoi_tao, TrangThaiGiaoDich.thanh_cong)),
    )
    if bo_qua_yc is not None:
        cau = cau.where(ThanhToan.yeu_cau_doi_tra_id.is_(None) | (ThanhToan.yeu_cau_doi_tra_id != bo_qua_yc))
    return await db.scalar(cau) or Decimal(0)


async def chi_tiet(db: AsyncSession, nv: NhanVien, yc_id: int) -> DoiTraNoiBoChiTiet:
    yc, don, khach = await _lay(db, nv, yc_id)
    co = await dich_vu.dung_chi_tiet(db, yc, don.ma_don)
    return DoiTraNoiBoChiTiet(
        **co.model_dump(),
        id=yc.id,
        ten_khach=khach.ho_ten,
        so_dien_thoai_khach=khach.so_dien_thoai,
        ket_qua_kiem_hang=yc.ket_qua_kiem_hang,
        tong_da_thanh_toan=await tong_da_thanh_toan(db, don.id),
        da_co_giao_dich_hoan=await dich_vu.giao_dich_hoan(db, yc.id) is not None,
    )


async def _tinh_hoan(db: AsyncSession, yc: YeuCauDoiTra, don: DonHang) -> Decimal:
    """Số tiền hoàn (spec 04 mục 5), cộng phí vận chuyển khi trả toàn bộ các dòng; không vượt tổng đã trả."""
    cts = {c.id: c for c in (await db.execute(select(CtDonHang).where(CtDonHang.don_hang_id == don.id))).scalars()}
    ds = (await db.execute(select(CtYeuCauDoiTra).where(CtYeuCauDoiTra.yeu_cau_id == yc.id))).scalars().all()
    tra = {r.ct_don_hang_id: r.so_luong for r in ds}
    so = dich_vu.tien_hoan([(cts[i], sl) for i, sl in tra.items()])
    if all(tra.get(i) == c.so_luong for i, c in cts.items()):
        so += don.phi_van_chuyen
    so = lam_tron_vnd(so)
    con = await tong_da_thanh_toan(db, don.id) - await _tong_hoan(db, don.id, yc.id)
    if so > con:
        raise LoiNghiepVu(
            "HOAN_VUOT_SO_DA_TRA", "Tổng tiền hoàn vượt số tiền khách đã thanh toán", chi_tiet={"toi_da": str(con)}
        )
    return so


async def _bao_khach(db: AsyncSession, yc: YeuCauDoiTra, tieu_de: str, noi_dung: str | None = None) -> None:
    await thong_bao.gui_cho_khach(
        db, yc.khach_hang_id, loai="doi_tra", tieu_de=tieu_de, noi_dung=noi_dung, lien_ket="/tai-khoan/doi-tra"
    )


async def duyet(db: AsyncSession, nv: NhanVien, yc_id: int, huong: HuongXuLyDoiTra) -> DoiTraNoiBoChiTiet:
    """Dòng 3: xác minh đúng, chọn hướng xử lý; tạo vận đơn trả hàng (đơn giao tận nơi) và báo khách."""
    yc, don, _ = await _lay(db, nv, yc_id, khoa=True)
    if yc.trang_thai != TT.cho_duyet:
        raise _sai_trang_thai("Chỉ duyệt được yêu cầu đang chờ duyệt")
    so_tien = Decimal(0)
    if huong == HuongXuLyDoiTra.hoan_tien:
        if don.trang_thai_tt not in (TrangThaiThanhToan.da_thanh_toan, TrangThaiThanhToan.hoan_tien_mot_phan):
            raise dat_hang.khong_hop_le("huong_xu_ly", "Đơn chưa thanh toán nên không có gì để hoàn tiền")
        so_tien = await _tinh_hoan(db, yc, don)
    ma_van_don = None
    if don.hinh_thuc_nhan == HinhThucNhan.giao_tan_noi:
        don_vi = lay_don_vi_van_chuyen()
        so_co_so = (
            await db.scalar(
                select(func.coalesce(func.sum(CtYeuCauDoiTra.so_luong * CtDonHang.he_so), 0))
                .join(CtDonHang, CtDonHang.id == CtYeuCauDoiTra.ct_don_hang_id)
                .where(CtYeuCauDoiTra.yeu_cau_id == yc.id)
            )
            or 0
        )
        khoi_luong = max(int(so_co_so) * GRAM_MOI_DON_VI_CO_SO, GRAM_MOI_DON_VI_CO_SO)
        try:
            kq = await don_vi.tao_van_don(don, "tra_hang", khoi_luong)
        except Exception as e:  # noqa: BLE001  lỗi đối tác bất kỳ đều là 502, yêu cầu giữ nguyên để thử lại
            logger.warning("Tạo vận đơn trả hàng thất bại cho yêu cầu %s", yc.ma_yeu_cau, exc_info=True)
            raise LoiNghiepVu("LOI_DOI_TAC", "Không tạo được vận đơn trả hàng, vui lòng thử lại sau") from e
        db.add(
            VanDon(
                don_hang_id=don.id,
                loai=LoaiVanDon.tra_hang,
                yeu_cau_doi_tra_id=yc.id,
                don_vi_van_chuyen=don_vi.ten,
                ma_van_don=kq.ma_van_don,
                phi=Decimal(kq.phi),
                khoi_luong_gram=khoi_luong,
            )
        )
        ma_van_don = kq.ma_van_don
    yc.trang_thai, yc.huong_xu_ly, yc.duoc_si_id, yc.so_tien_hoan = TT.da_duyet, huong, nv.id, so_tien
    yc.updated_at = bay_gio_utc()
    await db.flush()
    noi_dung = f"Mã vận đơn trả hàng: {ma_van_don}" if ma_van_don else "Vui lòng mang hàng đến nhà thuốc"
    await _bao_khach(db, yc, f"Yêu cầu đổi trả {yc.ma_yeu_cau} đã được duyệt", noi_dung)
    return await chi_tiet(db, nv, yc_id)


async def tu_choi(db: AsyncSession, nv: NhanVien, yc_id: int, ly_do: str) -> DoiTraNoiBoChiTiet:
    """Dòng 2 (xác minh không đúng) hoặc dòng 5 (kho nhận nhưng kiểm không đạt, kèm bằng chứng kiểm hàng)."""
    yc, _, _ = await _lay(db, nv, yc_id, khoa=True)
    if yc.trang_thai == TT.kho_da_nhan:
        if not (yc.ket_qua_kiem_hang or "").strip():
            raise dat_hang.khong_hop_le("ly_do", "Từ chối sau khi kho nhận phải có kết quả kiểm hàng của kho")
    elif yc.trang_thai != TT.cho_duyet:
        raise _sai_trang_thai("Chỉ từ chối được yêu cầu chờ duyệt hoặc kho đã nhận")
    if await dich_vu.giao_dich_hoan(db, yc.id) is not None:
        raise _sai_trang_thai("Yêu cầu đã có giao dịch hoàn tiền")
    yc.trang_thai, yc.ly_do_tu_choi, yc.updated_at = TT.tu_choi, ly_do.strip(), bay_gio_utc()
    yc.duoc_si_id = yc.duoc_si_id or nv.id
    await db.flush()
    await _bao_khach(db, yc, f"Yêu cầu đổi trả {yc.ma_yeu_cau} không được chấp nhận", yc.ly_do_tu_choi)
    return await chi_tiet(db, nv, yc_id)


async def tao_hoan_tien(db: AsyncSession, nv: NhanVien, yc_id: int) -> DoiTraNoiBoChiTiet:
    """Dòng 6: kho đã nhận, hướng hoàn tiền -> giao dịch `hoan_tien` ở `khoi_tao` (Admin xác nhận chuyển ở AD17)."""
    yc, don, _ = await _lay(db, nv, yc_id, khoa=True)
    if yc.trang_thai != TT.kho_da_nhan or yc.huong_xu_ly != HuongXuLyDoiTra.hoan_tien:
        raise _sai_trang_thai("Chỉ tạo hoàn tiền cho yêu cầu hướng hoàn tiền mà kho đã nhận hàng")
    if await dich_vu.giao_dich_hoan(db, yc.id) is not None:
        raise LoiNghiepVu("TRUNG_DU_LIEU", "Yêu cầu này đã có giao dịch hoàn tiền")
    so_tien = await _tinh_hoan(db, yc, don)
    goc = (
        (
            await db.execute(
                select(ThanhToan)
                .where(
                    ThanhToan.don_hang_id == don.id,
                    ThanhToan.loai == LoaiGiaoDich.thanh_toan,
                    ThanhToan.trang_thai == TrangThaiGiaoDich.thanh_cong,
                )
                .order_by(ThanhToan.id.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )
    cong = goc.cong_thanh_toan if goc else (don.phuong_thuc_tt or PhuongThucThanhToan.cod)
    db.add(
        ThanhToan(
            don_hang_id=don.id,
            loai=LoaiGiaoDich.hoan_tien,
            cong_thanh_toan=cong,
            so_tien=so_tien,
            trang_thai=TrangThaiGiaoDich.khoi_tao,
            thanh_toan_goc_id=goc.id if goc else None,
            yeu_cau_doi_tra_id=yc.id,
            ghi_chu=f"Hoàn tiền đổi trả {yc.ma_yeu_cau}",
        )
    )
    yc.so_tien_hoan, yc.updated_at = so_tien, bay_gio_utc()
    don.trang_thai_tt = TrangThaiThanhToan.cho_hoan_tien
    await db.flush()
    yeu_cau_tk = cong in dich_vu.CONG_HOAN_THU_CONG
    await _bao_khach(
        db,
        yc,
        f"Đang hoàn tiền cho yêu cầu {yc.ma_yeu_cau}",
        "Vui lòng nhập tài khoản nhận hoàn tiền"
        if yeu_cau_tk
        else "Nhà thuốc sẽ hoàn về phương thức bạn đã thanh toán",
    )
    return await chi_tiet(db, nv, yc_id)


async def gui_hang_thay_the(db: AsyncSession, nv: NhanVien, yc_id: int) -> DoiTraNoiBoChiTiet:
    """Dòng 8 và dòng 30: tạo đơn thay thế 0đ trỏ về đơn gốc, giữ hàng FEFO, vào thẳng "Đã xác nhận"."""
    yc, goc, _ = await _lay(db, nv, yc_id, khoa=True)
    if yc.trang_thai != TT.kho_da_nhan or yc.huong_xu_ly != HuongXuLyDoiTra.gui_hang_thay_the:
        raise _sai_trang_thai("Chỉ gửi hàng thay thế cho yêu cầu hướng thay thế mà kho đã nhận hàng")
    dong = (
        await db.execute(
            select(CtYeuCauDoiTra, CtDonHang)
            .join(CtDonHang, CtDonHang.id == CtYeuCauDoiTra.ct_don_hang_id)
            .where(CtYeuCauDoiTra.yeu_cau_id == yc.id)
            .order_by(CtYeuCauDoiTra.id)
        )
    ).all()
    zero = lam_tron_vnd(0)
    moi = DonHang(
        ma_don=await ma_don_hang(db),
        khach_hang_id=goc.khach_hang_id,
        kenh_ban=KenhBan.online,
        hinh_thuc_nhan=goc.hinh_thuc_nhan,
        phuong_thuc_tt=PhuongThucThanhToan.cod,
        trang_thai_tt=TrangThaiThanhToan.da_thanh_toan,  # đơn 0đ: không có gì để thu
        don_hang_goc_id=goc.id,
        tam_tinh=zero,
        giam_gia=zero,
        phi_van_chuyen=zero,
        tong_tien=zero,
        ten_nguoi_nhan=goc.ten_nguoi_nhan,
        sdt_nguoi_nhan=goc.sdt_nguoi_nhan,
        dia_chi_giao=goc.dia_chi_giao,
        ma_tinh=goc.ma_tinh,
        ma_quan_huyen=goc.ma_quan_huyen,
        ma_phuong_xa=goc.ma_phuong_xa,
        ghi_chu=f"Đơn thay thế cho đơn {goc.ma_don} (đổi trả {yc.ma_yeu_cau})",
    )
    moi.chi_tiet = [
        CtDonHang(
            san_pham_id=ct.san_pham_id,
            don_vi_id=ct.don_vi_id,
            ten_san_pham=ct.ten_san_pham,
            ten_don_vi=ct.ten_don_vi,
            he_so=ct.he_so,
            so_luong=r.so_luong,
            don_gia=zero,
            giam_gia_phan_bo=zero,
            thanh_tien=zero,
        )
        for r, ct in dong
    ]
    await khoi_tao_trang_thai(
        db,
        moi,
        TrangThaiDon.da_xac_nhan,
        TacNhan.duoc_si(nv.id),
        NGUON_NGUOI_DUNG,
        f"Thay thế cho {goc.ma_don}",
        so_dong=30,
    )
    thu_tu = sorted(moi.chi_tiet, key=lambda c: c.id)
    await ton_kho.giu_hang_nhieu(db, [YeuCauGiu(c.id, c.san_pham_id, c.so_luong * c.he_so) for c in thu_tu])
    yc.trang_thai, yc.updated_at = TT.hoan_tat, bay_gio_utc()
    await db.flush()
    await _bao_khach(
        db, yc, f"Đơn thay thế {moi.ma_don} đã được tạo", f"Nhà thuốc sẽ gửi hàng thay thế cho yêu cầu {yc.ma_yeu_cau}"
    )
    return await chi_tiet(db, nv, yc_id)
