"""
config.py — Central configuration for EpiCred Content Automation Tool
Loads all API keys and constants from .env

Supports up to 3 keys per service for automatic rotation:
  GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3
  NEWSDATA_API_KEY_1, NEWSDATA_API_KEY_2, NEWSDATA_API_KEY_3
"""
import os
from dotenv import load_dotenv

load_dotenv()


# ── Helper: collect up to 3 numbered keys for a service ──────────────────────
def _load_keys(base_env: str) -> list[str]:
    """
    Load up to 3 API keys from env vars named <BASE>_1, <BASE>_2, <BASE>_3.
    Also accepts the plain <BASE> name as key #1 for backwards compatibility.
    Filters out empty / placeholder values.
    """
    candidates = [os.getenv(base_env, "")]
    for i in range(1, 21):
        candidates.append(os.getenv(f"{base_env}_{i}", ""))
    return [k.strip() for k in candidates if k and not k.startswith("your_")]


# ── API Keys (lists for rotation) ─────────────────────────────────────────────
GEMINI_API_KEYS   = _load_keys("GEMINI_API_KEY")
NEWSDATA_API_KEYS = _load_keys("NEWSDATA_API_KEY")

# Single-key convenience aliases (first key or empty string)
GEMINI_API_KEY   = GEMINI_API_KEYS[0]   if GEMINI_API_KEYS   else ""
NEWSDATA_API_KEY = NEWSDATA_API_KEYS[0] if NEWSDATA_API_KEYS else ""

GNEWS_API_KEY           = os.getenv("GNEWS_API_KEY", "")
NUMBEO_API_KEY          = os.getenv("NUMBEO_API_KEY", "")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")

# ── Flask ─────────────────────────────────────────────────────────────────────
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
FLASK_DEBUG      = os.getenv("FLASK_DEBUG", "true").lower() == "true"
FLASK_PORT       = int(os.getenv("FLASK_PORT", 5000))

# ── Storage Paths ─────────────────────────────────────────────────────────────
BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR       = os.path.join(BASE_DIR, "storage")
NEWS_CACHE_PATH   = os.path.join(STORAGE_DIR, "news_cache.json")
CONTENT_LIB_DIR   = os.path.join(STORAGE_DIR, "content_library")
LOGS_DIR          = os.path.join(STORAGE_DIR, "logs")

# ── News Ingestion ────────────────────────────────────────────────────────────
# ── Search Keywords (MONEY-ONLY — no visa, no rankings, no living costs) ─────
#
# EpiCred is a LOAN company. Every keyword must relate to:
#   loan rates | loan products | scholarships | interest subsidy | eligibility
#
NEWS_KEYWORDS = [
    # Loan product news (what students actually search)
    "education loan interest rate India 2026",
    "education loan rate cut India",
    "education loan new launch India",
    "education loan without collateral 2026",
    "education loan eligibility change India",
    "education loan moratorium period update",
    "education loan for study abroad India",
    # Specific lender launches students care about
    "SBI education loan rate change",
    "ICICI education loan new scheme",
    "HDFC Credila education loan update",
    "Tata Capital education loan",
    "Auxilo education loan",
    "Avanse education loan rate",
    # RBI impact on loans (not generic RBI news)
    "RBI repo rate cut education loan",
    "MCLR rate cut student loan impact",
    # Govt scheme money
    "PM Vidyalaxmi education loan subsidy 2026",
    "CSIS interest subsidy education loan",
    "NSP scholarship amount 2026",
    "state government education loan scheme India",
    "education loan interest subvention",
    # Comparisons (high SEO value)
    "cheapest education loan India 2026",
    "lowest interest rate education loan abroad",
    "education loan comparison India 2026",
]

# Disabled — EpiCred audience doesn't want visa/ranking/living cost content
GLOBAL_TRENDS_KEYWORDS = []

