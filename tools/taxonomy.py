"""Sponsor -> parent-company mapping and therapeutic-area keyword rules."""
import re

# (regex on openFDA sponsor_name, parent as of Oct 2026). First match wins.
PARENTS = [
    (r"PFIZER|WYETH|SEAGEN|SEATTLE GEN|ARRAY BIO|MEDIVATION|ARENA PHARM|BIOHAVEN|GLOBAL BLOOD|HOSPIRA", "Pfizer"),
    (r"MERCK SHARP|^MSD\b|MSD MERCK|SCHERING|^MERCK AND CO|MERCK CO\b|ACCELERON|PROMETHEUS", "Merck & Co."),
    (r"NOVARTIS|^AAA\b|ADVANCED ACCELERATOR|AVEXIS|ENDOCYTE|CHINOOK|TOURMALINE", "Novartis"),
    (r"GENENTECH|HOFFMANN|ROCHE|CHUGAI|SPARK THERAP|FOUNDATION MEDICINE|89BIO", "Roche"),
    (r"ASTRAZENECA|ALEXION|MEDIMMUNE|PORTOLA|ACERTA|ZS PHARMA|AMPLIMMUNE|FUSION PHARM", "AstraZeneca"),
    (r"GLAXOSMITHKLINE|^GSK|TESARO|VIIV|BELLUS", "GSK"),
    (r"SANOFI|GENZYME|ABLYNX|PRINCIPIA|BIOVERATIV|KYMAB|PROVENTION|AVENTIS", "Sanofi"),
    (r"ELI LILLY|\bLILLY\b|LOXO|\bDICE\b|MORPHIC|POSEIDA|SIGILON|\bVERVE\b", "Eli Lilly"),
    (r"BRISTOL|CELGENE|\bJUNO\b|MIRATI|KARUNA|TURNING POINT|RAYZEBIO|MYOKARDIA|\bBMS\b", "Bristol Myers Squibb"),
    (r"JANSSEN|JOHNSON|ACTELION|MOMENTA|INTRA.?CELLULAR|ABIOMED|ARAGON|CILAG", "Johnson & Johnson"),
    (r"ABBVIE|ALLERGAN|PHARMACYCLICS|CEREVEL|IMMUNOGEN|STEMCENTRX", "AbbVie"),
    (r"AMGEN|HORIZON THERAP|HORIZON PHARMA|CHEMOCENTRYX|ONYX|KAI PHARM|FIVE PRIME", "Amgen"),
    (r"TAKEDA|SHIRE|MILLENNIUM|BAXALTA|NIMBUS|TIGENIX|ARIAD", "Takeda"),
    (r"GILEAD|KITE|IMMUNOMEDICS|FORTY SEVEN|CYMABAY|TIZONA", "Gilead Sciences"),
    (r"NOVO NORDISK|^NOVO\b", "Novo Nordisk"),
    (r"BAYER|ASKBIO", "Bayer"),
    (r"BOEHRINGER", "Boehringer Ingelheim"),
    (r"REGENERON", "Regeneron"),
    (r"VERTEX", "Vertex"),
    (r"ASTELLAS|IVERIC|AUDENTES|POTENZA|XYPHOS", "Astellas"),
    (r"DAIICHI", "Daiichi Sankyo"),
    (r"BIOGEN|REATA|HI BIO", "Biogen"),
    (r"EISAI", "Eisai"),
    (r"OTSUKA|AVANIR|ASTEX", "Otsuka"),
    (r"\bUCB\b|ZOGENIX|\bRA PHARM", "UCB"),
    (r"SUMITOMO|SUNOVION|MYOVANT|URO?VANT|DAINIPPON", "Sumitomo Pharma"),
    (r"KYOWA|ORCHARD THERAP", "Kyowa Kirin"),
    (r"EMD SERONO|MERCK KGAA|MERCK KGA", "Merck KGaA"),
    (r"BEONE|BEIGENE", "BeOne Medicines"),
    (r"^MODERNA", "Moderna"),
    (r"OCTAPHARMA", "Octapharma"),
    (r"^GE\b|GE HEALTHCARE", "GE HealthCare"),
    (r"^CSL", "CSL Behring"),
    (r"^GC\b|GC BIOPHARMA", "GC Biopharma"),
    (r"^LFB", "LFB"),
    (r"BIONTECH", "BioNTech"),
    (r"IONIS|AKCEA", "Ionis"),
    (r"TEVA|ACTAVIS", "Teva"),
    (r"^SERVIER", "Servier"),
    (r"ALCON|AERIE", "Alcon"),
    (r"LEO PHARMA", "LEO Pharma"),
    (r"VIATRIS|MYLAN", "Viatris"),
    (r"BAUSCH|VALEANT|SALIX", "Bausch Health"),
]
SHORT = {"Bristol Myers Squibb": "BMS", "Johnson & Johnson": "J&J"}


