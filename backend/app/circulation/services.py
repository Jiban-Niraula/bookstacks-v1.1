from datetime import datetime, timedelta

from app.errors import AppError
from app.extensions import db
from app.models import LOAN_PERIOD_DAYS, Book, Loan, Member
from app.permissions import role_has_permission


def get_loan_or_404(loan_id):
    loan = db.session.get(Loan, loan_id)
    if not loan:
        raise AppError(f"loan {loan_id} not found", 404)
    return loan


# ---- Self-service: a logged-in User borrows/returns for their own account ----

def self_borrow(book, user_id):
    if book.available_copies() <= 0:
        raise AppError(f'"{book.title}" has no available copies', 400)

    already = Loan.query.filter_by(book_id=book.id, user_id=user_id, returned_at=None).first()
    if already:
        raise AppError(f'You already have "{book.title}" checked out', 400)

    loan = Loan(
        book_id=book.id,
        user_id=user_id,
        borrowed_at=datetime.utcnow(),
        due_at=datetime.utcnow() + timedelta(days=LOAN_PERIOD_DAYS),
    )
    db.session.add(loan)
    db.session.commit()
    return loan


def self_or_staff_return(book, user_id, role):
    # Staff/Librarian/Super Admin process returns for anyone (the actual
    # "staff receives a returned book" workflow); self-service patron
    # accounts can only return their own loan.
    can_return_for_others = role_has_permission(role, "circulation:return")

    query = Loan.query.filter_by(book_id=book.id, returned_at=None)
    if not can_return_for_others:
        query = query.filter_by(user_id=user_id)
    loan = query.first()

    if not loan:
        scope = "" if can_return_for_others else " under your account"
        raise AppError(f'No active loan found for "{book.title}"{scope}', 400)

    loan.returned_at = datetime.utcnow()
    db.session.commit()
    return loan


# ---- Staff-mediated: Librarian/Staff issue/receive books for a Member ----

def issue_to_member(book_id, member_id, issued_by_user_id):
    book = db.session.get(Book, book_id)
    member = db.session.get(Member, member_id)
    if not book:
        raise AppError(f"book {book_id} not found", 404)
    if not member:
        raise AppError(f"member {member_id} not found", 404)
    if member.status != "active":
        raise AppError(f'"{member.full_name}"\'s membership is {member.status}, not active', 400)
    if book.available_copies() <= 0:
        raise AppError(f'"{book.title}" has no available copies', 400)

    already = Loan.query.filter_by(book_id=book_id, member_id=member_id, returned_at=None).first()
    if already:
        raise AppError(f'"{member.full_name}" already has "{book.title}" checked out', 400)

    loan = Loan(
        book_id=book_id,
        member_id=member_id,
        issued_by_user_id=issued_by_user_id,
        borrowed_at=datetime.utcnow(),
        due_at=datetime.utcnow() + timedelta(days=LOAN_PERIOD_DAYS),
    )
    db.session.add(loan)
    db.session.commit()
    return loan


def receive_return(loan_id):
    loan = get_loan_or_404(loan_id)
    if loan.returned_at:
        raise AppError("that loan was already returned", 400)

    loan.returned_at = datetime.utcnow()
    db.session.commit()
    return loan


def my_loans(user_id):
    return Loan.query.filter_by(user_id=user_id).order_by(Loan.borrowed_at.desc()).all()
