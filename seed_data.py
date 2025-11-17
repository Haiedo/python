"""
Seed data script for initial database setup
"""
from app import create_app, db
from app.models.category import Category
from app.models.user import User
from app.models.group import Group, GroupMember
from app.models.expense import Expense, ExpenseSplit
from app.models.payment import Payment
from datetime import datetime, timedelta
import random


def seed_categories():
    """Create default expense categories"""
    categories = [
        {'name': 'Ăn uống', 'icon': 'utensils', 'color': '#FF6B6B', 'description': 'Nhà hàng, siêu thị, giao đồ ăn'},
        {'name': 'Di chuyển', 'icon': 'car', 'color': '#4ECDC4', 'description': 'Xăng, xe bus, taxi, đỗ xe'},
        {'name': 'Giải trí', 'icon': 'film', 'color': '#45B7D1', 'description': 'Phim, game, sự kiện'},
        {'name': 'Mua sắm', 'icon': 'shopping-bag', 'color': '#FFA07A', 'description': 'Quần áo, điện tử, đồ gia dụng'},
        {'name': 'Hóa đơn', 'icon': 'file-text', 'color': '#98D8C8', 'description': 'Điện, nước, internet, điện thoại'},
        {'name': 'Y tế', 'icon': 'heart', 'color': '#F67280', 'description': 'Khám bệnh, thuốc, bảo hiểm'},
        {'name': 'Du lịch', 'icon': 'plane', 'color': '#6C5CE7', 'description': 'Vé máy bay, khách sạn, nghỉ dưỡng'},
        {'name': 'Giáo dục', 'icon': 'book', 'color': '#FDCB6E', 'description': 'Sách, khóa học, học phí'},
        {'name': 'Nhà ở', 'icon': 'home', 'color': '#00B894', 'description': 'Thuê nhà, bảo trì, nội thất'},
        {'name': 'Khác', 'icon': 'package', 'color': '#B2BEC3', 'description': 'Chi tiêu khác'}
    ]

    created_categories = []
    for cat_data in categories:
        category = Category(**cat_data)
        db.session.add(category)
        created_categories.append(category)
        print(f"Created category: {cat_data['name']}")

    db.session.commit()
    return created_categories


def create_users():
    """Create admin and demo users"""
    users_data = [
        {
            'username': 'admin',
            'email': 'admin@expensesplitter.com',
            'full_name': 'Quản trị viên',
            'phone': '0901234567',
            'password': 'admin123',
            'is_superadmin': True
        },
        {
            'username': 'nguyenvana',
            'email': 'nguyenvana@example.com',
            'full_name': 'Nguyễn Văn A',
            'phone': '0912345678',
            'password': 'password123',
            'is_superadmin': False
        },
        {
            'username': 'tranthib',
            'email': 'tranthib@example.com',
            'full_name': 'Trần Thị B',
            'phone': '0923456789',
            'password': 'password123',
            'is_superadmin': False
        },
        {
            'username': 'levanc',
            'email': 'levanc@example.com',
            'full_name': 'Lê Văn C',
            'phone': '0934567890',
            'password': 'password123',
            'is_superadmin': False
        },
        {
            'username': 'phamthid',
            'email': 'phamthid@example.com',
            'full_name': 'Phạm Thị D',
            'phone': '0945678901',
            'password': 'password123',
            'is_superadmin': False
        }
    ]

    created_users = []
    for user_data in users_data:
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            full_name=user_data['full_name'],
            phone=user_data['phone'],
            is_superadmin=user_data['is_superadmin']
        )
        user.set_password(user_data['password'])
        db.session.add(user)
        created_users.append(user)
        role = "ADMIN" if user_data['is_superadmin'] else "USER"
        print(f"Created {role}: {user_data['username']} (password: {user_data['password']})")

    db.session.commit()
    return created_users


