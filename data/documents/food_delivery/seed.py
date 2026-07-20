"""Seed script to populate the database with demo data."""
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.shop import Shop
from app.models.menu_item import MenuItem
from app.models.address import Address


def seed():
    app = create_app('development')
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()

        # --- Admin ---
        admin = User(
            username='admin',
            email='admin@delivery.com',
            name='系统管理员',
            phone='13800000000',
            role='admin',
            is_approved=True,
        )
        admin.set_password('admin123')

        # --- Test Merchant ---
        merchant = User(
            username='merchant1',
            email='merchant1@test.com',
            name='张三（商家）',
            phone='13900000001',
            role='merchant',
            is_approved=True,
        )
        merchant.set_password('123456')

        # --- Test Rider ---
        rider = User(
            username='rider1',
            email='rider1@test.com',
            name='李四（骑手）',
            phone='13900000002',
            role='rider',
            is_approved=True,
        )
        rider.set_password('123456')

        # --- Test Users ---
        user1 = User(
            username='user1',
            email='user1@test.com',
            name='王五（用户）',
            phone='13900000003',
            role='user',
            is_approved=True,
        )
        user1.set_password('123456')

        user2 = User(
            username='user2',
            email='user2@test.com',
            name='赵六（用户）',
            phone='13900000004',
            role='user',
            is_approved=True,
        )
        user2.set_password('123456')

        db.session.add_all([admin, merchant, rider, user1, user2])
        db.session.flush()

        # --- Addresses for users ---
        addr1 = Address(user_id=user1.id, label='家', address_detail='北京市朝阳区望京SOHO 1号楼 1201', is_default=True)
        addr2 = Address(user_id=user1.id, label='公司', address_detail='北京市海淀区中关村软件园 A栋 305')
        addr3 = Address(user_id=user2.id, label='学校', address_detail='北京市朝阳区北四环东路97号 北京联合大学', is_default=True)
        db.session.add_all([addr1, addr2, addr3])

        # --- Shop ---
        shop = Shop(
            merchant_id=merchant.id,
            name='美味居中餐厅',
            description='正宗川菜、粤菜、家常菜，新鲜食材每日采购，用心做好每一道菜。',
            address='北京市朝阳区建国路88号 SOHO现代城B1层',
            phone='010-88886666',
            status='approved',
            rating=4.5,
            total_sales=328,
        )
        db.session.add(shop)
        db.session.flush()

        # --- Menu Items ---
        menu_items_data = [
            {'name': '宫保鸡丁', 'price': 32.0, 'stock': 50, 'category': '热菜', 'description': '经典川菜，鸡肉丁配花生米，香辣可口'},
            {'name': '鱼香肉丝', 'price': 28.0, 'stock': 40, 'category': '热菜', 'description': '传统川菜，酸甜微辣，肉丝嫩滑'},
            {'name': '麻婆豆腐', 'price': 22.0, 'stock': 60, 'category': '热菜', 'description': '麻辣鲜香，豆腐嫩滑入味'},
            {'name': '糖醋里脊', 'price': 35.0, 'stock': 30, 'category': '热菜', 'description': '外酥里嫩，酸甜适口'},
            {'name': '番茄蛋花汤', 'price': 12.0, 'stock': 80, 'category': '汤品', 'description': '家常汤品，鲜美营养'},
            {'name': '酸辣汤', 'price': 15.0, 'stock': 50, 'category': '汤品', 'description': '酸辣开胃，暖身驱寒'},
            {'name': '蛋炒饭', 'price': 16.0, 'stock': 100, 'category': '主食', 'description': '粒粒分明的蛋炒饭，简单美味'},
            {'name': '红烧牛肉面', 'price': 26.0, 'stock': 40, 'category': '主食', 'description': '大块牛肉，浓郁汤底，手工面条'},
            {'name': '凉拌黄瓜', 'price': 10.0, 'stock': 120, 'category': '凉菜', 'description': '清爽开胃，夏日必备'},
            {'name': '可乐', 'price': 6.0, 'stock': 200, 'category': '饮品', 'description': '冰镇可口可乐 330ml'},
            {'name': '矿泉水', 'price': 3.0, 'stock': 300, 'category': '饮品', 'description': '农夫山泉 550ml'},
            {'name': '珍珠奶茶', 'price': 12.0, 'stock': 70, 'category': '饮品', 'description': '香甜奶茶配Q弹珍珠'},
        ]
        for item_data in menu_items_data:
            item = MenuItem(shop_id=shop.id, is_available=True, **item_data)
            db.session.add(item)

        db.session.commit()
        print('[OK] Seed data created successfully!')
        print()
        print('Test accounts:')
        print('  Admin    - username: admin      password: admin123')
        print('  Merchant - username: merchant1  password: 123456')
        print('  Rider    - username: rider1     password: 123456')
        print('  User     - username: user1      password: 123456')
        print('  User     - username: user2      password: 123456')


if __name__ == '__main__':
    seed()
