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

# 📌 Organizar jerarquía
def build_hierarchy(df):
    hierarchy = {}
    for _, row in df.iterrows():
        employee = row["Employee"]
        title = row["Title"]
        direct_report = row["DirectReport"]

        if direct_report not in hierarchy:
            hierarchy[direct_report] = []
        hierarchy[direct_report].append((employee, title))
    return hierarchy

hierarchy = build_hierarchy(filtered_df)

# 📌 Crear organigrama con nodos colapsables
selected_node = st.session_state.get("selected_node", None)

def generate_org_chart():
    nodes = []
    edges = []
    added_nodes = set()
    
    # Determinar nodo raíz
    root_nodes = [emp for emp in hierarchy if emp not in df["Employee"].values and emp != "Open Position"]
    
    # Si no hay un nodo seleccionado, mostrar solo la raíz
    if not selected_node:
        for root in root_nodes:
            title = df.loc[df["Employee"] == root, "Title"].values
            title = title[0] if len(title) > 0 else "Unknown Position"
            nodes.append(Node(id=root, label=f"{root}\n{title}", shape="box", color="#004488", font_color="white"))
            added_nodes.add(root)
    else:
        # Mostrar nodos expandidos
        title = df.loc[df["Employee"] == selected_node, "Title"].values
        title = title[0] if len(title) > 0 else "Unknown Position"
        nodes.append(Node(id=selected_node, label=f"{selected_node}\n{title}", shape="box", color="#004488", font_color="white"))
        if selected_node in hierarchy:
            for emp, emp_title in hierarchy[selected_node]:
                nodes.append(Node(id=emp, label=f"{emp}\n{emp_title}", shape="box", color="#004488", font_color="white"))
                edges.append(Edge(source=selected_node, target=emp))
                added_nodes.add(emp)
    
    config = Config(height=700, width=900, directed=True, hierarchical=True)
    return agraph(nodes=nodes, edges=edges, config=config)

# 📌 Manejar la selección del usuario
clicked_node = generate_org_chart()
if clicked_node:
    st.session_state["selected_node"] = clicked_node
