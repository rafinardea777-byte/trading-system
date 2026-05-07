"""רשימת חשבונות X לסריקה - אנליסטים, חדשות פיננסיות, פוליטיקה אמריקאית."""

# חשבונות עם השפעה ישירה על שווקים - נסרקים ראשונים
PRIORITY_REALTIME_ACCOUNTS = [
    # פוליטיקה וממשל ארה"ב
    "WhiteHouse", "POTUS", "realDonaldTrump", "PressSec", "VP",
    "USTreasury", "SecYellen", "federalreserve", "elonmusk",
    # סוכנויות ידיעות
    "AP", "Reuters", "BBCBreaking", "BBCNews", "BBCBusiness",
    "CNN", "NBCNews", "ABC", "CBSNews", "axios",
    "ReutersBiz", "ReutersTech",
]

# אנליסטים פיננסיים
FINTWIT_ANALYSTS = [
    "awealthofcs", "AswathDamodaran", "matt_levine", "EddyElfenbein", "OnlyCFO",
    "BrianFeroldi", "morganhousel", "LizAnnSonders", "fluentinfinance",
    "iancassel", "michaelbatnick", "abnormalreturns", "charliebilello", "ritholtz",
    "paulkrugman", "elerianm", "JustinWolfers", "C_Barraud",
]

# תקשורת פיננסית
MEDIA_ACCOUNTS = [
    "CNBC", "business", "WSJmarkets", "FinancialTimes", "TheEconomist",
    "Newsquawk", "unusual_whales",
]

# משקיעים מובילים
INVESTOR_ACCOUNTS = [
    "raydalio", "davidfaber", "jasonzweigwsj", "10kdiver", "benthompson",
    "OptionsHawk", "RedDogT3", "InvestorsLive",
]

# מוסדיים
INSTITUTIONAL_ACCOUNTS = [
    "blackrock", "GoldmanSachs", "MorganStanley", "stlouisfed", "morningstar",
]

# פלטפורמות / קהילות
PLATFORM_ACCOUNTS = [
    "Stocktwits", "themotleyfool", "Forbes", "grahamstephan",
    "SallieKrawcheck", "investingswede", "petermallouk",
]

# איחוד עם שמירת סדר חשיבות
ALL_ACCOUNTS = list(dict.fromkeys(
    PRIORITY_REALTIME_ACCOUNTS
    + FINTWIT_ANALYSTS
    + MEDIA_ACCOUNTS
    + INVESTOR_ACCOUNTS
    + INSTITUTIONAL_ACCOUNTS
    + PLATFORM_ACCOUNTS
))
