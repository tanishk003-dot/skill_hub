export type AssessmentType = 'Psychometric' | 'Behavioural' | 'Logical Thinking' | 'Reasoning' | 'Pattern Recognition' | 'Aptitude';
export type QuestionDifficulty = 'Easy' | 'Medium' | 'Hard';
export type QuestionType = 'SINGLE_CHOICE' | 'MULTI_CHOICE';

export interface QuestionOption {
  id: string;
  text: string;
}

export interface QuestionBankItem {
  id: number;
  type: AssessmentType;
  difficulty: QuestionDifficulty;
  skill_category: string;
  question_text: string;
  question_type: QuestionType;
  options: QuestionOption[];
  correct_answers?: string[];
  marks: number;
  created_at?: string;
}

export interface QuestionExamItem {
  id: number;
  question_text: string;
  question_type: QuestionType | 'CODING';
  skill_category: string;
  options?: QuestionOption[];
  marks: number;
  problem_statement?: string;
  allowed_languages?: string[];
  starter_code?: { [lang: string]: string };
  sample_test_cases?: Array<{ id: number; input: string; expected_output: string }>;
  time_limit_sec?: number;
  memory_limit_mb?: number;
}

export interface SectionCreatePayload {
  title: string;
  timer_minutes: number;
  question_ids: number[];
}

export interface AssessmentCreatePayload {
  title: string;
  type: AssessmentType;
  total_duration_minutes: number;
  passing_percentage: number;
  randomize_questions: boolean;
  randomize_options: boolean;
  sections: SectionCreatePayload[];
}

export interface SectionItem {
  id: number;
  title: string;
  order_index: number;
  timer_minutes: number;
  question_count: number;
  questions?: QuestionBankItem[];
}

export interface AssessmentItem {
  id: number;
  title: string;
  type: AssessmentType;
  total_duration_minutes: number;
  passing_percentage: number;
  randomize_questions: boolean;
  randomize_options: boolean;
  created_at: string;
  total_sections: number;
  total_questions: number;
  total_marks: number;
  sections?: SectionItem[];
}

export interface AssessmentAssignmentItem {
  id: number;
  assessment_id: number;
  assessment_title: string;
  assessment_type: AssessmentType;
  total_duration_minutes: number;
  passing_percentage: number;
  ase_id: number;
  ase_name: string;
  ase_email: string;
  assigned_by_name?: string;
  start_date: string;
  end_date: string;
  status: 'UPCOMING' | 'ACTIVE' | 'COMPLETED' | 'EXPIRED';
  attempt_id?: number;
  attempt_status?: string;
  total_score?: number;
  max_score?: number;
  percentage?: number;
  passed?: boolean;
  violation_count?: number;
  webcam_mode?: string;
}

export interface SectionExamView {
  id: number;
  title: string;
  timer_minutes: number;
  order_index: number;
  questions: QuestionExamItem[];
}

export interface ExamStartData {
  attempt_id: number;
  assessment_id: number;
  assessment_title: string;
  assessment_type: string;
  total_duration_minutes: number;
  started_at: string;
  server_time: string;
  remaining_total_seconds: number;
  sections: SectionExamView[];
  saved_responses: { [questionId: number]: string[] };
  violation_count: number;
  proctoring_debug: boolean;
  webcam_mode?: string;
  webcam_policy?: string;
  camera_no_face_seconds?: number;
  camera_multiple_faces_seconds?: number;
  camera_head_turn_seconds?: number;
  camera_grace_period_seconds?: number;
  camera_exempt?: boolean;
  camera_override_active?: boolean;
  camera_status?: string;
  accommodation_applied?: boolean;
  accommodation_notice?: string;
}

export interface ExamViolationItem {
  id: number;
  attempt_id: number;
  type: string;
  occurred_at: string;
  details?: any;
}

export interface SectionScore {
  section_id: number;
  title: string;
  score: number;
  max: number;
  percentage: number;
}

export interface QuestionReviewItem {
  question_id: number;
  section_title: string;
  question_text: string;
  question_type: QuestionType;
  skill_category: string;
  options: QuestionOption[];
  selected_options: string[];
  correct_answers: string[];
  is_correct: boolean;
  marks_obtained: number;
  max_marks: number;
}

export interface ExamResultData {
  attempt_id: number;
  assessment_id: number;
  assessment_title: string;
  ase_id: number;
  ase_name: string;
  ase_email: string;
  started_at: string;
  submitted_at?: string;
  status: string;
  total_score: number;
  max_score: number;
  percentage: number;
  passing_percentage: number;
  passed: boolean;
  section_scores: SectionScore[];
  skill_percentages: { [skill: string]: number };
  strong_areas: string[];
  weak_areas: string[];
  questions_review?: QuestionReviewItem[];
  violation_count?: number;
  auto_submit_reason?: string;
  proctoring_violations?: ExamViolationItem[];
}
