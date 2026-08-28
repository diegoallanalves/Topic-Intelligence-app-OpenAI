TOPICS = [
    "Forced Labor & Xinjiang",
    "Hong Kong",
    "Taiwan",
    "Human Rights & Political Repression",
    "COVID-19 & Pandemic Accountability",
    "Narcotics & Fentanyl",
    "Technology Competition, Telecom & Strategic Sectors",
    "Energy, Grid & Electrical Infrastructure",
    "Foreign Investment in the US",
    "Information & Technology Security",
    "Sanctions & Export Controls",
    "Tariffs, Trade Remedies & Market Access",
    "Supply Chain Security & Reshoring",
    "Federal Procurement & Buy American",
    "Defense, Military & Territorial Disputes",
    "Border Security & Migration",
    "Cross-Border Infrastructure",
    "USMCA & North American Trade",
    "Political / Foreign Influence",
    "Currency, Financial & Funding",
    "Appropriations Vehicles",
    "State Department & Foreign Aid",
]

ALLOWED_CONFIDENCE = {95, 85, 70, 50}

LEGAL_EFFECT_VERBS = {
    "prohibits", "prohibit", "bars", "bar", "requires", "require",
    "imposes", "impose", "levies", "levy", "authorises", "authorise",
    "authorizes", "authorize", "appropriates", "appropriate", "funds", "fund",
    "establishes", "establish", "directs", "direct", "restricts", "restrict",
    "suspends", "suspend", "withdraws", "withdraw", "designates", "designate",
    "amends", "amend", "conditions", "condition", "screens", "screen",
    "certifies", "certify", "repeals", "repeal", "waives", "waive",
    "allocates", "allocate", "maintains", "maintain",
}

BANNED_PROVISION_TERMS = {
    "daqo", "could", "may", "might", "potentially", "likely",
    "reflects", "signals", "sentiment", "risk",
}

TRAP_TERMS = [
    "transformer", "market access", "supply chain", "grid",
    "electrical equipment", "tariff",
]
