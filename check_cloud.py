import streamlit as st
import mysql.connector

def get_connection():
    # Attempt Cloud Connection
    try:
        conn = mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=st.secrets["mysql"]["port"],
            user=st.secrets["mysql"]["user"],
            password=st.secrets["mysql"]["password"],
            database=st.secrets["mysql"]["database"],
            ssl_ca="ca.pem",
            use_pure=True,           # <--- Force Python mode for better Windows compatibility
            connection_timeout=5     # <--- Don't hang forever if it fails
        )
        return conn, "Cloud (Aiven)"
    except Exception as e:
        # Fallback to Local SQLite if Cloud fails
        import sqlite3
        conn = sqlite3.connect('clarity_books.db')
        return conn, "Local (Offline Mode)"

# --- TEST THE BRIDGE ---
conn, mode = get_connection()
st.info(f"Connected via: **{mode}**")

if mode == "Local (Offline Mode)":
    st.warning("⚠️ Cloud DNS is still updating. Using local storage so you can keep building!")