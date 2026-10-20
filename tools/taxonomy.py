"""Sponsor -> parent-company mapping and therapeutic-area keyword rules."""
import re

# (regex on openFDA sponsor_name, parent as of Oct 2026). First match wins.
PARENTS = [
    (r"PFIZER|WYETH|SEAGEN|SEATTLE GEN|ARRAY BIO|MEDIVATION|ARENA PHARM|BIOHAVEN|GLOBAL BLOOD|HOSPIRA", "Pfizer"),
    (r"MERCK SHARP|^MSD|MSD MERCK|SCHERING|ORGANON|^MERCK AND CO|MERCK CO|ACCELERON|PROMETHEUS", "Merck & Co."),
    (r"NOVARTIS|^AAA\b|ADVANCED ACCELERATOR|AVEXIS|ENDOCYTE|CHINOOK|TOURMALINE", "Novartis"),
    (r"GENENTECH|HOFFMANN|ROCHE|CHUGAI|SPARK THERAP|FOUNDATION MEDICINE|89BIO", "Roche"),
    (r"ASTRAZENECA|ALEXION|MEDIMMUNE|PORTOLA|ACERTA|ZS PHARMA|AMPLIMMUNE|FUSION PHARM", "AstraZeneca"),
    (r"GLAXOSMITHKLINE|^GSK|TESARO|VIIV|BELLUS", "GSK"),
    (r"SANOFI|GENZYME|ABLYNX|PRINCIPIA|BIOVERATIV|KYMAB|PROVENTION|AVENTIS", "Sanofi"),
    (r"ELI LILLY|LILLY|LOXO|DICE|MORPHIC|POSEIDA|SIGILON|VERVE", "Eli Lilly"),
    (r"BRISTOL|CELGENE|JUNO|MIRATI|KARUNA|TURNING POINT|RAYZEBIO|MYOKARDIA|FIVE PRIME|FOREBIO|CELLULAR BIO|ORIC|BMS", "Bristol Myers Squibb"),
    (r"JANSSEN|JOHNSON|ACTELION|MOMENTA|INTRA.?CELLULAR|ABIOMED|ARAGON|XENCOR|CILAG", "Johnson & Johnson"),
    (r"ABBVIE|ALLERGAN|PHARMACYCLICS|CEREVEL|IMMUNOGEN|STEMCENTRX|AERIE|ELEVEN BIO", "AbbVie"),
    (r"AMGEN|HORIZON|CHEMOCENTRYX|ONYX|KAI PHARM", "Amgen"),
    (r"TAKEDA|SHIRE|MILLENNIUM|BAXALTA|NIMBUS|MARATHON|TIGENIX|ARIAD", "Takeda"),
    (r"GILEAD|KITE|IMMUNOMEDICS|FORTY SEVEN|CYMABAY|TIZONA", "Gilead Sciences"),
    (r"NOVO", "Novo Nordisk"),
    (r"BAYER|ASKBIO", "Bayer"),
    (r"BOEHRINGER", "Boehringer Ingelheim"),
    (r"REGENERON", "Regeneron"),
    (r"VERTEX", "Vertex"),
    (r"ASTELLAS|IVERIC|AUDENTES|POTENZA|XYPHOS", "Astellas"),
    (r"DAIICHI", "Daiichi Sankyo"),
    (r"BIOGEN|REATA|HI BIO", "Biogen"),
    (r"EISAI", "Eisai"),
    (r"OTSUKA|LUNDBECK|AVANIR|ASTEX|VISTAGEN", "Otsuka"),
    (r"UCB|ZOGENIX|RA PHARM", "UCB"),
    (r"SUMITOMO|SUNOVION|MYOVANT|URO?VANT|DAINIPPON|SUMITOMO DAI", "Sumitomo Pharma"),
    (r"KYOWA|ARDELYX|ORCHARD", "Kyowa Kirin"),
    (r"EMD SERONO|MERCK KGAA|MERCK KGA", "Merck KGaA"),
    (r"BEONE|BEIGENE", "BeOne Medicines"),
    (r"IONIS|AKCEA", "Ionis"),
    (r"TEVA|ACTAVIS", "Teva"),
    (r"SERVIER|AGIOS", "Servier"),
    (r"ALCON|NOVARTIS ALCON", "Alcon"),
    (r"LEO PHARMA|CELLTRION", "LEO Pharma"),
    (r"VIATRIS|MYLAN", "Viatris"),
    (r"BAUSCH|VALEANT|SALIX|BAUSCH HLTH", "Bausch Health"),
    (r"DR REDDY|SUN PHARMA|CIPLA|LUPIN", "Indian generics"),
]
SHORT = {"Bristol Myers Squibb": "BMS", "Johnson & Johnson": "J&J"}


