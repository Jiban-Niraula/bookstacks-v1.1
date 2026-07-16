from datetime import datetime

from flask import jsonify

from app.dashboard import bp
from app.models import Book, Loan


@bp.get("/stats")
def stats():
    books = Book.query.all()
    total_copies = sum(b.total_copies for b in books)
    total_available = sum(b.available_copies() for b in books)
    overdue = Loan.query.filter(
        Loan.returned_at.is_(None), Loan.due_at < datetime.utcnow()
    ).count()

    return jsonify(
        totalTitles=len(books),
        totalCopies=total_copies,
        totalAvailable=total_available,
        totalBorrowed=total_copies - total_available,
        totalOverdue=overdue,
    )
