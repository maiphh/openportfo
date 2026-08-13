"""Offline VN stock catalog used by fixture client and HTTP fallback."""

from __future__ import annotations

from decimal import Decimal

from app.ports.market import AssetSearchResult

# Liquid HOSE / HNX / UPCOM names (demo catalog — not a live exchange dump).
_VN_STOCKS: tuple[tuple[str, str, str], ...] = (
    ("VNM", "Vinamilk", "65000"),
    ("FPT", "FPT Corporation", "120000"),
    ("HPG", "Hoa Phat Group", "28000"),
    ("VIC", "Vingroup", "42000"),
    ("VHM", "Vinhomes", "38000"),
    ("VRE", "Vincom Retail", "18500"),
    ("VCB", "Vietcombank", "92000"),
    ("BID", "BIDV", "45000"),
    ("CTG", "VietinBank", "33000"),
    ("TCB", "Techcombank", "24500"),
    ("MBB", "MB Bank", "23000"),
    ("ACB", "Asia Commercial Bank", "25000"),
    ("VPB", "VPBank", "18500"),
    ("STB", "Sacombank", "32000"),
    ("HDB", "HDBank", "26000"),
    ("TPB", "TPBank", "17000"),
    ("VIB", "VIB", "18500"),
    ("SHB", "SHB", "11000"),
    ("MSB", "MSB", "13500"),
    ("SSB", "SeABank", "19500"),
    ("EIB", "Eximbank", "18500"),
    ("LPB", "LienVietPostBank", "31000"),
    ("GAS", "PetroVietnam Gas", "72000"),
    ("PLX", "Petrolimex", "38500"),
    ("POW", "PetroVietnam Power", "12500"),
    ("PVD", "PV Drilling", "26500"),
    ("PVS", "PV Technical Services", "34000"),
    ("BSR", "Binh Son Refining", "19500"),
    ("REE", "REE Corporation", "62000"),
    ("PC1", "PC1 Group", "24000"),
    ("GEG", "Gia Lai Electricity", "13500"),
    ("MWG", "Mobile World", "62000"),
    ("PNJ", "Phu Nhuan Jewelry", "98000"),
    ("MSN", "Masan Group", "72000"),
    ("MCH", "Masan Consumer", "165000"),
    ("SAB", "Sabeco", "56000"),
    ("VJC", "Vietjet Air", "98000"),
    ("HVN", "Vietnam Airlines", "26500"),
    ("GVR", "Vietnam Rubber Group", "31000"),
    ("BCM", "Becamex IDC", "64000"),
    ("KDH", "Khang Dien House", "32000"),
    ("NLG", "Nam Long", "36500"),
    ("DXG", "Dat Xanh Group", "15500"),
    ("PDR", "Phat Dat", "19500"),
    ("DIG", "DIC Corp", "17500"),
    ("NVL", "Novaland", "12500"),
    ("KBC", "Kinh Bac City", "26500"),
    ("IDC", "IDICO", "48000"),
    ("VGC", "Viglacera", "45000"),
    ("SSI", "SSI Securities", "26500"),
    ("VND", "VNDirect", "16500"),
    ("HCM", "Ho Chi Minh City Securities", "24500"),
    ("VCI", "Vietcap", "38500"),
    ("CTS", "Vietnam Bank for Industry Securities", "18500"),
    ("DGC", "Duc Giang Chemicals", "98000"),
    ("DPM", "PetroVietnam Fertilizer", "34000"),
    ("DCM", "Ca Mau Fertilizer", "33500"),
    ("GMD", "Gemadept", "72000"),
    ("HAH", "Hai An Transport", "38500"),
    ("VSC", "Vietnam Container Shipping", "18500"),
    ("IMP", "Imexpharm", "52000"),
    ("DHG", "DHG Pharma", "105000"),
    ("TRA", "Traphaco", "78000"),
    ("DBC", "Dabaco", "26500"),
    ("ANV", "Nam Viet", "18500"),
    ("VHC", "Vinh Hoan", "72000"),
    ("FMC", "Sao Ta Foods", "46500"),
    ("FRT", "FPT Retail", "145000"),
    ("DGW", "Digiworld", "38500"),
    ("PET", "PetroVietnam General Services", "24500"),
)


def stock_catalog() -> list[AssetSearchResult]:
    return [
        AssetSearchResult(
            symbol=symbol,
            name=name,
            asset_id=symbol,
            asset_type="stock",
            currency="VND",
        )
        for symbol, name, _ in _VN_STOCKS
    ]


def stock_prices() -> dict[str, tuple[Decimal, str]]:
    return {
        symbol: (Decimal(price), "VND") for symbol, _name, price in _VN_STOCKS
    }