# ── 40 Partner Lenders, Co-op Banks & Govt Schemes ──────────────────────────
TRACKED_ENTITIES = {
    # ── Private & Public Sector Banks ────────────────────────────────────────
    "ICICI Bank":         {"benefit": "Max ₹3 Cr for abroad studies",                          "rate": "9.50% – 14.25%",         "link": "https://www.icicibank.com/personal-banking/loans/education-loan"},
    "HDFC Bank":          {"benefit": "₹75 lakh unsecured; no cap with collateral",            "rate": "Floating, MCLR-linked",   "link": "https://www.hdfcbank.com/personal/borrow/loans/education-loan"},
    "Axis Bank":          {"benefit": "Max ₹75 lakh",                                          "rate": "Competitive",            "link": "https://www.axisbank.com/retail/loans/education-loan"},
    "Kotak Mahindra Bank":{"benefit": "Max ₹20 lakh (abroad)",                                "rate": "10.25% – 16%",          "link": "https://www.kotak.com/en/personal-banking/loans/education-loan.html"},
    "Yes Bank":           {"benefit": "High loan amounts available",                          "rate": "Competitive",            "link": "https://www.yesbank.in/personal-banking/loans/education-loan"},
    "Federal Bank":       {"benefit": "Max ₹20 lakh (abroad); low rates",                    "rate": "Competitive",            "link": "https://www.federalbank.co.in/education-and-career-loans"},
    "IndusInd Bank":      {"benefit": "Up to ₹5 lakh personal loan for education",           "rate": "From 10.49%",            "link": "https://www.indusind.com/in/en/personal/loans/personal-loan.html"},
    "RBL Bank":           {"benefit": "Max ₹2 Cr (secured)",                                  "rate": "9% – 14%",              "link": "https://www.rblbank.com/personal-banking/loans/education-loan"},
    "IDFC FIRST Bank":    {"benefit": "Max ₹1.5 Cr",                                          "rate": "9.5% – 16%",            "link": "https://www.idfcfirstbank.com/personal-banking/loans/education-loan"},
    "HDFC Credila":       {"benefit": "Max ₹1.5 Cr; HDFC group fintech",                     "rate": "10.25% – 15%",          "link": "https://www.hdfccredila.com"},
    "Auxilo":             {"benefit": "No cap on loan amount",                                "rate": "10.25% – 14%",          "link": "https://www.auxilo.com"},
    "Avanse":             {"benefit": "No cap on loan amount",                                "rate": "10% – 16.5%",           "link": "https://www.avanse.com/education-loan"},
    "Prodigy Finance":    {"benefit": "No cap; no cosigner needed for top global universities","rate": "11.24% – 13.25%",       "link": "https://prodigyfinance.com"},
    "Leap Finance":       {"benefit": "No cap on loan amount",                                "rate": "8.45% – 12.25%",        "link": "https://leapfinance.com"},
    "InCred Finance":     {"benefit": "Max ₹75 lakh",                                         "rate": "11% – 16%",             "link": "https://www.incred.com/education-loan"},
    "Bank of Baroda":     {"benefit": "Max ₹1.5 Cr",                                          "rate": "7.90% – 10.90%",        "link": "https://www.bankofbaroda.in/personal-banking/loans/education-loan"},
    "Union Bank of India":{"benefit": "Max ₹2 Cr",                                            "rate": "8.70% – 10.35%",        "link": "https://www.unionbankofindia.co.in/english/education-loan.aspx"},
    "Punjab National Bank":{"benefit": "100% coverage of education costs",                   "rate": "8.70% – 12.35%",        "link": "https://www.pnbindia.in/education.aspx"},
    "Propelld":           {"benefit": "100% coverage; instant disbursal",                    "rate": "12% – 15%",             "link": "https://www.propelld.com/site/education-loan"},
    "SBI":                {"benefit": "Max ₹3 Cr; Scholar Loan for IITs/NITs/top institutes","rate": "7.90% – 10.90%",        "link": "https://sbi.co.in/web/personal-banking/loans/education-loans"},
    "Tata Capital":       {"benefit": "Max ₹2 Cr",                                            "rate": "11% – 13.50%",          "link": "https://www.tatacapital.com/personal-loan/education-loan.html"},

    # ── Co-operative Banks ────────────────────────────────────────────────────
    "Saraswat Bank":      {"benefit": "₹1.5 Cr abroad · ₹75 lakh India — Saraswat Udaan",   "rate": "8.20% – 9.70%",         "link": "https://www.saraswatbank.com"},
    "Cosmos Bank":        {"benefit": "Max ₹1.25 Cr (abroad)",                               "rate": "Competitive",            "link": "https://webloan.cosmos.bank.in/apply/educationloan"},
    "Abhyudaya Co-op Bank":{"benefit": "₹20 lakh abroad · ₹10 lakh India",                 "rate": "Competitive",            "link": "https://www.abhyudayabank.co.in/educational-higher-loan"},
    "Bihar State Co-op Bank":{"benefit": "Max ₹30 lakh (abroad)",                           "rate": "9.50% fixed",            "link": "https://biharscb.co.in/student-education-loan"},
    "Telangana Co-op Apex Bank":{"benefit": "Max ₹40 lakh",                                 "rate": "Competitive",            "link": "https://tgcab.bank.in/loans/education-loan"},
    "HPSCB":              {"benefit": "Up to ₹4 lakh unsecured",                             "rate": "Competitive",            "link": "https://hpscb.bank.in/education-loan-scheme"},
    "Repco Bank":         {"benefit": "Max ₹2 lakh micro loan — EduAid scheme",              "rate": "From 4.75%",             "link": "https://www.repcobank.com/eduAid"},

    # ── Central Government Scholarships ──────────────────────────────────────
    "NSP":                {"benefit": "National Scholarship Portal — single window for all central & state scholarships",  "rate": "N/A", "link": "https://scholarships.gov.in"},
    "Central Sector Scheme":{"benefit": "Up to ₹20,000/year for UG/PG merit students (family income < ₹8 lakh)",         "rate": "N/A", "link": "https://myscheme.gov.in/schemes/csss-cus"},
    "Top Class Education Scheme":{"benefit": "Full tuition + living allowance for SC students in IITs/NITs",              "rate": "N/A", "link": "https://socialjustice.gov.in/schemes/27"},
    "NMMS":               {"benefit": "₹12,000/year for Class 9–12 students (income < ₹3.5 lakh)",                         "rate": "N/A", "link": "https://scholarships.gov.in"},
    "AICTE Scholarships": {"benefit": "Pragati · Saksham · Swanath for tech students (SC/ST/girls/orphans)",               "rate": "N/A", "link": "https://aicte-india.org/schemes"},
    "CSIS":               {"benefit": "Interest waiver during moratorium (income < ₹4.5 lakh, IBA-approved loans)",         "rate": "N/A", "link": "https://myscheme.gov.in/schemes/pm-uspycsiss"},
    "PM Vidyalaxmi":      {"benefit": "Loan via partner banks + 3% interest subvention for income < ₹8 lakh",              "rate": "Subsidized (3% subvention)", "link": "https://www.vidyalakshmi.co.in"},
    "NBCFDC":             {"benefit": "Max ₹20 lakh abroad for backward classes",                                           "rate": "3.5% – 4% p.a.", "link": "https://nbcfdc.gov.in/education-loan"},

    # ── Delhi Government Schemes ──────────────────────────────────────────────
    "DSFDC Delhi Loan":   {"benefit": "₹15 lakh abroad · ₹7.5 lakh India — no collateral, open year-round (Delhi domicile)", "rate": "Low interest", "link": "https://myscheme.gov.in/schemes/els-delhi"},
    "Delhi Edu Guarantee Scheme":{"benefit": "₹10 lakh govt credit guarantee for Delhi students",                          "rate": "N/A", "link": "https://myscheme.gov.in/schemes/hesdgs"},

    # ── Maharashtra Government Schemes ───────────────────────────────────────
    "Rajarshi Shahu Scholarship":{"benefit": "Full tuition waiver for general category (income < ₹8 lakh)",                "rate": "N/A", "link": "https://mahadbt.maharashtra.gov.in"},
    "Maharashtra Post-Matric Scholarship":{"benefit": "Full tuition + exam fee for SC/ST/OBC/SBC/VJNT students",           "rate": "N/A", "link": "https://mahadbt.maharashtra.gov.in"},
}

