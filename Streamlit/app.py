import streamlit as st
from streamlit_option_menu import option_menu
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Axis Bank Analytics", layout="wide")

# Custom CSS for styling........

st.markdown("""
<style>
            
/* Main App Background */
    .stApp {
        background-color: #F4F6F9;
    }

/* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #97144D;
    }

    section[data-testid="stSidebar"] * {
        background-color: #97144D;
        color: white;
        font-size: 16px;
    }
                
/* Header Styling */
    h1, h2, h3 {
        color: #97144D;
        font-weight: 700;
    }
            
/*card styling */
    div[data-testid="stMetric"] {
        background-color: #F8E6Ec;
        border: 2px solid #AE275F;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(151,20,77,0.2);
    }
    div[data-testid="stMetric"] label {
        color: #97144D;
        font-weight: bold;
    }
    div[data-testid="stMetric"] div {
        color:#97144D;
        font-size: 18px;
        font-weight:700;
    }
            
/* Button Styling */
    .stButton > button {
        background-color: #97144D;
        color: white;
        border-color: white;
        border-radius: 8px;
        height: 40px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #97144D;
        color: white;
    }
            
/* Cointainer card styling */
    .custom-card {
        background-color: #F8E6Ec;
        border-radius: 15px;
        padding: 20px;
        border: 2px solid #AE275F;
        box-shadow: 0 5px 15px rgba(151,20,77,0.3);
        margin-bottom: 20px;
    }
            
/*Selectbox styling */
    div[data-baseweb="select"] > div {
        background-color: white;
        color: #97144D;
        border-radius: 8px;
    }
    /* Selected option styling */
    div[data-baseweb="select"] span {
        color: #97144D;
        font-weight: 600;
    }
    /* Dropdown options styling */
    ul[role="listbox"] {
        background-color: white;
    }
    ul[role="listbox"] li {
        color: #97144D;
    }
            
</style>
""", unsafe_allow_html=True)


# Streamlit App Layout........

st.title("🏦 Axis Bank Transaction Analytics Dashboard")

API_URL = "http://127.0.0.1:8000"

with st.sidebar:
    role = option_menu(
        menu_title="LOGIN AS:",
        options=["Customer", "Branch Manager", "Region Manager"],
        icons=["person", "building", "globe"],
        menu_icon="cast",
        default_index=0,
    )

# -------------------------------------------------
# Customer Dashboard.
# -------------------------------------------------

if role == "Customer":


    # Initialize session state......
    if "customer_logged_in" not in st.session_state:
        st.session_state.customer_logged_in = False
    
    if "customer_data" not in st.session_state:
        st.session_state.customer_data = None
    
    if "selected_month" not in st.session_state:
        st.session_state.selected_month = []

    # LOGIN USING ACCOUNT NUMBER.......
    if not st.session_state.customer_logged_in:
        with st.sidebar:
            account_number = st.text_input("*Enter your Account Number:*")
        
            if st.button("Login"):
                if account_number:
                    response = requests.get(f"{API_URL}/customer/{account_number}")

                    if response.status_code == 200:
                        st.session_state.customer_logged_in = True
                        st.session_state.customer_data = response.json()
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Account not found. Please check your account number.")
                else:
                    st.warning("Please enter an account number.")

    # DASHBOARD VIEW.......
    if st.session_state.customer_logged_in:

        data = st.session_state.customer_data

        st.subheader("Customer Dashboard")

        st.header(f"Welcome, {data['customer_name']}!")

        # Logout button
        with st.sidebar:
            if st.button("Logout"):
                st.session_state.customer_logged_in = False
                st.session_state.customer_data = None
                st.session_state.selected_month = []
                st.success("Logged out successfully!")
                st.rerun()

        # Account Info..
        st.subheader("Account Info.")

        col1, col2 = st.columns(2)
        with col1:
            col1.metric(f"**Account Type:**", f"{data['account_type']}")
        with col2:
            col2.metric(f"**Branch:**", f"{data['branch']}")
        
        # Account Summary..
        st.subheader("Account Summary:")

        col1, col2 = st.columns(2)

        col1.metric("Opening Balance", f"₹{data['opening_balance']}")
        col2.metric("Closing Balance", f"₹{data['closing_balance']}")

        col3, col4 = st.columns(2)

        col3.metric("Savings Rate %", f"{data['savings_rate_percent']}%")
        col4.metric("Net Cash Flow", f"₹{data['net_cash_flow']}")

        # Alerts and Recommendations..
        if data['alerts']:
            for alert in data['alerts']:
                st.warning(alert)

        # Visualizations..
        st.subheader("Spending Analysis")

        monthly_df = pd.DataFrame(data['monthly_spend'], columns=['Month', 'Total Outgoings', 'Total Incomings'])

        # Convert month to datetime for sorting
        monthly_df['Month'] = pd.to_datetime(monthly_df['Month'])

        # Month Slicer
        selected_month = st.multiselect("Select Month:", options=monthly_df['Month'].dt.strftime('%Y-%m').unique())

        # Filter DataFrame based on selected months
        filtered_df = monthly_df[monthly_df['Month'].dt.strftime('%Y-%m').isin(selected_month)]

        if selected_month:
            filtered_df = monthly_df[monthly_df['Month'].dt.strftime('%Y-%m').isin(selected_month)]

        else:
            filtered_df = monthly_df
        
        # Charts..

        # Line chart for monthly trends
        fig = px.bar(filtered_df, x='Month', y=['Total Outgoings', 'Total Incomings'], 
                     title="Monthly Transaction Trends", barmode='group')
        
        fig.update_layout(xaxis_title="Month", yaxis_title="Amount (₹)", 
                          legend_title="Transaction Type",
                          template="plotly_white",
                          title_font=dict(size=20, color = "#97144D", family="Arial"))
        
        st.plotly_chart(fig, width=1000, height= 500)

        # Pie chart for category-wise spending
        cat_df = pd.DataFrame(data['category_details'], columns=['Category', 'Total Spend'])

        fig = px.pie(cat_df, names="Category", values="Total Spend",
                     title= f"Spending by Category for {selected_month[0] if selected_month else 'All Months'}")
        
        fig.update_layout(template="plotly_white",
                          title_font=dict(size=20, color = "#97144D", family="Arial"))
        
        st.plotly_chart(fig, width= 1000, height= 800)

