from sqlalchemy import or_

from app.errors import AppError
from app.extensions import db
from app.members.validators import UPDATABLE_TEXT_FIELDS, VALID_STATUSES
from app.models import Loan, Member


def list_members(query="", include_archived=False):
    q = Member.query
    if not include_archived:
        q = q.filter(Member.status != "archived")
    if query:
        like = f"%{query}%"
        q = q.filter(
            or_(
                Member.full_name.ilike(like),
                Member.membership_number.ilike(like),
                Member.email.ilike(like),
                Member.phone.ilike(like),
            )
        )
    return q.order_by(Member.full_name).all()


def get_member_or_404(member_id):
    member = db.session.get(Member, member_id)
    if not member:
        raise AppError(f"member {member_id} not found", 404)
    return member


def create_member(membership_number, full_name, data):
    if Member.query.filter_by(membership_number=membership_number).first():
        raise AppError("that membership number is already in use", 409)

    member = Member(
        membership_number=membership_number,
        full_name=full_name,
        email=(data.get("email") or "").strip() or None,
        phone=(data.get("phone") or "").strip() or None,
        address=(data.get("address") or "").strip() or None,
        notes=(data.get("notes") or "").strip() or None,
    )
    db.session.add(member)
    db.session.commit()
    return member


def member_with_loans(member_id):
    member = get_member_or_404(member_id)
    loans = Loan.query.filter_by(member_id=member_id).order_by(Loan.borrowed_at.desc()).all()
    result = member.to_dict()
    result["loans"] = [loan.to_dict() for loan in loans]
    return result


def update_member(member_id, data):
    member = get_member_or_404(member_id)
    for field, attr in UPDATABLE_TEXT_FIELDS:
        if field in data:
            setattr(member, attr, (data[field] or "").strip() or None)

    if "status" in data and data["status"] in VALID_STATUSES:
        member.status = data["status"]

    db.session.commit()
    return member


def archive_member(member_id):
    member = get_member_or_404(member_id)
    if member.active_loan_count() > 0:
        raise AppError(f'Cannot remove "{member.full_name}" — they have books checked out', 400)

    # Soft delete: archive rather than hard-delete. Loan rows reference
    # member_id, and their borrow history should stay intact even after
    # the membership itself is closed.
    member.status = "archived"
    db.session.commit()
    return member_id
