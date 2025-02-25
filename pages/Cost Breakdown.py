import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px

# 📌 Configurar credenciales de Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/drive.readonly"]
SHEET_ID = "1R3EMYJt7he4CklRTRWtC6iqPzACg_eWyHdV6BaTzTms"

# Función para obtener credenciales
def get_credentials():
    if "google_credentials" in st.secrets:
        return Credentials.from_service_account_info(st.secrets["google_credentials"], scopes=SCOPES)
    else:
        return Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

# 📌 Cargar datos desde Google Sheets
@st.cache_data(ttl=600)
def load_data():
    try:
        creds = get_credentials()
        client = gspread.authorize(creds)

        # Cargar Compliance Org Structure & Open
        worksheet_compliance = client.open_by_key(SHEET_ID).worksheet("Compliance Org Structure & Open")
        df_compliance = pd.DataFrame(worksheet_compliance.get_all_records())
        df_compliance.columns = df_compliance.columns.str.strip()

        # Cargar Vendor Management
        worksheet_vendor = client.open_by_key(SHEET_ID).worksheet("Vendor Management")
        df_vendors = pd.DataFrame(worksheet_vendor.get_all_records())
        df_vendors.columns = df_vendors.columns.str.strip()

        return df_compliance, df_vendors
    except Exception as e:
        st.error(f"⚠️ Error al cargar datos desde Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame()

# Cargar los datos
df_org, df_vendors = load_data()

# 📊 Limpieza de Datos Numéricos
def clean_numeric_column(df, col):
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace(r'[$,]', '', regex=True)
        df[col] = df[col].replace(['', ' ', 'N/A', 'NULL', 'None', '-', '--'], None)
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df[col] = df[col].fillna(0)

# Aplicar limpieza a df_org (empleados)
for col in ['Salary', 'Equity', 'Token']:
    clean_numeric_column(df_org, col)

# Verificar si df_vendors tiene las columnas antes de limpiarlas
if not df_vendors.empty:
    for col in ["Contract Monthly Price", "Contract Yearly Price"]:
        clean_numeric_column(df_vendors, col)

# Filtrar empleados activos
df_active = df_org[df_org['Status'].str.lower() == 'active'].copy()

# Calcular el costo total por empleado
df_active["Total Cost"] = df_active["Salary"] + df_active["Equity"] + df_active["Token"]
df_active["Total Salary per Month"] = df_active["Salary"] / 12

# 📊 Filtros en el Sidebar
st.sidebar.header("🛠 Filters")

with st.sidebar.expander("📍 Location Filters", expanded=False):
    selected_state = st.multiselect("Select State(s)", df_active["State"].unique(), default=df_active["State"].unique())

with st.sidebar.expander("🏢 Department Filters", expanded=False):
    selected_department = st.multiselect("Select Department(s)", df_active["Department"].unique(), default=df_active["Department"].unique())

with st.sidebar.expander("💼 Position Filters", expanded=False):
    available_positions = df_active["Position"].unique().tolist()
    selected_job_level = st.multiselect("Select Position", available_positions, default=available_positions)

df_filtered = df_active[(df_active["Department"].isin(selected_department)) & 
                         (df_active["State"].isin(selected_state)) & 
                         (df_active["Position"].isin(selected_job_level))]

# 📊 Métricas clave
st.title("Compliance Employee Cost Breakdown")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Yearly Salary", f"${df_filtered['Salary'].sum():,.2f}")
    st.metric("Total Salary per Month", f"${df_filtered['Total Salary per Month'].sum():,.2f}")

with col2:
    st.metric("Total Yearly Equity", f"${df_filtered['Equity'].sum():,.2f}")
    st.metric("Average Salary", f"${df_filtered['Salary'].mean():,.2f}")

with col3:
    st.metric("Total Yearly Tokens", f"${df_filtered['Token'].sum():,.2f}")
    st.metric("Average Equity per Year", f"${df_filtered['Equity'].mean():,.2f}")

# 📊 Visualizaciones
st.plotly_chart(px.bar(df_filtered, x="Department", y="Total Cost", title="Total Cost by Department", color="Department"))
fig_pie = px.pie(df_filtered, names="Position", values="Total Cost", title="Total Cost by Position", hole=0.3, template="plotly_white")
st.plotly_chart(fig_pie)

# 📊 Tabla con la Información de Empleados
st.subheader("Employee Details")
st.dataframe(df_filtered[["Compliance Employee", "Title", "Department", "Position", "Salary", "Equity", "Token", "Total Cost"]])
