import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()
backend_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(backend_env_path):
    load_dotenv(backend_env_path)

def fix_database():
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", 3306))
    db_user = os.getenv("DB_USER", "finance_user")
    db_password = os.getenv("DB_PASSWORD", "your_secure_password")
    db_name = os.getenv("DB_NAME", "finance_db")

    DATABASE_URL = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            check_sql = text("SHOW COLUMNS FROM transactions LIKE 'user_id'")
            result = conn.execute(check_sql).fetchone()
            
            if not result:
                print("Adding user_id column to transactions table...")
                conn.execute(text("ALTER TABLE transactions ADD COLUMN user_id INTEGER"))
                conn.execute(text("ALTER TABLE transactions ADD CONSTRAINT fk_transactions_user_id FOREIGN KEY (user_id) REFERENCES users(id)"))
                conn.commit()
                print("Successfully added user_id column and foreign key constraint to transactions.")
            else:
                print("Column user_id already exists in transactions table.")
    except Exception as e:
        print(f"Error modifying database: {e}")

if __name__ == "__main__":
    fix_database()
