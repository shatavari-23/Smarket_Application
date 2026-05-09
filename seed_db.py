import json
import os
from app import app, db, Product, User, bcrypt

def seed_database():
    with app.app_context():
        # Create all tables based on the models in database.py
        # This will not affect existing tables or data.
        db.create_all()

        # Create a default admin user
        if not User.query.filter_by(email='admin@smarket.com').first():
            hashed_password = bcrypt.generate_password_hash('admin').decode('utf-8')
            admin_user = User(name='Admin User', email='admin@smarket.com', password=hashed_password, role='admin')
            db.session.add(admin_user)

        # Create or update the default seller user
        seller_user = User.query.filter_by(email='seller@example.com').first()
        if not seller_user:
            hashed_password = bcrypt.generate_password_hash('password').decode('utf-8')
            seller_user = User(name='Gauri', email='seller@example.com', password=hashed_password, role='seller')
            db.session.add(seller_user)
        else:
            # If the seller already exists, just update the name
            seller_user.name = 'Gauri'
        
        # Re-fetch the seller user to ensure we have the ID after commit
        seller_user = User.query.filter_by(email='seller@example.com').first()
        if not seller_user:
            raise Exception("Could not create or find the default seller user.")
        json_path = os.path.join(os.path.dirname(__file__), 'products.json')
        with open(json_path) as f:
            products = json.load(f)
            for product_id, product_data in products.items():
                # Check if product already exists
                if not db.session.get(Product, int(product_id)):
                    new_product = Product(
                        id=int(product_id),
                        name=product_data['name'],
                        price=product_data['price'],
                        category=product_data['category'],
                        description=product_data['description'],
                        image=product_data['image'],
                        seller_id=seller_user.id,
                        stock=100,  # Assuming a default stock of 100
                        status='approved'
                    )
                    db.session.add(new_product)
            db.session.commit()

if __name__ == '__main__':
    seed_database()
    print("Database seeded successfully!")
