"""Data models for CorpExpenseAudit environment."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from datetime import datetime


class ClaimCategory(str, Enum):
    """Valid expense claim categories."""
    TRAVEL = "travel"
    MEALS = "meals"
    ACCOMMODATION = "accommodation"
    OFFICE_SUPPLIES = "office_supplies"
    EQUIPMENT = "equipment"
    ENTERTAINMENT = "entertainment"
    MISCELLANEOUS = "miscellaneous"


class ClaimStatus(str, Enum):
    """Claim processing status."""
    PENDING_REVIEW = "pending_review"
    REVIEWED = "reviewed"
    FLAGGED = "flagged"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_INFO = "needs_info"


class GSTStatus(str, Enum):
    """GST compliance status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    UNVERIFIABLE = "unverifiable"
    NOT_APPLICABLE = "not_applicable"


class FraudType(str, Enum):
    """Types of fraud patterns detected."""
    DUPLICATE_CLAIM = "duplicate_claim"
    INFLATED_AMOUNT = "inflated_amount"
    SAME_DAY_ROUND_TRIP = "same_day_round_trip"
    FAKE_GST_INVOICE = "fake_gst_invoice"
    PERSONAL_VS_BUSINESS = "personal_vs_business"
    MISMATCHED_DATES = "mismatched_dates"
    SERIAL_CLAIM_PATTERN = "serial_claim_pattern"


class ExpenseClaim(BaseModel):
    """Individual expense claim model."""
    claim_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    employee_id: str
    amount: float
    claimed_category: str  # User's categorization (may be wrong)
    correct_category: str  # Ground truth
    description: str
    date_submitted: datetime
    date_of_expense: datetime
    has_gst_invoice: bool
    gst_invoice_valid: bool  # Ground truth
    merchant_name: str
    merchant_city: Optional[str] = None
    mileage_claimed: Optional[float] = None
    is_fraud: bool = False  # Ground truth
    fraud_types: List[FraudType] = Field(default_factory=list)
    fraudulent_reason: Optional[str] = None
    policy_compliant: bool = True  # Ground truth for policy
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActionInspectClaim(BaseModel):
    """Action: Inspect a specific claim."""
    claim_id: str


class ActionCategorizeClaim(BaseModel):
    """Action: Categorize a claim."""
    claim_id: str
    category: str
    confidence: float = Field(ge=0.0, le=1.0)


class ActionVerifyGST(BaseModel):
    """Action: Verify GST compliance."""
    claim_id: str


class ActionFlagFraud(BaseModel):
    """Action: Flag a claim as fraudulent."""
    claim_id: str
    reason: str
    fraud_types: List[str] = Field(default_factory=list)


class ActionApproveClaim(BaseModel):
    """Action: Approve a claim."""
    claim_id: str
    approved_amount: float


class ActionRejectClaim(BaseModel):
    """Action: Reject a claim."""
    claim_id: str
    reason: str


class ActionRequestMoreInfo(BaseModel):
    """Action: Request more information for a claim."""
    claim_id: str
    information_needed: str


class ActionExportReport(BaseModel):
    """Action: Export final audit report."""
    pass


class AuditState(BaseModel):
    """Current state of the audit task."""
    task_id: str
    task_difficulty: str
    all_claims: List[ExpenseClaim]
    pending_claims: List[str]  # claim_ids
    reviewed_decisions: Dict[str, Dict[str, Any]]  # claim_id -> decision
    current_step: int
    max_steps: int
    total_reward: float = 0.0
    step_rewards: List[float] = Field(default_factory=list)
    inspections: Dict[str, int] = Field(default_factory=dict)  # Track inspection count per claim
    gst_verifications: Dict[str, GSTStatus] = Field(default_factory=dict)
    categorizations: Dict[str, str] = Field(default_factory=dict)
    fraud_flags: Dict[str, str] = Field(default_factory=dict)
    approvals: Dict[str, float] = Field(default_factory=dict)
    rejections: Dict[str, str] = Field(default_factory=dict)
    info_requests: Dict[str, str] = Field(default_factory=dict)
    audit_complete: bool = False
    final_accuracy: Optional[float] = None
    final_report: Optional[Dict[str, Any]] = None


class GraderMetrics(BaseModel):
    """Metrics returned by graders."""
    task_id: str
    difficulty: str
    final_score: float = Field(ge=0.0, le=1.0)
    correct_categorizations: int
    total_claims: int
    correctly_detected_fraud: int
    total_fraudulent: int
    correctly_approved_valid: int
    correctly_rejected_invalid: int
    correctly_rejected_fraudulent: int
    incorrectly_approved_fraudulent: int
    avg_confidence: float
    gst_accuracy: float
    total_steps_used: int
    efficiency_score: float
    detailed_results: Dict[str, Any] = Field(default_factory=dict)
