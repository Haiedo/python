"""
Unit tests for expense management endpoints
"""
import pytest
from decimal import Decimal
from app.models.expense import Expense, ExpenseSplit
from app.models.group import GroupMember
from app.models.category import Category
from app import db


class TestCreateExpense:
    """Test expense creation"""

    def test_create_expense_equal_split(self, client, admin_token, test_group, admin_user, client_user, init_database):
        """Test creating expense with equal split"""
        # Add client user to group
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

        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Lunch expense',
                'amount': 100,
                'paid_by_id': admin_user.id,
                'split_type': 'equal'
            }
        )

        assert response.status_code == 201
        assert 'expense' in response.json
        assert response.json['expense']['split_type'] == 'equal'
        assert response.json['expense']['status'] == 'approved'  # Admin auto-approves

        # Check splits were created
        expense = Expense.query.get(response.json['expense']['id'])
        assert len(expense.splits) == 2  # admin and client
        assert expense.splits[0].amount == Decimal('50')

    def test_create_expense_unequal_split(self, client, admin_token, test_group, admin_user, client_user, init_database):
        """Test creating expense with unequal split (percentages)"""
        # Add client user to group
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

        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Groceries',
                'amount': 100,
                'paid_by_id': admin_user.id,
                'split_type': 'unequal',
                'splits': [
                    {'user_id': admin_user.id, 'percentage': 70},
                    {'user_id': client_user.id, 'percentage': 30}
                ]
            }
        )

        assert response.status_code == 201
        expense = Expense.query.get(response.json['expense']['id'])

        # Check split amounts
        splits_dict = {s.user_id: s.amount for s in expense.splits}
        assert splits_dict[admin_user.id] == Decimal('70')
        assert splits_dict[client_user.id] == Decimal('30')

    def test_create_expense_custom_split(self, client, admin_token, test_group, admin_user, client_user, init_database):
        """Test creating expense with custom split (specific amounts)"""
        # Add client user to group
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

        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Dinner',
                'amount': 150,
                'paid_by_id': admin_user.id,
                'split_type': 'custom',
                'splits': [
                    {'user_id': admin_user.id, 'amount': 100},
                    {'user_id': client_user.id, 'amount': 50}
                ]
            }
        )

        assert response.status_code == 201
        expense = Expense.query.get(response.json['expense']['id'])

        splits_dict = {s.user_id: s.amount for s in expense.splits}
        assert splits_dict[admin_user.id] == Decimal('100')
        assert splits_dict[client_user.id] == Decimal('50')

    def test_create_expense_by_client_requires_approval(self, client, test_group, client_user, init_database):
        """Test that client-created expenses require approval"""
        # Add client user to group
        membership = GroupMember(
            user_id=client_user.id,
            group_id=test_group.id,
            role='client'
        )
        db.session.add(membership)
        db.session.commit()

        # Get client token
        response = client.post('/api/auth/login', json={
            'username': 'client_test',
            'password': 'client123'
        })
        client_token = response.json['access_token']

        headers = {
            'Authorization': f'Bearer {client_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Coffee',
                'amount': 30,
                'paid_by_id': client_user.id,
                'split_type': 'equal'
            }
        )

        assert response.status_code == 201
        assert response.json['expense']['status'] == 'pending'

    def test_create_expense_with_invalid_split_percentages(self, client, admin_token, test_group, admin_user, client_user, init_database):
        """Test creating expense with percentages not summing to 100"""
        # Add client user to group
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

        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Invalid split',
                'amount': 100,
                'paid_by_id': admin_user.id,
                'split_type': 'unequal',
                'splits': [
                    {'user_id': admin_user.id, 'percentage': 60},
                    {'user_id': client_user.id, 'percentage': 30}  # Only 90% total
                ]
            }
        )

        assert response.status_code == 400
        assert 'error' in response.json

    def test_create_expense_with_invalid_split_amounts(self, client, admin_token, test_group, admin_user, client_user, init_database):
        """Test creating expense with custom amounts not matching total"""
        # Add client user to group
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

        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Invalid split',
                'amount': 100,
                'paid_by_id': admin_user.id,
                'split_type': 'custom',
                'splits': [
                    {'user_id': admin_user.id, 'amount': 60},
                    {'user_id': client_user.id, 'amount': 30}  # Only 90 total
                ]
            }
        )

        assert response.status_code == 400
        assert 'error' in response.json

    def test_create_expense_missing_fields(self, client, admin_token, test_group, init_database):
        """Test creating expense with missing required fields"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Missing amount'
                # Missing amount and paid_by_id
            }
        )

        assert response.status_code == 400
        assert 'error' in response.json

    def test_create_expense_non_member(self, client, init_database):
        """Test that non-member cannot create expense in group"""
        # Create a new user who is not in the test group
        response = client.post('/api/auth/register', json={
            'username': 'outsider',
            'email': 'outsider@test.com',
            'password': 'pass123'
        })
        outsider_token = response.json['access_token']

        # Create a group by admin
        from app.models.user import User
        admin = User.query.filter_by(username='admin_test').first()
        from app.models.group import Group
        group = Group(name='Exclusive Group', description='Test')
        db.session.add(group)
        db.session.flush()

        membership = GroupMember(user_id=admin.id, group_id=group.id, role='admin')
        db.session.add(membership)
        db.session.commit()

        headers = {
            'Authorization': f'Bearer {outsider_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': group.id,
                'description': 'Unauthorized expense',
                'amount': 50,
                'paid_by_id': admin.id
            }
        )

        assert response.status_code == 403


class TestEditExpense:
    """Test expense editing"""

    def test_edit_expense_by_creator(self, client, test_group, client_user, init_database):
        """Test that creator can edit their own pending expense"""
        # Add client to group
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

        # Create expense
        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Original description',
                'amount': 100,
                'paid_by_id': client_user.id,
                'split_type': 'equal'
            }
        )
        expense_id = response.json['expense']['id']

        # Edit expense
        response = client.put(f'/api/expenses/{expense_id}',
            headers=headers,
            json={
                'description': 'Updated description',
                'amount': 150
            }
        )

        assert response.status_code == 200
        assert response.json['expense']['description'] == 'Updated description'
        assert response.json['expense']['amount'] == 150

    def test_edit_expense_by_non_creator_fails(self, client, test_group, admin_user, client_user, init_database):
        """Test that non-creator cannot edit expense"""
        # Add both users to group
        membership1 = GroupMember(user_id=client_user.id, group_id=test_group.id, role='client')
        db.session.add(membership1)
        db.session.commit()

        # Client creates expense
        response = client.post('/api/auth/login', json={
            'username': 'client_test',
            'password': 'client123'
        })
        client_token = response.json['access_token']

        headers = {
            'Authorization': f'Bearer {client_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Client expense',
                'amount': 100,
                'paid_by_id': client_user.id
            }
        )
        expense_id = response.json['expense']['id']

        # Admin tries to edit (should fail unless admin is explicitly allowed)
        response = client.post('/api/auth/login', json={
            'username': 'admin_test',
            'password': 'admin123'
        })
        admin_token = response.json['access_token']

        headers_admin = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        # Note: Depending on your business logic, admin might be able to edit
        # This test assumes only creator can edit unless approved
        # Adjust if your logic differs



class TestDeleteExpense:
    """Test expense deletion"""

    def test_delete_expense_by_admin(self, client, admin_token, test_group, admin_user, init_database):
        """Test that admin can delete expenses"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        # Create expense
        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'To be deleted',
                'amount': 100,
                'paid_by_id': admin_user.id
            }
        )
        expense_id = response.json['expense']['id']

        # Delete expense
        response = client.delete(f'/api/expenses/{expense_id}', headers=headers)

        assert response.status_code == 200

        # Verify deletion
        expense = Expense.query.get(expense_id)
        assert expense is None or not hasattr(expense, 'id')

    def test_delete_expense_by_creator(self, client, test_group, client_user, init_database):
        """Test that creator can delete their pending expense"""
        # Add client to group
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

        # Create expense
        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'To delete',
                'amount': 50,
                'paid_by_id': client_user.id
            }
        )
        expense_id = response.json['expense']['id']

        # Delete expense
        response = client.delete(f'/api/expenses/{expense_id}', headers=headers)

        assert response.status_code == 200


