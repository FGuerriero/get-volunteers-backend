#!/usr/bin/env python3
"""
Script to verify that tests use isolated database and don't affect production data.
"""
import os
import sys

# Set testing environment
os.environ["TESTING"] = "1"

from app.db.database import SQLALCHEMY_DATABASE_URL, engine
from app.config import settings

def main():
    print("=== Database Isolation Test ===")
    print(f"Production database URL: {settings.database_url}")
    print(f"Test database URL: {SQLALCHEMY_DATABASE_URL}")
    
    if SQLALCHEMY_DATABASE_URL == "sqlite:///:memory:":
        print("✅ SUCCESS: Tests are using in-memory SQLite database")
        print("✅ Production database is safe from test interference")
        return 0
    else:
        print("❌ ERROR: Tests are NOT using isolated database!")
        print("❌ This could corrupt production data!")
        return 1

if __name__ == "__main__":
    sys.exit(main())