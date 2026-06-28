from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "screen_results.json"

FILTERS = "fa_div_o5,fa_forwardpe_u8,fa_pb_u0.8,geo_usa,ind_stocksonly"
FINVIZ_BASE = "https://finviz.com/screener.ashx"

FORWARD_PE_MAX = 8.0
PB_MAX = 0.8
DIVIDEND_MIN = 5.0

# Relaxed screen for "near misses" section
RELAXED_FORWARD_PE_MAX = 10.0
RELAXED_PB_MAX = 1.0

REFRESH_TIMEZONE = "America/New_York"
REFRESH_HOUR = 7
REFRESH_MINUTE = 0
REFRESH_DAY = "fri"

TIER_1 = {"CNXC", "RITM", "OTF", "FSK", "MFA"}
TIER_2 = {
    "NMFC", "CGBD", "MFIC", "PFLT", "PMT", "CIM",
    "FBRT", "TRTX", "BRSP", "GBLI",
}

OPERATING_TICKERS = {"CNXC", "GBLI"}

MREIT_KEYWORDS = ("mortgage", "reit", "realty trust", "real estate finance")
BDC_KEYWORDS = ("bdc", "capital corp", "finance corp", "income fund", "investment corp")