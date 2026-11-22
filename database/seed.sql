-- L&K Skill Hub - Seed Data (Phase 1, 2, 3 & 4)
USE `skillhub_db`;

-- 1. Users
INSERT INTO `users` (`id`, `name`, `email`, `hashed_password`, `role`, `is_active`, `is_demo`, `must_change_password`) VALUES
(1, 'System Admin', 'admin.demo@csm.tech', '$2b$12$SIOyPQk7wFQdVnufMnv9mOgfY2/tu2EYU6N1fBZ3JOMZXg/uihcw2', 'ADMIN', 1, 0, 1),
(2, 'Senior Mentor', 'mentor.demo@csm.tech', '$2b$12$NBvjFBxTF8cKkt9RR.HINuPhf4Xl3iyUbRm7OhP4t7SqpcllSqsTi', 'MENTOR', 1, 0, 1),
(3, 'Associate Engineer', 'ase.demo@csm.tech', '$2b$12$r0FRfsUhOA9RRzfGVnucNu7Llfwk.e7Arcq5T1b5OdLrOQL1QS3Xa', 'ASE', 1, 0, 1),
(4, 'Aarav Sharma', 'demo.aarav.sharma@csm.tech', '$2b$12$r0FRfsUhOA9RRzfGVnucNu7Llfwk.e7Arcq5T1b5OdLrOQL1QS3Xa', 'ASE', 1, 1, 1),
(5, 'Diya Patel', 'demo.diya.patel@csm.tech', '$2b$12$r0FRfsUhOA9RRzfGVnucNu7Llfwk.e7Arcq5T1b5OdLrOQL1QS3Xa', 'ASE', 1, 1, 1),
(6, 'Rohan Gupta', 'demo.rohan.gupta@csm.tech', '$2b$12$r0FRfsUhOA9RRzfGVnucNu7Llfwk.e7Arcq5T1b5OdLrOQL1QS3Xa', 'ASE', 1, 1, 1),
(7, 'Ananya Verma', 'demo.ananya.verma@csm.tech', '$2b$12$r0FRfsUhOA9RRzfGVnucNu7Llfwk.e7Arcq5T1b5OdLrOQL1QS3Xa', 'ASE', 1, 1, 1),
(8, 'Kabir Mehta', 'demo.kabir.mehta@csm.tech', '$2b$12$r0FRfsUhOA9RRzfGVnucNu7Llfwk.e7Arcq5T1b5OdLrOQL1QS3Xa', 'ASE', 1, 1, 1),
(9, 'Ishita Roy', 'demo.ishita.roy@csm.tech', '$2b$12$r0FRfsUhOA9RRzfGVnucNu7Llfwk.e7Arcq5T1b5OdLrOQL1QS3Xa', 'ASE', 1, 1, 1)
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`), `email`=VALUES(`email`), `is_demo`=VALUES(`is_demo`), `must_change_password`=VALUES(`must_change_password`);

-- 2. Phase 1 Mentor-ASE Mapping
INSERT INTO `mentor_ase_assignments` (`id`, `mentor_id`, `ase_id`) VALUES
(1, 2, 3),
(2, 2, 4),
(3, 2, 5),
(4, 2, 6),
(5, 2, 7),
(6, 2, 8),
(7, 2, 9)
ON DUPLICATE KEY UPDATE `mentor_id`=VALUES(`mentor_id`);

-- 3. Phase 4 Cohorts
INSERT INTO `cohorts` (`id`, `name`, `description`, `start_date`, `created_by`) VALUES
(1, 'Alpha Engineering Cohort 2026', 'Spring 2026 Associate Engineering Batch', '2026-01-15', 1),
(2, 'Beta Full-Stack Batch 2026', 'Summer 2026 Full-Stack Accelerate Batch', '2026-03-01', 1)
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`);

-- 4. Phase 4 Cohort Members
INSERT INTO `cohort_members` (`id`, `cohort_id`, `ase_id`) VALUES
(1, 1, 3),
(2, 1, 4),
(3, 1, 5),
(4, 1, 6),
(5, 2, 7),
(6, 2, 8),
(7, 2, 9)
ON DUPLICATE KEY UPDATE `cohort_id`=VALUES(`cohort_id`);

