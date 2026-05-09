"""
Script to test the database connection is working using psycopg2.
"""

import psycopg2
import os

from dotenv import load_dotenv
from urllib.parse import quote_plus, urlunparse

load_dotenv()

user = os.getenv('USER')
pw = os.getenv('PASSWORD')
if not pw:
    raise RuntimeError("Database password is missing in .env file.")
pw_encoded = quote_plus(pw)
host = os.getenv('HOST')
port = os.getenv('PORT')
dbname = os.getenv('DBNAME')

netloc = f"{user}:{pw_encoded}@{host}:{port}"
uri = urlunparse(("postgresql+psycopg2", netloc, f"/{dbname}", "", "sslmode=require", ""))


print("Testing DB URL (masked):", uri[:40] + '...')
try:
    conn = psycopg2.connect(
        database=os.getenv('DBNAME'),
        user=os.getenv('USER'),
        password=pw_encoded,
        host=os.getenv('HOST'),
        port=os.getenv('PORT'),
        sslmode='require'
    )

    with conn.cursor() as cur:
        cur.execute('SELECT 1')
        print("SELECT 1 ->", cur.fetchone())
        print("Database connection successful!")

except psycopg2.OperationalError as e:
    print("Database connection failed:", type(e).__name__, e)
