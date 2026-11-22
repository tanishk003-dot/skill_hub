import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.models.user import User, UserRole
from app.models.cohort import Cohort, CohortMember
from app.models.training import TrainingAssignment
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.models.phase9_models import AseReadinessHistory, AseRiskSignal
from app.services.readiness_service import calculate_ase_readiness

FORMULAS = {
    "time_to_productivity": "Avg(Days from enrollment to first Readiness Score >= 75%)",
    "training_roi": "Average Skill Uplift % = Mean(Post-Training Assessment % - Pre-Training Baseline %)",
    "causation_note": "Note: These operational metrics reflect empirical correlations across learning touchpoints and do not constitute proven mathematical causation."
}

def get_ceo_command_center_analytics(db: Session) -> Dict[str, Any]:
    ases = db.query(User).filter(User.role == UserRole.ASE, User.is_active == True).all()
    total_ases = len(ases)

    # 1. Org-wide readiness average
    readiness_scores = []
    for ase in ases:
        r = calculate_ase_readiness(db, ase.id)
        readiness_scores.append(r["overall_score"])

    org_readiness_avg = round(sum(readiness_scores) / total_ases, 1) if total_ases > 0 else 0.0

    # 2. Dynamic Time-to-productivity (days from enrollment to first Readiness Score >= 75%)
    # Minimum sample threshold: 5 ASEs
    MIN_SAMPLE_SIZE = 5
    ttp_days_list = []
    for ase in ases:
        # Check readiness history or successful attempt >= 75%
        hist = db.query(AseReadinessHistory).filter(
            AseReadinessHistory.ase_id == ase.id,
            AseReadinessHistory.overall_score >= 75.0
        ).order_by(AseReadinessHistory.created_at.asc()).first()
        if hist and hist.created_at and ase.created_at:
            enroll_dt = ase.created_at.date() if hasattr(ase.created_at, 'date') else ase.created_at
            eval_dt = hist.created_at.date() if hasattr(hist.created_at, 'date') else hist.created_at
            diff = (eval_dt - enroll_dt).days
            ttp_days_list.append(max(0, diff))
        else:
            # Fallback to submitted attempt >= 75%
            first_pass = db.query(AssessmentAttempt).filter(
                AssessmentAttempt.ase_id == ase.id,
                AssessmentAttempt.percentage >= 75.0,
                AssessmentAttempt.status == AttemptStatus.SUBMITTED
            ).order_by(AssessmentAttempt.submitted_at.asc()).first()
            if first_pass and first_pass.submitted_at and ase.created_at:
                enroll_dt = ase.created_at.date() if hasattr(ase.created_at, 'date') else ase.created_at
                sub_dt = first_pass.submitted_at.date() if hasattr(first_pass.submitted_at, 'date') else first_pass.submitted_at
                diff = (sub_dt - enroll_dt).days
                ttp_days_list.append(max(0, diff))

    ttp_sample_size = len(ttp_days_list)
    if ttp_sample_size >= MIN_SAMPLE_SIZE:
        time_to_productivity_days = round(sum(ttp_days_list) / ttp_sample_size, 1)
        time_to_productivity_display = f"{time_to_productivity_days} Days"
        time_to_productivity_status = "Computed"
    else:
        time_to_productivity_days = None
        time_to_productivity_display = "Insufficient data"
        time_to_productivity_status = f"Insufficient data (N={ttp_sample_size}, minimum {MIN_SAMPLE_SIZE} required)"

    # 3. Dynamic Training ROI (Skill Uplift % = Post-Training Assessment % - Pre-Training Baseline %)
    # Minimum sample threshold: 5 evaluated trainings
    uplift_list = []
    completed_trainings = db.query(TrainingAssignment).filter(
        TrainingAssignment.status == "COMPLETED",
        TrainingAssignment.completed_at.isnot(None)
    ).all()

    for ta in completed_trainings:
        pre_att = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.ase_id == ta.ase_id,
            AssessmentAttempt.submitted_at < ta.completed_at,
            AssessmentAttempt.status == AttemptStatus.SUBMITTED
        ).order_by(AssessmentAttempt.submitted_at.desc()).first()

        post_att = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.ase_id == ta.ase_id,
            AssessmentAttempt.submitted_at >= ta.completed_at,
            AssessmentAttempt.status == AttemptStatus.SUBMITTED
        ).order_by(AssessmentAttempt.submitted_at.asc()).first()

        if pre_att and post_att:
            uplift = post_att.percentage - pre_att.percentage
            uplift_list.append(uplift)

    roi_sample_size = len(uplift_list)
    if roi_sample_size >= MIN_SAMPLE_SIZE:
        training_roi_uplift_pct = round(sum(uplift_list) / roi_sample_size, 1)
        training_roi_display = f"+{training_roi_uplift_pct}%"
        training_roi_status = "Computed"
    else:
        training_roi_uplift_pct = None
        training_roi_display = "Insufficient data"
        training_roi_status = f"Insufficient data (N={roi_sample_size}, minimum {MIN_SAMPLE_SIZE} required)"

    # 4. Cohort comparisons with privacy masking (< 3 ASEs masked)
    cohorts = db.query(Cohort).all()
    cohort_benchmarks = []
    for c in cohorts:
        members = db.query(CohortMember).filter(CohortMember.cohort_id == c.id).all()
        member_count = len(members)

        if member_count < 3:
            # Requirement 7: Mask groups under 3 ASEs
            cohort_benchmarks.append({
                "cohort_id": c.id,
                "cohort_name": f"Confidential Cohort (Unit #{c.id})",
                "member_count": "< 3 (Masked)",
                "average_readiness": "Masked for Privacy",
                "risk_profile": "Protected",
                "is_masked": True
            })
        else:
            member_ids = [m.ase_id for m in members]
            cohort_scores = [calculate_ase_readiness(db, uid)["overall_score"] for uid in member_ids]
            c_avg = round(sum(cohort_scores) / len(cohort_scores), 1) if cohort_scores else 0.0
            cohort_benchmarks.append({
                "cohort_id": c.id,
                "cohort_name": c.name,
                "member_count": member_count,
                "average_readiness": f"{c_avg}%",
                "risk_profile": "Optimal" if c_avg >= 75 else "Action Required",
                "is_masked": False
            })

    # 5. Org-wide Skill Gap Heatmap (Computed dynamically from submitted assessments)
    skill_totals: Dict[str, List[float]] = {}
    submitted_attempts = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.status == AttemptStatus.SUBMITTED
    ).all()

    for att in submitted_attempts:
        if att.skill_percentages and isinstance(att.skill_percentages, dict):
            for skill, pct in att.skill_percentages.items():
                try:
                    val = float(pct)
                    skill_totals.setdefault(skill, []).append(val)
                except (ValueError, TypeError):
                    continue

    skill_gap_heatmap = []
    attempts_count = len(submitted_attempts)
    if attempts_count >= MIN_SAMPLE_SIZE and skill_totals:
        for skill_name, scores in skill_totals.items():
            mastery = round(sum(scores) / len(scores), 1)
            gap = round(max(0.0, 100.0 - mastery), 1)
            if mastery >= 75.0:
                status_str = "Strong"
            elif mastery >= 65.0:
                status_str = "Moderate Gap"
            else:
                status_str = "High Focus Area"
            skill_gap_heatmap.append({
                "skill": skill_name,
                "mastery_pct": mastery,
                "gap_pct": gap,
                "status": status_str,
                "sample_size": len(scores)
            })
    else:
        # Display explicit insufficient data state when below sample threshold
        skill_gap_heatmap = [
            {"skill": "System Architecture Logic", "mastery_pct": None, "gap_pct": None, "status": "Insufficient data", "sample_size": attempts_count},
            {"skill": "Pattern Recognition", "mastery_pct": None, "gap_pct": None, "status": "Insufficient data", "sample_size": attempts_count},
            {"skill": "Deductive Logic", "mastery_pct": None, "gap_pct": None, "status": "Insufficient data", "sample_size": attempts_count}
        ]

    # 6. Risk distribution
    risks = db.query(AseRiskSignal).all()
    high_risk_count = sum(1 for r in risks if r.risk_level == "HIGH")
    med_risk_count = sum(1 for r in risks if r.risk_level == "MEDIUM")
    low_risk_count = sum(1 for r in risks if r.risk_level == "LOW")

    return {
        "org_readiness_avg": org_readiness_avg,
        "total_active_ases": total_ases,
        "time_to_productivity_days": time_to_productivity_days,
        "time_to_productivity_display": time_to_productivity_display,
        "time_to_productivity_sample_size": ttp_sample_size,
        "time_to_productivity_status": time_to_productivity_status,
        "training_roi_uplift_pct": training_roi_uplift_pct,
        "training_roi_display": training_roi_display,
        "training_roi_sample_size": roi_sample_size,
        "training_roi_status": training_roi_status,
        "formulas": FORMULAS,
        "cohort_benchmarks": cohort_benchmarks,
        "skill_gap_heatmap": skill_gap_heatmap,
        "risk_summary": {
            "high": high_risk_count,
            "medium": med_risk_count,
            "low": max(0, total_ases - high_risk_count - med_risk_count)
        }
    }

