import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import numpy as np

# -------------------------
# Cargar Datos desde Google Sheets
# -------------------------
@st.cache_data(ttl=600)
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    SHEET_ID = "1kNILyJzBS5794YmBfPRLdAISb4vMbUZ9G2BjGKDgDDw"

    # Cargar Compliance Org Structure & Open
    worksheet_compliance = client.open_by_key(SHEET_ID).worksheet("Compliance Org Structure & Open")
    df_compliance = pd.DataFrame(worksheet_compliance.get_all_records())
    df_compliance.columns = df_compliance.columns.str.strip()

    # Cargar Vendor Management
    worksheet_vendor = client.open_by_key(SHEET_ID).worksheet("Vendor Management")
    df_vendors = pd.DataFrame(worksheet_vendor.get_all_records())
    df_vendors.columns = df_vendors.columns.str.strip()

    return df_compliance, df_vendors

# Cargar los datos
df_org, df_vendors = load_data()

# Filtrar empleados activos
df_active = df_org[df_org['Status'].str.lower() == 'active'].copy()

# -------------------------
# Limpieza de Datos Numéricos
# -------------------------
for col in ['Salary', 'Equity', 'Token']:
    df_active[col] = df_active[col].replace(r'[$,]', '', regex=True).astype(float)

# Calcular Costo Total por Empleado
df_active["Total Cost"] = df_active["Salary"] + df_active["Equity"] + df_active["Token"]
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

def categorize_title(title, contract):
    title = title.lower()
    if contract.lower() == "consultants":
        return "Consultors"
    elif any(substring in title for substring in ["vp - program governance", "vp - global sanctions", "vp - compliance technology", "vp - financial crimes", "vp - kyc & onboarding", "vp - crypto investigations", "vp - bsa officer / risk officer"]):
        return "VP"
    elif any(substring in title for substring in ["avp - compliance team lead", "avp - onboarding & kyc (edd)", "avp - program governance", "avp - fraud", "avp - vendor management"]):
        return "AVP"
    elif "analyst" in title:
        return "Analyst"
    elif "associate" in title:
        return "Associate"
    return "Other"

df_active["Job Level"] = df_active.apply(lambda row: "Consultors" if row["Contract"].lower() == "consultants" else row["Position"], axis=1)
# -------------------------
# Filtros en el Sidebar (Panel Izquierdo)
# -------------------------
st.sidebar.header("🛠 Filters")

with st.sidebar.expander("📍 Location Filters", expanded=False):
    selected_state = st.multiselect("Select State(s)", df_active["State"].unique(), default=df_active["State"].unique())

with st.sidebar.expander("🏢 Department Filters", expanded=False):
    selected_department = st.multiselect("Select Department(s)", df_active["Department"].unique(), default=df_active["Department"].unique())

with st.sidebar.expander("💼 Job Level Filters", expanded=False):
    selected_job_level = st.multiselect("Select Job Level(s)", ["VP", "AVP", "Analyst", "Associate", "Consultors"], default=["VP", "AVP", "Analyst", "Associate", "Consultors"])
    

df_filtered = df_active[(df_active["Department"].isin(selected_department)) & (df_active["State"].isin(selected_state)) & (df_active["Job Level"].isin(selected_job_level))]

# -------------------------
# Métricas clave
# -------------------------
# Asegurar que "Contract Yearly Price" es numérico
df_vendors["Contract Yearly Price"] = df_vendors["Contract Yearly Price"].replace(r'[$,]', '', regex=True)
df_vendors["Contract Yearly Price"] = pd.to_numeric(df_vendors["Contract Yearly Price"], errors="coerce").fillna(0)



# Calcular el total de costos de licencias (solo vendors activos)
total_licensing_cost = df_vendors[df_vendors["Status"].str.lower() == "active"]["Contract Yearly Price"].sum()

# Calcular el costo total de operación del compliance
total_compliance_operation_cost = df_filtered["Total Cost"].sum() + total_licensing_cost

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

with col4:
    st.metric("Total Vendor Cost per Year", f"${total_licensing_cost:,.2f}")
    st.metric("Total Compliance Operation Cost", f"${total_compliance_operation_cost:,.2f}")


