import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import numpy as np
# -------------------------
# Página y CSS
# -------------------------
st.set_page_config(page_title="Compliance Dashboard KRIs", layout="wide")
st.markdown(
    """
    <style>
    .title {
         font-size: 2rem;
         font-weight: bold;
         text-align: center;
         margin-bottom: 1rem;
         color: white;
    }
    .subheader {
         font-size: 1.25rem;
         font-weight: 600;
         text-align: center;
         margin-top: 1rem;
         color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="title">Compliance Dashboard KRIs</p>', unsafe_allow_html=True)



# -------------------------
# Cargar Datos de Google Sheets
# -------------------------
@st.cache_data(ttl=600)
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    SHEET_ID = "1kNILyJzBS5794YmBfPRLdAISb4vMbUZ9G2BjGKDgDDw"
    worksheet = client.open_by_key(SHEET_ID).worksheet("Compliance Org Structure & Open")
    df = pd.DataFrame(worksheet.get_all_records())
    df.columns = df.columns.str.strip()
    return df

df_org = load_data()
df_active = df_org[df_org['Status'].str.lower() == 'active'].copy()




# -------------------------
# Limpieza de Datos Numéricos
# -------------------------
for col in ['Salary', 'Equity', 'Token']:
    df_active[col] = df_active[col].replace('[\$,]', '', regex=True)
    df_active[col] = pd.to_numeric(df_active[col], errors='coerce')

# -------------------------
# Geocodificación Dinámica (Country, State)
# -------------------------
@st.cache_data(ttl=86400, show_spinner=False)
def get_coords_from_geopy(country, state):
    geolocator = Nominatim(user_agent="employee_geocoder")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    query = f"{state}, {country}"
    location = geocode(query)
    if location:
        return location.latitude, location.longitude
    else:
        return None, None

unique_locs = df_active[['Country', 'State']].drop_duplicates().copy()
unique_locs["coords"] = unique_locs.apply(lambda row: get_coords_from_geopy(row["Country"], row["State"]), axis=1)
unique_locs["lat"] = unique_locs["coords"].apply(lambda x: x[0])
unique_locs["lon"] = unique_locs["coords"].apply(lambda x: x[1])
df_active = df_active.merge(unique_locs[["Country", "State", "lat", "lon"]], on=["Country", "State"], how="left")
df_active = df_active.dropna(subset=["lat", "lon"])

# -------------------------
# Filtros en el Sidebar (Panel Izquierdo)
# -------------------------
st.sidebar.header("🛠 Filters")

with st.sidebar.expander("📍 Location Filters", expanded=False):
    selected_country = st.selectbox("Select a Country", ["All"] + sorted(df_active["Country"].unique()))
    if selected_country != "All":
        filtered_states = df_active[df_active["Country"] == selected_country]["State"].unique()
        selected_state = st.selectbox("Select a State", ["All"] + sorted(filtered_states))
    else:
        selected_state = "All"

with st.sidebar.expander("💰 Budget Filters", expanded=False):
    budget_total = st.number_input("Total Budget", value=1000000, step=10000)


with st.sidebar.expander("🏢 Department & Position Filters", expanded=False):
    selected_department = st.multiselect("Select Department(s)", df_active["Department"].unique(), default=df_active["Department"].unique())
    selected_job_level = st.multiselect("Select Job Level(s)", ["VP", "AVP", "Analyst", "Associate", "Consultors"], default=["VP", "AVP", "Analyst", "Associate", "Consultors"])

# -------------------------
# Filtrar Datos según la Selección
# -------------------------
filtered_df = df_active.copy()
if selected_country != "All":
    filtered_df = filtered_df[filtered_df["Country"] == selected_country]
if selected_state != "All":
    filtered_df = filtered_df[filtered_df["State"] == selected_state]
if selected_department:
    filtered_df = filtered_df[filtered_df["Department"].isin(selected_department)]

# -------------------------
# Indicadores Clave (KRIs)
# -------------------------
total_salary = filtered_df['Salary'].sum()
remaining_budget = budget_total - total_salary
total_equity = filtered_df['Equity'].sum()
total_tokens = filtered_df['Token'].sum()
total_employees = filtered_df.shape[0]

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Salary", f"${total_salary:,.2f}")
col2.metric("Total Budget", f"${budget_total:,.2f}")
col3.metric("Remaining Budget", f"${remaining_budget:,.2f}")
col4.metric("Total Equity", f"${total_equity:,.2f}")
col5.metric("Total Tokens", f"${total_tokens:,.2f}")
st.markdown(f'<p class="subheader">Total Active Employees: {total_employees}</p>', unsafe_allow_html=True)

# -------------------------
# Gráfica de Barras: Empleados por Departamento
# -------------------------
df_dept = df_active.groupby("Department").size().reset_index(name="Employee Count")
fig_dept = px.bar(
    df_dept,
    x="Department",
    y="Employee Count",
    title="Employees by Department",
    color="Department",
    text="Employee Count",
    template="plotly_white"
)
fig_dept.update_traces(texttemplate='%{text}', textposition='outside')
st.markdown("### Employees by Department")
st.plotly_chart(fig_dept, use_container_width=True)


# -------------------------
# Gráfica de Barras: Empleados por País
# -------------------------
df_country = df_active.groupby("Country").size().reset_index(name="Employee Count")
fig_country = px.bar(
    df_country,
    x="Country",
    y="Employee Count",
    title="Employees by Country",
    color="Country",
    text="Employee Count",
    template="plotly_white"
)
fig_country.update_traces(texttemplate='%{text}', textposition='outside')
st.markdown("### Employees by Country")
st.plotly_chart(fig_country, use_container_width=True)


# -------------------------
# Mapa con Filtro (Ubicaciones de Empleados)
# -------------------------
df_location = filtered_df.groupby(['Country', 'State', 'lat', 'lon']).agg({
    'Compliance Employee': 'count'
}).reset_index().rename(columns={'Compliance Employee': 'Employee Count'})

fig_map = px.scatter_mapbox(
    df_location,
    lat="lat",
    lon="lon",
    size="Employee Count",
    size_max=30,
    hover_name="Country",
    hover_data=["State", "Employee Count"],
    zoom=3,
    height=600,
    title="Employee Locations"
)
fig_map.update_layout(
    mapbox_style="carto-darkmatter",  # Cambia el fondo a negro
    margin={"r": 0, "t": 50, "l": 0, "b": 0},
    uirevision="constant"
)

st.markdown("### Employee Locations (Filtered)")
st.plotly_chart(fig_map, use_container_width=True)

# -------------------------
# Tabla de Detalles con Filtro
# -------------------------
st.markdown("### Employee Details (Filtered)")
st.dataframe(filtered_df, use_container_width=True)




# -------------------------
# Gráfico: Total Equity Granted por Departamento
# -------------------------
df_equity_department = filtered_df[['Department', 'Equity']].dropna()
df_equity_department = df_equity_department.groupby('Department', as_index=False)['Equity'].sum()

fig_equity_department = px.bar(
    df_equity_department,
    x='Department',
    y='Equity',
    title="Total Equity Granted per Department",
    color='Department',
    text='Equity',
    template="plotly_white"
)
fig_equity_department.update_traces(texttemplate='%{text:.2f}', textposition='outside')
fig_equity_department.update_layout(xaxis_title="Department", yaxis_title="Total Equity", xaxis={'categoryorder':'total descending'})

st.markdown("### Total Equity Granted per Department")
st.plotly_chart(fig_equity_department, use_container_width=True)

# Total Tokens por Departamento
df_tokens_department = filtered_df.groupby('Department', as_index=False)['Token'].sum()
fig_tokens_department = px.bar(df_tokens_department, x='Department', y='Token', title="🏢 Total Tokens Granted per Department", color='Department', text='Token', template="plotly_white")
fig_tokens_department.update_traces(texttemplate='%{text:.2f}', textposition='outside')

st.plotly_chart(fig_tokens_department, use_container_width=True)

# -------------------------
# Listas de empleados
# -------------------------
st.markdown("### Employee Lists")

# Lista de empleados activos (filtrando correctamente con paréntesis en la condición)
st.write("**List of current active employees:**", 
         df_active[(df_active['Status'].str.lower() == 'active') & 
                   (df_active['Contract'].str.contains('Arkham Employee', na=False))])

# Lista de empleados que fueron despedidos
st.write("**List of employees who were let go:**", 
         df_org[df_org['Status'].str.lower() == 'inactive'])

# Lista de consultores con números de presupuesto asociados
st.write("**List of consultants with associated budget numbers:**", 
         df_active[(df_active['Status'].str.lower() == 'active') & 
                   (df_active['Contract'].str.contains('Consultants', na=False))])










