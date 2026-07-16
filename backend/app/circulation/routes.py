from flask import jsonify, request

from app.books.services import get_book_or_404
from app.circulation import bp
from app.circulation.services import (
    issue_to_member, my_loans, receive_return, self_borrow, self_or_staff_return,
)
from app.decorators import current_user_id, login_required, permission_required


# ---- Self-service borrow/return (any authenticated user) ----
# NOTE: this is not the same thing as staff "issuing" a book to a member --
# see /api/circulation/issue below.

@bp.post("/api/books/<int:book_id>/borrow")
@login_required
def borrow_book(book_id):
    book = get_book_or_404(book_id)
    self_borrow(book, current_user_id())
    return jsonify(book.to_dict())


@bp.post("/api/books/<int:book_id>/return")
@login_required
def return_book(book_id):
    book = get_book_or_404(book_id)
    self_or_staff_return(book, current_user_id(), request.current_user["role"])
    return jsonify(book.to_dict())


# ---- Staff-mediated circulation ----

@bp.post("/api/circulation/issue")
@permission_required("circulation:issue")
def issue():
    data = request.get_json(silent=True) or {}
    book_id = data.get("bookId")
    member_id = data.get("memberId")
    if not book_id or not member_id:
        return jsonify(error="bookId and memberId are required"), 400

    loan = issue_to_member(book_id, member_id, current_user_id())
    return jsonify(loan.to_dict()), 201


@bp.post("/api/circulation/return/<int:loan_id>")
@permission_required("circulation:return")
def return_loan(loan_id):
    loan = receive_return(loan_id)
    return jsonify(loan.to_dict())


# ---- My loans ----

@bp.get("/api/my/loans")
@login_required
def my_loans_route():
    loans = my_loans(current_user_id())
    return jsonify([loan.to_dict() for loan in loans])
