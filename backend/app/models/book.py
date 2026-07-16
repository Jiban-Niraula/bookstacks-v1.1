from app.extensions import db


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    genre = db.Column(db.String(80), nullable=False, default="General")
    total_copies = db.Column(db.Integer, nullable=False, default=1)

    def active_loan_count(self):
        from app.models.loan import Loan
        return Loan.query.filter_by(book_id=self.id, returned_at=None).count()

    def available_copies(self):
        return self.total_copies - self.active_loan_count()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "genre": self.genre,
            "totalCopies": self.total_copies,
            "availableCopies": self.available_copies(),
        }