GENERIC = r"\b(INC|LLC|CORP|CORPORATION|LTD|LIMITED|LP|CO|COMPANY|SA|SPA|AB|AG|AS|A/S|GMBH|BV|NV|THERAPS?|THERAPEUTICS?|PHARMS?|PHARMACEUTICALS?|PHARMA|BIOPHARMA|BIOTECH|BIOSCIENCES?|HLTHCARE|HEALTHCARE|HLTH|LABS?|LABORATORIES|USA|US|AMERICA|MEDICINES?|FARMACEUTICI|TX|IRELAND|MALTA|LUXEMBOURG|UK|DIV|DIVISION)\b"


def title(s):
    s = re.sub(r"[,.]", " ", s.upper())
    s = re.sub(GENERIC, " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.title() if s else "Unknown"


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
    "givlaari": "Metabolic & Endocrine",     "xenpozyme": "Metabolic & Endocrine", "xdemvy": "Ophthalmology", "xolremdi": "Immunology", "voquezna": "Gastroenterology",
    "inqovi": "Oncology", "lumvoa": "Ophthalmology", "scenesse": "Dermatology", "lisraya": "Immunology", "seysara": "Dermatology",
    "symproic": "Gastroenterology", "lucemyra": "Psychiatry", "exem-foam-kit": "Diagnostic imaging", "brexafemme": "Infectious disease",
    "vivjoa": "Infectious disease", "byfavo": "Pain & Anesthesia", "imfinzi": "Oncology", "pluvicto": "Oncology",
    "crenessity": "Metabolic & Endocrine", "defencath": "Infectious disease", "zaynich": "Infectious disease", "utebzi": "Infectious disease",
    "jesduvroq": "Hematology", "xenoview": "Diagnostic imaging", "attruby": "Cardiovascular",
    "tzield": "Metabolic & Endocrine", "gallium-ga-68-gozetotide": "Diagnostic imaging",
}
SPONSOR_OVERRIDE = {"pepaxto": "Oncopeptides", "hovilpri": "AiCuris",
                    "hibsago": "GlaxoSmithKline"}  # openFDA does not list Hibsago yet; applicant inferred (bepirovirsen is GSK's asset): confirm once openFDA catches up

# Condition strings from ClinicalTrials.gov are messy; fold the common ones into disease groups for the product-pipeline view.
COND_GROUPS = [
    ("Non-small cell lung cancer", r"non.?small|nsclc|lung adenocarcinoma|lung squamous"),
    ("Small cell lung cancer", r"small.?cell lung|sclc"),
    ("Lung cancer (other)", r"lung|bronch|thoracic"),
    ("Melanoma", r"melanoma"),
    ("Breast cancer", r"breast|her2.positive"),
    ("Prostate cancer", r"prostat"),
    ("Colorectal cancer", r"colorectal|colon|rectal"),
    ("Gastric / oesophageal cancer", r"(gastric|stomach|oesophag\w*|esophag\w*|gastro.?oesophageal|gej)\W+(\w+\W+){0,3}(cancer|carcinoma|adenocarcinoma|tumou?r|neoplasm)|gastric cancer|\bgej\b"),
    ("Liver cancer", r"hepatocellular|liver cancer|\bhcc\b|biliary|cholangio"),
    ("Pancreatic cancer", r"pancrea"),
    ("Kidney cancer", r"renal cell|kidney cancer|\brcc\b"),
    ("Bladder / urothelial cancer", r"bladder|urothel"),
    ("Head and neck cancer", r"head and neck|hnscc|nasopharyn|oral cavity|laryn"),
    ("Cervical / endometrial / ovarian cancer", r"cervi|endometri|ovarian|fallopian|uterine|vulvar|gynecolog"),
    ("Lymphoma", r"lymphoma|hodgkin|\bdlbcl\b"),
    ("Multiple myeloma", r"myeloma"),
    ("Leukaemia", r"leuk|\bcll\b|\baml\b|\ball\b|myelodysplas|myelofibrosis|myeloproliferative"),
    ("Brain / CNS tumours", r"glioma|glioblastoma|brain tumou?r|meningioma|neuroblastoma"),
    ("Other solid tumours", r"cancer|carcinoma|tumou?r|neoplasm|sarcoma|malignan|mesothelioma|thymic|skin cancer|merkel|basal cell|cutaneous squamous"),
    ("Rheumatoid arthritis", r"rheumatoid"),
    ("Psoriasis / psoriatic arthritis", r"psoria"),
    ("Spondyloarthritis", r"spondyl"),
    ("Atopic dermatitis / eczema", r"atopic|eczema"),
    ("Asthma", r"asthma"),
    ("COPD", r"copd|chronic obstructive"),
    ("Crohn's / ulcerative colitis", r"crohn|ulcerative colitis|inflammatory bowel|\bibd\b"),
    ("Lupus", r"lupus"),
    ("Type 2 diabetes", r"type 2 diabetes|type ii diabetes|t2dm|diabetes mellitus, type 2"),
    ("Type 1 diabetes", r"type 1 diabetes|type i diabetes|t1dm"),
    ("Obesity / weight", r"obes|overweight|weight"),
    ("Heart failure", r"heart failure"),
    ("Hypertension / cardiovascular risk", r"hypertens|cardiovascular|myocardial|atrial|stroke|coronary"),
    ("Chronic kidney disease", r"kidney disease|renal insufficiency|nephro|\bckd\b"),
    ("Multiple sclerosis", r"multiple sclerosis"),
    ("Migraine", r"migraine|headache"),
    ("Alzheimer's / dementia", r"alzheimer|dementia"),
    ("Epilepsy / seizures", r"epilep|seizure"),
    ("Depression / anxiety", r"depress|anxiety"),
    ("Schizophrenia / bipolar", r"schizo|bipolar"),
    ("HIV", r"\bhiv\b|human immunodeficiency"),
    ("Hepatitis", r"hepatitis"),
    ("COVID-19", r"covid|sars-cov"),
    ("Cystic fibrosis", r"cystic fibrosis"),
    ("Healthy volunteers", r"healthy|volunteer"),
]


