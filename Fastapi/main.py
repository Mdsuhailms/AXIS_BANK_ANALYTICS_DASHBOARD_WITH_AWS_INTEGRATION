from fastapi import FastAPI
from Fastapi.dashboard import customer_dashboard, branch_dashboard, region_dashboard, branch, city

app = FastAPI()

@app.get("/")
def root():
    return {"message": "API running"}

# -------------------------------------------------
# CUSTOMER DASHBOARD ENDPOINT
# -------------------------------------------------
@app.get("/customer/{account_number}")
def get_customer_dashboard(account_number):
    return customer_dashboard(account_number)

# -------------------------------------------------
# BRANCH DASHBOARD ENDPOINT
# -------------------------------------------------
@app.get("/branches")
def get_all_branches():
    return branch()


@app.get("/branch/{branch_name}")
def get_branch_dashboard(branch_name):
    return branch_dashboard(branch_name)


# -------------------------------------------------
# REGION DASHBOARD ENDPOINT
# -------------------------------------------------
@app.get("/cities")
def get_all_cities():
    return city()


@app.get("/region/{city}")
def get_region_dashboard(city):
    return region_dashboard(city)
