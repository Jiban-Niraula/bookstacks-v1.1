from datetime import datetime

from app.extensions import db


class Member(db.Model):
    """
    A library patron. Deliberately separate from User: Users are people who
    log into this system (staff + the legacy self-service accounts); Members
    are patron records staff create and manage (photo, membership number,
    contact info, fine/loan history) and don't need a login at all.
    """
    __tablename__ = "members"

    id = db.Column(db.Integer, primary_key=True)
    membership_number = db.Column(db.String(30), unique=True, nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active")  # active | suspended | archived
    expiry_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def active_loan_count(self):
        from app.models.loan import Loan
        return Loan.query.filter_by(member_id=self.id, returned_at=None).count()

    def to_dict(self):
        return {
            "id": self.id,
            "membershipNumber": self.membership_number,
            "fullName": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "status": self.status,
            "expiryDate": self.expiry_date.isoformat() if self.expiry_date else None,
            "notes": self.notes,
            "activeLoans": self.active_loan_count(),
            "createdAt": self.created_at.isoformat(),
        }
