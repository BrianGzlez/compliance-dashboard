import streamlit as st
import time
import numpy as np
import matplotlib.pyplot as plt


# 📌 Forzar colores del dashboard con CSS
st.markdown(
    """
    <style>
        /* Color de fondo de la app */
        .stApp {
            background-color: #000000 !important;
        }

        /* Color de fondo de la barra lateral */
        section[data-testid="stSidebar"] {
            background-color: #1A1A1A !important;
        }

        /* Color de los inputs, selects y botones */
        div.st-bd {
            background-color: #31333F !important;
            color: #FFFFFF !important;
            border-radius: 10px !important;
        }

        /* Color del texto en toda la app */
        body, .stTextInput, .stSelectbox, .stButton, .stNumberInput, .stDataFrame {
            color: #FFFFFF !important;
            font-family: sans-serif !important;
        }

        /* Cambiar colores de los títulos */
        h1, h2, h3, h4, h5, h6 {
            color: #FFFFFF !important;
        }

        /* Cambiar color de métricas */
        div[data-testid="stMetricValue"] {
            color: #FFFFFF !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Compliance Dashboard")  # Prueba si los colores se aplican

# Configuración de la página con tema oscuro
st.set_page_config(page_title="Arkham Exchange - Compliance", layout="wide")

# Estilos personalizados de Streamlit
st.markdown(
    """
    <style>
    body {
        background-color: #000000;
        color: #FFFFFF;
    }
    .stApp {
        background-color: #000000;
    }
    h1, h2, h4 {
        text-align: center;
        color: #FFFFFF;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Función para animación de escritura
def typewriter_effect(text, delay=0.1, size="h1", color="white", italic=False):
    display_text = ""
    text_placeholder = st.empty()
    for char in text:
        display_text += char
        style = f"text-align: center; color: {color};"
        if italic:
            style += " font-style: italic;"
        text_placeholder.markdown(f'<{size} style="{style}">{display_text}</{size}>', unsafe_allow_html=True)
        time.sleep(delay)
    return text_placeholder

# Espaciado antes del título
st.markdown("<br><br><br>", unsafe_allow_html=True)

# Animación del título
typewriter_effect("Arkham Exchange", delay=0.15)

# Pausa antes de mostrar el subtítulo
time.sleep(0.5)

# Animación del subtítulo
typewriter_effect("Compliance", delay=0.1, size="h2")

# Espaciado de dos líneas
st.markdown("<br><br>", unsafe_allow_html=True)

# Animación del texto "TRADE WITH INTELLIGENCE."
typewriter_effect("TRADE WITH INTELLIGENCE.", delay=0.08, size="h4", color="#cccccc", italic=True)

# Espaciado antes de la gráfica
st.markdown("<br><br>", unsafe_allow_html=True)

# Contenedor para la gráfica animada
chart_placeholder = st.empty()

# Función para generar la gráfica sin bordes visibles y en pantalla completa
def generate_trading_chart():
    fig, ax = plt.subplots(figsize=(12, 2))  # Aumentamos el tamaño del gráfico para que sea full-width

    # Ajustar la figura para que ocupe toda la pantalla sin márgenes
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    # Fondo completamente negro
    ax.set_facecolor("#000000")  # Fondo interno del gráfico
    fig.patch.set_facecolor("#000000")  # Fondo exterior del gráfico

    # Eliminar todos los bordes
    for spine in ax.spines.values():
        spine.set_color("#000000")  # Oculta completamente los bordes

    # Ocultar ejes y etiquetas
    ax.set_xticks([])
    ax.set_yticks([])
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)

    # Generar datos iniciales
    x_data = np.linspace(0, 100, 100)  # Asegura que cubra toda la pantalla
    y_data = np.cumsum(np.random.randn(100) * 0.5) + 10  # Simulación de tendencia

    # Animación de la gráfica
    for i in range(10, len(x_data)):
        ax.clear()
        ax.set_facecolor("#000000")  # Mantener fondo negro
        ax.plot(x_data[:i], y_data[:i], color="#00FF99", linewidth=1.5)  # Línea de trading en color verde neón

        # Volver a ocultar ejes y bordes después de limpiar
        for spine in ax.spines.values():
            spine.set_color("#000000")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)

        # Dibujar la gráfica en el placeholder
        chart_placeholder.pyplot(fig)
        time.sleep(0.1)  # Retardo de animación

# Ejecutar la animación de la gráfica
generate_trading_chart()
