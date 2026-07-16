from sqlalchemy import or_

from app.errors import AppError
from app.extensions import db
from app.models import Book, Loan


def list_books(query=""):
    if not query:
        return Book.query.order_by(Book.id).all()
    like = f"%{query}%"
    return (
        Book.query.filter(
            or_(Book.title.ilike(like), Book.author.ilike(like), Book.genre.ilike(like))
        )
        .order_by(Book.id)
        .all()
    )


def get_book_or_404(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        raise AppError(f"book {book_id} not found", 404)
    return book


def create_book(title, author, genre, copies):
    book = Book(title=title, author=author, genre=genre, total_copies=copies)
    db.session.add(book)
    db.session.commit()
    return book


def delete_book(book_id):
    book = get_book_or_404(book_id)
    if book.active_loan_count() > 0:
        raise AppError(f'Cannot delete "{book.title}" — it is currently borrowed', 400)

    Loan.query.filter_by(book_id=book_id).delete()
    db.session.delete(book)
    db.session.commit()
    return book_id
