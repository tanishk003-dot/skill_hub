import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.llm_service import get_llm_provider, is_demo_mode

logger = logging.getLogger(__name__)

class BaseInsightsProvider(ABC):
    """
    Abstract interface for Skill Hub Analytics & Actionable Insights.
    """

    @abstractmethod
    def generate_candidate_improvements(self, skill_percentages: Dict[str, float]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def compute_suggested_focus_area(self, skill_percentages: Dict[str, float]) -> Optional[str]:
        pass

    @abstractmethod
    def evaluate_needs_attention(
        self,
        ase_info: Dict[str, Any],
        latest_attempt: Optional[Dict[str, Any]],
        has_assignment: bool
    ) -> Optional[Dict[str, Any]]:
        pass


class RuleBasedInsightsProvider(BaseInsightsProvider):
    """
    Deterministic rule-based insights engine.
    """
    DEFAULT_ACTION_TEMPLATES = {
        "Deductive Logic": {
            "HIGH": "Review propositional calculus and syllogisms. Complete 15 deductive logic practice drills.",
            "MEDIUM": "Refine speed on conditional premises and multi-step deduction problems."
        },
        "Conditional Reasoning": {
            "HIGH": "Study truth tables, contrapositive inference, and hypothesis testing patterns.",
            "MEDIUM": "Practice identifying subtle logical fallacies in conditional statements."
        },
        "Pattern Recognition": {
            "HIGH": "Practice numeric, geometric, and recursive sequence problem sets daily.",
            "MEDIUM": "Focus on high-speed sequence completion under timed constraints."
        },
        "Critical Reasoning": {
            "HIGH": "Study assumption identification, argument strengthening, and weakening principles.",
            "MEDIUM": "Analyze business case studies to evaluate underlying assumptions."
        },
        "Quantitative Aptitude": {
            "HIGH": "Strengthen arithmetic fundamentals, percentages, ratios, and time-complexity estimation.",
            "MEDIUM": "Practice rapid mental math calculations and data sufficiency shortcuts."
        },
        "Data Interpretation": {
            "HIGH": "Practice reading complex graphs, multi-column tables, and rate-of-change metrics.",
            "MEDIUM": "Work on fast approximation techniques for large dataset comparisons."
        }
    }

    def generate_candidate_improvements(self, skill_percentages: Dict[str, float]) -> Dict[str, Any]:
        if not skill_percentages:
            return {
                "strong_areas": [],
                "weak_areas": [],
                "improvements": [],
                "primary_focus_area": "No skill evaluations completed yet.",
                "is_ai": False,
                "provider": "rule-based"
            }

        strong_areas = []
        weak_areas = []
        improvements = []

        for skill, score in skill_percentages.items():
            score_val = round(float(score), 1)
            templates = self.DEFAULT_ACTION_TEMPLATES.get(skill, {
                "HIGH": f"Dedicated practice and foundational review required in {skill}.",
                "MEDIUM": f"Targeted problem sets recommended to elevate {skill} score above 70%."
            })

            if score_val < 50.0:
                priority = "HIGH"
                weak_areas.append(skill)
                improvements.append({
                    "skill": skill,
                    "score": score_val,
                    "priority": priority,
                    "priority_badge": "High Priority (< 50%)",
                    "suggested_action": templates["HIGH"],
                    "target_goal": "Target: Reach at least 65% in next assessment attempt"
                })
            elif score_val < 70.0:
                priority = "MEDIUM"
                weak_areas.append(skill)
                improvements.append({
                    "skill": skill,
                    "score": score_val,
                    "priority": priority,
                    "priority_badge": "Medium Priority (50-70%)",
                    "suggested_action": templates["MEDIUM"],
                    "target_goal": "Target: Reach 75%+ proficiency"
                })
            else:
                strong_areas.append(skill)

        improvements.sort(key=lambda x: (0 if x["priority"] == "HIGH" else 1, x["score"]))

        primary_focus = improvements[0]["skill"] if improvements else (
            strong_areas[0] if strong_areas else "General Aptitude"
        )

        return {
            "strong_areas": strong_areas,
            "weak_areas": weak_areas,
            "improvements": improvements,
            "primary_focus_area": primary_focus,
            "is_ai": False,
            "provider": "rule-based"
        }

    def compute_suggested_focus_area(self, skill_percentages: Dict[str, float]) -> Optional[str]:
        if not skill_percentages:
            return "Pending First Assessment"
        lowest_skill = min(skill_percentages.items(), key=lambda x: x[1])
        if lowest_skill[1] < 70.0:
            return f"Strengthen {lowest_skill[0]} ({lowest_skill[1]:.0f}%)"
        return "Advanced Competencies"

    def evaluate_needs_attention(
        self,
        ase_info: Dict[str, Any],
        latest_attempt: Optional[Dict[str, Any]],
        has_assignment: bool
    ) -> Optional[Dict[str, Any]]:
        if latest_attempt and (
            latest_attempt.get("violation_count", 0) > 0 or 
            latest_attempt.get("status") == "AUTO_SUBMITTED_VIOLATION"
        ):
            v_count = latest_attempt.get("violation_count", 0)
            return {
                "ase_id": ase_info["id"],
                "ase_name": ase_info["name"],
                "ase_email": ase_info["email"],
                "reason": f"Proctoring security flag ({v_count} violations recorded)",
                "severity": "CRITICAL",
                "score": latest_attempt.get("percentage"),
                "status": latest_attempt.get("status")
            }

        if latest_attempt and latest_attempt.get("status") in ["SUBMITTED", "AUTO_SUBMITTED", "COMPLETED"]:
            if not latest_attempt.get("passed", False):
                pct = latest_attempt.get("percentage", 0.0)
                return {
                    "ase_id": ase_info["id"],
                    "ase_name": ase_info["name"],
                    "ase_email": ase_info["email"],
                    "reason": f"Failed passing requirement ({pct:.1f}%)",
                    "severity": "HIGH",
                    "score": pct,
                    "status": latest_attempt.get("status")
                }

        if has_assignment and not latest_attempt:
            return {
                "ase_id": ase_info["id"],
                "ase_name": ase_info["name"],
                "ase_email": ase_info["email"],
                "reason": "Assigned evaluation has not been attempted",
                "severity": "MEDIUM",
                "score": None,
                "status": "NOT_ATTEMPTED"
            }

        return None


class LLMInsightsProvider(BaseInsightsProvider):
    """
    AI-powered Insights Engine with automatic fallback to RuleBasedInsightsProvider.
    """
    def __init__(self):
        self._fallback = RuleBasedInsightsProvider()

    def generate_candidate_improvements(self, skill_percentages: Dict[str, float]) -> Dict[str, Any]:
        # Always build baseline from rule-based
        base_result = self._fallback.generate_candidate_improvements(skill_percentages)
        if not skill_percentages:
            return base_result

        try:
            provider = get_llm_provider()
            demo_mode = is_demo_mode()
            
            # Format prompt for LLM
            prompt = (
                f"Candidate skill evaluation scores:\n"
                f"{json.dumps(skill_percentages, indent=2)}\n\n"
                f"Weak skills needing focus: {base_result['weak_areas']}\n"
                f"Provide concise, tailored improvement directives for the weak areas."
            )
            
            messages = [
                {"role": "system", "content": "You are an expert technical skills coach. Provide actionable, concise engineering learning guidance."},
                {"role": "user", "content": prompt}
            ]

            llm_reply, _, _ = provider.generate_completion(messages, max_tokens=400, temperature=0.6)
            
            base_result["is_ai"] = True
            base_result["provider"] = provider.provider_name
            base_result["demo_mode"] = demo_mode
            base_result["ai_study_plan"] = llm_reply
            return base_result
        except Exception as e:
            logger.warning(f"LLMInsightsProvider failed, falling back to RuleBased: {e}")
            base_result["is_ai"] = False
            base_result["provider"] = "rule-based (fallback)"
            return base_result

    def compute_suggested_focus_area(self, skill_percentages: Dict[str, float]) -> Optional[str]:
        return self._fallback.compute_suggested_focus_area(skill_percentages)

    def evaluate_needs_attention(
        self,
        ase_info: Dict[str, Any],
        latest_attempt: Optional[Dict[str, Any]],
        has_assignment: bool
    ) -> Optional[Dict[str, Any]]:
        return self._fallback.evaluate_needs_attention(ase_info, latest_attempt, has_assignment)


# Global service instances
rule_based_insights_service = RuleBasedInsightsProvider()
llm_insights_service = LLMInsightsProvider()
insights_service = llm_insights_service

def mark_ai_insights_stale(db: Session, ase_id: int):
    """Marks cached AI recommendations stale when a new attempt is submitted or training is assigned."""
    from app.models.chat import AIInsightsCache
    cache = db.query(AIInsightsCache).filter(AIInsightsCache.ase_id == ase_id).first()
    if cache:
        cache.is_stale = True
        db.commit()
