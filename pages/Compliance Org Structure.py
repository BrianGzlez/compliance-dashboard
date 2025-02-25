import streamlit as st
import pandas as pd
import gspread
import graphviz
from google.oauth2.service_account import Credentials

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

# 🎨 Función para generar organigrama
def generate_org_chart(data):
    dot = graphviz.Digraph(format="png")

    # 🔲 Configuración del diseño
    dot.attr(size="20,12", rankdir="TB", nodesep="0.5", ranksep="1.0", splines="true", concentrate="true", bgcolor="black")

    # 🎨 Colores para modo oscuro
    active_color = "#004488"  # Azul oscuro para empleados activos
    open_color = "#666666"  # Gris oscuro para posiciones abiertas
    text_color_active = "white"  # Texto blanco en nodos activos
    text_color_open = "black"  # Texto negro en posiciones abiertas
    edge_color = "white"  # Líneas blancas para contraste

    # 🔗 Agregar nodos y conexiones
    added_nodes = set()
    levels = {}

    for _, row in data.iterrows():
        employee = row["Employee"]
        title = row["Title"]
        direct_report = row["DirectReport"]

        # Asegurar que Adam Westwood-Booth siempre tenga "Head of Compliance"
        if employee == "Adam Westwood-Booth":
            title = "Head of Compliance"

        # Formato de etiquetas
        if employee == "Open Position":
            label = f"Open Position\n{title}"
            node_color = open_color
            font_color = text_color_open
        else:
            label = f"{employee}\n{title}"
            node_color = active_color
            font_color = text_color_active

        if employee not in added_nodes:
            dot.node(employee, label=label, shape="box", style="filled", fillcolor=node_color, fontcolor=font_color, fontsize="14", width="2", height="1")
            added_nodes.add(employee)

        if direct_report and direct_report != "Open Position":
            # Buscar título de DirectReport
            direct_report_title = data.loc[data["Employee"] == direct_report, "Title"]
            direct_report_title = direct_report_title.values[0] if not direct_report_title.empty else "Unknown Position"

            direct_report_label = f"{direct_report}\n{direct_report_title}"

            if direct_report not in added_nodes:
                dot.node(direct_report, label=direct_report_label, shape="box", style="filled", fillcolor=active_color, fontcolor=text_color_active, fontsize="14", width="2", height="1")
                added_nodes.add(direct_report)

            dot.edge(direct_report, employee, arrowhead="vee", color=edge_color, penwidth="2")

            # Organizar nodos en niveles
            if direct_report not in levels:
                levels[direct_report] = 0
            levels[employee] = levels[direct_report] + 1

    # 📌 Alinear nodos por niveles
    level_groups = {}
    for node, level in levels.items():
        if level not in level_groups:
            level_groups[level] = []
        level_groups[level].append(node)

    for level_nodes in level_groups.values():
        dot.attr(rank="same")
        for node in level_nodes:
            dot.node(node)

    return dot

# 📌 Mostrar organigrama en un solo gráfico
st.subheader(f"Organigrama: {selected_department}")
st.graphviz_chart(generate_org_chart(filtered_df))
