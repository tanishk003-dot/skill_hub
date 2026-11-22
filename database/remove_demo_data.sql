-- ============================================================================
-- L&K Skill Hub - Remove Demo Seed Data Script (Phases 1 - 12)
-- Deletes all demo records marked with is_demo = 1 / TRUE
-- while preserving administrative accounts and production system configuration.
-- ============================================================================

-- 0.0000 Phase 12 Buddy System & Doubt Forum
DELETE FROM forum_rate_limits WHERE user_id IN (SELECT id FROM users WHERE is_demo = 1);
DELETE FROM forum_filter_audit_logs WHERE user_id IN (SELECT id FROM users WHERE is_demo = 1);
DELETE FROM forum_identity_audit_logs WHERE viewer_id IN (SELECT id FROM users WHERE is_demo = 1);
DELETE FROM forum_reports WHERE reporter_id IN (SELECT id FROM users WHERE is_demo = 1);
DELETE FROM forum_votes WHERE user_id IN (SELECT id FROM users WHERE is_demo = 1);
DELETE FROM forum_answers WHERE is_demo = 1;
DELETE FROM forum_posts WHERE is_demo = 1;
DELETE FROM buddy_milestones WHERE buddy_id IN (SELECT id FROM users WHERE is_demo = 1);
DELETE FROM buddy_ratings WHERE rated_by_id IN (SELECT id FROM users WHERE is_demo = 1);
DELETE FROM buddy_pairings WHERE is_demo = 1;

-- 0.000 Phase 11 Analytics, 1-on-1s, Reporting Tokens & Staffing Projects
DELETE FROM staffing_project_skills WHERE project_id IN (SELECT id FROM staffing_projects WHERE is_demo = 1);
DELETE FROM staffing_projects WHERE is_demo = 1;
DELETE FROM reporting_token_audit_logs WHERE token_id IN (SELECT id FROM reporting_api_tokens WHERE is_demo = 1);
DELETE FROM reporting_api_tokens WHERE is_demo = 1;
DELETE FROM one_on_one_comments WHERE is_demo = 1;
DELETE FROM one_on_one_action_items WHERE is_demo = 1;
DELETE FROM one_on_one_goals WHERE is_demo = 1;
DELETE FROM one_on_one_meetings WHERE is_demo = 1;
DELETE FROM question_item_analytics WHERE is_demo = 1;

-- 0.00 Phase 10 Webcam Proctoring & Accommodations
DELETE FROM accommodation_audit_logs WHERE is_demo = 1;
DELETE FROM accommodation_requests WHERE is_demo = 1;
DELETE FROM webcam_audit_logs WHERE is_demo = 1;
DELETE FROM webcam_proctoring_snapshots WHERE is_demo = 1;
DELETE FROM camera_override_logs WHERE is_demo = 1;
DELETE FROM camera_heartbeats WHERE is_demo = 1;
DELETE FROM camera_handshakes WHERE is_demo = 1;
DELETE FROM webcam_consents WHERE is_demo = 1;

-- 0.0 Phase 9 WOW Pack (Readiness, Gamification, Certificates, Milestones, Mock Interview)
DELETE FROM mock_interview_rate_logs WHERE ase_id IN (SELECT id FROM users WHERE is_demo = 1);
DELETE FROM mock_interview_sessions WHERE is_demo = 1;
DELETE FROM issued_certificates WHERE is_demo = 1;
DELETE FROM reassessment_schedules WHERE is_demo = 1;
DELETE FROM mentor_nudge_logs WHERE ase_id IN (SELECT id FROM users WHERE is_demo = 1);
DELETE FROM ase_risk_signals WHERE is_demo = 1;
DELETE FROM ai_learning_roadmaps WHERE is_demo = 1;
DELETE FROM onboarding_milestones WHERE is_demo = 1;
DELETE FROM ase_gamification WHERE is_demo = 1;
DELETE FROM ase_readiness_history WHERE is_demo = 1;

