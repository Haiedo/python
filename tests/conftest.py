"""
Pytest configuration and fixtures
"""
import pytest
from app import create_app, db
from app.models.user import User
from app.models.group import Group, GroupMember
from app.models.category import Category


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    app = create_app('testing')
    return app


@pytest.fixture(scope='function')
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def init_database(app):
    """Initialize database with test data"""
    with app.app_context():
        # Create tables
        db.create_all()

        # Create test category
        category = Category(
            name='Food',
            icon='🍔',
            color='#FF5733'
        )
        db.session.add(category)

        # Create test users
        admin_user = User(
            username='admin_test',
            email='admin@test.com',
            full_name='Admin User',
            is_superadmin=True
        )
        admin_user.set_password('admin123')

        client_user = User(
            username='client_test',
            email='client@test.com',
            full_name='Client User'
        )
        client_user.set_password('client123')

        db.session.add(admin_user)
        db.session.add(client_user)
        db.session.commit()

        yield db

        # Cleanup
        db.session.remove()
        db.drop_all()


@pytest.fixture
def admin_user(init_database):
    """Get admin user"""
    return User.query.filter_by(username='admin_test').first()


@pytest.fixture
def client_user(init_database):
    """Get client user"""
    return User.query.filter_by(username='client_test').first()


@pytest.fixture
def admin_token(client, init_database):
    """Get JWT token for admin user"""
    response = client.post('/api/auth/login', json={
        'username': 'admin_test',
        'password': 'admin123'
    })
    return response.json['access_token']


@pytest.fixture
def client_token(client, init_database):
    """Get JWT token for client user"""
    response = client.post('/api/auth/login', json={
        'username': 'client_test',
        'password': 'client123'
    })
    return response.json['access_token']


@pytest.fixture
def test_group(init_database, admin_user):
    """Create test group with admin user"""
    group = Group(
        name='Test Group',
        description='Test group for unit tests',
        currency='VND'
    )
    db.session.add(group)
    db.session.flush()

    # Add admin as member
    membership = GroupMember(
        user_id=admin_user.id,
        group_id=group.id,
        role='admin'
    )
    db.session.add(membership)
    db.session.commit()

    return group


def get_auth_headers(token):
    """Helper function to get authorization headers"""
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
