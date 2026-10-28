"""Tests for label_match / condition_group (issue #5). Run: python3 -m unittest discover -s tools -p 'test_*.py'

Each negative case is a misfire seen in, or found while auditing, the keyword match of a condition against a label's Indications text.
"""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(__file__))
from taxonomy import condition_group, label_match

OESOPH_CANCER = "Gastric / oesophageal cancer"


class LabelMatch(unittest.TestCase):
    def test_oesophagitis_is_not_oesophageal_cancer(self):
        # the original misfire: a gastro-oesophageal reflux / erosive oesophagitis label must not count as oesophageal cancer
        label = "healing of erosive esophagitis and relief of heartburn; treatment of gastroesophageal reflux disease; Zollinger-Ellison syndrome"
        self.assertEqual(label_match(OESOPH_CANCER, label), 0)
        self.assertNotEqual(condition_group("Erosive Esophagitis"), OESOPH_CANCER)
        self.assertNotEqual(condition_group("Eosinophilic Esophagitis"), OESOPH_CANCER)

    def test_oesophageal_cancer_still_matches(self):
        self.assertEqual(label_match(OESOPH_CANCER, "treatment of patients with unresectable or metastatic esophageal squamous cell carcinoma"), 1)
        self.assertEqual(label_match(OESOPH_CANCER, "HER2-positive gastric or gastroesophageal junction (GEJ) adenocarcinoma"), 1)
        self.assertEqual(condition_group("Esophageal Squamous Cell Carcinoma"), OESOPH_CANCER)

    def test_not_indicated_clause_does_not_count(self):
        label = "TAFINLAR is indicated for melanoma with BRAF V600E. Limitations of Use: TAFINLAR is not indicated for treatment of patients with colorectal cancer because of known intrinsic resistance."
        self.assertEqual(label_match("Colorectal cancer", label), 0)
        self.assertEqual(label_match("Melanoma", label), 1)

    def test_all_is_not_leukaemia(self):
        # \ball\b matched case-insensitively against the word "all" in ordinary prose
        self.assertEqual(label_match("Leukaemia", "indicated for all adult patients with moderate to severe plaque psoriasis"), 0)
        self.assertEqual(label_match("Leukaemia", "relapsed or refractory B-cell precursor ALL in adults"), 1)
        self.assertEqual(label_match("Leukaemia", "chronic lymphocytic leukemia (CLL)"), 1)

    def test_her2_positive_gastric_is_not_breast(self):
        self.assertEqual(label_match("Breast cancer", "HER2-positive gastric or gastroesophageal junction adenocarcinoma"), 0)
        self.assertNotEqual(condition_group("HER2-positive gastric cancer"), "Breast cancer")
        self.assertEqual(label_match("Breast cancer", "adjuvant treatment of HER2-positive early breast cancer"), 1)

    def test_weight_in_prose_is_not_obesity(self):
        self.assertEqual(label_match("Obesity / weight", "pediatric patients weighing at least 25 kg; dose by body weight"), 0)
        self.assertEqual(label_match("Obesity / weight", "to reduce excess body weight and maintain weight reduction in adults with obesity"), 1)

    def test_fallback_needs_the_whole_condition(self):
        # conditions outside the groups used to match on any single word of five letters or more
        label = "moderately to severely active rheumatoid arthritis; giant cell arteritis (1.9)"
        self.assertEqual(label_match("Severe Alopecia Areata", label), 0)
        self.assertEqual(label_match("Giant Cell Arteritis (Gca)", label), 1)
        self.assertEqual(label_match("Anaplastic Astrocytoma", "locally advanced or metastatic anaplastic thyroid cancer"), 0)
        for junk in ("Metastasis", "Progression-Free Survival", "Adult Disease", "Renal Impairment", "Microsatellite Instability Low"):
            self.assertEqual(label_match(junk, "metastasis progression-free survival adult disease renal impairment microsatellite instability"), 0, junk)

    def test_word_order_plurals_and_accents(self):
        label = "treatment of ulcerative colitis; juvenile idiopathic arthritis; Waldenström's macroglobulinemia; complicated urinary tract infections (cUTI)"
        self.assertEqual(label_match("Arthritis Juvenile Idiopathic", label), 1)
        self.assertEqual(label_match("Waldenstrom Macroglobulinemia", label), 1)
        self.assertEqual(label_match("Complicated Urinary Tract Infection (Cut…", label), 1)
        self.assertEqual(label_match(condition_group("Colitis, Ulcerative"), label), 1)

    def test_diabetes_types_are_not_mixed_up(self):
        self.assertEqual(condition_group("Diabetes Mellitus, Type 1"), "Type 1 diabetes")
        self.assertEqual(condition_group("Type2 Diabetes Mellitus"), "Type 2 diabetes")
        self.assertEqual(condition_group("Diabetes Mellitus, Non-Insulin-Dependent"), "Type 2 diabetes")
        self.assertEqual(label_match("Type 1 diabetes", "glycemic control in adults with type 2 diabetes mellitus"), 0)

    def test_biomarkers_and_outcomes_are_not_conditions(self):
        label = "patients with BRCA-mutated breast cancer; metastases; mutation; progression-free survival"
        for junk in ("Brca 2 Gene Mutation", "Metastases", "Pik3Ca Mutation"):
            self.assertEqual(label_match(junk, label), 0, junk)

    def test_broad_groups_are_flagged_not_asserted(self):
        self.assertEqual(label_match("Other solid tumours", "indicated for adults with advanced renal cell carcinoma and melanoma; cancer"), 2)
        self.assertEqual(label_match("Healthy volunteers", "healthy volunteers"), 0)

    def test_empty_label(self):
        self.assertEqual(label_match("Asthma", ""), 0)


if __name__ == "__main__":
    unittest.main()