def create_groups(users):
    """Create demo groups with members"""
    groups_data = [
        {
            'name': 'Nhóm bạn cùng phòng',
            'description': 'Chi tiêu chung cho phòng trọ',
            'currency': 'VND',
            'admin_idx': 1,  # nguyenvana
            'member_indices': [1, 2, 3]  # nguyenvana, tranthib, levanc
        },
        {
            'name': 'Du lịch Đà Lạt',
            'description': 'Chuyến du lịch cuối tuần',
            'currency': 'VND',
            'admin_idx': 2,  # tranthib
            'member_indices': [2, 3, 4]  # tranthib, levanc, phamthid
        },
        {
            'name': 'Team công ty',
            'description': 'Các hoạt động team building',
            'currency': 'VND',
            'admin_idx': 1,  # nguyenvana
            'member_indices': [1, 2, 3, 4]  # All regular users
        }
    ]

    created_groups = []
    for group_data in groups_data:
        group = Group(
            name=group_data['name'],
            description=group_data['description'],
            currency=group_data['currency']
        )
        db.session.add(group)
        db.session.flush()  # Get group ID

        # Add admin
        admin_member = GroupMember(
            user_id=users[group_data['admin_idx']].id,
            group_id=group.id,
            role='admin'
        )
        db.session.add(admin_member)

        # Add other members
        for idx in group_data['member_indices']:
            if idx != group_data['admin_idx']:  # Skip admin, already added
                member = GroupMember(
                    user_id=users[idx].id,
                    group_id=group.id,
                    role='member'
                )
                db.session.add(member)

        created_groups.append(group)
        print(f"Created group: {group_data['name']} with {len(group_data['member_indices'])} members")

    db.session.commit()
    return created_groups


def create_expenses(groups, users, categories):
    """Create demo expenses"""
    if not groups or not users or not categories:
        print("⊘ Skipping expenses: No groups, users, or categories available")
        return []

    expenses_data = [
        # Group 1: Nhóm bạn cùng phòng
        {
            'group_idx': 0,
            'creator_idx': 1,
            'category_idx': 0,  # Ăn uống
            'amount': 500000,
            'description': 'Đi siêu thị mua đồ ăn tháng này',
            'split_type': 'equal',
            'member_indices': [1, 2, 3]
        },
        {
            'group_idx': 0,
            'creator_idx': 2,
            'category_idx': 4,  # Hóa đơn
            'amount': 300000,
            'description': 'Tiền điện tháng 11',
            'split_type': 'equal',
            'member_indices': [1, 2, 3]
        },
        # Group 2: Du lịch Đà Lạt
        {
            'group_idx': 1,
            'creator_idx': 2,
            'category_idx': 6,  # Du lịch
            'amount': 2000000,
            'description': 'Khách sạn 2 đêm ở Đà Lạt',
            'split_type': 'equal',
            'member_indices': [2, 3, 4]
        },
        {
            'group_idx': 1,
            'creator_idx': 3,
            'category_idx': 0,  # Ăn uống
            'amount': 600000,
            'description': 'Ăn tối nhà hàng',
            'split_type': 'equal',
            'member_indices': [2, 3, 4]
        },
        # Group 3: Team công ty
        {
            'group_idx': 2,
            'creator_idx': 1,
            'category_idx': 2,  # Giải trí
            'amount': 1200000,
            'description': 'Team building bowling',
            'split_type': 'equal',
            'member_indices': [1, 2, 3, 4]
        }
    ]

    created_expenses = []
    for exp_data in expenses_data:
        expense = Expense(
            group_id=groups[exp_data['group_idx']].id,
            category_id=categories[exp_data['category_idx']].id,
            created_by_id=users[exp_data['creator_idx']].id,
            paid_by_id=users[exp_data['creator_idx']].id,  # Người tạo là người chi tiền
            amount=exp_data['amount'],
            description=exp_data['description'],
            split_type=exp_data['split_type'],
            status='approved',
            expense_date=datetime.now() - timedelta(days=random.randint(1, 30))
        )
        db.session.add(expense)
        db.session.flush()

        # Create expense splits
        num_members = len(exp_data['member_indices'])
        split_amount = exp_data['amount'] / num_members

        for idx in exp_data['member_indices']:
            split = ExpenseSplit(
                expense_id=expense.id,
                user_id=users[idx].id,
                amount=split_amount,
                percentage=100 / num_members
            )
            db.session.add(split)

        created_expenses.append(expense)
        print(f"Created expense: {exp_data['description']} - {exp_data['amount']:,} VND")

    db.session.commit()
    return created_expenses


