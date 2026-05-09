from app import app, db, User, bcrypt

with app.app_context():
    # Create a buyer user if one doesn't exist
    user = User.query.filter_by(email='buyer@example.com').first()
    if not user:
        hashed_password = bcrypt.generate_password_hash('password123').decode('utf-8')
        user = User(name='Test Buyer', email='buyer@example.com', password=hashed_password, role='buyer')
        db.session.add(user)
        db.session.commit()
        print("Buyer user created successfully!")
    else:
        print("Buyer user already exists.")
