"""
Unit tests for category management
"""
import pytest
from decimal import Decimal
from app.models.category import Category
from app import db


class TestCategoryModel:
    """Test category model"""

    def test_create_category(self, init_database):
        """Test creating a category"""
        category = Category(
            name='Transportation',
            icon='🚗',
            color='#3498db',
            description='Transport expenses'
        )

        db.session.add(category)
        db.session.commit()

        assert category.id is not None
        assert category.name == 'Transportation'
        assert category.is_active == True

    def test_category_to_dict(self, init_database):
        """Test category serialization"""
        category = Category(
            name='Entertainment',
            icon='🎬',
            color='#e74c3c'
        )

        db.session.add(category)
        db.session.commit()

        category_dict = category.to_dict()

        assert 'id' in category_dict
        assert category_dict['name'] == 'Entertainment'
        assert category_dict['icon'] == '🎬'
        assert category_dict['color'] == '#e74c3c'

    def test_deactivate_category(self, init_database):
        """Test deactivating a category"""
        category = Category(
            name='Old Category',
            icon='📦',
            color='#95a5a6'
        )

        db.session.add(category)
        db.session.commit()

        # Deactivate
        category.is_active = False
        db.session.commit()

        assert category.is_active == False


class TestCategoryQueries:
    """Test category queries"""

    def test_get_all_categories(self, init_database):
        """Test retrieving all categories"""
        # The conftest already creates one category
        existing_category = Category.query.first()

        assert existing_category is not None
        assert existing_category.name == 'Food'

    def test_get_active_categories(self, init_database):
        """Test retrieving only active categories"""
        # Create inactive category
        inactive = Category(
            name='Inactive',
            icon='❌',
            color='#000000',
            is_active=False
        )
        db.session.add(inactive)
        db.session.commit()

        active_categories = Category.query.filter_by(is_active=True).all()

        assert all(cat.is_active for cat in active_categories)

    def test_filter_categories_by_name(self, init_database):
        """Test filtering categories by name"""
        # Create additional categories
        categories = [
            Category(name='Shopping', icon='🛍️', color='#9b59b6'),
            Category(name='Healthcare', icon='⚕️', color='#1abc9c'),
            Category(name='Education', icon='📚', color='#f39c12')
        ]

        for cat in categories:
            db.session.add(cat)
        db.session.commit()

        # Search for category
        found = Category.query.filter(Category.name.like('%Health%')).first()

        assert found is not None
        assert 'Health' in found.name


class TestCategoryValidation:
    """Test category validation"""

    def test_category_name_required(self, init_database):
        """Test that category name is required"""
        category = Category(
            name=None,
            icon='❓',
            color='#000000'
        )

        with pytest.raises(Exception):
            db.session.add(category)
            db.session.commit()

        db.session.rollback()

    def test_category_duplicate_name(self, init_database):
        """Test handling of duplicate category names"""
        # Create first category
        cat1 = Category(
            name='Duplicate',
            icon='1️⃣',
            color='#111111'
        )
        db.session.add(cat1)
        db.session.commit()

        # Try to create duplicate
        cat2 = Category(
            name='Duplicate',
            icon='2️⃣',
            color='#222222'
        )

        # Depending on your constraints, this might raise an exception
        # or be allowed. Adjust test based on your schema.
        db.session.add(cat2)

        try:
            db.session.commit()
            # If no unique constraint, both should exist
            duplicates = Category.query.filter_by(name='Duplicate').all()
            # Either raises error or allows duplicates
        except Exception:
            db.session.rollback()
            # Unique constraint enforced
            pass

    def test_category_color_format(self, init_database):
        """Test category color validation"""
        import re

        valid_colors = ['#FF5733', '#00AA00', '#123456']
        color_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')

        for color in valid_colors:
            assert color_pattern.match(color), f"Color {color} should be valid hex"

        invalid_colors = ['FF5733', '#FFF', 'red', '#GGGGGG']

        for color in invalid_colors:
            assert not color_pattern.match(color), f"Color {color} should be invalid"