# -------------------------
# Visualizaciones
# -------------------------
st.plotly_chart(px.bar(df_filtered, x="Department", y="Total Cost", title="Total Cost by Department", color="Department"))
fig_pie = px.pie(df_filtered, names="Job Level", values="Total Cost", title="Total Cost by Job Level", hole=0.3, template="plotly_white")
fig_pie.update_traces(textinfo='percent+label', pull=[0.1 if i == max(df_filtered["Total Cost"]) else 0 for i in df_filtered["Total Cost"]])
st.plotly_chart(fig_pie)

# Mostrar tabla de empleados cuando se filtra por gráfico o sidebar
if len(selected_job_level) == 1:
    st.subheader(f"Employees in {selected_job_level[0]} Level")
    df_filtered_by_level = df_filtered[df_filtered["Job Level"] == selected_job_level[0]]
    st.dataframe(df_filtered_by_level[['Compliance Employee', 'Title', 'Department', 'Job Level', 'Salary', 'Equity', 'Token', 'Total Cost']])


# -------------------------
# Tabla con la Información de Empleados
# -------------------------
st.subheader("Employee Details")
col_details, col_chart = st.columns(2)

with col_details:
    st.dataframe(df_filtered[['Compliance Employee', 'Title', 'Department', 'Job Level', 'Salary', 'Equity', 'Token', 'Total Cost']])

with col_chart:
    st.plotly_chart(px.box(df_filtered, x='Job Level', y='Total Cost', title="Total Cost Distribution by Job Level", color='Job Level', template="plotly_white"))


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
st.subheader("📊 Budget Impact")

# Agregar filtro en el sidebar para seleccionar el tipo de impacto presupuestario
with st.sidebar.expander("💰 Budget Filters", expanded=False):
    budget_input = st.number_input("Enter the Estimated Annual Budget ($)", min_value=0, value=10000000, step=100000)




# Filtrar datos según el estado de los empleados
df_active_total = df_org[df_org["Status"].str.lower() == "active"]["Total Cost"].sum()
df_offer_stage_total = df_org[df_org["Status"].str.lower() == "offer stage"]["Total Cost"].sum()
df_open_position_total = df_org[df_org["Status"].str.lower() == "open position"]["Total Cost"].sum()

# Calcular el incremento en caso de contratar todas las posiciones abiertas y en oferta
total_with_hires = df_active_total + df_offer_stage_total + df_open_position_total
increase_percentage = ((total_with_hires - df_active_total) / df_active_total) * 100 if df_active_total > 0 else 0

# Mostrar los valores calculados
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Current Year Budget Usage", f"${df_active_total:,.2f}")
    st.metric("Projected Budget with Hires", f"${total_with_hires:,.2f}")
with col2:
    st.metric("Increase %", f"{increase_percentage:.2f}%")
    st.metric("Allowed Monthly Budget", f"${budget_input / 12:,.2f}")
with col3:
    st.metric("Offer Stage Positions Cost", f"${df_offer_stage_total:,.2f}")
    st.metric("Open Positions Cost", f"${df_open_position_total:,.2f}")
with col4:
    remaining_budget = budget_input - total_with_hires
    st.metric("Remaining Budget", f"${remaining_budget:,.2f}")

# Crear gráfico de barras comparando los diferentes escenarios
fig_budget_comparison = px.bar(
    x=["Current Budget Usage", "Projected with Hires", "Budget"],
    y=[df_active_total, total_with_hires, budget_input],
    title="Budget Scenario Comparison",
    labels={"x": "Scenario", "y": "Total Cost ($)"},
    template="plotly_white",
    text_auto=True
)

st.plotly_chart(fig_budget_comparison)
# -------------------------
# Vendor Cost Analysis
# -------------------------
st.subheader("💰 Vendor Cost Analysis")

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
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Yearly Vendor Cost", f"${total_yearly_cost:,.2f}")
with col2:
    st.metric("Total Monthly Vendor Cost", f"${total_monthly_cost:,.2f}")
with col3:
    st.metric("Number of Active Vendors", num_vendors)
with col4:
    avg_yearly_cost = total_yearly_cost / num_vendors if num_vendors > 0 else 0
    st.metric("Avg Yearly Cost per Vendor", f"${avg_yearly_cost:,.2f}")

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