-- 5. Question Bank (10 Sample Questions)
INSERT INTO `question_bank` (`id`, `type`, `difficulty`, `skill_category`, `question_text`, `question_type`, `options`, `correct_answers`, `marks`) VALUES
(1, 'Logical Thinking', 'Easy', 'Deductive Logic', 'All microservices in Cluster A communicate via gRPC. Service X is in Cluster A. Which conclusion is strictly true?', 'SINGLE_CHOICE', '[{"id": "opt1", "text": "Service X communicates via gRPC."}, {"id": "opt2", "text": "Service X uses REST API."}, {"id": "opt3", "text": "Service X cannot communicate with other services."}, {"id": "opt4", "text": "Service X communicates only with external clients."}]', '["opt1"]', 2),
(2, 'Logical Thinking', 'Medium', 'Conditional Reasoning', 'If a cache miss occurs, the system queries the database. The system did NOT query the database. What can be concluded?', 'SINGLE_CHOICE', '[{"id": "opt1", "text": "A cache hit occurred (no cache miss)."}, {"id": "opt2", "text": "The database is down."}, {"id": "opt3", "text": "A cache miss definitely occurred."}, {"id": "opt4", "text": "The query timed out."}]', '["opt1"]', 2),
(3, 'Pattern Recognition', 'Medium', 'Pattern Recognition', 'Find the next number in the memory allocation series: 2, 4, 8, 16, 32, __?', 'SINGLE_CHOICE', '[{"id": "opt1", "text": "48"}, {"id": "opt2", "text": "64"}, {"id": "opt3", "text": "56"}, {"id": "opt4", "text": "72"}]', '["opt2"]', 1),
(4, 'Pattern Recognition', 'Hard', 'Pattern Recognition', 'Identify the missing sequence in binary shifts: 0001, 0010, 0100, ____?', 'SINGLE_CHOICE', '[{"id": "opt1", "text": "1000"}, {"id": "opt2", "text": "0110"}, {"id": "opt3", "text": "0011"}, {"id": "opt4", "text": "1111"}]', '["opt1"]', 1),
(5, 'Logical Thinking', 'Hard', 'System Architecture Logic', 'Which of the following are ACID properties in relational transaction management? (Select all that apply)', 'MULTI_CHOICE', '[{"id": "opt1", "text": "Atomicity"}, {"id": "opt2", "text": "Consistency"}, {"id": "opt3", "text": "Availability"}, {"id": "opt4", "text": "Durability"}]', '["opt1", "opt2", "opt4"]', 3),
(6, 'Aptitude', 'Easy', 'Numerical Computation', 'A server processes 1,200 requests in 2 minutes. What is its throughput in requests per second (RPS)?', 'SINGLE_CHOICE', '[{"id": "opt1", "text": "10 RPS"}, {"id": "opt2", "text": "15 RPS"}, {"id": "opt3", "text": "20 RPS"}, {"id": "opt4", "text": "600 RPS"}]', '["opt1"]', 1),
(7, 'Aptitude', 'Medium', 'Numerical Computation', 'If database query latency increases from 50ms to 75ms, what is the percentage increase in latency?', 'SINGLE_CHOICE', '[{"id": "opt1", "text": "25%"}, {"id": "opt2", "text": "33.3%"}, {"id": "opt3", "text": "50%"}, {"id": "opt4", "text": "75%"}]', '["opt3"]', 2),
(8, 'Reasoning', 'Medium', 'Critical Reasoning', 'Statement: High CPU utilization in a service always triggers an alert. Observation: Alert #401 was triggered. What can be safely deduced?', 'SINGLE_CHOICE', '[{"id": "opt1", "text": "CPU utilization is definitely high."}, {"id": "opt2", "text": "The service has crashed."}, {"id": "opt3", "text": "Alert #401 could be for high CPU or another configured trigger."}, {"id": "opt4", "text": "Memory is 100% full."}]', '["opt3"]', 2),
(9, 'Reasoning', 'Easy', 'Critical Reasoning', 'Select the properties that contribute to horizontally scalable web applications: (Select all that apply)', 'MULTI_CHOICE', '[{"id": "opt1", "text": "Stateless application servers"}, {"id": "opt2", "text": "Centralized session storage / Redis"}, {"id": "opt3", "text": "Hardcoded in-memory state on single nodes"}, {"id": "opt4", "text": "Load balancing across multiple instances"}]', '["opt1", "opt2", "opt4"]', 3),
(10, 'Aptitude', 'Hard', 'Data Interpretation', 'An engineering team completed 40 story points in Sprint 1 and 50 story points in Sprint 2 with 5 developers. What was the average velocity per developer per sprint?', 'SINGLE_CHOICE', '[{"id": "opt1", "text": "9 story points"}, {"id": "opt2", "text": "10 story points"}, {"id": "opt3", "text": "12 story points"}, {"id": "opt4", "text": "18 story points"}]', '["opt1"]', 2)
ON DUPLICATE KEY UPDATE `question_text`=VALUES(`question_text`);

