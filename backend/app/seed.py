import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.question import QuestionBank, AssessmentType, QuestionDifficulty, QuestionType
from app.models.assessment import Assessment, AssessmentSection, AssessmentSectionQuestion
from app.models.assessment_assignment import AssessmentAssignment
from app.models.cohort import Cohort, CohortMember
from app.models.training import Training, TrainingAssignment
from app.models.live_class import LiveClass, LiveClassAttendee
from app.models.notification import Notification, ReminderSent
from app.models.chat import ChatSession, ChatMessage, LLMUsageLog, AIInsightsCache
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus, ExamViolation

logger = logging.getLogger(__name__)

SAMPLE_QUESTIONS = [
    # Section 1 questions (Logical & Pattern)
    {
        "type": AssessmentType.LOGICAL_THINKING,
        "difficulty": QuestionDifficulty.EASY,
        "skill_category": "Deductive Logic",
        "question_text": "All microservices in Cluster A communicate via gRPC. Service X is in Cluster A. Which conclusion is strictly true?",
        "question_type": QuestionType.SINGLE_CHOICE,
        "options": [
            {"id": "opt1", "text": "Service X communicates via gRPC."},
            {"id": "opt2", "text": "Service X uses REST API."},
            {"id": "opt3", "text": "Service X cannot communicate with other services."},
            {"id": "opt4", "text": "Service X communicates only with external clients."}
        ],
        "correct_answers": ["opt1"],
        "marks": 2
    },
    {
        "type": AssessmentType.LOGICAL_THINKING,
        "difficulty": QuestionDifficulty.MEDIUM,
        "skill_category": "Conditional Reasoning",
        "question_text": "If a cache miss occurs, the system queries the database. The system did NOT query the database. What can be concluded?",
        "question_type": QuestionType.SINGLE_CHOICE,
        "options": [
            {"id": "opt1", "text": "A cache hit occurred (no cache miss)."},
            {"id": "opt2", "text": "The database is down."},
            {"id": "opt3", "text": "A cache miss definitely occurred."},
            {"id": "opt4", "text": "The query timed out."}
        ],
        "correct_answers": ["opt1"],
        "marks": 2
    },
    {
        "type": AssessmentType.PATTERN_RECOGNITION,
        "difficulty": QuestionDifficulty.MEDIUM,
        "skill_category": "Pattern Recognition",
        "question_text": "Find the next number in the memory allocation series: 2, 4, 8, 16, 32, __?",
        "question_type": QuestionType.SINGLE_CHOICE,
        "options": [
            {"id": "opt1", "text": "48"},
            {"id": "opt2", "text": "64"},
            {"id": "opt3", "text": "56"},
            {"id": "opt4", "text": "72"}
        ],
        "correct_answers": ["opt2"],
        "marks": 1
    },
    {
        "type": AssessmentType.PATTERN_RECOGNITION,
        "difficulty": QuestionDifficulty.HARD,
        "skill_category": "Pattern Recognition",
        "question_text": "Identify the missing sequence in binary shifts: 0001, 0010, 0100, ____?",
        "question_type": QuestionType.SINGLE_CHOICE,
        "options": [
            {"id": "opt1", "text": "1000"},
            {"id": "opt2", "text": "0110"},
            {"id": "opt3", "text": "0011"},
            {"id": "opt4", "text": "1111"}
        ],
        "correct_answers": ["opt1"],
        "marks": 1
    },
    {
        "type": AssessmentType.LOGICAL_THINKING,
        "difficulty": QuestionDifficulty.HARD,
        "skill_category": "System Architecture Logic",
        "question_text": "Which of the following are ACID properties in relational transaction management? (Select all that apply)",
        "question_type": QuestionType.MULTI_CHOICE,
        "options": [
            {"id": "opt1", "text": "Atomicity"},
            {"id": "opt2", "text": "Consistency"},
            {"id": "opt3", "text": "Availability"},
            {"id": "opt4", "text": "Durability"}
        ],
        "correct_answers": ["opt1", "opt2", "opt4"],
        "marks": 3
    },
    # Section 2 questions (Aptitude & Reasoning)
    {
        "type": AssessmentType.APTITUDE,
        "difficulty": QuestionDifficulty.EASY,
        "skill_category": "Numerical Computation",
        "question_text": "A server processes 1,200 requests in 2 minutes. What is its throughput in requests per second (RPS)?",
        "question_type": QuestionType.SINGLE_CHOICE,
        "options": [
            {"id": "opt1", "text": "10 RPS"},
            {"id": "opt2", "text": "15 RPS"},
            {"id": "opt3", "text": "20 RPS"},
            {"id": "opt4", "text": "600 RPS"}
        ],
        "correct_answers": ["opt1"],
        "marks": 1
    },
    {
        "type": AssessmentType.APTITUDE,
        "difficulty": QuestionDifficulty.MEDIUM,
        "skill_category": "Numerical Computation",
        "question_text": "If database query latency increases from 50ms to 75ms, what is the percentage increase in latency?",
        "question_type": QuestionType.SINGLE_CHOICE,
        "options": [
            {"id": "opt1", "text": "25%"},
            {"id": "opt2", "text": "33.3%"},
            {"id": "opt3", "text": "50%"},
            {"id": "opt4", "text": "75%"}
        ],
        "correct_answers": ["opt3"],
        "marks": 2
    },
    {
        "type": AssessmentType.REASONING,
        "difficulty": QuestionDifficulty.MEDIUM,
        "skill_category": "Critical Reasoning",
        "question_text": "Statement: High CPU utilization in a service always triggers an alert. Observation: Alert #401 was triggered. What can be safely deduced?",
        "question_type": QuestionType.SINGLE_CHOICE,
        "options": [
            {"id": "opt1", "text": "CPU utilization is definitely high."},
            {"id": "opt2", "text": "The service has crashed."},
            {"id": "opt3", "text": "Alert #401 could be for high CPU or another configured trigger."},
            {"id": "opt4", "text": "Memory is 100% full."}
        ],
        "correct_answers": ["opt3"],
        "marks": 2
    },
    {
        "type": AssessmentType.REASONING,
        "difficulty": QuestionDifficulty.EASY,
        "skill_category": "Critical Reasoning",
        "question_text": "Select the properties that contribute to horizontally scalable web applications: (Select all that apply)",
        "question_type": QuestionType.MULTI_CHOICE,
        "options": [
            {"id": "opt1", "text": "Stateless application servers"},
            {"id": "opt2", "text": "Centralized session storage / Redis"},
            {"id": "opt3", "text": "Hardcoded in-memory state on single nodes"},
            {"id": "opt4", "text": "Load balancing across multiple instances"}
        ],
        "correct_answers": ["opt1", "opt2", "opt4"],
        "marks": 3
    },
    {
        "type": AssessmentType.APTITUDE,
        "difficulty": QuestionDifficulty.HARD,
        "skill_category": "Data Interpretation",
        "question_text": "An engineering team completed 40 story points in Sprint 1 and 50 story points in Sprint 2 with 5 developers. What was the average velocity per developer per sprint?",
        "question_type": QuestionType.SINGLE_CHOICE,
        "options": [
            {"id": "opt1", "text": "9 story points"},
            {"id": "opt2", "text": "10 story points"},
            {"id": "opt3", "text": "12 story points"},
            {"id": "opt4", "text": "18 story points"}
        ],
        "correct_answers": ["opt1"],
        "marks": 2
    }
]

