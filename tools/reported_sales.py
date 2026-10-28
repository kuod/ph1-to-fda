"""Reported full-year 2025 sales (USD millions) for drugs on the approval list, used as sourced floors under the peak-sales anchors.

Every figure was read from the document linked in SRC (checked 27 Oct 2026); nothing here comes from memory. These are company-reported
net sales for calendar 2025 and are lower bounds on global sales where a note says so (partner-booked sales, partial years, rounded figures).
Currency conversions use the rate stated beside the figure. A drug missing from this table has no verified figure and keeps its editorial
anchor or its modelled value. Add a drug here only with a figure read from its sponsor's results release, annual report or filing.
"""
SRC = {
    "LLY": ("Eli Lilly, Q4 and full-year 2025 results, 4 Feb 2026 (revenue by product table)", "https://seekingalpha.com/pr/20387250"),
    "ABBV": ("AbbVie, Q4 and full-year 2025 results, 4 Feb 2026 (key product revenues)", "https://news.abbvie.com/2026-02-04-AbbVie-Reports-Full-Year-and-Fourth-Quarter-2025-Financial-Results"),
    "GILD": ("Gilead, Q4 and full-year 2025 results, 10 Feb 2026 (text, $ billions to one decimal except Veklury and Tecartus)", "https://www.biospace.com/press-releases/gilead-sciences-announces-fourth-quarter-and-full-year-2025-financial-results"),
    "NVO": ("Novo Nordisk, FY2025 company announcement (Form 6-K): Ozempic DKK 127,089 million; USD at the document's 2025 average rate of DKK 6.62 per USD", "https://www.sec.gov/Archives/edgar/data/353278/000035327826000006/caq42025.htm"),
    "PFE": ("Pfizer, Q4 and full-year 2025 earnings release, 3 Feb 2026 (revenues by product)", "https://s206.q4cdn.com/795948973/files/doc_financials/2025/q4/Q4-2025-PFE-Earnings-Release.pdf"),
    "AZN": ("AstraZeneca, FY and Q4 2025 results, Feb 2026 (Table 3, product revenue: product sales plus alliance revenue)", "https://data.fca.org.uk/artefacts/NSM/RNS/59563de3-5a71-4031-9f0b-61dfc61dc769.html"),
    "ROG": ("Roche, 2025 results, 29 Jan 2026 (top 20 pharmaceuticals, CHF); USD at 0.8305 CHF per USD, the Federal Reserve G.5A 2025 annual average", "https://www.roche.com/media/releases/med-cor-2026-01-29"),
    "NVS": ("Novartis, Q4 and FY2025 results (Form 6-K), 4 Feb 2026 (brand net sales, USD)", "https://www.sec.gov/Archives/edgar/data/1114448/000111444826000007/a260204-99_2.htm"),
    "BMY": ("Bristol Myers Squibb, Q4 and FY2025 results (Form 8-K exhibit 99.1), Feb 2026 (worldwide product revenue)", "https://www.sec.gov/Archives/edgar/data/14272/000001427226000002/a2025q4ex991.htm"),
    "JNJ": ("Johnson & Johnson, Q4 and full-year 2025 results, 21 Jan 2026 (reported sales by product, twelve months)", "https://s203.q4cdn.com/636242992/files/doc_news/Johnson--Johnson-reports-Q4-and-Full-Year-2025-results-2026.pdf"),
    "MRK": ("Merck & Co., Q4 and full-year 2025 results, 3 Feb 2026 (worldwide sales)", "https://www.msd.com/news/merck-co-inc-rahway-n-j-usa-announces-fourth-quarter-and-full-year-2025-financial-results-highlights-progress-advancing-broad-diverse-pipeline/"),
    "AMGN": ("Amgen, Q4 and full-year 2025 results, Feb 2026 (total product sales)", "https://www.amgen.com/newsroom/press-releases/2026/02/amgen-reports-fourth-quarter-and-full-year-2025-financial-results"),
    "REGN": ("Regeneron, Q4 and full-year 2025 results, 30 Jan 2026 (Libtayo global net product sales; Dupixent global net sales as recorded by Sanofi)", "https://seekingalpha.com/pr/20382253"),
}
# id: (USD millions, SRC key, caveat or "")
REPORTED = {
    "mounjaro": (22965, "LLY", ""), "verzenio": (5723, "LLY", ""),
    "skyrizi": (17562, "ABBV", ""), "rinvoq": (8304, "ABBV", ""), "ubrelvy": (1271, "ABBV", ""), "qulipta": (1036, "ABBV", ""),
    "biktarvy": (14300, "GILD", "rounded to $0.1B"), "veklury": (911, "GILD", ""), "yescarta": (1500, "GILD", "rounded to $0.1B"),
    "tecartus": (344, "GILD", ""), "trodelvy": (1400, "GILD", "rounded to $0.1B"),
    "ozempic": (19198, "NVO", "converted from DKK"),
    "vyndaqel": (6380, "PFE", "Vyndaqel family (Vyndaqel, Vyndamax, Vynmac)"), "paxlovid": (2362, "PFE", ""),
    "comirnaty": (4367, "PFE", "Pfizer-recorded revenue; excludes BioNTech's separately recorded share, so a lower bound"),
    "nurtec-odt": (1424, "PFE", "Nurtec ODT/Vydura"), "abrysvo": (1033, "PFE", ""), "lorbrena": (1023, "PFE", ""), "tukysa": (463, "PFE", ""),
    "elrexfio": (304, "PFE", ""), "cibinqo": (284, "PFE", ""), "tivdak": (147, "PFE", ""),
    "imfinzi": (6063, "AZN", ""), "calquence": (3518, "AZN", ""), "wainua": (212, "AZN", "AstraZeneca-recorded; global sales are not stated, so a lower bound"),
    "enhertu": (2775, "AZN", "AstraZeneca-recorded (includes $1,798M alliance revenue); global sales are not stated, so a lower bound"),
    "ocrevus": (8441, "ROG", "CHF 7,010M converted"), "vabysmo": (4939, "ROG", "CHF 4,102M converted"), "evrysdi": (2116, "ROG", "CHF 1,757M converted"),
    "polivy": (1770, "ROG", "CHF 1,470M converted"), "xofluza": (490, "ROG", "CHF 407M converted; Roche-recorded"),
    "kisqali": (4783, "NVS", ""), "leqvio": (1198, "NVS", ""), "scemblix": (1285, "NVS", ""), "zolgensma": (1232, "NVS", "Zolgensma group"),
    "kymriah": (381, "NVS", ""),
    "reblozyl": (2327, "BMY", ""), "camzyos": (1068, "BMY", ""), "breyanzi": (1358, "BMY", ""), "zeposia": (577, "BMY", ""), "abecma": (427, "BMY", ""),
    "krazati": (205, "BMY", ""), "cobenfy": (155, "BMY", ""), "sotyktu": (291, "BMY", ""),
    "erleada": (3574, "JNJ", ""), "rybrevant": (734, "JNJ", "Rybrevant/Lazcluze"), "carvykti": (1887, "JNJ", ""), "talvey": (463, "JNJ", ""),
    "tecvayli": (670, "JNJ", ""), "caplyta": (700, "JNJ", "J&J-recorded since its 2025 acquisition of Intra-Cellular, so a partial year and a lower bound"),
    "winrevair": (1443, "MRK", ""), "capvaxive": (759, "MRK", ""), "welireg": (716, "MRK", ""),
    "ohtuvayre": (178, "MRK", "Merck-recorded since the 7 Oct 2025 Verona acquisition: about one quarter, so a lower bound"),
    "tezspire": (1478, "AMGN", "Amgen-recorded sales only; global sales are not stated, so a lower bound"),
    "evenity": (2100, "AMGN", ""), "tepezza": (1903, "AMGN", ""), "lumakras": (363, "AMGN", ""),
    "dupixent": (17807, "REGN", "global net sales as recorded by Sanofi"), "libtayo": (1453, "REGN", ""),
}
