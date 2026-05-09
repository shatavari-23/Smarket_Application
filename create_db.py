from app import app
from database import db

def recreate_database():
    with app.app_context():
        print("Dropping all database tables...")
        db.drop_all()

        print("Creating all database tables...")
        db.create_all()

        print("Database has been recreated successfully!")