from app import app
from database import db
from seed_db import seed_database
from create_db import recreate_database

def setup_database():
    """
    Sets up the database by creating it, creating all tables, and seeding it with initial data.
    """
    recreate_database()
    with app.app_context():
        db.create_all()
        seed_database()

if __name__ == '__main__':
    setup_database()
    print("Database setup complete. You can now run the application using 'python app.py'")
