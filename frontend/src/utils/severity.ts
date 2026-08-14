import type { FailureSeverity } from '../types/fmms';

/** Map a SAP defect-catalog DefectClass (S1..S4) to FMMS's FailureSeverity enum. */
export function severityFromDefectClass(defectClass: string): FailureSeverity {
  const value = defectClass.trim().toUpperCase();
  if (value === 'S1') return 'CRITICAL';
  if (value === 'S2') return 'HIGH';
  if (value === 'S3') return 'MEDIUM';
  return 'LOW';
}