def generate_ceo_executive_pdf(db: Session) -> str:
    analytics = get_ceo_command_center_analytics(db)
    
    pdf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "reports"))
    os.makedirs(pdf_dir, exist_ok=True)
    file_path = os.path.join(pdf_dir, f"ceo_executive_report_{int(datetime.now(timezone.utc).timestamp())}.pdf")

    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        'CEOHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E3A8A')
    )
    sub_style = ParagraphStyle(
        'CEOSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B')
    )
    body_bold = ParagraphStyle(
        'CEOBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0F172A')
    )
    formula_style = ParagraphStyle(
        'CEOFormula',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#475569')
    )

    elements = []
    elements.append(Paragraph("L&K SKILL HUB — CEO EXECUTIVE COMMAND CENTER", header_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"Engineering Readiness & Upskilling ROI Diagnostic • {datetime.now(timezone.utc).strftime('%B %d, %Y')}", sub_style))
    elements.append(Spacer(1, 16))

    # KPI Summary Table
    ttp_val_str = analytics.get('time_to_productivity_display') or (f"{analytics['time_to_productivity_days']} Days" if analytics.get('time_to_productivity_days') is not None else "Insufficient data")
    roi_val_str = analytics.get('training_roi_display') or (f"+{analytics['training_roi_uplift_pct']}%" if analytics.get('training_roi_uplift_pct') is not None else "Insufficient data")

    kpi_data = [
        [
            Paragraph("<b>Org-Wide Readiness</b><br/><font size='16' color='#1E3A8A'><b>" + str(analytics['org_readiness_avg']) + "%</b></font>", body_bold),
            Paragraph("<b>Time-to-Productivity</b><br/><font size='14' color='#1E3A8A'><b>" + ttp_val_str + "</b></font>", body_bold),
            Paragraph("<b>Training ROI Uplift</b><br/><font size='14' color='#F97316'><b>" + roi_val_str + "</b></font>", body_bold),
            Paragraph("<b>Active Cohorts</b><br/><font size='16' color='#0F172A'><b>" + str(len(analytics['cohort_benchmarks'])) + "</b></font>", body_bold)
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[130, 130, 130, 130])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 18))

    # Formula Explanations & Causation Notice
    elements.append(Paragraph(f"<b>Time-to-Productivity Formula:</b> {FORMULAS['time_to_productivity']}", formula_style))
    elements.append(Paragraph(f"<b>Training ROI Formula:</b> {FORMULAS['training_roi']}", formula_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"<i>{FORMULAS['causation_note']}</i>", formula_style))
    elements.append(Spacer(1, 16))

    # Cohort Benchmarks (Masked for <3 members)
    elements.append(Paragraph("<b>Cohort Performance Benchmarks (Groups &lt; 3 ASEs Privacy-Masked)</b>", body_bold))
    elements.append(Spacer(1, 6))

    cohort_rows = [["Cohort Name", "Enrolled ASEs", "Mean Readiness", "Operational Profile"]]
    for cb in analytics['cohort_benchmarks']:
        cohort_rows.append([
            str(cb['cohort_name']),
            str(cb['member_count']),
            str(cb['average_readiness']),
            str(cb['risk_profile'])
        ])

    cohort_table = Table(cohort_rows, colWidths=[190, 110, 110, 110])
    cohort_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F8FAFC')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    elements.append(cohort_table)
    elements.append(Spacer(1, 18))

    # Skill Gap Heatmap
    elements.append(Paragraph("<b>Organizational Competency & Skill Gap Distribution</b>", body_bold))
    elements.append(Spacer(1, 6))

    gap_rows = [["Competency Domain", "Mastery %", "Competency Gap %", "Priority Status"]]
    for g in analytics['skill_gap_heatmap']:
        gap_rows.append([
            g['skill'],
            f"{g['mastery_pct']}%",
            f"{g['gap_pct']}%",
            g['status']
        ])

    gap_table = Table(gap_rows, colWidths=[200, 100, 110, 110])
    gap_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F8FAFC')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    elements.append(gap_table)

    doc.build(elements)
    return file_path
