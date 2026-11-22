from app.models.question import QuestionType
from app.core.scoring import score_question, calculate_assessment_results

class MockQuestion:
    def __init__(self, q_id, q_type, correct, marks, skill):
        self.id = q_id
        self.question_type = q_type
        self.correct_answers = correct
        self.marks = marks
        self.skill_category = skill

class MockSectionQuestion:
    def __init__(self, question):
        self.question = question

class MockSection:
    def __init__(self, s_id, title, questions):
        self.id = s_id
        self.title = title
        self.section_questions = [MockSectionQuestion(q) for q in questions]


def test_single_choice_scoring():
    # Correct answer
    is_corr, marks = score_question(
        question_type=QuestionType.SINGLE_CHOICE,
        correct_answers=["opt1"],
        selected_options=["opt1"],
        marks=2
    )
    assert is_corr is True
    assert marks == 2.0

    # Wrong answer
    is_corr, marks = score_question(
        question_type=QuestionType.SINGLE_CHOICE,
        correct_answers=["opt1"],
        selected_options=["opt2"],
        marks=2
    )
    assert is_corr is False
    assert marks == 0.0

    # Empty answer
    is_corr, marks = score_question(
        question_type=QuestionType.SINGLE_CHOICE,
        correct_answers=["opt1"],
        selected_options=[],
        marks=2
    )
    assert is_corr is False
    assert marks == 0.0

    # Multiple choices selected on single choice question
    is_corr, marks = score_question(
        question_type=QuestionType.SINGLE_CHOICE,
        correct_answers=["opt1"],
        selected_options=["opt1", "opt2"],
        marks=2
    )
    assert is_corr is False
    assert marks == 0.0


def test_multi_choice_scoring():
    # Exact full match
    is_corr, marks = score_question(
        question_type=QuestionType.MULTI_CHOICE,
        correct_answers=["opt1", "opt3"],
        selected_options=["opt3", "opt1"],
        marks=3
    )
    assert is_corr is True
    assert marks == 3.0

    # Partial match (missing one correct answer) -> strict all-or-nothing
    is_corr, marks = score_question(
        question_type=QuestionType.MULTI_CHOICE,
        correct_answers=["opt1", "opt3"],
        selected_options=["opt1"],
        marks=3
    )
    assert is_corr is False
    assert marks == 0.0

    # Extra incorrect choice selected
    is_corr, marks = score_question(
        question_type=QuestionType.MULTI_CHOICE,
        correct_answers=["opt1", "opt3"],
        selected_options=["opt1", "opt2", "opt3"],
        marks=3
    )
    assert is_corr is False
    assert marks == 0.0


def test_calculate_assessment_results_passing():
    q1 = MockQuestion(1, QuestionType.SINGLE_CHOICE, ["opt1"], 2, "Logic")
    q2 = MockQuestion(2, QuestionType.SINGLE_CHOICE, ["opt2"], 2, "Logic")
    q3 = MockQuestion(3, QuestionType.MULTI_CHOICE, ["opt1", "opt2"], 4, "Aptitude")

    sec1 = MockSection(1, "Section 1", [q1, q2])
    sec2 = MockSection(2, "Section 2", [q3])

    # ASE answers q1 correct, q2 wrong, q3 correct
    # Total marks available = 2 + 2 + 4 = 8
    # Total marks obtained = 2 + 0 + 4 = 6
    # Percentage = 6 / 8 * 100 = 75.0%
    responses = {
        1: ["opt1"],
        2: ["opt3"],
        3: ["opt1", "opt2"]
    }

    result = calculate_assessment_results(
        passing_percentage=60.0,
        sections=[sec1, sec2],
        responses_by_question=responses
    )

    assert result["total_score"] == 6.0
    assert result["max_score"] == 8.0
    assert result["percentage"] == 75.0
    assert result["passed"] is True

    # Section 1: 2 / 4 = 50.0%
    assert result["section_scores"][0]["score"] == 2.0
    assert result["section_scores"][0]["max"] == 4.0
    assert result["section_scores"][0]["percentage"] == 50.0

    # Section 2: 4 / 4 = 100.0%
    assert result["section_scores"][1]["score"] == 4.0
    assert result["section_scores"][1]["max"] == 4.0
    assert result["section_scores"][1]["percentage"] == 100.0

    # Skills:
    # Logic: 2 / 4 = 50.0% (< 70 -> weak area)
    # Aptitude: 4 / 4 = 100.0% (>= 70 -> strong area)
    assert result["skill_percentages"]["Logic"] == 50.0
    assert result["skill_percentages"]["Aptitude"] == 100.0
    assert "Aptitude" in result["strong_areas"]
    assert "Logic" in result["weak_areas"]


def test_calculate_assessment_results_failing():
    q1 = MockQuestion(1, QuestionType.SINGLE_CHOICE, ["opt1"], 5, "Algorithms")
    q2 = MockQuestion(2, QuestionType.SINGLE_CHOICE, ["opt2"], 5, "Algorithms")

    sec = MockSection(1, "Coding", [q1, q2])

    # Total 10, obtained 5 = 50.0% < 60%
    responses = {
        1: ["opt1"],
        2: ["opt1"]  # wrong
    }

    result = calculate_assessment_results(
        passing_percentage=60.0,
        sections=[sec],
        responses_by_question=responses
    )

    assert result["percentage"] == 50.0
    assert result["passed"] is False
    assert "Algorithms" in result["weak_areas"]
