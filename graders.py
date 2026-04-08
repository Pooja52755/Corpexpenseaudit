"""Deterministic graders for CorpExpenseAudit tasks."""

from typing import Dict, Any, List
from models import AuditState, GraderMetrics, FraudType
from environment import CorpExpenseAudit


class TaskGrader:
    """Base grader for tasks."""
    
    @staticmethod
    def grade_easy_task(state: AuditState) -> GraderMetrics:
        """Grade the easy task."""
        return TaskGrader._grade_task(state, "easy")
    
    @staticmethod
    def grade_medium_task(state: AuditState) -> GraderMetrics:
        """Grade the medium task."""
        return TaskGrader._grade_task(state, "medium")
    
    @staticmethod
    def grade_hard_task(state: AuditState) -> GraderMetrics:
        """Grade the hard task."""
        return TaskGrader._grade_task(state, "hard")
    
    @staticmethod
    def _grade_task(state: AuditState, difficulty: str) -> GraderMetrics:
        """Grade a task based on agent decisions."""
        
        total_claims = len(state.all_claims)
        correct_categorizations = 0
        total_categorizations = 0
        
        correctly_detected_fraud = 0
        total_fraudulent_claims = sum(1 for c in state.all_claims if c.is_fraud)
        false_positive_fraud = 0
        
        correctly_rejected_fraudulent = 0
        correctly_rejected_invalid = 0
        incorrectly_approved_fraudulent = 0
        correctly_approved_valid = 0
        gst_correct = 0
        info_requests_useful = 0
        
        avg_confidence = 0.0
        confidence_count = 0
        
        # Analyze each claim
        for claim in state.all_claims:
            claim_id = claim.claim_id
            
            # 1. Check categorization
            if claim_id in state.categorizations:
                total_categorizations += 1
                categorized = state.categorizations[claim_id]
                if categorized.lower() == claim.correct_category.lower():
                    correct_categorizations += 1
            
            # 2. Check GST verification
            if claim_id in state.gst_verifications:
                gst_status = state.gst_verifications[claim_id]
                if not claim.has_gst_invoice and gst_status == "not_applicable":
                    gst_correct += 1
                elif claim.has_gst_invoice and claim.gst_invoice_valid and gst_status == "compliant":
                    gst_correct += 1
                elif claim.has_gst_invoice and not claim.gst_invoice_valid and gst_status == "non_compliant":
                    gst_correct += 1
            
            # 3. Check fraud flagging
            if claim_id in state.fraud_flags:
                if claim.is_fraud:
                    correctly_detected_fraud += 1
                else:
                    false_positive_fraud += 1
            
            # 4. Check approvals vs rejections
            if claim_id in state.approvals:
                if claim.is_fraud:
                    incorrectly_approved_fraudulent += 1
                else:
                    correctly_approved_valid += 1
            
            if claim_id in state.rejections:
                if claim.is_fraud:
                    correctly_rejected_fraudulent += 1
                elif not claim.policy_compliant:
                    correctly_rejected_invalid += 1
        
        # Calculate metrics
        categorization_accuracy = correct_categorizations / total_categorizations if total_categorizations > 0 else 0.0
        
        fraud_detection_rate = correctly_detected_fraud / total_fraudulent_claims if total_fraudulent_claims > 0 else 1.0
        false_positive_rate = false_positive_fraud / (total_claims - total_fraudulent_claims) if (total_claims - total_fraudulent_claims) > 0 else 0.0
        
        gst_accuracy = gst_correct / total_claims if total_claims > 0 else 0.0
        
        # Calculate step efficiency
        steps_used = state.current_step
        max_steps = state.max_steps
        efficiency_score = max(0.0, 1.0 - (steps_used / max_steps))
        
        # Build detailed results
        detailed_results = {
            "categorization": {
                "correct": correct_categorizations,
                "total": total_categorizations,
                "accuracy": categorization_accuracy
            },
            "fraud_detection": {
                "correctly_detected": correctly_detected_fraud,
                "total_fraudulent": total_fraudulent_claims,
                "false_positives": false_positive_fraud,
                "detection_rate": fraud_detection_rate,
                "false_positive_rate": false_positive_rate
            },
            "approvals_rejections": {
                "correctly_approved_valid": correctly_approved_valid,
                "correctly_rejected_fraudulent": correctly_rejected_fraudulent,
                "correctly_rejected_invalid": correctly_rejected_invalid,
                "incorrectly_approved_fraudulent": incorrectly_approved_fraudulent
            },
            "gst": {
                "correct": gst_correct,
                "total": total_claims,
                "accuracy": gst_accuracy
            },
            "efficiency": {
                "steps_used": steps_used,
                "max_steps": max_steps,
                "efficiency_score": efficiency_score
            },
            "reward": {
                "total_reward": state.total_reward,
                "step_count": len(state.step_rewards)
            }
        }
        
        # Calculate final score based on difficulty
        fraud_approval_penalty = incorrectly_approved_fraudulent * 0.10
        
        if difficulty == "easy":
            # Easy: focus on basic categorization and simple decisions
            final_score = (
                0.4 * categorization_accuracy +
                0.3 * fraud_detection_rate +
                0.2 * gst_accuracy +
                0.1 * efficiency_score -
                fraud_approval_penalty
            )
        elif difficulty == "medium":
            # Medium: balance between all metrics
            final_score = (
                0.25 * categorization_accuracy +
                0.35 * fraud_detection_rate +
                0.25 * gst_accuracy +
                0.15 * efficiency_score -
                fraud_approval_penalty
            )
        else:  # hard
            # Hard: emphasis on fraud detection and accuracy
            final_score = (
                0.20 * categorization_accuracy +
                0.40 * fraud_detection_rate +
                0.25 * gst_accuracy +
                0.15 * efficiency_score -
                fraud_approval_penalty
            )
        
        # Clamp score between 0 and 1
        final_score = max(0.0, min(1.0, final_score))
        
        return GraderMetrics(
            task_id=state.task_id,
            difficulty=difficulty,
            final_score=final_score,
            correct_categorizations=correct_categorizations,
            total_claims=total_claims,
            correctly_detected_fraud=correctly_detected_fraud,
            total_fraudulent=total_fraudulent_claims,
            correctly_approved_valid=correctly_approved_valid,
            correctly_rejected_invalid=correctly_rejected_invalid,
            correctly_rejected_fraudulent=correctly_rejected_fraudulent,
            incorrectly_approved_fraudulent=incorrectly_approved_fraudulent,
            avg_confidence=avg_confidence,
            gst_accuracy=gst_accuracy,
            total_steps_used=steps_used,
            efficiency_score=efficiency_score,
            detailed_results=detailed_results
        )