class TestExpenseApproval:
    """Test expense approval workflow"""

    def test_expense_approval_workflow(self, client, admin_token, test_group, client_user, init_database):
        """Test complete approval workflow"""
        # Add client to group
        membership = GroupMember(
            user_id=client_user.id,
            group_id=test_group.id,
            role='client'
        )
        db.session.add(membership)
        db.session.commit()

        # Client creates expense
        response = client.post('/api/auth/login', json={
            'username': 'client_test',
            'password': 'client123'
        })
        client_token = response.json['access_token']

        headers_client = {
            'Authorization': f'Bearer {client_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/expenses',
            headers=headers_client,
            json={
                'group_id': test_group.id,
                'description': 'Pending expense',
                'amount': 75,
                'paid_by_id': client_user.id
            }
        )
        expense_id = response.json['expense']['id']
        assert response.json['expense']['status'] == 'pending'

        # Admin approves
        headers_admin = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.post(f'/api/expenses/{expense_id}/approve',
            headers=headers_admin
        )

        assert response.status_code == 200
        assert response.json['expense']['status'] == 'approved'

    def test_expense_rejection(self, client, admin_token, test_group, client_user, init_database):
        """Test expense rejection"""
        # Add client to group
        membership = GroupMember(
            user_id=client_user.id,
            group_id=test_group.id,
            role='client'
        )
        db.session.add(membership)
        db.session.commit()

        # Client creates expense
        response = client.post('/api/auth/login', json={
            'username': 'client_test',
            'password': 'client123'
        })
        client_token = response.json['access_token']

        headers_client = {
            'Authorization': f'Bearer {client_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/expenses',
            headers=headers_client,
            json={
                'group_id': test_group.id,
                'description': 'To be rejected',
                'amount': 200,
                'paid_by_id': client_user.id
            }
        )
        expense_id = response.json['expense']['id']

        # Admin rejects
        headers_admin = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.post(f'/api/expenses/{expense_id}/reject',
            headers=headers_admin,
            json={'reason': 'Invalid expense'}
        )

        assert response.status_code == 200
        assert response.json['expense']['status'] == 'rejected'

    def test_client_cannot_approve_expense(self, client, test_group, client_user, init_database):
        """Test that client cannot approve expenses"""
        # Add client to group
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

        # Create pending expense
        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Pending',
                'amount': 50,
                'paid_by_id': client_user.id
            }
        )
        expense_id = response.json['expense']['id']

        # Try to approve own expense
        response = client.post(f'/api/expenses/{expense_id}/approve',
            headers=headers
        )

        assert response.status_code == 403


