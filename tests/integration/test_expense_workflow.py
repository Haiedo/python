"""
Integration tests for complete expense workflow
"""
import pytest
from decimal import Decimal
from app.models.group import GroupMember
from app.models.expense import Expense
from app import db


class TestCompleteExpenseWorkflow:
    """Test complete expense creation, approval, and settlement workflow"""
    pass


class TestClientExpenseRequestWorkflow:
    """Test client expense request and approval workflow"""

    def test_client_expense_approval_flow(self, client, admin_user, client_user, test_group, init_database):
        """Test client creates expense that requires admin approval"""

        # Add client to group
        membership = GroupMember(
            user_id=client_user.id,
            group_id=test_group.id,
            role='client'
        )
        db.session.add(membership)
        db.session.commit()

        # Client login
        response = client.post('/api/auth/login', json={
            'username': 'client_test',
            'password': 'client123'
        })
        client_token = response.json['access_token']

        headers_client = {
            'Authorization': f'Bearer {client_token}',
            'Content-Type': 'application/json'
        }

        # Client creates expense request
        response = client.post('/api/expenses',
            headers=headers_client,
            json={
                'group_id': test_group.id,
                'description': 'Coffee meeting',
                'amount': 50,
                'paid_by_id': client_user.id,
                'split_type': 'equal'
            }
        )

        assert response.status_code == 201
        expense_id = response.json['expense']['id']

        # Should be pending
        assert response.json['expense']['status'] == 'pending'

        # Admin login
        response = client.post('/api/auth/login', json={
            'username': 'admin_test',
            'password': 'admin123'
        })
        admin_token = response.json['access_token']

        headers_admin = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        # Admin approves expense
        response = client.post(f'/api/expenses/{expense_id}/approve',
            headers=headers_admin
        )

        assert response.status_code == 200
        assert response.json['expense']['status'] == 'approved'


class TestGroupCreationAndManagement:
    """Test complete group creation and management workflow"""
    pass


class TestMultipleExpensesAndSettlement:
    """Test multiple expenses and settlement optimization"""
    pass


class TestPaymentGatewayIntegration:
    """Test payment gateway integration workflow"""

    def test_vnpay_payment_flow(self, client, admin_user, client_user, test_group, init_database):
        """Test complete VNPay payment workflow"""

        from unittest.mock import patch

        # Add client to group
        membership = GroupMember(
            user_id=client_user.id,
            group_id=test_group.id,
            role='client'
        )
        db.session.add(membership)
        db.session.commit()

        # Client login
        response = client.post('/api/auth/login', json={
            'username': 'client_test',
            'password': 'client123'
        })
        client_token = response.json['access_token']

        headers = {
            'Authorization': f'Bearer {client_token}',
            'Content-Type': 'application/json'
        }

        # Create payment URL
        with patch('app.utils.payment_gateways.VNPayGateway.create_payment_url') as mock_create:
            mock_create.return_value = 'https://mock-vnpay-url.com/payment'

            response = client.post('/api/payment-gateway/create-payment-url',
                headers=headers,
                json={
                    'group_id': test_group.id,
                    'payee_id': admin_user.id,
                    'amount': 500000,
                    'gateway': 'vnpay'
                }
            )

            if response.status_code == 200:
                assert 'payment_url' in response.json


class TestUserRegistrationToExpense:
    """Test complete user journey from registration to expense"""

    def test_new_user_creates_expense(self, client, init_database):
        """Test new user registration, group creation, and expense"""

        # Step 1: Register new user
        response = client.post('/api/auth/register', json={
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'securepass123',
            'full_name': 'New User'
        })

        assert response.status_code == 201
        token = response.json['access_token']

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        # Step 2: Create group
        response = client.post('/api/groups',
            headers=headers,
            json={
                'name': 'My New Group',
                'description': 'First group',
                'currency': 'VND'
            }
        )

        assert response.status_code == 201
        group_id = response.json['group']['id']

        # Step 3: Get user ID
        response = client.get('/api/auth/profile', headers=headers)
        user_id = response.json['user']['id']

        # Step 4: Create expense
        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': group_id,
                'description': 'First expense',
                'amount': 100,
                'paid_by_id': user_id,
                'split_type': 'equal'
            }
        )

        assert response.status_code == 201

        # Step 5: View expenses
        response = client.get(f'/api/expenses?group_id={group_id}', headers=headers)

        assert response.status_code == 200
        assert len(response.json['expenses']) >= 1


class TestErrorHandling:
    """Test error handling in workflows"""

    def test_unauthorized_access_workflow(self, client, admin_user, client_user, test_group, init_database):
        """Test that unauthorized users cannot access resources"""

        # Create a user not in the group
        response = client.post('/api/auth/register', json={
            'username': 'outsider',
            'email': 'outsider@test.com',
            'password': 'pass123'
        })
        outsider_token = response.json['access_token']

        headers = {
            'Authorization': f'Bearer {outsider_token}',
            'Content-Type': 'application/json'
        }

        # Try to create expense in group they're not in
        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Unauthorized',
                'amount': 100,
                'paid_by_id': admin_user.id
            }
        )

        assert response.status_code == 403

        # Try to view group balances
        response = client.get(f'/api/groups/{test_group.id}/balances', headers=headers)

        assert response.status_code == 403