def title(s):
    s = re.sub(r"\b(INC|LLC|CORP|LTD|LP|CO|THERAPS?|THERAP|PHARMS?|PHARMACEUTICALS?|HLTHCARE|USA|US|AMERICA)\b\.?", "", s.upper())
    s = re.sub(r"\s+", " ", s).strip(" ,.")
    return s.title().replace("Pharm", "Pharma") if s else "Unknown"


def parent(sponsor):
    if not sponsor:
        return "Unknown"
    for rx, p in PARENTS:
        if re.search(rx, sponsor.upper()):
            return p
    return title(sponsor)


# Therapeutic areas: ordered rules; text = indication + label + pharm class + ingredient. Highest score wins.
TA = [
    ("Oncology", r"cancer|carcinoma|tumou?r|leuk[a]?emia|lymphoma|myeloma|melanoma|sarcoma|neoplasm|malignan|glioma|blastoma|myelofibrosis|myelodysplastic|metasta|kinase inhibitor|antineoplastic|CAR T|mesothelioma|polycythemia|mastocytosis|\bNSCLC\b|\bAML\b|\bCLL\b"),
    ("Hematology", r"hemophilia|thrombocytop|anemia|sickle|hemoglobin|neutropenia|thrombo|coagul|iron deficiency|PNH|hemolytic|factor (VII|VIII|IX)|myelofibrosis|von willebrand|anticoagul|hereditary angioedema|complement"),
    ("Neurology", r"epilep|seizure|migraine|parkinson|alzheimer|multiple sclerosis|neuromyelitis|myasthenia|huntington|amyotrophic|spinal muscular|neuropath|dyskinesia|narcolepsy|insomnia|restless|tardive|rett|friedreich|duchenne|CGRP|dementia|neurolog|cataplexy|spasticity|cerebral|neurodegen|myotonic|dravet|lennox|polyneuropathy|amyloidosis"),
    ("Psychiatry", r"schizophren|depress|bipolar|anxiety|ADHD|attention deficit|psych|agitation|opioid use|alcohol|smoking|postpartum|binge|opioid withdrawal|sedation"),
    ("Infectious disease", r"infection|bacteri|virus|viral|HIV|hepatitis|influenza|COVID|SARS|fung|malaria|tubercul|antibiotic|antimicrobial|sepsis|pneumonia|CMV|cytomegalovirus|smallpox|anthrax|ebola|RSV|clostridi|herpes|parasit|chagas|onchocerc|helminth|lice|scabies|antibacterial|antiviral|antifungal|worm"),
    ("Immunology", r"arthritis|psoria|lupus|atopic|dermatitis|crohn|ulcerative colitis|inflammatory|autoimmun|spondyl|uveitis|eosinophil|vasculitis|asthma|urticaria|sjogren|graft|transplant|immunosuppress|IL-\d|interleukin|JAK|alopecia areata|hidradenitis|prurigo|sclerosis"),
    ("Cardiovascular", r"heart|cardi|hypertension|atrial|angina|lipid|cholesterol|LDL|hypertriglycer|thromboembol|stroke|pulmonary arterial|(?<!neo)\bvascular|hyperkalemia|edema|anticoag|myocard|blood pressure|hypotension|PCSK9"),
    ("Metabolic & Endocrine", r"diabet|obes|weight|glucose|insulin|GLP|thyroid|growth hormone|acromegaly|cushing|hypoparathyroid|osteoporosis|hypophosphat|phenylketon|lipodystrophy|hyperinsulin|hypoglyc|NASH|steatohepat|porphyria|gout|hyperuric|homocystin|testosterone|endocrin|calcium|cystinosis|fabry|gaucher|pompe|mucopolysacch|lysosomal|urea cycle|hyperoxaluria|metabolic|enzyme replacement|acid sphingomyelinase|wilson|hypercortisol"),
    ("Respiratory", r"cystic fibrosis|COPD|pulmonary|asthma|bronch|respiratory|idiopathic pulmonary|cough|lung"),
    ("Gastroenterology", r"gastro|bowel|constipation|diarrhea|colitis|hepat|liver|biliary|cholangitis|pancrea|reflux|nausea|vomiting|cholestasis|crohn|short bowel|gallstone|ulcer|colon|GERD|bowel prep|cholestatic"),
    ("Dermatology", r"acne|rosacea|psoria|dermat|skin|alopecia|hyperhidrosis|actinic|wound|epidermolysis|vitiligo|hidradenitis|wrinkle|glabellar|cosmetic|prurigo|topical"),
    ("Ophthalmology", r"ocular|\beye|retina|macular|neovascular|glaucoma|dry eye|uveitis|ophthalm|myopia|presbyopia|cornea|keratitis|conjunctiv|thyroid eye"),
    ("Renal & Urology", r"kidney|renal|nephr|dialysis|bladder|urinary|prostat|IgA|hyperphosphat|overactive|erectile|hyperkal|uremic|pruritus associated with CKD|lupus nephritis"),
    ("Women's health", r"contracepti|menopaus|endometriosis|vasomotor|uterine|fibroid|vaginal|postpartum|hypoactive sexual|preterm|labor|ovarian stim|fertility|dyspareunia"),
    ("Musculoskeletal", r"osteo|bone|muscle|achondroplasia|fibrodysplasia|fracture|tendon|cartilage|myopathy|dystrophy|skeletal|arthropathy"),
    ("Pain & Anesthesia", r"pain|analges|anesthe|opioid|neuromuscular block|local anesth"),
    ("Diagnostic imaging", r"diagnostic|PET\b|positron|imaging|radioactive diagnostic|contrast|F 18|F-18|Ga 68|Ga-68|Cu 64|Tc 99|fluorescence|visualization|optical imaging|MRI|ultrasound"),
]
MODALITY = [
    ("Antibody / ADC", r"mab\b|mab-|-mab"),
    ("Oligonucleotide / siRNA", r"sen\b|rsen|siran|vutrisiran|patisiran|givosiran|lumasiran|inclisiran|nusinersen|eplontersen|olezarsen|plozasiran|olezarsen|\bpegcetacoplan|-siran|-sen$|golodirsen|viltolarsen|casimersen|eteplirsen|inotersen|tofersen"),
    ("Peptide / protein", r"ase\b|-ase|cept\b|-cept|tide\b|-tide|insulin|pegvaliase|peptide|glutide|relin|rin\b|cog|alfa|beta|octocog|factor|toxin|botulinum"),
]

