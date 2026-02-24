from Fastapi.db import db_connection

# -------------------------------------------------
# Customer Dashboard: Provides detailed insights for individual customers based on their account number.
# -------------------------------------------------
def customer_dashboard(account_number):

    conn = db_connection()
    cursor = conn.cursor()

    # Fetch accoount information
    cursor.execute("""
        SELECT 
            holder_name, account_type, branch, statement_period
            FROM account_info
            WHERE account_number = %s
            """, (account_number,))
    
    acc_info = cursor.fetchone()

    if acc_info:
        cust_name = acc_info[0]
        acc_type = acc_info[1]
        branch = acc_info[2]
        statement_period = acc_info[3]
    else:
        return {"Account not found..!"}

    # Fetch account summary
    cursor.execute("""
        SELECT
            opening_balance, closing_balance, total_credits, total_debits, total_transactions
            FROM account_summary
            WHERE account_number = %s
            """, (account_number,))
    
    acc_summary = cursor.fetchone()
    
    if acc_summary:
        opening_balance = acc_summary[0]
        closing_balance = acc_summary[1]
        total_credits = acc_summary[2]
        total_debits = acc_summary[3]
        total_transactions = acc_summary[4]
    else:
        return {"Account summary not available..!"}
    

    # Fetch Categorical transaction details
    cursor.execute("""
        SELECT category, SUM(debit_amount)AS total_spend
        FROM transactions
        WHERE account_number = %s
        GROUP BY category
        """, (account_number,))
    
    category_details = cursor.fetchall()

    # Fetch Monthly transaction trends
    cursor.execute("""
        SELECT TO_CHAR(transaction_date, 'YYYY-MM') AS month, 
            COALESCE(SUM(debit_amount), 0) AS total_outgoings, 
            COALESCE(SUM(credit_amount), 0) AS total_incomings
        FROM transactions
        WHERE account_number = %s
        GROUP BY month
        ORDER BY month
        """, (account_number,))
    
    monthly_spend = cursor.fetchall()

    # Savings Rate Calculation
    net_cash_flow = total_credits - total_debits

    savings_rate = 0
    if total_credits > 0:
        savings_rate = (net_cash_flow / total_credits) * 100

    # Alerts for account
    alerts = []

    if closing_balance <0:
        alerts.append("Negative Balance Warning: Your account is overdrawn. Please deposit funds to avoid penalties.")
    
    if total_debits > total_credits:
        alerts.append("High Spending Alert: Your outgoing transactions exceed your incoming transactions. Consider reviewing your spending habits.")

    if savings_rate < 10:
        alerts.append("Low Savings Rate: Your savings rate is below 10%. Consider increasing your savings to build a stronger financial future.")
    
    cursor.close()
    conn.close()

    return {
        "customer_name": cust_name,
        "account_type": acc_type,
        "branch": branch,
        "statement_period": statement_period,
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "total_credits": total_credits,
        "total_debits": total_debits,
        "total_transactions": total_transactions,
        "net_cash_flow": net_cash_flow,
        "savings_rate_percent": round(savings_rate, 2),
        "category_details": category_details,
        "monthly_spend": monthly_spend,
        "alerts": alerts
    }

# Fetch all branches for dropdown
def branch():
    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT branch
        FROM account_info
        """)
    
    branches = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return branches


# -------------------------------------------------
# Branch Dashboard: Provides aggregated insights for a specific branch, including customer count, transaction volumes, and growth trends.
# -------------------------------------------------
def branch_dashboard(branch_name):

    conn = db_connection()
    cursor = conn.cursor()

    # Fetch Branch information
    cursor.execute("""
        SELECT COUNT(DISTINCT t.account_number) AS total_customers,
        SUM(t.debit_amount) AS total_debits,
        SUM(t.credit_amount) AS total_credits
        FROM transactions t
        JOIN account_info a 
        ON t.account_number = a.account_number
        WHERE a.branch = %s
        """, (branch_name,)) 
    
    results = cursor.fetchone()

    total_customers = results[0] if results else 0
    total_debits = results[1] if results else 0
    total_credits = results[2] if results else 0

    # Fetch average balance across all accounts
    cursor.execute("""
        SELECT AVG(s.closing_balance) 
        FROM account_summary s
        JOIN account_info a 
        ON s.account_number = a.account_number
        WHERE a.branch = %s
        """, (branch_name,))
    
    avg_balance = cursor.fetchone()[0]

    # Fetch Transaction Velocity (number of transactions per month)
    cursor.execute("""
        SELECT DATE_TRUNC('month', t.transaction_date) AS month, 
        COUNT(*) AS transaction_count
        FROM transactions t
        JOIN account_info a 
        ON t.account_number = a.account_number
        WHERE a.branch = %s
        GROUP BY month
        ORDER BY month
        """, (branch_name,))
    
    transaction_velocity = cursor.fetchall()

    # Fetch Negative Balance Ratio
    cursor.execute("""
        SELECT COUNT(*) FILTER (WHERE s.closing_balance < 0) * 100.0 / COUNT(*)
        FROM account_summary s
        JOIN account_info a
        ON s.account_number = a.account_number
        WHERE a.branch = %s
        """, (branch_name,))

    negative_balance_ratio = cursor.fetchone()[0] or 0

    # Fetch Growth Rate (month-over-month)
    cursor.execute("""
        SELECT DATE_TRUNC('month', t.transaction_date) AS month,
                SUM(t.credit_amount) AS monthly_deposits
        FROM transactions t
        JOIN account_info a
        ON t.account_number = a.account_number
        WHERE a.branch = %s
        GROUP BY month
        ORDER BY month
        """, (branch_name,))

    growth_rate = cursor.fetchall()           

    cursor.close()
    conn.close()

    return {
        "total_customers": total_customers,
        "total_credits": total_credits,
        "total_debits": total_debits,
        "average_balance": avg_balance,
        "transaction_velocity": transaction_velocity,
        "negative_balance_ratio": negative_balance_ratio,
        "growth_rate": growth_rate
    }

# Fetch all Cities for dropdown
def city():
    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT SPLIT_PART(branch, ' - ', 1) AS city
        FROM account_info
        ORDER BY city;
        """)
    
    cities = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return cities


# -------------------------------------------------
# Region Dashboard: Provides Region level insights
# -------------------------------------------------
def region_dashboard(city):

    conn = db_connection()
    cursor = conn.cursor()

    # Branch count in the city
    cursor.execute("""
        SELECT COUNT(DISTINCT branch)
        FROM account_info
        """)
    branch_count = cursor.fetchone()[0]

    # Branch Comparision
    cursor.execute("""
        SELECT a.branch, SUM(s.closing_balance) AS total_deposits
        FROM account_summary s
        JOIN account_info a
        ON s.account_number = a.account_number
        GROUP BY a.branch
        ORDER BY total_deposits DESC
        """)
    branch_comparison = cursor.fetchall()

    cursor.close()
    conn.close()

    return{
        "branch_count": branch_count,
        "branch_comparison": branch_comparison
    }