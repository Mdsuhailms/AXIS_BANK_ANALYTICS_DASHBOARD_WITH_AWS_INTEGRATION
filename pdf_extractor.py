import re
import os
import boto3
import fitz  # PyMuPDF
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# -------------------------------------------------
# Initialize Bucket and S3 client
# -------------------------------------------------

AWS_REGION = os.getenv("AWS_REGION")
BUCKET_NAME = os.getenv("BUCKET_NAME")
BUCKET_PREFIX = os.getenv("BUCKET_PREFIX")

s3 = boto3.client("s3", region_name=AWS_REGION)

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
# Transaction Categories
# -------------------------------------------------
TRANSACTION_CATEGORIES = {
    # Food & Dining
    'FOOD_DELIVERY': ['ZOMATO', 'SWIGGY', 'EATSURE', 'UBER EATS'],

    'RESTAURANTS': ['ANNAPOORNA', 'JUNIOR KUPPANNA', 'SREE ANNAPOORNA', 'HOTEL ANNAPOORNA',
                    'SHREE ANANDHAAS', 'KOVAI BIRIYANI', 'A2B ADYAR ANANDA BHAVAN', 'HOTEL', 'RESTAURANT'],

    'GROCERIES': ['DMART', 'MORE SUPERMARKET', 'SPAR HYPERMARKET', 'RELIANCE FRESH',
                  'NILGIRIS', 'PAZHAMUDIR NILAYAM', 'KOVAI PAZHAMUDIR'],

    # Shopping
    'ONLINE_SHOPPING': ['AMAZON', 'FLIPKART', 'MYNTRA', 'AJIO', 'MEESHO'],

    # Transportation
    'RIDE_HAILING': ['UBER', 'OLA', 'RAPIDO'],

    'FUEL': ['INDIAN OIL', 'BHARAT PETROLEUM', 'HP PETROL', 'SHELL', 'FUEL', 'PETROL', 'DIESEL'],

    # Bills & Utilities
    'ELECTRICITY': ['TANGEDCO', 'TAMILNADU ELECTRICITY', 'ELECTRICITY BILL', 'EB BILL'],

    'INTERNET': ['ACT FIBERNET', 'ACTBB', 'INTERNET BILL', 'BROADBAND'],

    'MOBILE_RECHARGE': ['AIRTEL RECHARGE', 'JIO RECHARGE', 'VI RECHARGE', 'POSTPAID', 'PREPAID'],

    'GAS': ['INDANE GAS', 'HP GAS', 'BHARAT GAS', 'GAS BILL'],

    'RENT': ['RENT', 'HOUSE RENT', 'LANDLORD RENT'],

    # Healthcare
    'PHARMACY': ['MEDPLUS', 'NETMEDS', 'APOLLO PHARMACY'],

    'HEALTH_INSURANCE': ['HEALTH INSURANCE', 'PREMIUM'],

    # Entertainment & Subscriptions
    'STREAMING': ['NETFLIX', 'HOTSTAR', 'AMAZON PRIME'],

    'ENTERTAINMENT': ['BOOKMYSHOW', 'PVR CINEMAS', 'INOX', 'CINEMA', 'MOVIE', 'THEATRE'],

    # Financial
    'INVESTMENTS': ['AXISMUTUALFUND', 'SIP', 'MUTUAL FUND', 'ZERODHA', 'GROWW'],

    'CREDIT_CARD_PAYMENT': ['AXIS CREDIT CARD', 'CREDIT CARD', 'PAYMENT'],

    'SALARY': ['SALARY', 'PSG INDUSTRIES'],

    'BONUS': ['BONUS'],

    'INTEREST': ['INT/CREDIT', 'INTEREST'],

    'INSURANCE': ['INSURANCE', 'PREMIUM'],


    # Transfers
    'FAMILY_SUPPORT': ['FAMILY SUPPORT'],

    'RECEIVED_MONEY': ['RECEIVED FROM', 'UPI/.*?/RECEIVED'],

    # Banking
    'ATM_WITHDRAWAL': ['ATM/CASH WDL', 'ATM WITHDRAWAL'],

    'BANK_CHARGES': ['CHG/', 'CHARGES', 'SMS ALERT'],

    'EMI_LOAN': ['EMI/', 'LOAN PAYMENT', 'HOME LOAN', 'PERSONAL LOAN', 'CAR LOAN'],
}