def run_easy_grader(env: CorpExpenseAudit) -> GraderMetrics:
    """Run the grader for easy task."""
    if env.state is None:
        raise RuntimeError("Environment not initialized")
    return TaskGrader.grade_easy_task(env.state)


def run_medium_grader(env: CorpExpenseAudit) -> GraderMetrics:
    """Run the grader for medium task."""
    if env.state is None:
        raise RuntimeError("Environment not initialized")
    return TaskGrader.grade_medium_task(env.state)


def run_hard_grader(env: CorpExpenseAudit) -> GraderMetrics:
    """Run the grader for hard task."""
    if env.state is None:
        raise RuntimeError("Environment not initialized")
    return TaskGrader.grade_hard_task(env.state)


def print_grader_results(metrics: GraderMetrics) -> None:
    """Print grader results in a formatted manner."""
    print("\n" + "="*70)
    print(f"TASK GRADING RESULTS - {metrics.difficulty.upper()}")
    print("="*70)
    print(f"Task ID: {metrics.task_id}")
    print(f"Final Score: {metrics.final_score:.4f} / 1.0000")
    print("-"*70)
    print(f"Categorization Accuracy: {metrics.correct_categorizations}/{metrics.total_claims} ({metrics.detailed_results['categorization']['accuracy']:.2%})")
    print(f"Fraud Detection: {metrics.correctly_detected_fraud}/{metrics.total_fraudulent} ({metrics.detailed_results['fraud_detection']['detection_rate']:.2%})")
    print(f"False Positive Rate: {metrics.detailed_results['fraud_detection']['false_positives']} false alarms")
    print(f"GST Accuracy: {metrics.correctly_detected_fraud} verified correctly")
    print(f"Approvals: {metrics.correctly_approved_valid} valid claims approved")
    print(f"Rejections: {metrics.correctly_rejected_fraudulent} fraudulent + {metrics.correctly_rejected_invalid} invalid")
    print(f"Fraud Approval Errors: {metrics.incorrectly_approved_fraudulent} (Heavy penalty)")
    print(f"Steps Used: {metrics.total_steps_used} / {metrics.detailed_results['efficiency']['max_steps']}")
    print(f"Efficiency Score: {metrics.efficiency_score:.2%}")
    print(f"Total Reward Accumulated: {metrics.detailed_results['reward']['total_reward']:.4f}")
    print("="*70 + "\n")