-- 0. Phase 8 AI Class Summary & Assessments
DELETE FROM ai_generate_rate_logs WHERE user_id IN (SELECT id FROM users WHERE is_demo = 1);
DELETE FROM class_effectiveness_reports WHERE is_demo = 1;
DELETE FROM ai_generated_questions WHERE ai_assessment_id IN (SELECT id FROM ai_generated_assessments WHERE is_demo = 1);
DELETE FROM ai_generated_assessments WHERE is_demo = 1;
DELETE FROM class_summaries WHERE is_demo = 1;
DELETE FROM class_transcripts WHERE is_demo = 1;

-- 0.1 Phase 7 Coding Submissions & Plagiarism
DELETE FROM coding_plagiarism_flags WHERE is_demo = 1;
DELETE FROM coding_run_logs WHERE ase_id IN (SELECT id FROM users WHERE is_demo = 1);
DELETE FROM coding_submissions WHERE ase_id IN (SELECT id FROM users WHERE is_demo = 1);

-- 0.2 Phase 6 AI Chat & LLM Usage Logs
DELETE FROM ai_insights_cache WHERE is_demo = 1;
DELETE FROM llm_usage_logs WHERE is_demo = 1;
DELETE FROM chat_messages WHERE is_demo = 1;
DELETE FROM chat_sessions WHERE is_demo = 1;

-- 1. Phase 5 Notifications & Reminders
DELETE FROM reminders_sent WHERE is_demo = 1;
DELETE FROM notifications WHERE is_demo = 1;

-- 2. Phase 5 Live Classes & Attendance
DELETE FROM live_class_attendees WHERE is_demo = 1;
DELETE FROM live_classes WHERE is_demo = 1;

-- 3. Phase 5 Trainings & Assignments
DELETE FROM training_assignments WHERE is_demo = 1;
DELETE FROM trainings WHERE is_demo = 1;

-- 4. Phase 3 Exam Violations
DELETE FROM exam_violations 
WHERE attempt_id IN (SELECT id FROM assessment_attempts WHERE is_demo = 1);

-- 5. Phase 2 Assessment Responses & Attempts
DELETE FROM assessment_responses 
WHERE attempt_id IN (SELECT id FROM assessment_attempts WHERE is_demo = 1);

DELETE FROM assessment_attempts 
WHERE is_demo = 1;

-- 6. Assessment Assignments
DELETE FROM assessment_assignments 
WHERE is_demo = 1;

-- 7. Phase 4 Cohorts & Members
DELETE FROM cohort_members 
WHERE cohort_id IN (SELECT id FROM cohorts WHERE is_demo = 1)
   OR ase_id IN (SELECT id FROM users WHERE is_demo = 1);

DELETE FROM cohorts 
WHERE is_demo = 1;

-- 8. Phase 1 Mentor-ASE Assignments & Demo Users
DELETE FROM mentor_ase_assignments 
WHERE ase_id IN (SELECT id FROM users WHERE is_demo = 1);

DELETE FROM users 
WHERE is_demo = 1;

-- 9. Phase 7 Quotes & Coding Plagiarism Flags
DELETE FROM coding_plagiarism_flags WHERE is_demo = 1;
DELETE FROM motivational_quotes WHERE is_demo = 1;

-- 10. Phase 13 Microsoft Integration Demo Data Cleanup
DELETE FROM class_attendance_imports;
DELETE FROM sso_oauth_states;
DELETE FROM sso_audit_logs WHERE user_id IN (SELECT id FROM users WHERE is_demo = 1);
DELETE FROM user_notification_preferences WHERE user_id IN (SELECT id FROM users WHERE is_demo = 1);
DELETE FROM user_sso_accounts WHERE user_id IN (SELECT id FROM users WHERE is_demo = 1);

-- 11. Final Polish Audit Logs & Login Attempts Cleanup
DELETE FROM admin_audit_logs WHERE actor_id IN (SELECT id FROM users WHERE is_demo = 1);
DELETE FROM login_attempts WHERE email IN (SELECT email FROM users WHERE is_demo = 1);