# -------------------------------------------------
# Branch Manager Dashboard.
# -------------------------------------------------

elif role == "Branch Manager":

    # Initialize session state......
    if "branch_data" not in st.session_state:
        st.session_state.branch_data = None

    if "selected_branch" not in st.session_state:
        st.session_state.selected_branch = None
    
    # Sidebar for branch selection
    with st.sidebar:

        @st.cache_data
        def load_branches():
            response = requests.get(f"{API_URL}/branches")
            if response.status_code == 200:
                return response.json()
            else:
                st.error("Failed to load branches.")
                return []
        
        branch_list = load_branches()

        branch_name = st.selectbox("Select Branch:", options = branch_list)
    
        if st.button("GET DATA"):
            response = requests.get(f"{API_URL}/branch/{branch_name}")

            if response.status_code == 200:
                st.session_state.branch_data = response.json()
                st.session_state.selected_branch = branch_name
                st.rerun()
            else:
                st.error("Branch not found. Please check the branch name.")

    # Dashboard View
    if st.session_state.branch_data:
        data = st.session_state.branch_data
        branch_name = st.session_state.selected_branch

        st.header(f"{branch_name} - Branch Dashboard")

        # Logout button
        with st.sidebar:
            if st.button("Logout"):
                st.session_state.branch_data = None
                st.session_state.selected_branch = None
                st.rerun()

        # Dashboard view...
        col1, col2, col3 = st.columns(3)

        col1.metric("Total Customers", data['total_customers'])
        col2.metric("Total Deposits", f"₹{data['total_credits']}")
        col3.metric("Total Withdrawals", f"₹{data['total_debits']}")

        col4, col5 = st.columns(2)

        col4.metric("Negative Balance %", f"{data['negative_balance_ratio']}%")
        col5.metric("Average Balance / Customer", f"₹{round(data['average_balance'], 2)}")
        
        # Growth chart for branches...
        df_growth = pd.DataFrame(data['growth_rate'], columns=['Month', 'Monthly_deposits'])

        fig = px.bar(df_growth, x='Month', y='Monthly_deposits', 
                     title="Monthly Deposit Growth Rate", barmode='group')
        
        fig.update_layout(template="plotly_white",
                          title_font=dict(size=20, color = "#97144D", family="Arial"))        
        
        st.plotly_chart(fig, width=1000, height=500)

# -------------------------------------------------
#  Region Manager Dashboard.
# -------------------------------------------------

elif role == "Region Manager":

    # Initialize session state......
    if "region_data" not in st.session_state:
        st.session_state.region_data = None
    
    if "selected_city" not in st.session_state:
        st.session_state.selected_city = None
    
    # Sidebar for city selection
    with st.sidebar:

        @st.cache_data
        def load_cities():
            response = requests.get(f"{API_URL}/cities")
            if response.status_code == 200:
                return response.json()
            else:
                st.error("Failed to load cities.")
                return []
        
        city_list = load_cities()
        
        city_name = st.selectbox("*Enter City Name:*", options = city_list)
    
        if st.button("GET DATA"):
            response = requests.get(f"{API_URL}/region/{city_name}")
            if response.status_code == 200:
                st.session_state.region_data = response.json()
                st.session_state.selected_city = city_name
                st.rerun()
            else:
                st.error("City not found. Please check the city name.")

    # Dashboard View
    if st.session_state.region_data:
        data = st.session_state.region_data
        city_name = st.session_state.selected_city

        # Logout button
        with st.sidebar:
            if st.button("Logout"):
                st.session_state.region_data = None
                st.session_state.selected_city = None
                st.rerun()
    
        st.header(f"{city_name} - Region Dashboard")
        
        st.subheader(f"Total Branches: {data['branch_count']}")

        # Branch comparison Chart...

        df_branch = pd.DataFrame(data["branch_comparison"], columns=["Branch", "Total Deposits"])

        df_branch["color"] = df_branch["Total Deposits"].apply(lambda x: "negative" if x<0 else "positive")

        fig = px.bar(df_branch, x="Branch", y="Total Deposits", 
                     color="color",
                     color_discrete_map={
                         "positive": "#2E8B57",
                         "negative": "#FF4B4B"
                     },
                     title="Branch-wise Total Deposits")

        fig.update_layout(template="plotly_white",
                    title_font=dict(size=20, color = "#97144D", family="Arial"),
                    showlegend = False)

        st.plotly_chart(fig, width=1000, height=500)
