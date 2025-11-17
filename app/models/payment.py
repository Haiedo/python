from datetime import datetime
from app import db


class Payment(db.Model):
    """Payment model for tracking settlements between users"""
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    payer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    payee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    currency = db.Column(db.String(3), default='VND')
    payment_method = db.Column(db.String(50))
    notes = db.Column(db.Text)
    transaction_id = db.Column(db.String(100), unique=True)
    gateway_response = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    group = db.relationship('Group')
    payer = db.relationship('User', foreign_keys=[payer_id], back_populates='payments_made')
    payee = db.relationship('User', foreign_keys=[payee_id], back_populates='payments_received')
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])

    def to_dict(self):
        """Convert payment to dictionary"""
        return {
            'id': self.id,
            'group_id': self.group_id,
            'payer_id': self.payer_id,
            'payee_id': self.payee_id,
            'amount': float(self.amount),
            'currency': self.currency,
            'payment_method': self.payment_method,
            'notes': self.notes,
            'transaction_id': self.transaction_id,
            'status': self.status,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'payer': self.payer.to_dict() if self.payer else None,
            'payee': self.payee.to_dict() if self.payee else None
        }

    def __repr__(self):
        return f'<Payment {self.payer_id}->{self.payee_id} {self.amount}>'
