/** API response type definitions — aligned with design §5 */

export interface AuthUser {
  id: string;
  email: string;
}

export interface AuthResp {
  accessToken: string;
  user: AuthUser;
}

export interface FieldValue<T = string> {
  value: T;
  machineValue: T;
  origin: "machine" | "user";
}

export interface Sentence {
  id: string;
  text: string;
  machineText: string | null;
  origin: "machine" | "user";
  sources: string[];
  reasonClinical: string;
  reasonGuideline: string;
}

export interface McgHit {
  ruleId: string;
  category: string;
  severity: string;
  citation: string;
  clinicalExplanation: string;
  evidence: string;
}

export interface LabFactView {
  name: string;
  value: number | string;
  unit: string;
  span: [number, number];
}

export interface VitalFactView {
  name: string;
  value: number;
  unit: string;
  span: [number, number];
}

export interface SymptomFactView {
  name: string;
  description: string;
  span: [number, number];
}

export interface MedicationFactView {
  name: string;
  dose: string;
  route: string;
  span: [number, number];
}

export interface FactVerification {
  kind: "lab" | "vital";
  name: string;
  value: number | string;
  status: "verified" | "failed" | "unverifiable";
  detail: string;
}

export interface ExtractedFacts {
  chiefComplaint: string;
  hpiSummary: string;
  suspectedConditions: string[];
  labs: LabFactView[];
  vitals: VitalFactView[];
  symptoms: SymptomFactView[];
  medications: MedicationFactView[];
  imagingFindings: string[];
  interventions: string[];
  history: string[];
  verifications: FactVerification[];
}

export interface CaseStructured {
  chiefComplaint: FieldValue;
  hpiSummary: FieldValue;
  disposition: FieldValue;
  keyFindings: FieldValue<string[]>;
  suspectedConditions: FieldValue<string[]>;
  uncertainties: FieldValue<string[]>;
  revisedHPI: {
    fullText: string;
    sentences: Sentence[];
  };
  decisionPath: string;
  mcgHits: McgHit[];
  missingCoreFields: string[];
  warnings: string[];
  extractedFacts: ExtractedFacts | null;
}

export interface CaseDetail {
  id: string;
  rawText: string;
  createdAt: string;
  updatedAt: string;
  structured: CaseStructured | null;
}

export interface CaseListItem {
  id: string;
  chiefComplaintPreview: string;
  disposition: string | null;
  origin: string;
  createdAt: string;
  updatedAt: string;
}

export interface CaseListResp {
  items: CaseListItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface LlmLogItem {
  id: string;
  prompt: string;
  rawResponse: string;
  durationMs: number;
  status: string;
  model: string;
  createdAt: string;
}

export interface LlmLogResp {
  enabled: boolean;
  items: LlmLogItem[];
}
