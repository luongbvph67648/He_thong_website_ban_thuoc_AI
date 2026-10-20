"""Tạo đơn hộ khách đặt qua điện thoại (DS07, spec 04 mục 1.1 dòng 4 và 5).

Cùng quy tắc với đặt hàng online (KTV02): kiểm tra dòng như giỏ hàng (chặn thuốc kê đơn), tính giá/giảm/phí ship, giữ
hàng FEFO, tất cả trong một transaction. COD vào thẳng "Đã xác nhận"; VNPay/MoMo vào "Chờ thanh toán" và khách thanh
toán ở trang của mình (nên cần tài khoản khách, tra bằng SĐT).
"""

from datetime import timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import idempotency
from app.core.cau_hinh import doc_cau_hinh
from app.core.loi import LoiNghiepVu
from app.core.ma_chung_tu import ma_don_hang
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import DonHang
from app.models.enums import HinhThucNhan, KenhBan, PhuongThucThanhToan, TrangThaiDon, TrangThaiTaiKhoan
from app.models.he_thong import NhanVien
from app.models.khach_hang import DiaChi, KhachHang
from app.modules.ban_hang import dat_hang
from app.modules.ban_hang.schemas_dat_ho import DonHoRa, DonHoVao, KhachTimRa
from app.modules.ban_hang.trang_thai import NGUON_NGUOI_DUNG, khoi_tao_trang_thai, tac_nhan_tu_nhan_vien
from app.modules.dia_chi.dich_vu import ten_dia_gioi
from app.modules.dia_chi.schemas import DiaChiRa
from app.modules.gio_hang import dich_vu as dich_vu_gio
from app.modules.kho import ton_kho
from app.modules.kho.ton_kho import YeuCauGiu
from app.modules.khuyen_mai import ap_dung

THAO_TAC = "dat-ho"


async def _khach_theo_sdt(db: AsyncSession, sdt: str) -> KhachHang | None:
    return (
        await db.execute(
            select(KhachHang).where(
                KhachHang.so_dien_thoai == sdt,
                KhachHang.deleted_at.is_(None),
                KhachHang.trang_thai == TrangThaiTaiKhoan.hoat_dong,
            )
        )
    ).scalar_one_or_none()


async def tim_khach(db: AsyncSession, sdt: str) -> KhachTimRa:
    """Tra khách có tài khoản bằng đúng SĐT (không tìm gần đúng, không trả email hay dữ liệu sức khỏe)."""
    khach = await _khach_theo_sdt(db, sdt)
    if khach is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy khách hàng với số điện thoại này")
    ds = (
        (
            await db.execute(
                select(DiaChi).where(DiaChi.khach_hang_id == khach.id).order_by(DiaChi.la_mac_dinh.desc(), DiaChi.id)
            )
        )
        .scalars()
        .all()
    )
    return KhachTimRa(
        ho_ten=khach.ho_ten, so_dien_thoai=khach.so_dien_thoai, dia_chi=[DiaChiRa.model_validate(d) for d in ds]
    )