-- 6. Sample Assessment
INSERT INTO `assessments` (`id`, `title`, `type`, `total_duration_minutes`, `passing_percentage`, `randomize_questions`, `randomize_options`, `created_by`) VALUES
(1, 'Engineering Logic, Reasoning & Aptitude Assessment', 'Logical Thinking', 30, 60.0, 0, 0, 1)
ON DUPLICATE KEY UPDATE `title`=VALUES(`title`);

-- 7. Sections
INSERT INTO `assessment_sections` (`id`, `assessment_id`, `title`, `order_index`, `timer_minutes`) VALUES
(1, 1, 'Section A: Logical & Pattern Recognition', 0, 15),
(2, 1, 'Section B: Quantitative Aptitude & Critical Reasoning', 1, 15)
ON DUPLICATE KEY UPDATE `title`=VALUES(`title`);

-- 8. Section Questions Mapping
INSERT INTO `assessment_section_questions` (`section_id`, `question_id`, `order_index`) VALUES
(1, 1, 0), (1, 2, 1), (1, 3, 2), (1, 4, 3), (1, 5, 4),
(2, 6, 0), (2, 7, 1), (2, 8, 2), (2, 9, 3), (2, 10, 4)
ON DUPLICATE KEY UPDATE `order_index`=VALUES(`order_index`);

-- 9. Assessment Assignments (Cohort & Individual)
INSERT INTO `assessment_assignments` (`id`, `assessment_id`, `ase_id`, `cohort_id`, `assigned_by`, `start_date`, `end_date`, `is_demo`) VALUES
(1, 1, 3, 1, 1, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_ADD(NOW(), INTERVAL 14 DAY), 0),
(2, 1, 4, 1, 1, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_ADD(NOW(), INTERVAL 14 DAY), 1),
(3, 1, 5, 1, 1, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_ADD(NOW(), INTERVAL 14 DAY), 1),
(4, 1, 6, 1, 1, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_ADD(NOW(), INTERVAL 14 DAY), 1),
(5, 1, 7, 2, 1, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_ADD(NOW(), INTERVAL 14 DAY), 1),
(6, 1, 8, 2, 1, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_ADD(NOW(), INTERVAL 14 DAY), 1),
(7, 1, 9, 2, 1, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_ADD(NOW(), INTERVAL 14 DAY), 1)
ON DUPLICATE KEY UPDATE `start_date`=VALUES(`start_date`);

