import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_agraph import agraph, Node, Edge, Config

# 📌 Definir los permisos (scopes) correctos para Google Sheets y Drive
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/drive.readonly"]
SHEET_ID = "1R3EMYJt7he4CklRTRWtC6iqPzACg_eWyHdV6BaTzTms"
SHEET_NAME = "Compliance Org Structure & Open"

# 📌 Obtener credenciales desde Streamlit Secrets o desde un archivo local
def get_credentials():
    if "google_credentials" in st.secrets:
        return Credentials.from_service_account_info(st.secrets["google_credentials"], scopes=SCOPES)
    else:
        return Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

# 📌 Autenticación con Google Sheets
try:
    creds = get_credentials()
    client = gspread.authorize(creds)
except Exception as e:
    st.error(f"🚨 Error al cargar las credenciales: {e}")
    st.stop()

# 📂 Función para cargar datos desde Google Sheets
@st.cache_data(ttl=600)
def load_data(sheet_name):
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"⚠️ Error loading sheet: {e}")
        return pd.DataFrame()

df = load_data(SHEET_NAME)

# 🚨 Validar si los datos están vacíos
if df.empty:
    st.stop()

# 📊 Limpieza de Datos
df = df[["Compliance Employee", "Title", "Direct Report", "Department", "Status"]].fillna("")
df.rename(columns={"Compliance Employee": "Employee",
                   "Title": "Title",
                   "Direct Report": "DirectReport",
                   "Department": "Department",
                   "Status": "Status"}, inplace=True)

df["Employee"] = df["Employee"].str.strip().replace("", "Open Position")
df["DirectReport"] = df["DirectReport"].str.strip().replace("", "Open Position")
df["Title"] = df["Title"].str.strip().replace("", "Unknown Position")
df["Status"] = df["Status"].str.strip().replace("", "Active")

# Asegurar que Adam Westwood-Booth siempre tenga el título correcto
df.loc[df["Employee"] == "Adam Westwood-Booth", "Title"] = "Head of Compliance"

# 🛑 Eliminar empleados inactivos
df = df[df["Status"].str.lower() != "inactive"]

# 📌 Sidebar para seleccionar departamento
departments = sorted(df["Department"].dropna().unique().tolist())  
selected_department = st.sidebar.selectbox("Select Department:", ["All Departments"] + departments)

# 🔎 Filtrar datos por departamento o mostrar toda la empresa
if selected_department == "All Departments":
    filtered_df = df.copy()  # Usamos todos los datos sin filtro
else:
    filtered_df = df[df["Department"] == selected_department]

# 🎨 Generar organigrama con Streamlit-Agraph
def generate_org_chart(data):
    nodes = []
    edges = []
    added_nodes = set()

    for _, row in data.iterrows():
        employee = row["Employee"]
        title = row["Title"]
        direct_report = row["DirectReport"]

        if employee not in added_nodes:
            nodes.append(Node(id=employee, label=f"{employee}\n{title}", shape="box", color="#004488"))
            added_nodes.add(employee)

        if direct_report and direct_report != "Open Position":
            if direct_report not in added_nodes:
                direct_report_title = data.loc[data["Employee"] == direct_report, "Title"]
                direct_report_title = direct_report_title.values[0] if not direct_report_title.empty else "Unknown Position"
                nodes.append(Node(id=direct_report, label=f"{direct_report}\n{direct_report_title}", shape="box", color="#004488"))
                added_nodes.add(direct_report)

            edges.append(Edge(source=direct_report, target=employee))

    config = Config(height=700, width=900, directed=True, hierarchical=True)
    return agraph(nodes=nodes, edges=edges, config=config)

# 📌 Mostrar organigrama en un solo gráfico
st.subheader(f"Structure: {selected_department}")
generate_org_chart(filtered_df)