# Hand-assigned areas where FDA/openFDA text was missing or ambiguous.
TA_OVERRIDE = {
    "xadago": "Neurology", "bavencio": "Oncology", "austedo": "Neurology", "bevyxxa": "Hematology", "aliqopa": "Oncology",
    "verzenio": "Oncology", "xepi": "Dermatology", "ilumya": "Immunology", "olumiant": "Immunology", "poteligeo": "Oncology",
    "annovera": "Women's health", "takhzyro": "Immunology", "lumoxiti": "Oncology", "tegsedi": "Neurology", "revcovi": "Immunology",
    "aemcolo": "Infectious disease", "gamifant": "Immunology", "firdapse": "Neurology", "xospata": "Oncology", "egaten": "Infectious disease",
    "zulresso": "Psychiatry", "nubeqa": "Oncology", "rozlytrek": "Oncology", "gallium-ga-68-edotreotide": "Diagnostic imaging",
    "brukinsa": "Oncology", "tissueblue": "Ophthalmology", "ubrelvy": "Neurology", "ayvakit": "Oncology", "tepezza": "Ophthalmology",
    "pizensy": "Gastroenterology", "tukysa": "Oncology", "retevmo": "Oncology", "artesunate": "Infectious disease", "uplizna": "Neurology",
    "zepzelca": "Oncology", "dojolvi": "Metabolic & Endocrine", "xeglyze": "Dermatology", "evrysdi": "Neurology",
    "zokinvy": "Metabolic & Endocrine", "nulibry": "Metabolic & Endocrine", "nextstellis": "Women's health", "welireg": "Oncology",
    "nexobrid": "Dermatology", "joenja": "Immunology", "aqneursa": "Neurology", "gomekli": "Oncology", "kygevvi": "Neurology",
    "redemplo": "Metabolic & Endocrine", "zycubo": "Metabolic & Endocrine", "loargys": "Metabolic & Endocrine",
    "simtriyo": "Psychiatry", "zanvastro": "Neurology", "emcitate": "Metabolic & Endocrine",
    "brineura": "Neurology", "polivy": "Oncology", "padcev": "Oncology", "bylvay": "Gastroenterology", "lamzede": "Metabolic & Endocrine",
    "skyclarys": "Neurology", "litfulo": "Dermatology", "zelsuvmi": "Dermatology", "miplyffa": "Neurology", "iomervu": "Diagnostic imaging",
    "tryngolza": "Metabolic & Endocrine", "nuzolvence": "Infectious disease", "danyelza": "Oncology", "lutathera": "Oncology",
    "givlaari": "Metabolic & Endocrine",
}
SPONSOR_OVERRIDE = {"pepaxto": "Oncopeptides", "hovilpri": "AiCuris"}