def init_db():
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            # assessment_attempts check
            res = conn.execute(text("PRAGMA table_info(assessment_attempts)"))
            cols = [row[1] for row in res.fetchall()]
            if cols:
                if "violation_count" not in cols:
                    conn.execute(text("ALTER TABLE assessment_attempts ADD COLUMN violation_count INTEGER NOT NULL DEFAULT 0"))
                if "auto_submit_reason" not in cols:
                    conn.execute(text("ALTER TABLE assessment_attempts ADD COLUMN auto_submit_reason VARCHAR(255) NULL"))
                if "is_demo" not in cols:
                    conn.execute(text("ALTER TABLE assessment_attempts ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0"))
                if "camera_override_active" not in cols:
                    conn.execute(text("ALTER TABLE assessment_attempts ADD COLUMN camera_override_active INTEGER NOT NULL DEFAULT 0"))
                if "camera_exempt" not in cols:
                    conn.execute(text("ALTER TABLE assessment_attempts ADD COLUMN camera_exempt INTEGER NOT NULL DEFAULT 0"))
                if "accommodation_applied" not in cols:
                    conn.execute(text("ALTER TABLE assessment_attempts ADD COLUMN accommodation_applied INTEGER NOT NULL DEFAULT 0"))
                if "extended_total_duration_minutes" not in cols:
                    conn.execute(text("ALTER TABLE assessment_attempts ADD COLUMN extended_total_duration_minutes INTEGER NULL"))
                if "last_camera_heartbeat_at" not in cols:
                    conn.execute(text("ALTER TABLE assessment_attempts ADD COLUMN last_camera_heartbeat_at DATETIME NULL"))
                if "camera_status" not in cols:
                    conn.execute(text("ALTER TABLE assessment_attempts ADD COLUMN camera_status VARCHAR(30) NOT NULL DEFAULT 'INACTIVE'"))

            # assessments check (Phase 10 columns)
            res_ass = conn.execute(text("PRAGMA table_info(assessments)"))
            cols_ass = [row[1] for row in res_ass.fetchall()]
            if cols_ass:
                if "webcam_mode" not in cols_ass:
                    conn.execute(text("ALTER TABLE assessments ADD COLUMN webcam_mode VARCHAR(20) NOT NULL DEFAULT 'REQUIRED'"))
                if "webcam_policy" not in cols_ass:
                    conn.execute(text("ALTER TABLE assessments ADD COLUMN webcam_policy VARCHAR(20) NOT NULL DEFAULT 'WARNING_ONLY'"))
                if "camera_no_face_seconds" not in cols_ass:
                    conn.execute(text("ALTER TABLE assessments ADD COLUMN camera_no_face_seconds INTEGER NOT NULL DEFAULT 15"))
                if "camera_multiple_faces_seconds" not in cols_ass:
                    conn.execute(text("ALTER TABLE assessments ADD COLUMN camera_multiple_faces_seconds INTEGER NOT NULL DEFAULT 10"))
                if "camera_head_turn_seconds" not in cols_ass:
                    conn.execute(text("ALTER TABLE assessments ADD COLUMN camera_head_turn_seconds INTEGER NOT NULL DEFAULT 15"))
                if "camera_grace_period_seconds" not in cols_ass:
                    conn.execute(text("ALTER TABLE assessments ADD COLUMN camera_grace_period_seconds INTEGER NOT NULL DEFAULT 30"))

            # users check
            res_u = conn.execute(text("PRAGMA table_info(users)"))
            cols_u = [row[1] for row in res_u.fetchall()]
            if cols_u:
                if "is_demo" not in cols_u:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0"))
                if "is_buddy_volunteer" not in cols_u:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_buddy_volunteer INTEGER NOT NULL DEFAULT 0"))

            # assessment_assignments check
            res_a = conn.execute(text("PRAGMA table_info(assessment_assignments)"))
            cols_a = [row[1] for row in res_a.fetchall()]
            if cols_a:
                if "cohort_id" not in cols_a:
                    conn.execute(text("ALTER TABLE assessment_assignments ADD COLUMN cohort_id INTEGER NULL"))
                if "is_demo" not in cols_a:
                    conn.execute(text("ALTER TABLE assessment_assignments ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0"))

            # question_bank check (Phase 11 columns)
            res_qb = conn.execute(text("PRAGMA table_info(question_bank)"))
            cols_qb = [row[1] for row in res_qb.fetchall()]
            if cols_qb:
                if "version" not in cols_qb:
                    conn.execute(text("ALTER TABLE question_bank ADD COLUMN version INTEGER NOT NULL DEFAULT 1"))
                if "author_id" not in cols_qb:
                    conn.execute(text("ALTER TABLE question_bank ADD COLUMN author_id INTEGER NULL"))
                if "is_ai_generated" not in cols_qb:
                    conn.execute(text("ALTER TABLE question_bank ADD COLUMN is_ai_generated INTEGER NOT NULL DEFAULT 0"))
                if "ai_review_status" not in cols_qb:
                    conn.execute(text("ALTER TABLE question_bank ADD COLUMN ai_review_status VARCHAR(30) NOT NULL DEFAULT 'APPROVED'"))

            # assessment_responses check (Phase 11 columns)
            res_ar = conn.execute(text("PRAGMA table_info(assessment_responses)"))
            cols_ar = [row[1] for row in res_ar.fetchall()]
            if cols_ar:
                if "time_spent_seconds" not in cols_ar:
                    conn.execute(text("ALTER TABLE assessment_responses ADD COLUMN time_spent_seconds FLOAT NOT NULL DEFAULT 0.0"))
                if "question_version" not in cols_ar:
                    conn.execute(text("ALTER TABLE assessment_responses ADD COLUMN question_version INTEGER NOT NULL DEFAULT 1"))

            conn.commit()
        except Exception as e:
            logger.warning(f"Schema check error: {e}")

    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # 1. Phase 1 Users
        admin_user = db.query(User).filter(User.email == "admin.demo@csm.tech").first()
        if not admin_user:
            logger.info("Seeding Phase 1 initial users...")
            admin = User(
                name="System Admin",
                email="admin.demo@csm.tech",
                hashed_password=hash_password("Admin@123"),
                role=UserRole.ADMIN,
                is_active=True,
                must_change_password=True
            )
            mentor = User(
                name="Senior Mentor",
                email="mentor.demo@csm.tech",
                hashed_password=hash_password("Mentor@123"),
                role=UserRole.MENTOR,
                is_active=True,
                must_change_password=True
            )
            ase = User(
                name="Associate Engineer",
                email="ase.demo@csm.tech",
                hashed_password=hash_password("Ase@123"),
                role=UserRole.ASE,
                is_active=True,
                must_change_password=True
            )
            db.add_all([admin, mentor, ase])
            db.commit()
            db.refresh(mentor)
            db.refresh(ase)
            
            assignment = MentorAseAssignment(
                mentor_id=mentor.id,
                ase_id=ase.id
            )
            db.add(assignment)
            db.commit()

        # 2. Phase 2 Questions
        q_count = db.query(QuestionBank).count()
        if q_count == 0:
            logger.info("Seeding Question Bank with 10 engineering questions...")
            q_objects = []
            for q_data in SAMPLE_QUESTIONS:
                q = QuestionBank(**q_data)
                db.add(q)
                q_objects.append(q)
            db.commit()

            # 3. Create Sample Assessment
            admin_user = db.query(User).filter(User.role == UserRole.ADMIN).first()
            assessment = Assessment(
                title="Engineering Logic, Reasoning & Aptitude Assessment",
                type=AssessmentType.LOGICAL_THINKING,
                total_duration_minutes=30,
                passing_percentage=60.0,
                randomize_questions=False,
                randomize_options=False,
                created_by=admin_user.id if admin_user else None
            )
            db.add(assessment)
            db.flush()

            # Section 1
            sec1 = AssessmentSection(
                assessment_id=assessment.id,
                title="Section A: Logical & Pattern Recognition",
                order_index=0,
                timer_minutes=15
            )
            db.add(sec1)
            db.flush()

            for idx, q in enumerate(q_objects[:5]):
                sq = AssessmentSectionQuestion(
                    section_id=sec1.id,
                    question_id=q.id,
                    order_index=idx
                )
                db.add(sq)

            # Section 2
            sec2 = AssessmentSection(
                assessment_id=assessment.id,
                title="Section B: Quantitative Aptitude & Critical Reasoning",
                order_index=1,
                timer_minutes=15
            )
            db.add(sec2)
            db.flush()

            for idx, q in enumerate(q_objects[5:]):
                sq = AssessmentSectionQuestion(
                    section_id=sec2.id,
                    question_id=q.id,
                    order_index=idx
                )
                db.add(sq)

            db.commit()

            # 4. Assign assessment to the sample ASE
            ase_user = db.query(User).filter(User.email == "ase.demo@csm.tech").first()
            if ase_user:
                now_utc = datetime.now(timezone.utc)
                assignment = AssessmentAssignment(
                    assessment_id=assessment.id,
                    ase_id=ase_user.id,
                    assigned_by=admin_user.id if admin_user else None,
                    start_date=now_utc - timedelta(days=1),
                    end_date=now_utc + timedelta(days=14)
                )
                db.add(assignment)
                db.commit()
                logger.info("Sample assessment created and assigned to ASE (ase.demo@csm.tech)!")

        # 5. Phase 4 Cohorts & Additional Demo ASEs
        cohort_count = db.query(Cohort).count()
        if cohort_count == 0:
            logger.info("Seeding Phase 4 Cohorts, 6 Demo ASEs, and Completed Evaluation Attempts...")
            admin_user = db.query(User).filter(User.role == UserRole.ADMIN).first()
            mentor_user = db.query(User).filter(User.email == "mentor.demo@csm.tech").first()
            now_utc = datetime.now(timezone.utc)
            today_date = now_utc.date()

            # Cohorts
            c1 = Cohort(
                name="Alpha Engineering Cohort 2026",
                description="Core backend, high-scale architecture, and distributed systems batch",
                start_date=today_date - timedelta(days=45),
                created_by=admin_user.id if admin_user else None,
                is_demo=True
            )
            c2 = Cohort(
                name="Beta Full-Stack Batch 2026",
                description="Modern web systems, Angular microfrontends, and cloud deployment batch",
                start_date=today_date - timedelta(days=20),
                created_by=mentor_user.id if mentor_user else None,
                is_demo=True
            )
            db.add(c1)
            db.add(c2)
            db.commit()
            db.refresh(c1)
            db.refresh(c2)

            # Assign existing sample ASE to Cohort 1
            sample_ase = db.query(User).filter(User.email == "ase.demo@csm.tech").first()
            if sample_ase:
                db.add(CohortMember(cohort_id=c1.id, ase_id=sample_ase.id))

            # 6 Demo ASEs
            demo_ases_data = [
                ("Aarav Sharma", "demo.aarav.sharma@csm.tech", c1.id),
                ("Diya Patel", "demo.diya.patel@csm.tech", c1.id),
                ("Rohan Gupta", "demo.rohan.gupta@csm.tech", c1.id),
                ("Ananya Verma", "demo.ananya.verma@csm.tech", c2.id),
                ("Kabir Mehta", "demo.kabir.mehta@csm.tech", c2.id),
                ("Ishita Roy", "demo.ishita.roy@csm.tech", c2.id),
            ]

            demo_user_objs = {}
            for name, email, c_id in demo_ases_data:
                u = db.query(User).filter(User.email == email).first()
                if not u:
                    u = User(
                        name=name,
                        email=email,
                        hashed_password=hash_password("Ase@123"),
                        role=UserRole.ASE,
                        is_active=True,
                        is_demo=True,
                        must_change_password=True
                    )
                    db.add(u)
                    db.commit()
                    db.refresh(u)

                    # Assign to mentor
                    if mentor_user:
                        db.add(MentorAseAssignment(mentor_id=mentor_user.id, ase_id=u.id))

                    # Assign to cohort
                    db.add(CohortMember(cohort_id=c_id, ase_id=u.id))
                    db.commit()
                demo_user_objs[email] = u

            # Assessment attempts seeding
            assessment = db.query(Assessment).first()
            if assessment:
                # 1. Attempt for sample_ase (80%, passed, clean)
                if sample_ase:
                    assign_sample = db.query(AssessmentAssignment).filter(
                        AssessmentAssignment.assessment_id == assessment.id,
                        AssessmentAssignment.ase_id == sample_ase.id
                    ).first()
                    if assign_sample and not assign_sample.attempt:
                        att_sample = AssessmentAttempt(
                            assessment_assignment_id=assign_sample.id,
                            ase_id=sample_ase.id,
                            started_at=now_utc - timedelta(days=5),
                            submitted_at=now_utc - timedelta(days=5, minutes=-25),
                            status=AttemptStatus.SUBMITTED,
                            total_score=16.0,
                            max_score=20.0,
                            percentage=80.0,
                            passed=True,
                            violation_count=0,
                            is_demo=True,
                            section_scores=[
                                {"section_id": 1, "title": "Section A: Logical & Pattern Recognition", "score": 8, "max": 10, "percentage": 80.0},
                                {"section_id": 2, "title": "Section B: Quantitative Aptitude & Critical Reasoning", "score": 8, "max": 10, "percentage": 80.0}
                            ],
                            skill_percentages={"Deductive Logic": 85.0, "Pattern Recognition": 75.0, "Quantitative Aptitude": 80.0, "Critical Reasoning": 80.0},
                            strong_areas=["Deductive Logic", "Pattern Recognition", "Quantitative Aptitude", "Critical Reasoning"],
                            weak_areas=[]
                        )
                        db.add(att_sample)

                # 2. ase1: 85%, passed, clean
                ase1 = demo_user_objs.get("demo.aarav.sharma@csm.tech")
                if ase1:
                    asg1 = AssessmentAssignment(assessment_id=assessment.id, ase_id=ase1.id, cohort_id=c1.id, assigned_by=mentor_user.id if mentor_user else None, start_date=now_utc - timedelta(days=10), end_date=now_utc + timedelta(days=10), is_demo=True)
                    db.add(asg1)
                    db.commit()
                    db.refresh(asg1)
                    att1 = AssessmentAttempt(
                        assessment_assignment_id=asg1.id, ase_id=ase1.id, started_at=now_utc - timedelta(days=3), submitted_at=now_utc - timedelta(days=3, minutes=-20),
                        status=AttemptStatus.SUBMITTED, total_score=17.0, max_score=20.0, percentage=85.0, passed=True, violation_count=0, is_demo=True,
                        section_scores=[{"section_id": 1, "title": "Section A: Logical & Pattern Recognition", "score": 9, "max": 10, "percentage": 90.0}, {"section_id": 2, "title": "Section B: Quantitative Aptitude & Critical Reasoning", "score": 8, "max": 10, "percentage": 80.0}],
                        skill_percentages={"Deductive Logic": 90.0, "Pattern Recognition": 85.0, "Quantitative Aptitude": 80.0, "Critical Reasoning": 85.0},
                        strong_areas=["Deductive Logic", "Pattern Recognition", "Quantitative Aptitude", "Critical Reasoning"], weak_areas=[]
                    )
                    db.add(att1)

                # 3. ase2: 65%, passed, flagged 1 violation
                ase2 = demo_user_objs.get("demo.diya.patel@csm.tech")
                if ase2:
                    asg2 = AssessmentAssignment(assessment_id=assessment.id, ase_id=ase2.id, cohort_id=c1.id, assigned_by=mentor_user.id if mentor_user else None, start_date=now_utc - timedelta(days=10), end_date=now_utc + timedelta(days=10), is_demo=True)
                    db.add(asg2)
                    db.commit()
                    db.refresh(asg2)
                    att2 = AssessmentAttempt(
                        assessment_assignment_id=asg2.id, ase_id=ase2.id, started_at=now_utc - timedelta(days=2), submitted_at=now_utc - timedelta(days=2, minutes=-22),
                        status=AttemptStatus.SUBMITTED, total_score=13.0, max_score=20.0, percentage=65.0, passed=True, violation_count=1, is_demo=True,
                        section_scores=[{"section_id": 1, "title": "Section A: Logical & Pattern Recognition", "score": 7, "max": 10, "percentage": 70.0}, {"section_id": 2, "title": "Section B: Quantitative Aptitude & Critical Reasoning", "score": 6, "max": 10, "percentage": 60.0}],
                        skill_percentages={"Deductive Logic": 70.0, "Pattern Recognition": 60.0, "Quantitative Aptitude": 65.0, "Critical Reasoning": 65.0},
                        strong_areas=["Deductive Logic"], weak_areas=["Pattern Recognition", "Quantitative Aptitude", "Critical Reasoning"]
                    )
                    db.add(att2)
                    db.commit()
                    db.refresh(att2)
                    db.add(ExamViolation(attempt_id=att2.id, type="FULLSCREEN_EXIT", occurred_at=now_utc - timedelta(days=2, minutes=-10), details={"reason": "User exited fullscreen"}))

                # 4. ase3: 45%, failed
                ase3 = demo_user_objs.get("demo.rohan.gupta@csm.tech")
                if ase3:
                    asg3 = AssessmentAssignment(assessment_id=assessment.id, ase_id=ase3.id, cohort_id=c1.id, assigned_by=mentor_user.id if mentor_user else None, start_date=now_utc - timedelta(days=10), end_date=now_utc + timedelta(days=10), is_demo=True)
                    db.add(asg3)
                    db.commit()
                    db.refresh(asg3)
                    att3 = AssessmentAttempt(
                        assessment_assignment_id=asg3.id, ase_id=ase3.id, started_at=now_utc - timedelta(days=1), submitted_at=now_utc - timedelta(days=1, minutes=-28),
                        status=AttemptStatus.SUBMITTED, total_score=9.0, max_score=20.0, percentage=45.0, passed=False, violation_count=0, is_demo=True,
                        section_scores=[{"section_id": 1, "title": "Section A: Logical & Pattern Recognition", "score": 5, "max": 10, "percentage": 50.0}, {"section_id": 2, "title": "Section B: Quantitative Aptitude & Critical Reasoning", "score": 4, "max": 10, "percentage": 40.0}],
                        skill_percentages={"Deductive Logic": 40.0, "Pattern Recognition": 55.0, "Quantitative Aptitude": 45.0, "Critical Reasoning": 40.0},
                        strong_areas=[], weak_areas=["Deductive Logic", "Pattern Recognition", "Quantitative Aptitude", "Critical Reasoning"]
                    )
                    db.add(att3)

                # 5. ase4: 90%, passed, clean
                ase4 = demo_user_objs.get("demo.ananya.verma@csm.tech")
                if ase4:
                    asg4 = AssessmentAssignment(assessment_id=assessment.id, ase_id=ase4.id, cohort_id=c2.id, assigned_by=mentor_user.id if mentor_user else None, start_date=now_utc - timedelta(days=10), end_date=now_utc + timedelta(days=10), is_demo=True)
                    db.add(asg4)
                    db.commit()
                    db.refresh(asg4)
                    att4 = AssessmentAttempt(
                        assessment_assignment_id=asg4.id, ase_id=ase4.id, started_at=now_utc - timedelta(hours=18), submitted_at=now_utc - timedelta(hours=17, minutes=35),
                        status=AttemptStatus.SUBMITTED, total_score=18.0, max_score=20.0, percentage=90.0, passed=True, violation_count=0, is_demo=True,
                        section_scores=[{"section_id": 1, "title": "Section A: Logical & Pattern Recognition", "score": 9, "max": 10, "percentage": 90.0}, {"section_id": 2, "title": "Section B: Quantitative Aptitude & Critical Reasoning", "score": 9, "max": 10, "percentage": 90.0}],
                        skill_percentages={"Deductive Logic": 95.0, "Pattern Recognition": 90.0, "Quantitative Aptitude": 85.0, "Critical Reasoning": 90.0},
                        strong_areas=["Deductive Logic", "Pattern Recognition", "Quantitative Aptitude", "Critical Reasoning"], weak_areas=[]
                    )
                    db.add(att4)

                # 6. ase5: 35%, AUTO_SUBMITTED_VIOLATION (2 violations)
                ase5 = demo_user_objs.get("demo.kabir.mehta@csm.tech")
                if ase5:
                    asg5 = AssessmentAssignment(assessment_id=assessment.id, ase_id=ase5.id, cohort_id=c2.id, assigned_by=mentor_user.id if mentor_user else None, start_date=now_utc - timedelta(days=10), end_date=now_utc + timedelta(days=10), is_demo=True)
                    db.add(asg5)
                    db.commit()
                    db.refresh(asg5)
                    att5 = AssessmentAttempt(
                        assessment_assignment_id=asg5.id, ase_id=ase5.id, started_at=now_utc - timedelta(hours=8), submitted_at=now_utc - timedelta(hours=7, minutes=50),
                        status=AttemptStatus.AUTO_SUBMITTED_VIOLATION, total_score=7.0, max_score=20.0, percentage=35.0, passed=False, violation_count=2,
                        auto_submit_reason="Exceeded maximum allowed security violations (2/2)", is_demo=True,
                        section_scores=[{"section_id": 1, "title": "Section A: Logical & Pattern Recognition", "score": 4, "max": 10, "percentage": 40.0}, {"section_id": 2, "title": "Section B: Quantitative Aptitude & Critical Reasoning", "score": 3, "max": 10, "percentage": 30.0}],
                        skill_percentages={"Deductive Logic": 30.0, "Pattern Recognition": 40.0, "Quantitative Aptitude": 35.0, "Critical Reasoning": 35.0},
                        strong_areas=[], weak_areas=["Deductive Logic", "Pattern Recognition", "Quantitative Aptitude", "Critical Reasoning"]
                    )
                    db.add(att5)
                    db.commit()
                    db.refresh(att5)
                    db.add(ExamViolation(attempt_id=att5.id, type="FULLSCREEN_EXIT", occurred_at=now_utc - timedelta(hours=7, minutes=55), details={"reason": "Fullscreen exited"}))
                    db.add(ExamViolation(attempt_id=att5.id, type="TAB_SWITCH", occurred_at=now_utc - timedelta(hours=7, minutes=50), details={"reason": "Tab hidden / visibility change"}))

                # 7. ase6: assigned, NOT attempted (handles zero attempts gracefully)
                ase6 = demo_user_objs.get("demo.ishita.roy@csm.tech")
                if ase6:
                    asg6 = AssessmentAssignment(assessment_id=assessment.id, ase_id=ase6.id, cohort_id=c2.id, assigned_by=mentor_user.id if mentor_user else None, start_date=now_utc - timedelta(days=2), end_date=now_utc + timedelta(days=12), is_demo=True)
                    db.add(asg6)

                db.commit()

                # =============================================================
                # Phase 5 Seed Data: Trainings, Live Classes, Notifications
                # =============================================================
                existing_training = db.query(Training).first()
                if not existing_training:
                    # 1. Trainings
                    tr1 = Training(
                        title="Advanced Distributed Systems & Microservices",
                        description="Deep dive into resilient microservices architecture, circuit breakers, and event-driven patterns.",
                        skill_category="System Architecture Logic",
                        type="Self-paced",
                        resources=[{"name": "Microservices Patterns Reference", "url": "https://microservices.io", "type": "link"}],
                        duration_hours=4.0,
                        created_by=admin_user.id if admin_user else 1,
                        is_demo=True
                    )
                    tr2 = Training(
                        title="Pattern Recognition & Algorithm Optimization",
                        description="Master algorithmic patterns, binary shift optimizations, and memory efficiency techniques.",
                        skill_category="Pattern Recognition",
                        type="Workshop",
                        resources=[{"name": "Algorithm Patterns Cheat Sheet", "url": "https://leetcode.com/explore", "type": "link"}],
                        duration_hours=2.5,
                        created_by=mentor_user.id if mentor_user else 2,
                        is_demo=True
                    )
                    db.add_all([tr1, tr2])
                    db.commit()
                    db.refresh(tr1)
                    db.refresh(tr2)

                    # 2. Training Assignments
                    # ase1: COMPLETED
                    if ase1:
                        ta1 = TrainingAssignment(
                            training_id=tr1.id, ase_id=ase1.id, cohort_id=c1.id,
                            assigned_by=mentor_user.id if mentor_user else 2,
                            due_date=now_utc + timedelta(days=5), status="COMPLETED",
                            progress_percent=100.0, completed_at=now_utc - timedelta(days=1), is_demo=True
                        )
                        db.add(ta1)
                    # ase2: IN_PROGRESS
                    if ase2:
                        ta2 = TrainingAssignment(
                            training_id=tr1.id, ase_id=ase2.id, cohort_id=c1.id,
                            assigned_by=mentor_user.id if mentor_user else 2,
                            due_date=now_utc + timedelta(days=7), status="IN_PROGRESS",
                            progress_percent=60.0, is_demo=True
                        )
                        db.add(ta2)
                    # ase3: NOT_STARTED (Overdue for testing overdue widget!)
                    if ase3:
                        ta3 = TrainingAssignment(
                            training_id=tr2.id, ase_id=ase3.id, cohort_id=c1.id,
                            assigned_by=mentor_user.id if mentor_user else 2,
                            due_date=now_utc - timedelta(days=1), status="NOT_STARTED", # Overdue
                            progress_percent=0.0, is_demo=True
                        )
                        db.add(ta3)
                    # ase4: IN_PROGRESS
                    if ase4:
                        ta4 = TrainingAssignment(
                            training_id=tr2.id, ase_id=ase4.id, cohort_id=c2.id,
                            assigned_by=mentor_user.id if mentor_user else 2,
                            due_date=now_utc + timedelta(days=4), status="IN_PROGRESS",
                            progress_percent=35.0, is_demo=True
                        )
                        db.add(ta4)

                    db.commit()

                    # 3. Live Class & Attendees
                    lc1 = LiveClass(
                        title="Interactive System Architecture & gRPC Masterclass",
                        description="Live interactive architecture session covering service mesh, load balancing, and RPC contracts.",
                        start_time=now_utc + timedelta(days=1),
                        duration_minutes=60,
                        audience_type="COHORT",
                        cohort_id=c1.id,
                        meeting_link="https://teams.microsoft.com/l/meetup-join/19%3ameeting_arch_masterclass%40thread.v2/0",
                        provider="MANUAL",
                        created_by=mentor_user.id if mentor_user else 2,
                        is_demo=True
                    )
                    db.add(lc1)
                    db.commit()
                    db.refresh(lc1)

                    if ase1:
                        db.add(LiveClassAttendee(live_class_id=lc1.id, ase_id=ase1.id, status="ATTENDED", marked_at=now_utc, marked_by=mentor_user.id if mentor_user else 2, is_demo=True))
                    if ase2:
                        db.add(LiveClassAttendee(live_class_id=lc1.id, ase_id=ase2.id, status="INVITED", is_demo=True))
                    if ase3:
                        db.add(LiveClassAttendee(live_class_id=lc1.id, ase_id=ase3.id, status="INVITED", is_demo=True))

                    # 4. Notifications
                    if ase1:
                        db.add(Notification(
                            user_id=ase1.id,
                            title="Welcome to L&K Skill Hub",
                            message="Your account is active. Explore your dashboard and training programs.",
                            type="GENERAL",
                            link="/ase/dashboard",
                            is_read=True,
                            is_demo=True
                        ))
                        db.add(Notification(
                            user_id=ase1.id,
                            title="Live Class Scheduled: System Architecture Masterclass",
                            message="You are invited to join the upcoming live session on Teams.",
                            type="LIVE_CLASS",
                            link="/ase/schedule",
                            is_read=False,
                            is_demo=True
                        ))

                    # 5. Phase 6 Demo Chat Session & Usage Logs
                    if ase1 and mentor and not db.query(ChatSession).first():
                        session1 = ChatSession(
                            user_id=ase1.id,
                            title="General Assessment Guidance",
                            is_active=True
                        )
                        db.add(session1)
                        db.flush()

                        db.add(ChatMessage(
                            session_id=session1.id,
                            user_id=ase1.id,
                            sender_role="USER",
                            content="What are my weakest skills based on my latest assessment?"
                        ))
                        db.add(ChatMessage(
                            session_id=session1.id,
                            user_id=ase1.id,
                            sender_role="ASSISTANT",
                            content="Based on your recent assessment results, your primary focus area is **Logical Thinking & Data Structures** (currently below 70%).\n\n**Recommended Next Steps:**\n1. Review the *Advanced Async Python* training module on your My Learning page.\n2. Practice section questions with 25-minute focused interval drills.\n3. Attend the upcoming Mentor Live Q&A session.",
                            feedback="UP"
                        ))

                        db.add(LLMUsageLog(
                            user_id=ase1.id,
                            role="ASE",
                            provider="mock",
                            model="mock-gpt-4",
                            prompt_tokens=142,
                            completion_tokens=68,
                            total_tokens=210
                        ))
                        db.add(LLMUsageLog(
                            user_id=mentor.id,
                            role="MENTOR",
                            provider="mock",
                            model="mock-gpt-4",
                            prompt_tokens=215,
                            completion_tokens=94,
                            total_tokens=309
                        ))

                    db.commit()
                    logger.info("Phase 5 & 6 Demo Data seeded successfully!")

                logger.info("Phase 4 & 5 Demo Data seeding complete!")

        # Phase 7 Seeding
        from app.seed_phase7 import seed_phase7_data
        seed_phase7_data()

        # Phase 13 Seeding: Default SSO configuration
        from app.models.phase13_models import SSOConfiguration
        if not db.query(SSOConfiguration).first():
            db.add(SSOConfiguration(allow_local_login=True, auto_provision_ase=False))
            db.commit()


    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
