import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import json
from google.oauth2.service_account import Credentials

# 📌 Google Sheets Configuration
SHEET_ID = "1R3EMYJt7he4CklRTRWtC6iqPzACg_eWyHdV6BaTzTms"

# 📌 Definir los permisos (scopes) correctos para Google Sheets y Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

# 📌 Función para cargar credenciales desde Streamlit Secrets o archivo local
def get_credentials():
    if "google_credentials" in st.secrets:
        creds_info = st.secrets["google_credentials"]
        return Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    else:
        return Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

# 📌 Autenticación con Google Sheets
creds = get_credentials()
client = gspread.authorize(creds)
worksheet = client.open_by_key(SHEET_ID).worksheet("Compliance Org Structure & Open")

# 📌 Función para cargar datos
@st.cache_data(ttl=600)
def load_data():
    df = pd.DataFrame(worksheet.get_all_records())

    # Estandarizar nombres de columnas
    df.columns = df.columns.str.strip().str.lower()

    # Verificar columnas necesarias
    if "status" not in df.columns:
        df["status"] = "offer stage"
    if "offer status" not in df.columns:
        df["offer status"] = "Pending"

    return df

df_org = load_data()

# 📌 Identificar la columna de status
possible_status_columns = [col for col in df_org.columns if "status" in col]
if not possible_status_columns:
    st.error("🚨 No 'status' column found in the dataset.")
    st.stop()

status_column = possible_status_columns[0]

# Standardize status values
df_org[status_column] = df_org[status_column].str.strip().str.lower()

# Filtrar DataFrames
hiring_process_df = df_org[df_org[status_column] == "offer stage"].copy()
open_positions_df = df_org[df_org[status_column].isin(["open position", "multiple position"])].copy()
open_positions_df = open_positions_df.dropna(axis=1, how="all")  # Remove empty columns
active_employees_df = df_org[df_org[status_column] == "active"].copy()

# 📌 Mostrar datos en Streamlit
st.title("📊 Compliance Hiring Tracker")

st.subheader("📋 Hiring Process Overview - Offer Stage Only")
st.dataframe(hiring_process_df)

st.subheader("📌 Open Positions")
st.dataframe(open_positions_df)

st.subheader("✅ Active Employees")
st.dataframe(active_employees_df)

# 📌 Hiring Status Distribution Chart
st.subheader("📊 Hiring Analytics")

st.write("### Hiring Status Distribution")
status_counts = df_org[status_column].value_counts().reset_index()
status_counts.columns = ["Status", "Count"]
fig_status = px.bar(status_counts, x="Status", y="Count", color="Status", text="Count",
                    title="Hiring Status Distribution", labels={"Count": "Number of Employees"})
st.plotly_chart(fig_status, use_container_width=True)

# 📌 Offer Status Breakdown
st.write("### Offer Status Breakdown")
offer_counts = hiring_process_df["offer status"].value_counts().reset_index()
offer_counts.columns = ["Offer Status", "Count"]
fig_offer = px.bar(offer_counts, x="Offer Status", y="Count", color="Offer Status", text="Count",
                   title="Offer Status Breakdown", labels={"Count": "Number of Employees"})
st.plotly_chart(fig_offer, use_container_width=True)

# 📌 Hiring by Department
st.write("### Hiring by Department")
department_counts = hiring_process_df["department"].value_counts().reset_index()
department_counts.columns = ["Department", "Count"]
fig_dept = px.bar(department_counts, x="Department", y="Count", color="Department", text="Count",
                  title="Hiring by Department", labels={"Count": "Number of Employees"})
st.plotly_chart(fig_dept, use_container_width=True)

# 📌 Open Positions by Department
st.write("### Open Positions by Department")
open_positions_counts = open_positions_df["department"].value_counts().reset_index()
open_positions_counts.columns = ["Department", "Count"]
fig_open_positions = px.bar(open_positions_counts, x="Department", y="Count", color="Department", text="Count",
                            title="Open Positions by Department", labels={"Count": "Number of Openings"})
st.plotly_chart(fig_open_positions, use_container_width=True)

# 📌 Company Distribution by Department
st.write("### Company Distribution by Department")

if "company" in df_org.columns and "department" in df_org.columns:
    company_dept_counts = df_org[
        df_org["company"].notna() & df_org["department"].notna() & 
        (df_org["company"].str.strip() != "") & (df_org["department"].str.strip() != "")
    ]
    company_dept_counts = company_dept_counts.groupby(["company", "department"]).size().reset_index(name="Count")

    if not company_dept_counts.empty:
        fig_company_dept = px.bar(
            company_dept_counts, x="department", y="Count", color="company", text="Count",
            title="Company Distribution Across Departments",
            labels={"Count": "Number of Employees", "department": "Department", "company": "Company"}
        )
        st.plotly_chart(fig_company_dept, use_container_width=True)
    else:
        st.write("ℹ️ No data available for Company Distribution by Department.")
