from flask import jsonify, request

from app.books import bp
from app.books.services import create_book, delete_book, get_book_or_404, list_books
from app.books.validators import validate_new_book
from app.decorators import permission_required


@bp.get("")
def list_all():
    return jsonify([b.to_dict() for b in list_books()])


@bp.get("/search")
def search():
    q = request.args.get("q", "").strip()
    return jsonify([b.to_dict() for b in list_books(q)])


@bp.post("")
@permission_required("books:create")
def add():
    data = request.get_json(silent=True) or {}
    title, author, genre, copies = validate_new_book(data)
    book = create_book(title, author, genre, copies)
    return jsonify(book.to_dict()), 201


@bp.delete("/<int:book_id>")
@permission_required("books:delete")
def remove(book_id):
    get_book_or_404(book_id)  # 404s before attempting delete
    deleted_id = delete_book(book_id)
    return jsonify(deleted=deleted_id)
