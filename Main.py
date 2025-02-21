import streamlit as st
import time
import numpy as np

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
