import { PlacenameRecord } from './placename-record.model';

export type ClassificationType = 'STRONG' | 'WEAK' | 'NONE';

export interface ClassificationResult {
  id: number;
  placenameRecord: PlacenameRecord;
  classification: ClassificationType;
  evidenceSpan: string;
  classificationMethod: string;
  confidenceScore: number | null;
  llmReasoning: string | null;
  classifiedAt: string;
}

export interface ClassificationStats {
  distribution: { [key in ClassificationType]: number };
  total: number;
  regexClassified: number;
  llmClassified: number;
}