async def tao_don_ho(db: AsyncSession, nv: NhanVien, vao: DonHoVao, khoa: str) -> DonHoRa:
    dau_van_tay = idempotency.dau_van_tay(vao.model_dump(mode="json"))
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"{THAO_TAC}:{nv.id}:{khoa}"})
    da_co = idempotency.tra_cuu(THAO_TAC, nv.id, khoa, dau_van_tay)
    if da_co is not None:
        ton_tai = await db.scalar(select(DonHang.id).where(DonHang.ma_don == da_co["don"]["ma_don"]))
        if ton_tai is not None:
            return DonHoRa.model_validate(da_co)

    truc_tuyen = vao.phuong_thuc_tt != PhuongThucThanhToan.cod
    khach = await _khach_theo_sdt(db, vao.sdt_khach) if vao.sdt_khach else None
    if vao.sdt_khach and khach is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy khách hàng với số điện thoại này")
    if truc_tuyen and khach is None:
        raise dat_hang.khong_hop_le("sdt_khach", "Thanh toán online cần khách có tài khoản để nhận link thanh toán")
    dia_chi: DiaChi | None = None
    if vao.hinh_thuc_nhan == HinhThucNhan.giao_tan_noi:
        if vao.dia_chi is None:
            raise dat_hang.khong_hop_le("dia_chi", "Cần nhập địa chỉ giao hàng")
        ten_tinh, ten_xa = ten_dia_gioi(vao.dia_chi.ma_tinh, vao.dia_chi.ma_phuong_xa)
        dia_chi = DiaChi(  # chỉ để chụp vào đơn, không lưu vào sổ địa chỉ của khách
            ten_nguoi_nhan=vao.ten_nguoi_nhan,
            so_dien_thoai=vao.sdt_nguoi_nhan,
            dia_chi_chi_tiet=vao.dia_chi.dia_chi_chi_tiet,
            ma_tinh=vao.dia_chi.ma_tinh,
            ten_tinh=ten_tinh,
            ma_phuong_xa=vao.dia_chi.ma_phuong_xa,
            ten_phuong_xa=ten_xa,
        )
    elif vao.dia_chi is not None:
        raise dat_hang.khong_hop_le("dia_chi", "Đơn nhận tại nhà thuốc không có địa chỉ giao")

    gop: dict[tuple[int, int], int] = {}
    for d in vao.dong:  # cùng sản phẩm và đơn vị thì gộp số lượng
        gop[(d.san_pham_id, d.don_vi_id)] = gop.get((d.san_pham_id, d.don_vi_id), 0) + d.so_luong
    dong_dat = await dich_vu_gio.kiem_tra_dong_de_dat(
        db, [(i, sp, dv, sl) for i, ((sp, dv), sl) in enumerate(gop.items())]
    )
    t = await dat_hang.tinh_tien(db, khach.id if khach else None, dong_dat, dia_chi, vao.ma_giam_gia, dung_luot=True)

    bay_gio = bay_gio_utc()
    thoi_han = int(await doc_cau_hinh(db, "thoi_han_thanh_toan_phut", dat_hang.THOI_HAN_THANH_TOAN_PHUT))
    don = DonHang(
        ma_don=await ma_don_hang(db),
        khach_hang_id=khach.id if khach else None,
        kenh_ban=KenhBan.dien_thoai,
        hinh_thuc_nhan=vao.hinh_thuc_nhan,
        phuong_thuc_tt=vao.phuong_thuc_tt,
        ma_giam_gia_id=t.ma_dung.id if t.ma_dung else None,
        tam_tinh=t.tam_tinh,
        giam_gia=t.giam,
        phi_van_chuyen=t.phi,
        tong_tien=t.tong_tien,
        ghi_chu=vao.ghi_chu,
        han_thanh_toan=bay_gio + timedelta(minutes=thoi_han) if truc_tuyen else None,
    )
    if dia_chi is not None:
        dat_hang.ghi_dia_chi_giao(don, dia_chi)
    else:
        don.ten_nguoi_nhan, don.sdt_nguoi_nhan = vao.ten_nguoi_nhan, vao.sdt_nguoi_nhan
    don.chi_tiet = dat_hang.dong_cua_don(t)
    den = TrangThaiDon.cho_thanh_toan if truc_tuyen else TrangThaiDon.da_xac_nhan
    tac_nhan = await tac_nhan_tu_nhan_vien(db, nv)
    ls = await khoi_tao_trang_thai(db, don, den, tac_nhan, NGUON_NGUOI_DUNG)

    thu_tu = sorted(don.chi_tiet, key=lambda c: c.id)
    await ton_kho.giu_hang_nhieu(db, [YeuCauGiu(c.id, c.san_pham_id, c.so_luong * c.he_so) for c in thu_tu])

    await db.refresh(ls)
    ra = DonHoRa(
        don=dat_hang.don_ra(don, vao.ma_giam_gia and ap_dung.chuan_hoa_ma(vao.ma_giam_gia), [ls]),
        lien_ket_thanh_toan=f"/thanh-toan/ket-qua?ma={don.ma_don}" if truc_tuyen else None,
    )
    idempotency.ghi_nho(THAO_TAC, nv.id, khoa, dau_van_tay, ra.model_dump(mode="json"))
    return ra
