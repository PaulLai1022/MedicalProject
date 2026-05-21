# Main Change Summary

1. **Improved separation between confirmed and differential diagnoses**
   - Added the `differential_diagnoses` field.
   - Updated the extraction prompt so phrases such as `possible`, `rule out`, `concern for`, and `less likely` are classified as differential diagnoses instead of `suspected_conditions`.
   - Added backward compatibility for older LLM outputs: if `differential_diagnoses` is missing, the parser fills it with an empty list.

2. **Reduced the risk of mixing urine glucose with blood glucose**
   - Added the `urine_glucose` lab field name.
   - Updated the LLM extraction prompt to require glucose values from urinalysis contexts to use `urine_glucose`, not `glucose_mg_dl`.
   - Added verifier-side urinalysis context detection: if a `glucose_mg_dl` value comes from a urinalysis section, it is marked as failed so urine glucose is not used for hyperglycemia or HHS rules.

3. **Made lab and vital verification more tolerant of real-world note formatting**
   - Increased the verifier source-span window from 80 to 300 characters to better support ER lab tables where labels and values may be far apart.
   - Added whole-text fallback verification for labs and vitals when no regex hit is found in the local source window.
   - Added the same whole-text fallback for temperature verification.
   - Updated pH and HCO3 regex patterns to support compact formats such as `VpH7.23` and `AHCO37.4`.

4. **Reduced false-positive rule triggers from differential language**
   - Added hedge and differential marker filtering in the rules engine.
   - If a symptom description contains terms such as `possible`, `concern for`, `rule out`, or `less likely`, it is skipped when building clinical-phrase context.
   - This prevents differential diagnoses from triggering rules such as `INFECTION_TRIGGER` or `DEHYDRATION`.

5. **Tightened MCG diabetes rule logic**
   - `HYPERGLYCEMIA_GE_200` no longer triggers solely on `glucose_mg_dl >= 200`; it now also requires evidence of ketosis or acidosis.
   - `HHS_GLUCOSE_GT_600` now excludes cases with serum ketones, urine ketones, or a DKA clinical phrase.
   - Updated the corresponding citations and clinical explanations to reflect the stricter rule logic.

6. **Made generated clinical narratives more cautious**
   - Added prompt constraints telling the LLM not to use strong causal wording such as `due to`, `triggered by`, or `secondary to` unless the original note explicitly states causality.
   - Added composer post-processing: if the generated sentence uses strong causal language but the source note does not contain explicit causal wording, the sentence is softened and the change is recorded in `reasonClinical`.

7. **Synchronized API output structure**
   - Added `differentialDiagnoses` to the camelCase API output.
   - Preserved `differential_diagnoses` when converting verified facts to dictionaries.
