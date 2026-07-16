from datetime import datetime

from app.extensions import db

LOAN_PERIOD_DAYS = 14


class Loan(db.Model):
    """
    A single borrow record. Availability is derived from these rows
    (total_copies minus active loans) rather than a counter on Book, so
    there's one source of truth for who has what and when it's due.

    Two different borrowing paths write to this same table:
      - user_id:   the legacy self-service flow (a logged-in account
                   borrows for itself via /api/books/<id>/borrow).
      - member_id: the real staff workflow (Librarian/Staff issue a book
                   to a Member via /api/circulation/issue).
    Exactly one of the two should be set per loan. issued_by_user_id
    records which staff account processed a member loan, for audit history.
    """
    __tablename__ = "loans"

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=True)
    issued_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    borrowed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    due_at = db.Column(db.DateTime, nullable=False)
    returned_at = db.Column(db.DateTime, nullable=True)

    def is_overdue(self):
        return self.returned_at is None and datetime.utcnow() > self.due_at

    def borrower_name(self):
        if self.member_id:
            from app.models.member import Member
            member = db.session.get(Member, self.member_id)
            return member.full_name if member else None
        if self.user_id:
            from app.models.user import User
            user = db.session.get(User, self.user_id)
            return user.username if user else None
        return None

    def to_dict(self):
        from app.models.book import Book
        book = db.session.get(Book, self.book_id)
        return {
            "id": self.id,
            "bookId": self.book_id,
            "bookTitle": book.title if book else None,
            "memberId": self.member_id,
            "userId": self.user_id,
            "borrowerName": self.borrower_name(),
            "borrowedAt": self.borrowed_at.isoformat(),
            "dueAt": self.due_at.isoformat(),
            "returnedAt": self.returned_at.isoformat() if self.returned_at else None,
            "overdue": self.is_overdue(),
        }
