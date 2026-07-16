from app.errors import AppError

UPDATABLE_TEXT_FIELDS = (
    ("fullName", "full_name"), ("email", "email"), ("phone", "phone"),
    ("address", "address"), ("notes", "notes"),
)
VALID_STATUSES = ("active", "suspended", "archived")


def validate_new_member(data):
    membership_number = (data.get("membershipNumber") or "").strip()
    full_name = (data.get("fullName") or "").strip()

    if not membership_number or not full_name:
        raise AppError("membershipNumber and fullName are required", 400)
    return membership_number, full_name