PARTNER_LENDERS = [
    # Private & Public Banks
    "ICICI Bank", "HDFC Bank", "Axis Bank", "Kotak Mahindra Bank", "Yes Bank",
    "Federal Bank", "IndusInd Bank", "RBL Bank", "IDFC FIRST Bank",
    "HDFC Credila", "Auxilo", "Avanse", "Prodigy Finance", "Leap Finance",
    "InCred Finance", "Bank of Baroda", "Union Bank of India", "Punjab National Bank",
    "Propelld", "SBI", "Tata Capital",
    # Co-op Banks
    "Saraswat Bank", "Cosmos Bank", "Abhyudaya Co-op Bank", "Bihar State Co-op Bank",
    "Telangana Co-op Apex Bank", "HPSCB", "Repco Bank",
    # Govt Schemes
    "NSP", "Central Sector Scheme", "Top Class Education Scheme", "NMMS",
    "AICTE Scholarships", "CSIS", "PM Vidyalaxmi", "NBCFDC",
    "DSFDC Delhi Loan", "Delhi Edu Guarantee Scheme",
    "Rajarshi Shahu Scholarship", "Maharashtra Post-Matric Scholarship",
]

# Only search for loan rates and new loan products — not generic "education loan" which pulls junk
TRACKED_KEYWORDS = (
    [f"{name} education loan rate" for name in list(TRACKED_ENTITIES.keys())[:28]] +  # Banks & co-ops
    [f"{name} loan new" for name in list(TRACKED_ENTITIES.keys())[:21]] +  # Bank product launches
    [f"{name} scholarship 2026" for name in list(TRACKED_ENTITIES.keys())[28:]]  # Schemes with year
)