-- 10. Sample Completed Assessment Attempts (Demo Data for Heatmap & Analytics)
INSERT INTO `assessment_attempts` (`id`, `assessment_assignment_id`, `ase_id`, `started_at`, `submitted_at`, `status`, `total_score`, `max_score`, `percentage`, `passed`, `section_scores`, `skill_percentages`, `violation_count`, `auto_submit_reason`, `is_demo`) VALUES
(1, 2, 4, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY), 'SUBMITTED', 18.0, 20.0, 90.0, 1,
 '{"Section A: Logical & Pattern Recognition": 8.0, "Section B: Quantitative Aptitude & Critical Reasoning": 10.0}',
 '{"Deductive Logic": 100.0, "Conditional Reasoning": 100.0, "Pattern Recognition": 100.0, "System Architecture Logic": 100.0, "Numerical Computation": 100.0, "Critical Reasoning": 80.0, "Data Interpretation": 100.0}',
 0, NULL, 1),

(2, 3, 5, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY), 'SUBMITTED', 15.0, 20.0, 75.0, 1,
 '{"Section A: Logical & Pattern Recognition": 7.0, "Section B: Quantitative Aptitude & Critical Reasoning": 8.0}',
 '{"Deductive Logic": 100.0, "Conditional Reasoning": 50.0, "Pattern Recognition": 100.0, "System Architecture Logic": 66.7, "Numerical Computation": 75.0, "Critical Reasoning": 80.0, "Data Interpretation": 50.0}',
 0, NULL, 1),

(3, 4, 6, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY), 'SUBMITTED', 9.0, 20.0, 45.0, 0,
 '{"Section A: Logical & Pattern Recognition": 4.0, "Section B: Quantitative Aptitude & Critical Reasoning": 5.0}',
 '{"Deductive Logic": 50.0, "Conditional Reasoning": 0.0, "Pattern Recognition": 50.0, "System Architecture Logic": 33.3, "Numerical Computation": 40.0, "Critical Reasoning": 60.0, "Data Interpretation": 0.0}',
 1, NULL, 1),

(4, 5, 7, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY), 'SUBMITTED', 16.0, 20.0, 80.0, 1,
 '{"Section A: Logical & Pattern Recognition": 8.0, "Section B: Quantitative Aptitude & Critical Reasoning": 8.0}',
 '{"Deductive Logic": 100.0, "Conditional Reasoning": 100.0, "Pattern Recognition": 50.0, "System Architecture Logic": 100.0, "Numerical Computation": 80.0, "Critical Reasoning": 75.0, "Data Interpretation": 100.0}',
 0, NULL, 1),

(5, 6, 8, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY), 'AUTO_SUBMITTED_VIOLATION', 12.0, 20.0, 60.0, 1,
 '{"Section A: Logical & Pattern Recognition": 6.0, "Section B: Quantitative Aptitude & Critical Reasoning": 6.0}',
 '{"Deductive Logic": 50.0, "Conditional Reasoning": 50.0, "Pattern Recognition": 50.0, "System Architecture Logic": 66.7, "Numerical Computation": 60.0, "Critical Reasoning": 60.0, "Data Interpretation": 50.0}',
 2, 'MAX_VIOLATIONS_EXCEEDED', 1)
ON DUPLICATE KEY UPDATE `total_score`=VALUES(`total_score`);

-- 11. Phase 5 Sample Trainings
INSERT INTO `trainings` (`id`, `title`, `description`, `skill_category`, `type`, `resources`, `duration_hours`, `created_by`, `is_demo`) VALUES
(1, 'Advanced Distributed Systems & Microservices', 'Deep dive into resilient microservices architecture, circuit breakers, and event-driven patterns.', 'System Architecture Logic', 'Self-paced', '[{"name": "Microservices Patterns Reference", "url": "https://microservices.io", "type": "link"}]', 4.0, 1, 1),
(2, 'Pattern Recognition & Algorithm Optimization', 'Master algorithmic patterns, binary shift optimizations, and memory efficiency techniques.', 'Pattern Recognition', 'Workshop', '[{"name": "Algorithm Patterns Cheat Sheet", "url": "https://leetcode.com/explore", "type": "link"}]', 2.5, 2, 1)
ON DUPLICATE KEY UPDATE `title`=VALUES(`title`);

