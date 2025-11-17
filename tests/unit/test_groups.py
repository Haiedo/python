"""
Unit tests for group management endpoints
"""
import pytest


class TestGroupCreation:
    """Test group creation"""
    pass


class TestGroupMembership:
    """Test group membership operations"""
    pass


class TestGroupRoles:
    """Test group role management"""

    def test_assign_admin_role(self, client, admin_token, test_group, client_user, init_database):
        """Test assigning admin role to a member"""
        # First add as client
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        client.post(f'/api/groups/{test_group.id}/members',
            headers=headers,
            json={'user_id': client_user.id, 'role': 'client'}
        )

        # Update role to admin
        response = client.put(f'/api/groups/{test_group.id}/members/{client_user.id}/role',
            headers=headers,
            json={'role': 'admin'}
        )

        assert response.status_code == 200
        assert response.json['membership']['role'] == 'admin'

    def test_demote_last_admin_fails(self, client, admin_token, test_group, admin_user, init_database):
        """Test that last admin cannot be demoted"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.put(f'/api/groups/{test_group.id}/members/{admin_user.id}/role',
            headers=headers,
            json={'role': 'client'}
        )

        assert response.status_code == 400


class TestGroupOperations:
    """Test group CRUD operations"""

    def test_get_group_details(self, client, admin_token, test_group, init_database):
        """Test getting group details"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.get(f'/api/groups/{test_group.id}', headers=headers)

        assert response.status_code == 200
        assert response.json['group']['name'] == 'Test Group'

    def test_update_group(self, client, admin_token, test_group, init_database):
        """Test updating group details"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.put(f'/api/groups/{test_group.id}',
            headers=headers,
            json={
                'name': 'Updated Group Name',
                'description': 'Updated description'
            }
        )

        assert response.status_code == 200
        assert response.json['group']['name'] == 'Updated Group Name'

    def test_delete_group(self, client, admin_token, test_group, init_database):
        """Test deleting a group"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.delete(f'/api/groups/{test_group.id}', headers=headers)

        assert response.status_code == 200

    def test_leave_group(self, client, admin_token, test_group, client_user, init_database):
        """Test leaving a group"""
        # First add client to group
        headers_admin = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        client.post(f'/api/groups/{test_group.id}/members',
            headers=headers_admin,
            json={'user_id': client_user.id, 'role': 'client'}
        )

        # Get client token
        response = client.post('/api/auth/login', json={
            'username': 'client_test',
            'password': 'client123'
        })
        client_token = response.json['access_token']

        headers_client = {
            'Authorization': f'Bearer {client_token}',
            'Content-Type': 'application/json'
        }

        # Client leaves group
        response = client.post(f'/api/groups/{test_group.id}/leave',
            headers=headers_client
        )

        assert response.status_code == 200
