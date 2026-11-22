export interface ClassTranscript {
  id: number;
  live_class_id?: number;
  training_id?: number;
  uploaded_by?: number;
  topics_covered?: string;
  file_name?: string;
  file_type?: string;
  token_count: number;
  used_token_count: number;
  truncated_ratio: number;
  raw_text_present: boolean;
  expires_at?: string;
  created_at: string;
}

export interface KeyConcept {
  concept: string;
  explanation: string;
}

export interface ClassSummary {
  id: number;
  transcript_id?: number;
  live_class_id?: number;
  training_id?: number;
  key_topics: string[];
  key_concepts: KeyConcept[];
  practical_examples: string[];
  ase_recap: string;
  suggested_homework: string[];
  is_published: boolean;
  published_at?: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface AssessmentPlan {
  recommended_total_questions: number;
  difficulty_split: { [key: string]: number };
  topic_split: { [key: string]: number };
}

export interface AIGeneratedQuestion {
  id: number;
  ai_assessment_id: number;
  question_bank_id?: number;
  question_type: string;
  skill_category: string;
  difficulty: string;
  question_text: string;
  options: string[];
  correct_answers: string[];
  explanation: string;
  source: string;
  review_status: string; // PENDING, APPROVED, REJECTED
  mentor_verify_required: boolean;
  quality_flags: string[];
  created_at: string;
}

export interface AIGeneratedAssessment {
  id: number;
  live_class_id?: number;
  training_id?: number;
  title: string;
  generation_mode: string;
  status: string;
  recommended_total_questions: number;
  difficulty_split: { [key: string]: number };
  topic_split: { [key: string]: number };
  is_immutable: boolean;
  version: number;
  assessment_id?: number;
  questions: AIGeneratedQuestion[];
  created_at: string;
}

export interface MissedConcept {
  concept: string;
  score: number;
  reason: string;
}

export interface FollowUpProposal {
  title: string;
  duration_minutes: number;
  topics: string[];
  recommended_audience: string;
  suggested_agenda?: string[];
}

export interface ClassEffectivenessReport {
  has_enough_data: boolean;
  total_attempts: number;
  topic_scores: { [key: string]: number };
  missed_concepts: MissedConcept[];
  suggested_revision_topics: string[];
  follow_up_proposal: FollowUpProposal;
  message?: string;
}
