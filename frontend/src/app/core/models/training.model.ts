export interface ResourceItem {
  name: string;
  url?: string;
  file_path?: string;
  type: string; // link, file
}

export interface TrainingItem {
  id: number;
  title: string;
  description?: string;
  skill_category: string;
  type: string; // Self-paced, Live class, Workshop
  resources: ResourceItem[];
  duration_hours: number;
  created_by?: number;
  created_at: string;
  updated_at: string;
}

export interface TrainingCreatePayload {
  title: string;
  description?: string;
  skill_category: string;
  type: string;
  resources: ResourceItem[];
  duration_hours: number;
}

export interface TrainingAssignPayload {
  target: 'ALL' | 'COHORT' | 'SELECTED';
  cohort_id?: number;
  ase_ids?: number[];
  due_date: string; // ISO string
}

export interface TrainingAssignmentItem {
  id: number;
  training_id: number;
  training_title: string;
  training_description?: string;
  skill_category: string;
  training_type: string;
  duration_hours: number;
  resources: ResourceItem[];
  ase_id: number;
  ase_name: string;
  ase_email: string;
  cohort_id?: number;
  cohort_name?: string;
  due_date: string;
  status: 'NOT_STARTED' | 'IN_PROGRESS' | 'COMPLETED';
  progress_percent: number;
  completed_at?: string;
  is_overdue: boolean;
}

export interface SuggestedAseItem {
  ase_id: number;
  ase_name: string;
  ase_email: string;
  cohort_id?: number;
  cohort_name?: string;
  skill_category: string;
  score_percentage: number;
  reason: string;
}
