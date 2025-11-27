import sqlite3
import pathlib

def init_db():
    db_path = pathlib.Path(__file__).parent.parent / "fraud_cases.db"
    
    # Connect to database (creates it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fraud_cases (
        username TEXT PRIMARY KEY,
        security_identifier TEXT,
        card_ending TEXT,
        transaction_name TEXT,
        transaction_amount TEXT,
        transaction_time TEXT,
        transaction_category TEXT,
        transaction_source TEXT,
        transaction_location TEXT,
        security_question TEXT,
        security_answer TEXT,
        status TEXT,
        outcome_note TEXT
    )
    ''')
    
    # Sample data
    sample_cases = [
        (
            "John",
            "12345",
            "4242",
            "ABC Industry",
            "$125.50",
            "2 hours ago",
            "e-commerce",
            "alibaba.com",
            "Shanghai, China",
            "What is your mother's maiden name?",
            "Smith",
            "pending_review",
            ""
        ),
        (
            "Jane",
            "67890",
            "1111",
            "TechGadgets Inc",
            "$999.99",
            "Yesterday",
            "electronics",
            "amazon.com",
            "Seattle, WA",
            "What was the name of your first pet?",
            "Fluffy",
            "pending_review",
            ""
        ),
        (
            "Alice",
            "11223",
            "9876",
            "Luxury Bags Paris",
            "$2,500.00",
            "10 minutes ago",
            "retail",
            "pos",
            "Paris, France",
            "What is the name of your favorite teacher?",
            "Johnson",
            "pending_review",
            ""
        ),
        (
            "Bob",
            "33445",
            "5555",
            "Crypto Exchange X",
            "$5,000.00",
            "1 hour ago",
            "crypto",
            "online",
            "Unknown",
            "What is the city you were born in?",
            "Chicago",
            "pending_review",
            ""
        ),
        (
            "Charlie",
            "55667",
            "1234",
            "Gas Station 7-11",
            "$1.00",
            "5 minutes ago",
            "gas",
            "pos",
            "Miami, FL",
            "What is your father's middle name?",
            "James",
            "pending_review",
            ""
        )
    ]
    
    # Insert or replace sample data
    cursor.executemany('''
    INSERT OR REPLACE INTO fraud_cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_cases)
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {db_path}")

if __name__ == "__main__":
    init_db()
