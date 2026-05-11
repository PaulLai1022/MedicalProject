export interface NoteSample {
  id: string;
  title: string;
  subtitle: string;
  text: string;
}

const QUICK_DEMO = `58-year-old male with type 2 diabetes presents with altered mental status, glucose 412 mg/dL, urine ketones 3+, venous pH 7.24, bicarbonate 12 mEq/L.`;

const CASE_A = `CHIEF COMPLAINT: Diabetes issue
HPI: 47-year-old male with recent diagnosis of diabetes, on Jardiance and metformin, presents to ED for 1 day history of inability to take deep breaths, sleep well, nausea, and vomiting. Denies chest pain, fever, chills, abdominal pain.

VITALS: HR 113, BP 130/92, RR 20, SpO2 95% on room air.

PHYSICAL EXAM: Alert and awake, talking in complete sentences with no acute distress. Kussmaul breathing. Lungs clear bilaterally. RRR. GCS 15.

LABS:
- Urine ketones 60 (abnormal); serum ketones LARGE
- ABG: pH 7.200 (LL), pCO2 19.4 (LL), HCO3 7.4 (L), BE -18.0
- CMP: Glucose 93 mg/dL, CO2 <7 (LL), Na 138, K 4.1, Cl 105
- Lactate 1.9, Troponin negative

ED COURSE: Differential included thyroid disorder, hyperglycemia, DKA. Patient given bicarb, 3 L NS, started on insulin drip. Discussed with hospitalist for ICU admission. Critical care time 35 minutes.

CLINICAL IMPRESSION: Euglycemic DKA
DISPOSITION: Admit to ICU`;

const CASE_B = `CHIEF COMPLAINT: Diabetes / Hyperglycemia
HPI: 34-year-old female with history of T1DM (insulin-dependent) presents via ambulance with altered mental status in the setting of elevated blood glucose. 3 days of nausea, vomiting, and weakness.

VITALS: BP 101/48, HR 100-107, RR 15-23, SpO2 99-100%, Temp 98F.

PHYSICAL EXAM: Ill-appearing. Not alert. Oriented to person only. Responds to noxious stimuli. Tachycardia present, regular rhythm. Lungs clear. No abdominal tenderness.

LABS:
- Glucose 793 mg/dL (HH); Serum Acetone LARGE
- BMP: Na 129 (L), K 4.6, Cl 93 (L), CO2 7 (LL), BUN 43 (H), Cr 1.6 (H), GFR 39
- Venous BG: pH 7.23 (L), pCO2 21 (L), HCO3 9 (L), BE -17.2 (L)
- CBC: WBC 15.7 (H), Hgb 9.1 (L), Hct 28.6 (L)
- NT-proBNP 1110 (H); Lactic acid 1.7

ED COURSE: NS 1L bolus, ondansetron, ceftriaxone 1g (empiric for possible infection), insulin drip titrated to glucose, Foley placed, POC glucose q1h. Critical care time 120 minutes.

ASSESSMENT: DKA with hyperglycemia, AKI, possible sepsis, altered mental status.
DISPOSITION: Admit to ICU/CVU`;

export const SAMPLES: NoteSample[] = [
  { id: "quick",  title: "Quick demo",          subtitle: "1-line · DKA",        text: QUICK_DEMO },
  { id: "case-a", title: "Case A · DKA",        subtitle: "ER note · reference",  text: CASE_A },
  { id: "case-b", title: "Case B · DKA + AMS",  subtitle: "ER note · evaluation", text: CASE_B },
];
