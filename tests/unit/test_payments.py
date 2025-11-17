"""
Unit tests for payment management and payment gateway integration
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
from app.models.payment import Payment
from app.models.group import GroupMember
from app import db


class TestCreatePayment:
    """Test payment creation"""

    def test_create_payment_success(self, client, test_group, admin_user, client_user, init_database):
        """Test creating a payment"""
        # Add both users to group
        membership = GroupMember(
            user_id=client_user.id,
            group_id=test_group.id,
            role='client'
        )
        db.session.add(membership)
        db.session.commit()

        # Login as client
        response = client.post('/api/auth/login', json={
            'username': 'client_test',
            'password': 'client123'
        })
        client_token = response.json['access_token']

        headers = {
            'Authorization': f'Bearer {client_token}',
            'Content-Type': 'application/json'
        }

        # Create payment
        response = client.post('/api/payments',
            headers=headers,
            json={
                'group_id': test_group.id,
                'payee_id': admin_user.id,
                'amount': 100,
                'currency': 'VND',
                'payment_method': 'cash',
                'notes': 'Payment for lunch'
            }
        )

        assert response.status_code == 201
        assert 'payment' in response.json
        assert response.json['payment']['amount'] == 100
        assert response.json['payment']['status'] == 'pending'

    def test_create_payment_missing_fields(self, client, admin_token, test_group, init_database):
        """Test creating payment with missing required fields"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/payments',
            headers=headers,
            json={
                'group_id': test_group.id,
                'amount': 100
                # Missing payee_id
            }
        )

        assert response.status_code == 400
        assert 'error' in response.json

    def test_create_payment_invalid_amount(self, client, admin_token, test_group, client_user, init_database):
        """Test creating payment with invalid amount"""
        # Add client to group
        membership = GroupMember(
            user_id=client_user.id,
            group_id=test_group.id,
            role='client'
        )
        db.session.add(membership)
        db.session.commit()

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        # Negative amount
        response = client.post('/api/payments',
            headers=headers,
            json={
                'group_id': test_group.id,
                'payee_id': client_user.id,
                'amount': -50
            }
        )

        assert response.status_code == 400
        assert 'error' in response.json

        # Zero amount
        response = client.post('/api/payments',
            headers=headers,
            json={
                'group_id': test_group.id,
                'payee_id': client_user.id,
                'amount': 0
            }
        )

        assert response.status_code == 400

    def test_cannot_pay_yourself(self, client, admin_token, test_group, admin_user, init_database):
        """Test that user cannot pay themselves"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/payments',
            headers=headers,
            json={
                'group_id': test_group.id,
                'payee_id': admin_user.id,
                'amount': 100
            }
        )

        assert response.status_code == 400
        assert 'error' in response.json

    def test_payment_to_non_member(self, client, admin_token, test_group, init_database):
        """Test that payment to non-member fails"""
        # Create a user not in the group
        response = client.post('/api/auth/register', json={
            'username': 'outsider',
            'email': 'outsider@test.com',
            'password': 'pass123'
        })
        outsider_data = response.json

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/payments',
            headers=headers,
            json={
                'group_id': test_group.id,
                'payee_id': outsider_data['user']['id'],
                'amount': 100
            }
        )

        assert response.status_code == 400
        assert 'error' in response.json

    def test_payment_from_non_member(self, client, test_group, admin_user, init_database):
        """Test that non-member cannot create payment"""
        # Create outsider user
        response = client.post('/api/auth/register', json={
            'username': 'outsider2',
            'email': 'outsider2@test.com',
            'password': 'pass123'
        })
        outsider_token = response.json['access_token']

        headers = {
            'Authorization': f'Bearer {outsider_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/payments',
            headers=headers,
            json={
                'group_id': test_group.id,
                'payee_id': admin_user.id,
                'amount': 100
            }
        )

        assert response.status_code == 403


class TestPaymentApproval:
    """Test payment approval workflow"""

    def test_payment_approval_by_admin(self, client, admin_token, test_group, admin_user, client_user, init_database):
        """Test that admin can approve payments"""
        # Add client to group
        membership = GroupMember(
            user_id=client_user.id,
            group_id=test_group.id,
            role='client'
        )
        db.session.add(membership)
        db.session.commit()

        # Client creates payment
        response = client.post('/api/auth/login', json={
            'username': 'client_test',
            'password': 'client123'
        })
        client_token = response.json['access_token']

        headers_client = {
            'Authorization': f'Bearer {client_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/payments',
            headers=headers_client,
            json={
                'group_id': test_group.id,
                'payee_id': admin_user.id,
                'amount': 150
            }
        )
        payment_id = response.json['payment']['id']

        # Admin approves
        headers_admin = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.post(f'/api/payments/{payment_id}/approve',
            headers=headers_admin
        )

        assert response.status_code == 200
        assert response.json['payment']['status'] == 'completed'

    def test_payment_rejection(self, client, admin_token, test_group, admin_user, client_user, init_database):
        """Test payment rejection by admin"""
        # Add client to group
        membership = GroupMember(
            user_id=client_user.id,
            group_id=test_group.id,
            role='client'
        )
        db.session.add(membership)
        db.session.commit()

        # Client creates payment
        response = client.post('/api/auth/login', json={
            'username': 'client_test',
            'password': 'client123'
        })
        client_token = response.json['access_token']

        headers_client = {
            'Authorization': f'Bearer {client_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/payments',
            headers=headers_client,
            json={
                'group_id': test_group.id,
                'payee_id': admin_user.id,
                'amount': 200
            }
        )
        payment_id = response.json['payment']['id']

        # Admin rejects
        headers_admin = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.post(f'/api/payments/{payment_id}/reject',
            headers=headers_admin,
            json={'reason': 'Invalid payment'}
        )

        assert response.status_code == 200
        assert response.json['payment']['status'] == 'failed'

    def test_client_cannot_approve_payment(self, client, test_group, admin_user, client_user, init_database):
        """Test that client cannot approve payments"""
        # Add client to group
        membership = GroupMember(
            user_id=client_user.id,
            group_id=test_group.id,
            role='client'
        )
        db.session.add(membership)
        db.session.commit()

        # Client creates payment
        response = client.post('/api/auth/login', json={
            'username': 'client_test',
            'password': 'client123'
        })
        client_token = response.json['access_token']

        headers = {
            'Authorization': f'Bearer {client_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/payments',
            headers=headers,
            json={
                'group_id': test_group.id,
                'payee_id': admin_user.id,
                'amount': 100
            }
        )
        payment_id = response.json['payment']['id']

        # Try to approve own payment
        response = client.post(f'/api/payments/{payment_id}/approve',
            headers=headers
        )

        assert response.status_code == 403


class TestPaymentQueries:
    """Test payment listing and retrieval"""

    def test_get_group_payments(self, client, admin_token, test_group, admin_user, client_user, init_database):
        """Test getting all payments in a group"""
        # Add client to group
        membership = GroupMember(
            user_id=client_user.id,
            group_id=test_group.id,
            role='client'
        )
        db.session.add(membership)
        db.session.commit()

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        # Create multiple payments
        for i in range(3):
            payment = Payment(
                group_id=test_group.id,
                payer_id=client_user.id,
                payee_id=admin_user.id,
                amount=Decimal(50 + i * 10),
                status='completed'
            )
            db.session.add(payment)
        db.session.commit()

        # Get payments
        response = client.get(f'/api/payments?group_id={test_group.id}', headers=headers)

        assert response.status_code == 200
        assert 'payments' in response.json
        assert len(response.json['payments']) >= 3

    def test_get_payment_details(self, client, admin_token, test_group, admin_user, client_user, init_database):
        """Test getting single payment details"""
        # Add client to group
        membership = GroupMember(
            user_id=client_user.id,
            group_id=test_group.id,
            role='client'
        )
        db.session.add(membership)
        db.session.commit()

        # Create payment
        payment = Payment(
            group_id=test_group.id,
            payer_id=client_user.id,
            payee_id=admin_user.id,
            amount=Decimal('125.50'),
            notes='Test payment',
            status='completed'
        )
        db.session.add(payment)
        db.session.commit()

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.get(f'/api/payments/{payment.id}', headers=headers)

        assert response.status_code == 200
        assert 'payment' in response.json
        assert response.json['payment']['amount'] == 125.50


class TestDeletePayment:
    """Test payment deletion"""

    def test_delete_payment_by_admin(self, client, admin_token, test_group, admin_user, client_user, init_database):
        """Test that admin can delete payments"""
        # Add client to group
        membership = GroupMember(
            user_id=client_user.id,
            group_id=test_group.id,
            role='client'
        )
        db.session.add(membership)
        db.session.commit()

        # Create payment
        payment = Payment(
            group_id=test_group.id,
            payer_id=client_user.id,
            payee_id=admin_user.id,
            amount=Decimal('100'),
            status='pending'
        )
        db.session.add(payment)
        db.session.commit()
        payment_id = payment.id

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.delete(f'/api/payments/{payment_id}', headers=headers)

        assert response.status_code == 200



class TestPaymentStatusTracking:
    """Test payment status updates and tracking"""

    def test_payment_status_update(self, client, admin_token, test_group, admin_user, client_user, init_database):
        """Test updating payment status"""
        # Create payment
        payment = Payment(
            group_id=test_group.id,
            payer_id=client_user.id,
            payee_id=admin_user.id,
            amount=Decimal('100'),
            status='pending'
        )
        db.session.add(payment)
        db.session.commit()

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        # Check payment status
        response = client.get(f'/api/payment-gateway/payment-status/{payment.id}',
            headers=headers
        )

        assert response.status_code == 200
        assert 'status' in response.json

    def test_payment_failure_handling(self, client, admin_token, test_group, admin_user, client_user, init_database):
        """Test handling of failed payments"""
        # Create payment
        payment = Payment(
            group_id=test_group.id,
            payer_id=client_user.id,
            payee_id=admin_user.id,
            amount=Decimal('100'),
            status='pending',
            payment_method='vnpay'
        )
        db.session.add(payment)
        db.session.commit()

        # Simulate payment failure
        payment.status = 'failed'
        db.session.commit()

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.get(f'/api/payments/{payment.id}', headers=headers)

        assert response.status_code == 200
        assert response.json['payment']['status'] == 'failed'
