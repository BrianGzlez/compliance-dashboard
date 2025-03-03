import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import numpy as np 

st.markdown(
    """
    <style>
        div[data-testid="metric-container"] {
            width: 100% !important;
            text-align: center;
            font-size: 16px !important;  /* Reduce el tamaño de los números */
        }
        div[data-testid="stMetric"] > label {
            font-size: 16px !important;  /* Reduce el tamaño del título */
        }
        div[data-testid="stMetric"] > div {
            font-size: 22px !important;  /* Ajusta el tamaño de los números */
        }
    </style>
    """,
    unsafe_allow_html=True
)

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

# Verificar si df_vendors no está vacío antes de aplicar la limpieza
if not df_vendors.empty:
    for col in ["Contract Monthly Price", "Contract Yearly Price"]:
        if col in df_vendors.columns:
            clean_numeric_column(df_vendors, col)

# Aplicar limpieza a df_org (empleados)
for col in ['Salary', 'Equity', 'Token']:
    if col in df_org.columns:
        clean_numeric_column(df_org, col)

# Filtrar empleados activos
df_active = df_org[df_org['Status'].str.lower() == 'active'].copy()

# Calcular el costo total por empleado
df_active["Total Cost"] = df_active["Salary"] + df_active["Equity"] + df_active["Token"]
df_active["Total Salary per Month"] = df_active["Salary"] / 12

# Llenar valores NaN con 0
df_active.fillna(0, inplace=True)
df_org.fillna(0, inplace=True)

df_active["Total Salary per Month"] = df_active["Salary"] / 12
# Asegurar que las columnas numéricas sean de tipo float en df_org
for col in ['Salary', 'Equity', 'Token']:
    df_org[col] = df_org[col].replace(r'[$,]', '', regex=True).astype(float)

# Calcular el costo total por empleado
df_org["Total Cost"] = df_org["Salary"] + df_org["Equity"] + df_org["Token"]

# Llenar valores NaN con 0 para evitar errores en cálculos
df_org.fillna(0, inplace=True)

# Asegurar que Total Cost es float
df_org["Total Cost"] = df_org["Total Cost"].astype(float)


# Llenar valores NaN con 0 para evitar errores en cálculos
df_org.fillna(0, inplace=True)



# ✅ Asegurar que "Position" se mantiene correctamente en df_active
df_active["Position"] = df_active["Position"].str.strip()


# -------------------------
# Filtros en el Sidebar (Panel Izquierdo)
# -------------------------
st.sidebar.header("🛠 Filters")

with st.sidebar.expander("📍 Location Filters", expanded=False):
    selected_state = st.multiselect("Select State(s)", df_active["State"].unique(), default=df_active["State"].unique())

with st.sidebar.expander("🏢 Department Filters", expanded=False):
    selected_department = st.multiselect("Select Department(s)", df_active["Department"].unique(), default=df_active["Department"].unique())

with st.sidebar.expander("💼 Position Filters", expanded=False):
    available_positions = df_active["Position"].unique().tolist()  # Obtener todas las posiciones únicas
    selected_job_level = st.multiselect("Select Position", available_positions, default=available_positions)

    

df_filtered = df_active[(df_active["Department"].isin(selected_department)) & (df_active["State"].isin(selected_state)) & (df_active["Position"].isin(selected_job_level))]

# -------------------------
# Métricas clave
# -------------------------
# Asegurar que "Contract Yearly Price" es numérico
# Convertir precios a formato numérico, asegurando que los valores vacíos sean 0
for col in ["Contract Monthly Price", "Contract Yearly Price"]:
    if col in df_vendors.columns:
        df_vendors[col] = df_vendors[col].astype(str).replace(r'[$,]', '', regex=True).replace('', '0').astype(float)


df_vendors["Contract Yearly Price"] = df_vendors["Contract Yearly Price"].replace(r'[$,]', '', regex=True)
df_vendors["Contract Yearly Price"] = pd.to_numeric(df_vendors["Contract Yearly Price"], errors="coerce").fillna(0)

# Filtrar solo empleados Full-Time (Arkham Employee) y activos
df_full_time = df_org[(df_org["Contract"] == "Arkham Employee") & (df_org["Status"].str.lower() == "active")]

# Calcular métricas clave para Full-Time
full_time_salary_total = df_full_time["Salary"].sum()
full_time_monthly_salary_total = full_time_salary_total / 12
full_time_headcount = df_full_time.shape[0]

# Calcular métricas clave para Consultores
df_consultant = df_org[df_org["Contract"].str.lower() == "consultants"]
df_consultant_salary_total = df_consultant["Salary"].sum()
df_consultant_monthly_total = df_consultant_salary_total / 12
df_consultant_headcount = df_consultant.shape[0]

# Calcular costos de vendors activos
df_active_vendors = df_vendors[df_vendors["Status"].str.lower() == "active"]
total_vendor_cost_yearly = df_active_vendors["Contract Yearly Price"].sum()
total_vendor_cost_monthly = df_active_vendors["Contract Monthly Price"].sum()

