"""Current contribution eligibility; age is always calculated, never persisted."""
from datetime import date
from utils.date_utils import age_on
from utils.validators import ValidationError

LABELS = {
    "ELIGIBLE": "Eligible",
    "UNDER_23": "Not eligible - Under 23",
    "DECEASED": "Not eligible - Deceased",
    "DOB_UNKNOWN": "Review required - Date of birth missing",
    "LIVING_UNKNOWN": "Review required - Living status unknown",
    "ARCHIVED": "Not eligible - Archived",
}
MESSAGES = {
    "ELIGIBLE": "Living member, age 23 or older.",
    "UNDER_23": "This member is not yet eligible for annual family contribution. Contribution begins at age 23.",
    "DECEASED": "This member is deceased and is not eligible for contribution.",
    "DOB_UNKNOWN": "Contribution eligibility cannot be determined because the member's date of birth has not been recorded.",
    "LIVING_UNKNOWN": "Confirm that this member is living before recording contribution.",
    "ARCHIVED": "Restore this archived member before recording a new contribution.",
}


def get_member_contribution_eligibility(member, on=None):
    def get(key, default=None):
        return member.get(key, default) if isinstance(member, dict) else getattr(member, key, default)
    living = get("living_status")
    living = getattr(living, "value", living)
    age = age_on(get("date_of_birth"), on)
    code = ("DECEASED" if living == "DECEASED" else
            "DOB_UNKNOWN" if age is None else
            "LIVING_UNKNOWN" if living != "LIVING" else
            "UNDER_23" if age < 23 else
            "ARCHIVED" if not get("is_active", True) else "ELIGIBLE")
    return dict(eligibility=code, eligibility_label=LABELS[code], eligibility_message=MESSAGES[code],
                eligible=code == "ELIGIBLE", age=age)


def require_eligible(member, on=None):
    result = get_member_contribution_eligibility(member, on)
    if not result["eligible"]:
        raise ValidationError(result["eligibility_message"])
    return result


def historical_period(period, on=None):
    on = on or date.today()
    def get(key):
        return period.get(key) if isinstance(period, dict) else getattr(period, key)
    status = get("status")
    year = get("year")
    reference = get("due_date") or get("start_date")
    return (getattr(status, "value", status) == "CLOSED" or
            (year is not None and year < on.year) or
            (year is None and reference is not None and reference.year < on.year))