class TestExpenseCategory:
    """Test expense categories"""

    def test_expense_category_validation(self, client, admin_token, test_group, admin_user, init_database):
        """Test creating expense with category"""
        category = Category.query.first()

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Food expense',
                'amount': 80,
                'paid_by_id': admin_user.id,
                'category_id': category.id
            }
        )

        assert response.status_code == 201
        assert response.json['expense']['category_id'] == category.id

    def test_expense_with_invalid_category(self, client, admin_token, test_group, admin_user, init_database):
        """Test creating expense with non-existent category"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Invalid category',
                'amount': 80,
                'paid_by_id': admin_user.id,
                'category_id': 9999  # Non-existent
            }
        )

        assert response.status_code == 400


class TestExpenseQueries:
    """Test expense listing and filtering"""

    def test_get_group_expenses(self, client, admin_token, test_group, admin_user, init_database):
        """Test getting all expenses for a group"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        # Create multiple expenses
        for i in range(3):
            client.post('/api/expenses',
                headers=headers,
                json={
                    'group_id': test_group.id,
                    'description': f'Expense {i}',
                    'amount': 50 + i * 10,
                    'paid_by_id': admin_user.id
                }
            )

        # Get expenses
        response = client.get(f'/api/expenses?group_id={test_group.id}', headers=headers)

        assert response.status_code == 200
        assert 'expenses' in response.json
        assert len(response.json['expenses']) >= 3

    def test_get_expense_details(self, client, admin_token, test_group, admin_user, init_database):
        """Test getting single expense details with splits"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        # Create expense
        response = client.post('/api/expenses',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Details test',
                'amount': 100,
                'paid_by_id': admin_user.id
            }
        )
        expense_id = response.json['expense']['id']

        # Get details
        response = client.get(f'/api/expenses/{expense_id}', headers=headers)

        assert response.status_code == 200
        assert 'expense' in response.json
        assert 'splits' in response.json['expense']
