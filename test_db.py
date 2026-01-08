import mysql.connector
import streamlit as st

try:
    conn = mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        ssl_ca="ca.pem" # This looks for the file you just downloaded
    )
    if conn.is_connected():
        print("✅ Success! Clarity Books is connected to the Cloud.")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")