-- 12. Phase 5 Training Assignments
INSERT INTO `training_assignments` (`id`, `training_id`, `ase_id`, `cohort_id`, `assigned_by`, `due_date`, `status`, `progress_percent`, `completed_at`, `is_demo`) VALUES
(1, 1, 3, 1, 2, DATE_ADD(NOW(), INTERVAL 5 DAY), 'COMPLETED', 100.0, DATE_SUB(NOW(), INTERVAL 1 DAY), 1),
(2, 1, 4, 1, 2, DATE_ADD(NOW(), INTERVAL 7 DAY), 'IN_PROGRESS', 60.0, NULL, 1),
(3, 2, 5, 1, 2, DATE_SUB(NOW(), INTERVAL 1 DAY), 'NOT_STARTED', 0.0, NULL, 1), -- Overdue
(4, 2, 6, 2, 2, DATE_ADD(NOW(), INTERVAL 4 DAY), 'IN_PROGRESS', 35.0, NULL, 1)
ON DUPLICATE KEY UPDATE `status`=VALUES(`status`);

-- 13. Phase 5 Live Classes
INSERT INTO `live_classes` (`id`, `title`, `description`, `start_time`, `duration_minutes`, `audience_type`, `cohort_id`, `meeting_link`, `provider`, `created_by`, `is_demo`) VALUES
(1, 'Interactive System Architecture & gRPC Masterclass', 'Live interactive architecture session covering service mesh, load balancing, and RPC contracts.', DATE_ADD(NOW(), INTERVAL 1 DAY), 60, 'COHORT', 1, 'https://teams.microsoft.com/l/meetup-join/19%3ameeting_arch_masterclass%40thread.v2/0', 'MANUAL', 2, 1)
ON DUPLICATE KEY UPDATE `title`=VALUES(`title`);

-- 14. Phase 5 Live Class Attendees
INSERT INTO `live_class_attendees` (`id`, `live_class_id`, `ase_id`, `status`, `marked_at`, `marked_by`, `is_demo`) VALUES
(1, 1, 3, 'ATTENDED', NOW(), 2, 1),
(2, 1, 4, 'INVITED', NULL, NULL, 1),
(3, 1, 5, 'INVITED', NULL, NULL, 1)
ON DUPLICATE KEY UPDATE `status`=VALUES(`status`);

-- 15. Phase 5 Notifications
INSERT INTO `notifications` (`id`, `user_id`, `title`, `message`, `type`, `link`, `is_read`, `is_demo`) VALUES
(1, 3, 'Welcome to L&K Skill Hub', 'Your account is active. Explore your dashboard and training programs.', 'GENERAL', '/ase/dashboard', 1, 1),
(2, 3, 'Live Class Scheduled: System Architecture Masterclass', 'You are invited to join the upcoming live session on Teams.', 'LIVE_CLASS', '/ase/schedule', 0, 1)
ON DUPLICATE KEY UPDATE `title`=VALUES(`title`);

-- 16. Phase 6 Sample Chat Session & Messages
INSERT INTO `chat_sessions` (`id`, `user_id`, `title`, `is_active`, `is_demo`) VALUES
(1, 3, 'General Assessment Guidance', 1, 1),
(2, 2, 'Cohort Risk Diagnostics', 1, 1)
ON DUPLICATE KEY UPDATE `title`=VALUES(`title`);

INSERT INTO `chat_messages` (`id`, `session_id`, `user_id`, `sender_role`, `content`, `feedback`, `is_demo`) VALUES
(1, 1, 3, 'USER', 'What are my weakest skills based on my latest assessment?', NULL, 1),
(2, 1, 3, 'ASSISTANT', 'Based on your recent assessment results, your primary focus area is **Logical Thinking & Data Structures** (currently below 70%).\n\n**Recommended Next Steps:**\n1. Review the *Advanced Async Python* training module on your My Learning page.\n2. Practice section questions with 25-minute focused interval drills.\n3. Attend the upcoming Mentor Live Q&A session.', 'UP', 1)
ON DUPLICATE KEY UPDATE `content`=VALUES(`content`);

