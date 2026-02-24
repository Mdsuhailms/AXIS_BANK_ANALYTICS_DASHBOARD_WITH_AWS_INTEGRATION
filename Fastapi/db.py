import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# -------------------------------------------------
# DATABASE CONFIGURATION
# -------------------------------------------------

db_config = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT", 5432)
}

# -------------------------------------------------
# DATABASE CONNECTION
# -------------------------------------------------

def db_connection():
    return psycopg2.connect(**db_config)