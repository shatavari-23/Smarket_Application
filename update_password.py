from app import app, db, User, bcrypt

with app.app_context():
    user = User.query.filter_by(email='seller@example.com').first()
    if user:
        hashed_password = bcrypt.generate_password_hash('password').decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        print("Password updated for seller@example.com")

    # Also update buyer if exists
    buyer = User.query.filter_by(email='buyer@example.com').first()
    if buyer:
        hashed_password = bcrypt.generate_password_hash('password').decode('utf-8')
        buyer.password = hashed_password
        db.session.commit()
        print("Password updated for buyer@example.com")

    admin = User.query.filter_by(email='admin@example.com').first()
    if admin:
        hashed_password = bcrypt.generate_password_hash('password').decode('utf-8')
        admin.password = hashed_password
        db.session.commit()
        print("Password updated for admin@example.com")
