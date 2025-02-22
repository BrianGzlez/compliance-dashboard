import streamlit as st
import pandas as pd
import gspread
import graphviz
import json
from google.oauth2.service_account import Credentials

# Configurar página
st.set_page_config(page_title="Organizational Chart", layout="wide")

# 🔐 Cargar credenciales desde Streamlit Secrets
creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(creds_dict)
client = gspread.authorize(creds)

# ID de la Hoja de Google Sheets
SHEET_ID = "1kNILyJzBS5794YmBfPRLdAISb4vMbUZ9G2BjGKDgDDw"
SHEET_NAME = "Compliance Org Structure & Open"

# 📂 Función para cargar datos desde Google Sheets
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
selected_department = st.sidebar.selectbox("Select Department:", departments)

# 🔎 Filtrar datos por departamento
filtered_df = df[df["Department"] == selected_department]

# 🎨 Generar gráfico con Graphviz
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

for _, row in filtered_df.iterrows():
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
        if direct_report == "Adam Westwood-Booth":
            direct_report_title = "Head of Compliance"
        else:
            direct_report_title = filtered_df.loc[filtered_df["Employee"] == direct_report, "Title"]
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

# 📌 Mostrar gráfico en Streamlit
st.graphviz_chart(dot)