def categorize_transaction(description):

    desc_upper = description.upper()
    for category, keywords in TRANSACTION_CATEGORIES.items():
        for key in keywords:
            if key in desc_upper:
                return category
    
    return 'OTHER'


# Convert category code to readable display name

def get_category_display_name(category):
    return category.replace('_', ' ').title()

# -------------------------------------------------
# Utility: Safe Regex Search
# -------------------------------------------------
def safe_search(pattern, text, flags=0):

    match = re.search(pattern, text, flags)

    return match.group(1).strip() if match else ""

# -------------------------------------------------
# Extract Text from PDF
# -------------------------------------------------
def extract_text_from_pdf(bucket, key):

    obj = s3.get_object(Bucket=bucket, Key=key)
    pdf= obj['Body'].read()

    with fitz.open(stream=pdf, filetype="pdf") as pdf:
        text = "\n".join(page.get_text() for page in pdf)

    return text

# -------------------------------------------------
# Parse Account Info (EXTRACT ACCOUNT INFO. FROM PDF USING REGEX)
# -------------------------------------------------
def extract_holder_name(text):
    pattern = re.search(r"\n([A-Za-z\s\.]+)\n\1?\n\nDate\nTransaction Description", text)
    return pattern.group(1).strip() if pattern else ""


def parse_account_info(text):
    return {
        "account_number": safe_search(r"Account Number:\s*(\d+)", text),
        "holder_name": extract_holder_name(text),
        "account_type": safe_search(r"Account Type:\s*(.*?)\s+IFSC Code:", text, flags=re.DOTALL),
        "ifsc_code": safe_search(r"IFSC Code:\s*(\w+)", text),
        "branch": safe_search(r"Branch:\s*(.*?)\s+Statement Period:", text, flags=re.DOTALL),
        "customer_id": safe_search(r"Customer ID:\s*(\w+)", text),
        "statement_period": safe_search(r"Statement Period:\s*(.*?)\s+Customer ID:", text, flags=re.DOTALL)
    }

# -------------------------------------------------
# Parse Account Summary (EXTRACT ACCOUNT SUMMARY FROM PDF USING REGEX)
# -------------------------------------------------
def parse_account_summary(text):
    return {
        "opening_balance": safe_search(r"Opening Balance\s*\n\s*[A-Za-z₹■]?\s*(-?[\d,]+\.\d+)", text),
        "total_credits": safe_search(r"Total Credits.*?\n\s*[A-Za-z₹■]?\s*(-?[\d,]+\.\d+)", text),
        "total_debits": safe_search(r"Total Debits.*?\n\s*[A-Za-z₹■]?\s*(-?[\d,]+\.\d+)", text),
        "closing_balance": safe_search(r"Closing Balance\s*\n\s*[A-Za-z₹■]?\s*(-?[\d,]+\.\d+)", text),
        "total_transactions": safe_search(r"Total Transactions\s*\n\s*(\d+)", text)
    }

# -------------------------------------------------
# Parse Transactions (EXTRACT ALL TRANSACTION DETAILS FROM PDF WITH CATEGORIES)
# -------------------------------------------------


def safe_float(value):
    try:
        return float(value.replace(",", ""))
    except:
        return 0.0

def safe_int(value):
    try:
        return int(value)
    except:
        return 0
    
