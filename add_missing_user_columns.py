from app import app, db
from sqlalchemy import text

# This script will add missing columns to the `user` table if they are not present.
# It is safe to run multiple times.

ADD_IS_DELETED = """
ALTER TABLE `user`
ADD COLUMN `is_deleted` TINYINT(1) NOT NULL DEFAULT 0
"""

ADD_DELETED_AT = """
ALTER TABLE `user`
ADD COLUMN `deleted_at` DATETIME NULL
"""

CHECK_IS_DELETED = """
SELECT COUNT(*) AS cnt
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'user'
  AND COLUMN_NAME = 'is_deleted'
"""

CHECK_DELETED_AT = """
SELECT COUNT(*) AS cnt
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'user'
  AND COLUMN_NAME = 'deleted_at'
"""


def run():
    with app.app_context():
        conn = db.engine.connect()
        try:
            res = conn.execute(text(CHECK_IS_DELETED)).mappings().first()
            if res and res['cnt'] == 0:
                print('Adding column `is_deleted` to `user` table...')
                conn.execute(text(ADD_IS_DELETED))
                print('`is_deleted` added.')
            else:
                print('`is_deleted` already exists.')

            res = conn.execute(text(CHECK_DELETED_AT)).mappings().first()
            if res and res['cnt'] == 0:
                print('Adding column `deleted_at` to `user` table...')
                conn.execute(text(ADD_DELETED_AT))
                print('`deleted_at` added.')
            else:
                print('`deleted_at` already exists.')

            print('Done.')
        finally:
            conn.close()


if __name__ == '__main__':
    run()
