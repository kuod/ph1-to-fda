"""Sponsor -> parent-company mapping and therapeutic-area keyword rules."""
import json, os, re

# Sponsor -> parent company. The rules live in data/sponsor_parents.json (reviewable, with an as-of date): the parent is who
# owns the sponsor of record AS OF that date, not at approval. Rules are tried in order and the first match wins.
_SPEC = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "sponsor_parents.json")))
AS_OF = _SPEC["as_of"]
PARENTS = [("|".join(p["re"] for p in r["patterns"]), r["parent"]) for r in _SPEC["rules"]]
_COMPILED = [(re.compile(p["re"]), r["parent"]) for r in _SPEC["rules"] for p in r["patterns"]]
SHORT = {"Bristol Myers Squibb": "BMS", "Johnson & Johnson": "J&J"}


GENERIC = r"\b(INC|LLC|CORP|CORPORATION|LTD|LIMITED|LP|CO|COMPANY|SA|SPA|AB|AG|AS|A/S|GMBH|BV|NV|THERAPS?|THERAPEUTICS?|PHARMS?|PHARMACEUTICALS?|PHARMA|BIOPHARMA|BIOTECH|BIOSCIENCES?|HLTHCARE|HEALTHCARE|HLTH|LABS?|LABORATORIES|USA|US|AMERICA|MEDICINES?|FARMACEUTICI|TX|IRELAND|MALTA|LUXEMBOURG|UK|DIV|DIVISION)\b"


def title(s):
    s = re.sub(r"[,.]", " ", s.upper())
    s = re.sub(GENERIC, " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.title() if s else "Unknown"


def match_rule(sponsor):
    """(parent, matching pattern) for a sponsor; pattern is None when no rule matched and the cleaned name stands in."""
    if not sponsor:
        return "Unknown", None
    up = sponsor.upper()
    for rx, par in _COMPILED:
        if rx.search(up):
            return par, rx.pattern
    return title(sponsor), None


def parent(sponsor):
    return match_rule(sponsor)[0]


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
# Indications for labels that neither openFDA nor DailyMed returned (wording follows the FDA labels).
USE_OVERRIDE = {
    "bevyxxa": "Prophylaxis of venous thromboembolism in adult patients hospitalized for an acute medical illness",
    "zulresso": "Treatment of postpartum depression in patients 15 years and older",
    "pizensy": "Treatment of chronic idiopathic constipation in adults",
    "artesunate": "Initial treatment of severe malaria in adult and pediatric patients",
}
SPONSOR_OVERRIDE = {"pepaxto": "Oncopeptides", "hovilpri": "AiCuris",
                    "hibsago": "GlaxoSmithKline",
                    "blenrep": "GlaxoSmithKline"}  # Blenrep: openFDA no longer lists the withdrawn 2020 application; GSK was the sponsor  # openFDA does not list Hibsago yet; applicant inferred (bepirovirsen is GSK's asset): confirm once openFDA catches up

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
    "alyglo": "Immunology", "kedrab": "Infectious disease", "yimmugo": "Immunology", "qivigy": "Immunology", "adzynma": "Hematology",
}
CBER_GENE = {"luxturna", "zolgensma", "itvisma", "elevidys", "skysona", "lenmeldy", "kebilidi", "otarmeni", "hemgenix", "roctavian", "beqvez",
             "zynteglo", "lyfgenia", "casgevy", "vyjuvek", "zevaskyn", "adstiladrin", "waskyra", "fayuvi", "genglycos", "papzimeos", "encelto"}