-- 17. Phase 6 Sample LLM Usage Logs
INSERT INTO `llm_usage_logs` (`id`, `user_id`, `role`, `provider`, `model`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `is_demo`) VALUES
(1, 3, 'ASE', 'mock', 'mock-gpt-4', 142, 68, 210, 1),
(2, 2, 'MENTOR', 'mock', 'mock-gpt-4', 215, 94, 309, 1)
ON DUPLICATE KEY UPDATE `total_tokens`=VALUES(`total_tokens`);

-- 18. Phase 10 Sample Reasonable Accommodation
INSERT INTO `accommodation_requests` (`id`, `ase_id`, `requested_by`, `accommodation_type`, `extra_time_percent`, `reason_category`, `medical_notes`, `status`, `admin_notes`, `is_demo`) VALUES
(1, 3, 3, 'EXTRA_TIME_PCT', 50.0, 'COGNITIVE', 'Confidential documentation on file with occupational health.', 'APPROVED', 'Standard 50% extra time allowance approved for all timed sessions.', 1)
ON DUPLICATE KEY UPDATE `status`=VALUES(`status`);

-- 19. Phase 11 1-on-1 Mentoring Meeting (Demo Data with Fictitious Names & is_demo=1)
INSERT INTO `one_on_one_meetings` (`id`, `mentor_id`, `mentee_id`, `title`, `meeting_date`, `status`, `shared_notes`, `encrypted_private_notes`, `is_demo`) VALUES
(1, 2, 3, 'Sprint 4 Architecture & Async Mentoring Review', DATE_SUB(NOW(), INTERVAL 2 DAY), 'COMPLETED', 'Discussed async exception handling and test case coverage. Candidate showed steady progress on deductive logic tasks.', 'gAAAAABn...EncryptedPrivateNote...', 1)
ON DUPLICATE KEY UPDATE `title`=VALUES(`title`);

-- 20. Phase 11 1-on-1 Goals & Actions
INSERT INTO `one_on_one_goals` (`id`, `meeting_id`, `mentor_id`, `mentee_id`, `title`, `description`, `target_date`, `status`, `is_demo`) VALUES
(1, 1, 2, 3, 'Achieve 85%+ on System Architecture Section', 'Complete the Async Python drills and achieve target mastery score.', DATE_ADD(NOW(), INTERVAL 14 DAY), 'IN_PROGRESS', 1)
ON DUPLICATE KEY UPDATE `title`=VALUES(`title`);

INSERT INTO `one_on_one_action_items` (`id`, `meeting_id`, `goal_id`, `mentor_id`, `mentee_id`, `task`, `assigned_to`, `is_completed`, `is_demo`) VALUES
(1, 1, 1, 2, 3, 'Complete Chapter 4 Async IO exercises in My Learning', 'ASE', 1, 1),
(2, 1, 1, 2, 3, 'Review test case output with mentor during office hours', 'ASE', 0, 1)
ON DUPLICATE KEY UPDATE `task`=VALUES(`task`);