def create_payments(groups, users):
    """Create demo payments"""
    if not groups or not users:
        print("⊘ Skipping payments: No groups or users available")
        return []

    payments_data = [
        {
            'group_idx': 0,
            'payer_idx': 2,
            'payee_idx': 1,
            'amount': 166667,
            'notes': 'Trả tiền siêu thị',
            'status': 'completed'
        },
        {
            'group_idx': 1,
            'payer_idx': 3,
            'payee_idx': 2,
            'amount': 666667,
            'notes': 'Trả tiền khách sạn',
            'status': 'completed'
        },
        {
            'group_idx': 2,
            'payer_idx': 2,
            'payee_idx': 1,
            'amount': 300000,
            'notes': 'Trả tiền bowling',
            'status': 'pending'
        }
    ]

    created_payments = []
    for pay_data in payments_data:
        payment = Payment(
            group_id=groups[pay_data['group_idx']].id,
            payer_id=users[pay_data['payer_idx']].id,
            payee_id=users[pay_data['payee_idx']].id,
            amount=pay_data['amount'],
            notes=pay_data['notes'],
            status=pay_data['status'],
            payment_date=datetime.now() - timedelta(days=random.randint(0, 15))
        )
        db.session.add(payment)
        created_payments.append(payment)
        print(f"Created payment: {pay_data['notes']} - {pay_data['amount']:,} VND ({pay_data['status']})")

    db.session.commit()
    return created_payments


def clear_data():
    """Clear all existing data"""
    print("🗑️  Clearing existing data...")

    # Delete in correct order due to foreign key constraints
    try:
        Payment.query.delete()
        print("   Cleared payments")

        ExpenseSplit.query.delete()
        print("   Cleared expense splits")

        Expense.query.delete()
        print("   Cleared expenses")

        GroupMember.query.delete()
        print("   Cleared group members")

        Group.query.delete()
        print("   Cleared groups")

        User.query.delete()
        print("   Cleared users")

        Category.query.delete()
        print("   Cleared categories")

        db.session.commit()
        print(" All data cleared successfully!\n")

    except Exception as e:
        db.session.rollback()
        print(f"Error clearing data: {str(e)}\n")
        raise


def main():
    """Run all seed functions"""
    app = create_app('development')

    with app.app_context():
        print("Seeding database...")

        # Clear old data first
        clear_data()

        print("--- Creating Categories ---")
        categories = seed_categories()

        print("\n--- Creating Users ---")
        users = create_users()

        print("\n--- Creating Groups ---")
        groups = create_groups(users)

        print("\n--- Creating Expenses ---")
        expenses = create_expenses(groups, users, categories)

        print("\n--- Creating Payments ---")
        payments = create_payments(groups, users)

        print("\n Database seeding completed!")
        print("\n" + "="*60)
        print("📊 Summary:")
        print(f"   - Categories: {len(categories)}")
        print(f"   - Users: {len(users)} (1 admin, {len(users)-1} regular users)")
        print(f"   - Groups: {len(groups)}")
        print(f"   - Expenses: {len(expenses)}")
        print(f"   - Payments: {len(payments)}")
        print("="*60)
        print("\n🔑 Login Credentials:")
        print("   ADMIN:")
        print("   - Username: admin")
        print("   - Password: admin123")
        print("\n   REGULAR USERS:")
        print("   - Username: nguyenvana / tranthib / levanc / phamthid")
        print("   - Password: password123")
        print("="*60)


if __name__ == '__main__':
    main()
