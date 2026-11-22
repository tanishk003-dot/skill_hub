from typing import List, Dict, Any, Tuple
from app.models.question import QuestionType

def score_question(
    question_type: QuestionType,
    correct_answers: List[str],
    selected_options: List[str],
    marks: int
) -> Tuple[bool, float]:
    """
    Scores a question based on its type and selected options.
    Returns (is_correct: bool, marks_obtained: float).
    """
    if not selected_options:
        return False, 0.0

    # Normalize sets
    correct_set = set(str(a).strip() for a in correct_answers)
    selected_set = set(str(o).strip() for o in selected_options)

    if question_type == QuestionType.SINGLE_CHOICE:
        if len(selected_set) == 1 and selected_set == correct_set:
            return True, float(marks)
        return False, 0.0

    elif question_type == QuestionType.MULTI_CHOICE:
        # Multi-select requires all correct choices and no incorrect choices
        if selected_set == correct_set:
            return True, float(marks)
        return False, 0.0

    return False, 0.0


def calculate_assessment_results(
    passing_percentage: float,
    sections: List[Any],
    responses_by_question: Dict[int, List[str]]
) -> Dict[str, Any]:
    """
    Computes overall score, section breakdown, skill percentages, and pass/fail.
    """
    total_score = 0.0
    max_score = 0.0

    section_scores = []
    skill_stats: Dict[str, Dict[str, float]] = {}  # {skill: {"obtained": x, "max": y}}
    detailed_responses = []

    for section in sections:
        sec_obtained = 0.0
        sec_max = 0.0

        for sq in section.section_questions:
            q = sq.question
            sec_max += q.marks
            max_score += q.marks

            selected = responses_by_question.get(q.id, [])
            is_corr, marks_ob = score_question(
                question_type=q.question_type,
                correct_answers=q.correct_answers,
                selected_options=selected,
                marks=q.marks
            )

            sec_obtained += marks_ob
            total_score += marks_ob

            # Track skill categories
            skill = q.skill_category or "General"
            if skill not in skill_stats:
                skill_stats[skill] = {"obtained": 0.0, "max": 0.0}
            skill_stats[skill]["obtained"] += marks_ob
            skill_stats[skill]["max"] += q.marks

            detailed_responses.append({
                "question_id": q.id,
                "selected_options": selected,
                "is_correct": is_corr,
                "marks_obtained": marks_ob
            })

        sec_pct = round((sec_obtained / sec_max * 100), 1) if sec_max > 0 else 0.0
        section_scores.append({
            "section_id": section.id,
            "title": section.title,
            "score": round(sec_obtained, 2),
            "max": round(sec_max, 2),
            "percentage": sec_pct
        })

    # Overall percentage
    overall_percentage = round((total_score / max_score * 100), 1) if max_score > 0 else 0.0
    passed = overall_percentage >= passing_percentage

    # Skill percentages
    skill_percentages: Dict[str, float] = {}
    strong_areas = []
    weak_areas = []

    for skill, stats in skill_stats.items():
        pct = round((stats["obtained"] / stats["max"] * 100), 1) if stats["max"] > 0 else 0.0
        skill_percentages[skill] = pct
        if pct >= 70.0:
            strong_areas.append(skill)
        else:
            weak_areas.append(skill)

    return {
        "total_score": round(total_score, 2),
        "max_score": round(max_score, 2),
        "percentage": overall_percentage,
        "passed": passed,
        "section_scores": section_scores,
        "skill_percentages": skill_percentages,
        "strong_areas": strong_areas,
        "weak_areas": weak_areas,
        "detailed_responses": detailed_responses
    }