# Calcular costo de operaciones de cumplimiento
total_compliance_operation_cost_yearly = full_time_salary_total + df_consultant_salary_total + total_vendor_cost_yearly
total_compliance_operation_cost_monthly = total_compliance_operation_cost_yearly / 12

st.title("Compliance Operation Cost(s)")

col1, col2, col3, col4 = st.columns(4)

# Row 1
with col1:
    st.metric("Total Salary (Yearly)", f"${full_time_salary_total:,.2f}")
with col2:
    st.metric("Total Equity Allocated", f"${df_full_time['Equity'].sum():,.2f}")
with col3:
    st.metric("Total Token Allocated", f"${df_full_time['Token'].sum():,.2f}")
with col4:
    st.metric("Full-Time Head Count", f"{full_time_headcount}")

# Row 2
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Salary (Monthly)", f"${full_time_monthly_salary_total:,.2f}")
with col2:
    st.metric("Average Salary", f"${df_full_time['Salary'].mean():,.2f}")
with col3:
    st.metric("Average Equity Allocation", f"${df_full_time['Equity'].mean():,.2f}")
with col4:
    st.metric("Average Token Allocation", f"${df_full_time['Token'].mean():,.2f}")

# Row 3
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Consultant Cost (Yearly)", f"${df_consultant_salary_total:,.2f}")
with col2:
    st.metric("Total Consultant Cost (Monthly)", f"${df_consultant_monthly_total:,.2f}")
with col3:
    st.metric("Total Vendor Cost (Yearly)", f"${total_vendor_cost_yearly:,.2f}")
with col4:
    st.metric("Total Vendor Cost (Monthly)", f"${total_vendor_cost_monthly:,.2f}")

# Row 4
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Consultant Head Count", f"{df_consultant_headcount}")
with col2:
    st.metric("Compliance Operations Cost (Yearly)", f"${total_compliance_operation_cost_yearly:,.2f}")
with col3:
    st.metric("Compliance Operations Cost (Monthly)", f"${total_compliance_operation_cost_monthly:,.2f}")
with col4:
    st.empty()


# -------------------------
# Visualizaciones
# -------------------------
st.plotly_chart(px.bar(df_filtered, x="Department", y="Total Cost", title="Total Cost by Department", color="Department"))
fig_pie = px.pie(df_filtered, names="Position", values="Total Cost", title="Total Cost by Position", hole=0.3, template="plotly_white")
fig_pie.update_traces(textinfo='percent+label', pull=[0.1 if i == max(df_filtered["Total Cost"]) else 0 for i in df_filtered["Total Cost"]])
st.plotly_chart(fig_pie)

# Mostrar tabla de empleados cuando se filtra por gráfico o sidebar
if len(selected_job_level) == 1:
    st.subheader(f"Employees in {selected_job_level[0]} Level")
    df_filtered_by_level = df_filtered[df_filtered["Position"] == selected_job_level[0]]
    st.dataframe(df_filtered_by_level[['Compliance Employee', 'Title', 'Department', 'Position', 'Salary', 'Equity', 'Token', 'Total Cost']])


# -------------------------
# Tabla con la Información de Empleados
# -------------------------
st.subheader("Employee Details")
col_details, col_chart = st.columns(2)

with col_details:
    st.dataframe(df_filtered[['Compliance Employee', 'Title', 'Department', 'Position', 'Salary', 'Equity', 'Token', 'Total Cost']])

with col_chart:
    st.plotly_chart(px.box(df_filtered, x='Position', y='Total Cost', title="Total Cost Distribution by Position", color='Position', template="plotly_white"))


# -------------------------
# Crear Rangos de Equity y Tokens
# -------------------------
bins = [0, 10000, 20000, 30000, 40000, 50000, np.inf]
labels = ["0-10K", "10K-20K", "20K-30K", "30K-40K", "40K-50K", "50K+"]

df_filtered['Equity Range'] = pd.cut(df_filtered['Equity'], bins=bins, labels=labels, right=False)
df_filtered['Token Range'] = pd.cut(df_filtered['Token'], bins=bins, labels=labels, right=False)

# Visualización de Rangos de Equity y Tokens
col5, col6 = st.columns(2)

with col5:
    df_equity_range = df_filtered.groupby('Equity Range', as_index=False).size().rename(columns={'size': 'Employee Count'})
    st.plotly_chart(px.bar(df_equity_range, x='Equity Range', y='Employee Count', title="📊 Employees per Equity Range", color='Equity Range', text='Employee Count', template="plotly_white"))

with col6:
    df_token_range = df_filtered.groupby('Token Range', as_index=False).size().rename(columns={'size': 'Employee Count'})
    st.plotly_chart(px.pie(df_token_range, names='Token Range', values='Employee Count', title="🍩 Token Distribution by Range", hole=0.3, template="plotly_white"))

# -------------------------
# Total Tokens y Equity por Departamento
# -------------------------
df_tokens_equity_department = df_filtered.groupby('Department', as_index=False)[['Token', 'Equity']].sum()
st.plotly_chart(px.bar(df_tokens_equity_department, x='Department', y=['Token', 'Equity'], title="🏢 Total Token and Equity Granted per Department", barmode='group', text_auto=True, template="plotly_white"))


