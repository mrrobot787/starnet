"""
Agent Hospital Database Setup
Creates the database and initializes all tables
"""

import sqlite3
import os
from pathlib import Path

def setup_hospital_database():
    """Set up the Agent Hospital database"""
    
    print("Setting up Agent Hospital Database...")
    
    # Database path
    db_path = "agent_hospital.db"
    schema_path = os.path.join("AgentHospital", "hospital_schema.sql")
    
    if not os.path.exists(schema_path):
        print(f"ERROR: Schema file not found at {schema_path}")
        return False
    
    try:
        # Remove existing database if it exists
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"Removed existing database: {db_path}")
        
        # Create new database
        conn = sqlite3.connect(db_path)
        print(f"Created new database: {db_path}")
        
        # Read and execute schema
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements):
            try:
                conn.execute(statement)
                if i % 5 == 0:  # Progress indicator
                    print(f"Executed {i+1}/{len(statements)} statements...")
            except sqlite3.Error as e:
                print(f"Warning: Error executing statement {i+1}: {e}")
                # Continue with other statements
        
        conn.commit()
        conn.close()
        
        print(f"SUCCESS: Database setup complete!")
        print(f"Database file: {os.path.abspath(db_path)}")
        
        # Verify tables were created
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print(f"Created {len(tables)} tables:")
        for table in sorted(tables):
            print(f"  - {table}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Database setup failed: {e}")
        return False

def test_database():
    """Test basic database operations"""
    
    print("\nTesting database operations...")
    
    try:
        conn = sqlite3.connect("agent_hospital.db")
        
        # Test inserting a sample agent chart
        conn.execute("""
            INSERT INTO agent_chart 
            (admission_id, agent_id, state, ward, opened_at, opened_by, admission_reason, triage_score)
            VALUES ('TEST_ADM_001', 'TEST_AGENT_001', 'ADMITTED', 'GENERAL', 
                    datetime('now'), 'test_system', 'High burnout detected', 2.5)
        """)
        
        # Test querying
        cursor = conn.execute("SELECT * FROM agent_chart WHERE agent_id = 'TEST_AGENT_001'")
        result = cursor.fetchone()
        
        if result:
            print("SUCCESS: Database operations working")
            print(f"  Sample record: {result[0]} - {result[1]} - {result[2]}")
        else:
            print("ERROR: No data found after insert")
            return False
        
        # Clean up test data
        conn.execute("DELETE FROM agent_chart WHERE agent_id = 'TEST_AGENT_001'")
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"ERROR: Database test failed: {e}")
        return False

if __name__ == "__main__":
    print("Agent Hospital Database Setup")
    print("=" * 40)
    
    # Setup database
    setup_ok = setup_hospital_database()
    
    if setup_ok:
        # Test database
        test_ok = test_database()
        
        if test_ok:
            print("\nSUCCESS: Agent Hospital database is ready!")
            print("\nNext steps:")
            print("1. Run: python simple_hospital_test.py")
            print("2. Use the Agent Hospital system with full database support")
        else:
            print("\nWARNING: Database created but tests failed")
    else:
        print("\nFAILED: Could not set up database")
        exit(1)