def condition_group(c):
    c = (c or "").strip()
    for name, rx in COND_GROUPS:
        if re.search(rx, c, re.I):
            return name
    return (c[:40] + "…" if len(c) > 40 else c).title() or "Unspecified"


# CBER products: area by hand (indications are short and specific); modality by product class.
CBER_TA = {
    "luxturna": "Ophthalmology", "encelto": "Ophthalmology", "zolgensma": "Neurology", "itvisma": "Neurology", "elevidys": "Neurology",
    "skysona": "Neurology", "lenmeldy": "Neurology", "kebilidi": "Neurology", "otarmeni": "Neurology",
    "hemgenix": "Hematology", "roctavian": "Hematology", "beqvez": "Hematology", "zynteglo": "Hematology", "lyfgenia": "Hematology",
    "casgevy": "Hematology", "omisirge": "Hematology", "regenecyte": "Hematology", "tregzi": "Hematology",
    "hpc-cord-blood-md-anderson-cord-blood-bank": "Hematology",
    "vyjuvek": "Dermatology", "zevaskyn": "Dermatology", "stratagraft": "Dermatology", "maci": "Musculoskeletal",
    "adstiladrin": "Oncology", "kymriah": "Oncology", "tecartus": "Oncology", "breyanzi": "Oncology", "aucatzyl": "Oncology", "yescarta": "Oncology", "abecma": "Oncology", "carvykti": "Oncology", "amtagvi": "Oncology", "tecelra": "Oncology", "rethymic": "Immunology", "waskyra": "Immunology",
    "ryoncil": "Immunology", "lantidra": "Metabolic & Endocrine", "genglycos": "Metabolic & Endocrine",
    "symvess": "Cardiovascular", "papzimeos": "Respiratory",
    # blood and plasma products
    "rebinyn": "Hematology", "fibryga": "Hematology", "andexxa": "Hematology", "jivi": "Hematology", "esperoct": "Hematology",
    "sevenfact": "Hematology", "ryplazim": "Hematology", "altuviiio": "Hematology", "balfaxar": "Hematology", "fesilty": "Hematology",
    "haegarda": "Immunology", "panzyga": "Immunology", "cutaquig": "Immunology", "asceniv": "Immunology", "xembify": "Immunology",
    "alyglo": "Immunology", "kedrab": "Infectious disease",
}
CBER_GENE = {"luxturna", "zolgensma", "itvisma", "elevidys", "skysona", "lenmeldy", "kebilidi", "otarmeni", "hemgenix", "roctavian", "beqvez",
             "zynteglo", "lyfgenia", "casgevy", "vyjuvek", "zevaskyn", "adstiladrin", "waskyra", "fayuvi", "genglycos", "papzimeos", "encelto"}