-- 21. Phase 11 Staffing Projects & Skill Requirements
INSERT INTO `staffing_projects` (`id`, `name`, `description`, `headcount`, `start_date`, `ready_now_threshold_pct`, `status`, `created_by_user_id`, `is_demo`) VALUES
(1, 'Project Alpha: Cloud Microservices Migration', 'Modernization of legacy monolithic backend into distributed containerized microservices.', 3, DATE_ADD(NOW(), INTERVAL 30 DAY), 90.0, 'PLANNING', 1, 1)
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`);

INSERT INTO `staffing_project_skills` (`id`, `project_id`, `skill_name`, `min_level_pct`, `weight`) VALUES
(1, 1, 'Deductive Logic', 75.0, 1.0),
(2, 1, 'Pattern Recognition', 70.0, 1.0)
ON DUPLICATE KEY UPDATE `min_level_pct`=VALUES(`min_level_pct`);

-- 22. Phase 12 Buddy System & Doubt Forum (is_demo=1)
INSERT INTO `buddy_pairings` (`id`, `buddy_id`, `buddee_id`, `status`, `paired_by`, `paired_at`, `is_demo`) VALUES
(1, 4, 6, 'ACTIVE', 2, DATE_SUB(NOW(), INTERVAL 7 DAY), 1)
ON DUPLICATE KEY UPDATE `status`=VALUES(`status`);

INSERT INTO `buddy_milestones` (`id`, `pairing_id`, `buddy_id`, `buddee_id`, `title`, `description`, `status`, `xp_amount`, `xp_awarded`, `confirmed_at`) VALUES
(1, 1, 4, 6, 'Orientation & Study Plan Alignment', 'Completed 30-minute peer sync to review study roadmap and setup tooling.', 'CONFIRMED_BY_BUDDEE', 25, 1, DATE_SUB(NOW(), INTERVAL 3 DAY))
ON DUPLICATE KEY UPDATE `status`=VALUES(`status`);

INSERT INTO `forum_posts` (`id`, `cohort_id`, `author_id`, `title`, `body`, `tags`, `is_anonymous`, `status`, `is_resolved`, `view_count`, `is_demo`) VALUES
(1, 1, 4, 'How to handle unhandled exceptions in FastAPI background tasks?', 'When running background workers in FastAPI, unhandled exceptions do not seem to propagate to global middleware. What is the standard production pattern?', 'FastAPI,Async,Python', 0, 'PUBLISHED', 1, 42, 1),
(2, 1, 5, 'Clarification on Big-O complexity for tree traversal algorithms', 'In non-balanced BSTs, what is the worst-case space complexity for recursive DFS versus queue-based BFS?', 'Algorithms,DataStructures', 1, 'PUBLISHED', 0, 28, 1)
ON DUPLICATE KEY UPDATE `title`=VALUES(`title`);

INSERT INTO `forum_answers` (`id`, `post_id`, `author_id`, `body`, `is_anonymous`, `is_accepted`, `is_mentor_verified`, `is_ai_generated`, `upvote_count`, `is_demo`) VALUES
(1, 1, 2, 'In FastAPI, background tasks run after the response has been sent, so standard HTTP middleware cannot intercept them. You should wrap your background worker function in an explicit try/except block that logs to Sentry or CloudWatch.', 0, 1, 1, 0, 5, 1),
(2, 2, 4, 'For non-balanced BSTs (degenerate line), worst-case call stack space for DFS is O(N). For BFS, maximum queue width in a balanced tree is O(N), but in a degenerate line it is O(1).', 0, 0, 1, 0, 3, 1)
ON DUPLICATE KEY UPDATE `body`=VALUES(`body`);

-- 23. Phase 13 Microsoft Integration (is_demo=1)
INSERT INTO `sso_configurations` (`id`, `allow_local_login`, `auto_provision_ase`, `updated_by`) VALUES
(1, 1, 0, 1)
ON DUPLICATE KEY UPDATE `allow_local_login`=VALUES(`allow_local_login`);

INSERT INTO `user_notification_preferences` (`id`, `user_id`, `preferred_channels`, `quiet_hours_enabled`, `quiet_hours_start`, `quiet_hours_end`, `timezone`) VALUES
(1, 4, 'IN_APP,EMAIL,TEAMS', 1, '22:00', '07:00', 'Asia/Kolkata'),
(2, 5, 'IN_APP,EMAIL', 0, '22:00', '07:00', 'UTC')
ON DUPLICATE KEY UPDATE `preferred_channels`=VALUES(`preferred_channels`);

INSERT INTO `sso_audit_logs` (`id`, `user_id`, `event_type`, `upn`, `tid`, `oid`, `ip_address`, `user_agent`, `failure_reason`) VALUES
(1, 1, 'LOGIN_SUCCESS', 'admin.demo@csm.tech', 'demo-tenant-id', 'demo-oid-admin', '127.0.0.1', 'Mozilla/5.0 Demo Browser', NULL),
(2, 4, 'LINK', 'demo.aarav.sharma@csm.tech', 'demo-tenant-id', 'demo-oid-ase1', '127.0.0.1', 'Mozilla/5.0 Demo Browser', NULL)
ON DUPLICATE KEY UPDATE `event_type`=VALUES(`event_type`);