def parse_transactions(text):

    pattern = re.compile(
        r"(\d{2}-\d{2}-\d{4})\s+"  # Date
        r"(.+?)\s+"  # Transaction Description
        r"([A-Z0-9]+)\s+"  # Reference Number
        r"(DR|CR)\s+"  # Transaction Type
        r"(-?[\d,]+\.\d+)\s+"  # Amount 
        r"(-?[\d,]+\.\d+)",  # Balance
        
        re.DOTALL
    )

    rows = []
    
    for m in pattern.finditer(text):
        try:
            txn_date = datetime.strptime(m.group(1), "%d-%m-%Y").date()
            desc = m.group(2).strip()
            ref = m.group(3)
            txn_type = m.group(4)
            amount = safe_float(m.group(5))
            balance = safe_float(m.group(6))

            if amount is None or balance is None:
                print("skipping invalid transaction row:", m.group(0))
                continue
            
            category = categorize_transaction(desc)

            debit = amount if txn_type == "DR" else 0.0
            credit = amount if txn_type == "CR" else 0.0

            rows.append((txn_date, desc, ref, txn_type, debit, credit, category))
        
        except Exception as e:
            print("Error parsing transaction row:", e)
            continue
    
    return rows

# -------------------------------------------------
# DATABASE CONNECTION
# -------------------------------------------------

def get_conn():
    return psycopg2.connect(**db_config)

# -------------------------------------------------
# CHECK IF FILE IS ALREADY PROCESSED
# -------------------------------------------------

def is_file_processed(cursor, key):
    cursor.execute("SELECT 1 FROM processed_files WHERE file_name = %s", (key,))
    return cursor.fetchone() is not None

# -------------------------------------------------
# MARK FILE AS PROCESSED
# -------------------------------------------------

def mark_file_as_processed(cursor, key):
    cursor.execute("INSERT INTO processed_files (file_name) VALUES (%s)", (key,))


# -------------------------------------------------
# PROCESS PDF FILE
# -------------------------------------------------

def process_pdf(key, cursor):
    print(f"Processing file: {key}")

    # Extract text from PDF
    text = extract_text_from_pdf(BUCKET_NAME, key)

    # Account Info 
    acc_info = parse_account_info(text)

    # Account Summary 
    acc_summary = parse_account_summary(text)

    # Transactions
    transactions = parse_transactions(text)


    # Insert account info 
    cursor.execute("""
        INSERT INTO account_info (account_number, holder_name, account_type, ifsc_code, branch, customer_id, statement_period)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    
        ON CONFLICT (account_number) DO NOTHING
        """, (
        acc_info["account_number"],
        acc_info["holder_name"],
        acc_info["account_type"],
        acc_info["ifsc_code"],
        acc_info["branch"],
        acc_info["customer_id"],
        acc_info["statement_period"]
    ))

    # INSERT ACCOUNT SUMMARY 
    cursor.execute("""
        INSERT INTO account_summary (
            account_number, opening_balance, total_credits,
            total_debits, closing_balance, total_transactions
        )
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        acc_info["account_number"],
        safe_float(acc_summary["opening_balance"].replace(",", "")),
        safe_float(acc_summary["total_credits"].replace(",", "")),
        safe_float(acc_summary["total_debits"].replace(",", "")),
        safe_float(acc_summary["closing_balance"].replace(",", "")),
        safe_int(acc_summary["total_transactions"])
    ))

    # INSERT TRANSACTIONS
    execute_batch(cursor, """
        INSERT INTO transactions (
            account_number, transaction_date, description,
            reference, transaction_type, debit_amount,
            credit_amount, category
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, [
        (acc_info["account_number"], *t) for t in transactions
    ])

# -------------------------------------------------
# MAIN FUNCTION TO PROCESS ALL FILES IN S3 BUCKET
# -------------------------------------------------

def run_extraction():
    print("Checking for new files in S3 bucket...")

    conn = get_conn()
    cursor = conn.cursor()

    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=BUCKET_PREFIX)

    process_count = 0

    if "Contents" in response:
        for obj in response["Contents"]:
            key = obj["Key"]

            if not key.endswith(".pdf"):
                print(f"Skipping non-PDF file: {key}")
                continue

            if not is_file_processed(cursor, key):
                try:
                    process_pdf(key, cursor)
                    mark_file_as_processed(cursor, key)
                    print(f"Successfully processed: {key}")
                    process_count += 1

                except Exception as e:
                    conn.rollback()
                    print(f"Error processing {key}: {e}")
            else:
                print(f"Already processed: {key}")
    
    conn.commit()
    cursor.close()
    conn.close()

    print(f"Processing complete. Total new files processed: {process_count}")

if __name__ == "__main__":
    run_extraction()