# -------------------------
# Pay Bands Visualization
# -------------------------
st.subheader("Pay Bands by Department")

if "Department" in df_filtered.columns and "Salary" in df_filtered.columns:
    fig_pay_bands = px.box(
        df_filtered, 
        x='Department', 
        y='Salary', 
        title="Salary Distribution by Department", 
        color='Department', 
        template="plotly_white"
    )
    st.plotly_chart(fig_pay_bands)
else:
    st.write("ℹ️ No data available for Salary Distribution by Department.")




# -------------------------
# Budget Impact and Monthly Projection
# -------------------------
st.subheader("📊 Compliance Open Positions")

# Agregar filtro en el sidebar para seleccionar el tipo de impacto presupuestario
with st.sidebar.expander("💰 Budget Filters", expanded=False):
    budget_input = st.number_input("Enter the Estimated Annual Budget ($)", min_value=0, value=10000000, step=100000)

# Calcular el salario total de posiciones abiertas si aún no está definido
df_open_position_salary_total = df_org[df_org["Status"].str.lower() == "open position"]["Salary"].sum()
df_active_salary_total = df_org[df_org["Status"].str.lower() == "active"]["Salary"].sum()
df_offer_stage_salary_total = df_org[df_org["Status"].str.lower() == "offer stage"]["Salary"].sum()

total_with_hires = df_active_salary_total + df_open_position_salary_total + df_offer_stage_salary_total

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Open Positions #", f"{df_org[df_org['Status'].str.lower() == 'open position'].shape[0]}")

with col2:
    st.metric("Total Anticipated Employees", f"{df_filtered.shape[0] + df_org[df_org['Status'].str.lower() == 'open position'].shape[0]}")

with col3:
    st.metric("Open Position Salary (Yearly)", f"${df_open_position_salary_total:,.2f}")

col4, col5, col6 = st.columns(3)

with col4:
    st.metric("Open Position Salary (Monthly)", f"${df_open_position_salary_total / 12:,.2f}")

with col5:
    st.metric("Total Monthly (Actual + Open)", f"${(df_active_salary_total + df_open_position_salary_total) / 12:,.2f}")

with col6:
    st.metric("Total Yearly (Actual + Open)", f"${df_active_salary_total + df_open_position_salary_total:,.2f}")

# Crear gráfico de barras comparando los diferentes escenarios
fig_budget_comparison = px.bar(
    x=["Current Salary Usage", "Projected with Hires", "Budget"],
    y=[df_active_salary_total, total_with_hires, budget_input],
    title="Budget Scenario Comparison",
    labels={"x": "Scenario", "y": "Total Salary ($)"},
    template="plotly_white",
    text_auto=True
)

st.plotly_chart(fig_budget_comparison)

# -------------------------
# Vendor Cost Analysis
# -------------------------
st.subheader("Compliance Vendor Cost(s)")

# Convertir precios a formato numérico
df_vendors["Contract Monthly Price"] = df_vendors["Contract Monthly Price"].replace(r'[$,]', '', regex=True).astype(float)
df_vendors["Contract Yearly Price"] = df_vendors["Contract Yearly Price"].replace(r'[$,]', '', regex=True).astype(float)

# Filtrar solo vendors activos para métricas clave
df_active_vendors = df_vendors[df_vendors["Status"].str.lower() == "active"]
df_vendors["Contract Yearly Price"] = df_vendors["Contract Yearly Price"].replace(r'[$,]', '', regex=True).astype(float)

# Filtrar solo vendors activos
df_active_vendors = df_vendors[df_vendors["Status"].str.lower() == "active"]

# Calcular métricas clave
total_yearly_cost = df_active_vendors["Contract Yearly Price"].sum()
total_monthly_cost = df_active_vendors["Contract Monthly Price"].sum()
num_vendors = df_active_vendors.shape[0]

# Mostrar métricas clave
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Yearly Vendor Cost", f"${total_yearly_cost:,.2f}")
with col2:
    st.metric("Total Monthly Vendor Cost", f"${total_monthly_cost:,.2f}")
with col3:
    st.metric("Number of Active Vendors", num_vendors)

# Gráficos
fig_vendor_cost = px.bar(df_active_vendors, x="Vendor Name", y="Contract Yearly Price", title="Yearly Cost per Vendor",
                         labels={"Contract Yearly Price": "Yearly Cost ($)"}, template="plotly_white", text_auto=True, color="Vendor Name")
st.plotly_chart(fig_vendor_cost)

col_chart, col_table = st.columns(2)
with col_chart:
    fig_vendor_status = px.pie(df_vendors, names="Status", values="Contract Yearly Price", title="Cost Distribution by Vendor Status",
                               hole=0.3, template="plotly_white")
    st.plotly_chart(fig_vendor_status)

with col_table:
    st.subheader("📜 Vendor Details")
    st.dataframe(df_vendors[["Status", "Vendor Name", "Vendor Contact Name", "Vendor Email", "Contract Duration", "Contract Monthly Price", "Contract Yearly Price"]])