# RSS — ONLY feeds that publish education loan / scholarship content
RSS_FEEDS = [
    # Education-specific (these regularly publish loan/scholarship articles)
    "https://economictimes.indiatimes.com/industry/services/education/rssfeeds/22214038.cms",
    "https://www.buddy4study.com/feed",
    "https://www.shiksha.com/rss/articles",
    # Loan comparison portals (most likely to carry "X bank launches new education loan" news)
    "https://www.bankbazaar.com/rss/education-loan",
    "https://www.paisabazaar.com/feed/",
]

# Max articles to process per fetch cycle
MAX_ARTICLES_PER_SOURCE = 20
NEWS_CACHE_HOURS = 12  # Refresh cache every 12 hours (twice a day)

# ── Brand Voice ───────────────────────────────────────────────────────────────
PRESENTER_NAME = "Simran"

EPICRED_SOCIAL_LINKS = {
    "website":   "https://epicred.in/",
    "whatsapp":  "https://wa.me/919877889609",
    "linkedin":  "https://www.linkedin.com/company/epicred",
    "instagram": "https://www.instagram.com/epicred.in",
    "facebook":  "https://www.facebook.com/profile.php?id=61569345050781&mibextid=ZbWKwL",
    "presenter_linkedin": "https://www.linkedin.com/in/simran-jakhar",
}

BRAND_VOICE = {
    "name":     "EpiCred",
    "tagline":  "Simplifying education loans for Indian students",
    "tone":     "Conversational authority — like a smart elder sibling who works in finance. Trustworthy, data-driven, empowering. Never salesy — always 'here is what you need to know'.",
    "audience": "Indian students aged 18-25, Tier 2/3 cities, planning higher education or study abroad",
    "language": "English with occasional Hindi phrases welcome",
    "website":  "epicred.in",
    "positioning": "India's trusted education loan comparison & advisory platform with 40+ partner lenders",
}

# ── Platform Posting Rules ────────────────────────────────────────────────────
# Days: 0=Monday … 6=Sunday
PLATFORM_RULES = {
    "instagram_reel":     {"days": [0, 1, 3, 4], "time": "18:00", "weekly_count": 4,  "color": "11"},  # Tomato
    "instagram_carousel": {"days": [2, 5],        "time": "12:00", "weekly_count": 2,  "color": "3"},   # Banana
    "instagram_post":     {"days": [0, 2, 4],     "time": "10:00", "weekly_count": 3,  "color": "10"},  # Sage
    "linkedin_post":      {"days": [1, 2, 3],     "time": "09:00", "weekly_count": 3,  "color": "7"},   # Peacock
    "twitter_thread":     {"days": [0,1,2,3,4,5,6],"time": "10:00","weekly_count": 7,  "color": "8"},   # Graphite
    "youtube_shorts":     {"days": [2, 5],        "time": "17:00", "weekly_count": 2,  "color": "1"},   # Blueberry
    "youtube_script":     {"days": [1, 3, 5],     "time": "14:00", "weekly_count": 3,  "color": "9"},   # Flamingo (long-form 4-5 min)
}

# Score threshold — only MONEY-RELEVANT articles pass (loan rates, scholarships, eligibility)
TREND_SCORE_THRESHOLD = 6

# ── Key Manager initialisation ────────────────────────────────────────────────
# Import here to avoid circular deps; singletons are ready after this line.
from pipeline.key_manager import init_key_managers  # noqa: E402
init_key_managers(GEMINI_API_KEYS, NEWSDATA_API_KEYS)