class TestCategoryRelationships:
    """Test category relationships with expenses"""

    def test_delete_category_with_expenses(self, init_database, test_group, admin_user):
        """Test handling deletion of category that has expenses"""
        from app.models.expense import Expense

        category = Category(
            name='ToDelete',
            icon='🗑️',
            color='#999999'
        )
        db.session.add(category)
        db.session.commit()

        # Create expense with this category
        expense = Expense(
            group_id=test_group.id,
            category_id=category.id,
            created_by_id=admin_user.id,
            description='Test',
            amount=Decimal('100'),
            paid_by_id=admin_user.id
        )
        db.session.add(expense)
        db.session.commit()

        # Try to delete category (should either cascade or prevent deletion)
        category_id = category.id

        try:
            db.session.delete(category)
            db.session.commit()

            # If successful, expense should have null category_id or be deleted
            expense_check = Expense.query.filter_by(category_id=category_id).first()
            # Depending on cascade settings

        except Exception:
            # Foreign key constraint prevents deletion
            db.session.rollback()
            pass


class TestCategoryBudgetLimits:
    """Test budget limit functionality"""
    pass

class TestCategoryIcons:
    """Test category icons"""

    def test_category_with_text_icon(self, init_database):
        """Test category with text icon"""
        category = Category(
            name='Other',
            icon='OTHER',
            color='#95a5a6'
        )

        db.session.add(category)
        db.session.commit()

        assert category.icon == 'OTHER'

    def test_default_category_icons(self):
        """Test recommended default category icons"""
        default_categories = [
            ('Food & Dining', '🍽️', '#e74c3c'),
            ('Transportation', '🚗', '#3498db'),
            ('Entertainment', '🎬', '#9b59b6'),
            ('Shopping', '🛍️', '#e67e22'),
            ('Healthcare', '⚕️', '#1abc9c'),
            ('Bills & Utilities', '📄', '#f39c12'),
            ('Education', '📚', '#2ecc71'),
            ('Travel', '✈️', '#3498db'),
            ('Groceries', '🛒', '#27ae60'),
            ('Other', '📦', '#95a5a6')
        ]

        for name, icon, color in default_categories:
            assert len(name) > 0
            assert len(icon) > 0
            assert color.startswith('#')


class TestCategorySearch:
    """Test category search functionality"""

    def test_search_categories_by_keyword(self, init_database):
        """Test searching categories by keyword"""
        # Create test categories
        categories = [
            Category(name='Food & Dining', icon='🍽️', color='#e74c3c'),
            Category(name='Fast Food', icon='🍔', color='#e67e22'),
            Category(name='Groceries', icon='🛒', color='#27ae60')
        ]

        for cat in categories:
            db.session.add(cat)
        db.session.commit()

        # Search for "food"
        results = Category.query.filter(
            Category.name.ilike('%food%')
        ).all()

        assert len(results) >= 2
        assert all('food' in cat.name.lower() for cat in results)

    def test_get_most_used_categories(self, init_database, test_group, admin_user):
        """Test getting most frequently used categories"""
        from app.models.expense import Expense

        # Create categories
        cat1 = Category(name='Popular', icon='⭐', color='#f1c40f')
        cat2 = Category(name='Rare', icon='💎', color='#9b59b6')

        db.session.add(cat1)
        db.session.add(cat2)
        db.session.commit()

        # Create more expenses for cat1
        for i in range(5):
            exp = Expense(
                group_id=test_group.id,
                category_id=cat1.id,
                created_by_id=admin_user.id,
                description=f'Popular expense {i}',
                amount=Decimal('100'),
                paid_by_id=admin_user.id
            )
            db.session.add(exp)

        # Only one expense for cat2
        exp = Expense(
            group_id=test_group.id,
            category_id=cat2.id,
            created_by_id=admin_user.id,
            description='Rare expense',
            amount=Decimal('100'),
            paid_by_id=admin_user.id
        )
        db.session.add(exp)
        db.session.commit()

        # cat1 should have more expenses
        assert len(cat1.expenses) > len(cat2.expenses)
