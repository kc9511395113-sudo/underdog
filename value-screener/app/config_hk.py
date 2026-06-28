from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
HK_DATA_FILE = BASE_DIR / "data" / "screen_results_hk.json"

HK_LIST_URL = "https://stockanalysis.com/list/hong-kong-stock-exchange/"
HK_STATS_URL = "https://stockanalysis.com/quote/hkg/{symbol}/statistics/"

FORWARD_PE_MAX = 8.0
PB_MAX = 0.8
DIVIDEND_MIN = 5.0
RELAXED_FORWARD_PE_MAX = 12.0
RELAXED_PB_MAX = 1.0

# Liquid HK universe cap — scan top N by market cap from HKEX list
HK_SCAN_LIMIT = 250

HANG_SENG_FORWARD_PE = 11.2
HANG_SENG_SOURCE = "Hang Seng Index (Jun 2026)"

# Quality tier whitelists (from HK value analysis)
HK_TIER_1 = {
    "0883", "0939", "1398", "1288", "3988", "3328", "2628",
    "0857", "1088", "0728", "0762", "0005", "2388", "1336",
}
HK_TIER_2 = {
    "0144", "1882", "0386", "1898", "2328", "2601", "2318",
    "3968", "0916", "1171", "0288", "0002", "0003", "0006",
    "0016", "0012", "1299", "1810",
}

HK_TIER_NOTES = {
    "0883": "CNOOC — lowest fwd P/E among major HK oils; strong ROE, net cash, 6%+ yield.",
    "0939": "CCB — Big-4 bank; deep discount to book (~0.5× P/B); 5.4% yield.",
    "1398": "ICBC — world's largest bank by assets; classic HK value compounder.",
    "1288": "ABC — Agricultural Bank; similar profile to Big-4 peers.",
    "3988": "BOC — Bank of China; SOE bank at <0.6× book.",
    "3328": "BoCom — Bank of Communications; slightly higher growth bank.",
    "2628": "China Life — dominant insurer; cyclical but cheap on earnings.",
    "0857": "PetroChina — integrated oil major; energy SOE discount.",
    "1088": "China Shenhua — coal/energy; high dividend, low capex.",
    "0728": "China Telecom — defensive telco yield; stable cash flows.",
    "0762": "China Unicom — telco peer; similar yield profile.",
    "0005": "HSBC — global bank; HK bellwether, 6%+ yield at right price.",
    "2388": "BOC Hong Kong — pure HK bank play; cleaner balance sheet.",
    "1336": "PICC Group — insurance SOE; policy-driven but cheap.",
    "0144": "China Merchants Port — infrastructure yield; port monopoly assets.",
    "1882": "Haitian Int'l — engineering/construction; cyclical SOE.",
}