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

# Función para limpiar columnas numéricas (para vendors)
def clean_numeric_column(df, col):
    # Convertir a string y eliminar espacios
    df[col] = df[col].astype(str).str.strip()
    # Eliminar símbolos de moneda y comas
    df[col] = df[col].replace(r'[$,]', '', regex=True)
    # Reemplazar valores problemáticos por '0'
    df[col] = df[col].replace(['', ' ', 'N/A', 'NULL', 'None', '-', '--'], '0')
    # Convertir a numérico, forzando errores a NaN y luego llenarlos con 0
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Limpieza de Datos Numéricos para df_org (empleados)
for col in ['Salary', 'Equity', 'Token']:
    # Convertir a string, eliminar espacios y símbolos no deseados
    df_org[col] = df_org[col].astype(str).str.strip()
    df_org[col] = df_org[col].replace(r'[$,]', '', regex=True)
    # Reemplazar valores problemáticos por '0'
    df_org[col] = df_org[col].replace(['', ' ', 'N/A', 'NULL', 'None', '-', '--'], '0')
    # Convertir a numérico usando pd.to_numeric en lugar de astype(float)
    df_org[col] = pd.to_numeric(df_org[col], errors='coerce').fillna(0)

# Limpieza de Datos Numéricos para df_vendors
for col in ["Contract Monthly Price", "Contract Yearly Price"]:
    clean_numeric_column(df_vendors, col)

# Filtrar empleados activos
df_active = df_org[df_org['Status'].str.lower() == 'active'].copy()

# Mostrar valores únicos ANTES de limpiar (para depuración)
st.write("Valores únicos antes de limpiar:", df_org[['Salary', 'Equity', 'Token']].drop_duplicates())

# Calcular el costo total por empleado y otras métricas
df_active["Total Cost"] = df_active["Salary"] + df_active["Equity"] + df_active["Token"]
df_active["Total Salary per Month"] = df_active["Salary"] / 12

# Asegurar que en caso de NaN se llenen con 0 (por si acaso)
df_org.fillna(0, inplace=True)
df_active.fillna(0, inplace=True)

# -------------------------
# Filtros en el Sidebar
# -------------------------
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

# -------------------------
# Métricas clave
# -------------------------
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

# -------------------------
# Visualizaciones
# -------------------------
st.plotly_chart(px.bar(df_filtered, x="Department", y="Total Cost", title="Total Cost by Department", color="Department"))
fig_pie = px.pie(df_filtered, names="Position", values="Total Cost", title="Total Cost by Position", hole=0.3, template="plotly_white")
st.plotly_chart(fig_pie)

# -------------------------
# Tabla con la Información de Empleados
# -------------------------
st.subheader("Employee Details")
st.dataframe(df_filtered[['Compliance Employee', 'Title', 'Department', 'Position', 'Salary', 'Equity', 'Token', 'Total Cost']])

# -------------------------
# Budget Impact and Monthly Projection
# -------------------------
st.subheader("📊 Budget Impact")

with st.sidebar.expander("💰 Budget Filters", expanded=False):
    budget_input = st.number_input("Enter the Estimated Annual Budget ($)", min_value=0, value=10000000, step=100000)

df_active_total = df_org[df_org["Status"].str.lower() == "active"]["Total Cost"].sum()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Current Year Budget Usage", f"${df_active_total:,.2f}")
with col2:
    st.metric("Allowed Monthly Budget", f"${budget_input / 12:,.2f}")
with col3:
    remaining_budget = budget_input - df_active_total
    st.metric("Remaining Budget", f"${remaining_budget:,.2f}")

# -------------------------
# Vendor Cost Analysis
# -------------------------
st.subheader("💰 Vendor Cost Analysis")

# Filtrar solo vendors activos
df_active_vendors = df_vendors[df_vendors["Status"].str.lower() == "active"]

# Calcular métricas clave
total_yearly_cost = df_active_vendors["Contract Yearly Price"].sum()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Yearly Vendor Cost", f"${total_yearly_cost:,.2f}")

fig_vendor_cost = px.bar(df_active_vendors, x="Vendor Name", y="Contract Yearly Price", title="Yearly Cost per Vendor",
                         labels={"Contract Yearly Price": "Yearly Cost ($)"}, template="plotly_white", text_auto=True, color="Vendor Name")
st.plotly_chart(fig_vendor_cost)

# Mostrar datos limpios de vendors
st.subheader("📜 Vendor Details")
st.dataframe(df_vendors[["Status", "Vendor Name", "Contract Yearly Price"]])
