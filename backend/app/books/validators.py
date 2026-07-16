from app.errors import AppError


def validate_new_book(data):
    title = (data.get("title") or "").strip()
    author = (data.get("author") or "").strip()
    genre = (data.get("genre") or "General").strip()
    copies = data.get("copies")

    if not title or not author:
        raise AppError("title and author are required", 400)

    copies = int(copies) if isinstance(copies, (int, float)) and copies > 0 else 1
    return title, author, genre, copies
