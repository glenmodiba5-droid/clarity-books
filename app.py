import streamlit as st
import mysql.connector
import pandas as pd
import google.generativeai as genai
import hashlib
from groq import Groq

# --- 1. DATABASE UTILITIES ([mysql] SECRETS FORMAT) ---
def get_connection():
    """Centralized connection using your specific secrets format."""
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"]
    )

def init_aiven_mysql():
    """Builds the Phase 1 infrastructure in Aiven MySQL."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Users Table [cite: 4]
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY, 
                username VARCHAR(255) UNIQUE, 
                password TEXT
            );
        ''')
        
        # 2. Properties Table [cite: 17, 19]
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS properties (
                id INT AUTO_INCREMENT PRIMARY KEY, 
                owner_id INT, 
                name VARCHAR(255), 
                address TEXT, 
                monthly_rent DECIMAL(15, 2), 
                bond_balance DECIMAL(15, 2)
            );
        ''')
        
        # 3. Expenses Table [cite: 7]
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INT AUTO_INCREMENT PRIMARY KEY, 
                owner_id INT, 
                property_id INT, 
                category VARCHAR(255), 
                amount DECIMAL(15, 2), 
                date DATE
            );
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"MySQL Init Error: {e}")
        return False

# Trigger database setup immediately
init_aiven_mysql()

# --- 2. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Clarity Books | Wealth Management",
    page_icon="logo.png",
    layout="wide"
)

# --- 3. SECURITY UTILITIES ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def register_user(new_username, new_password):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        hashed_pw = make_hashes(new_password)
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (new_username, hashed_pw))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as err:
        st.error(f"Registration Failed: {err}")
        return False

# Initialize Session State
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'auth_mode' not in st.session_state:
    st.session_state['auth_mode'] = 'login'

# --- 4. THEME-AWARE CSS ---
st.markdown("""
    <style>
    .logo-text-blue { font-family: 'Helvetica Neue', sans-serif; font-weight: 800; font-size: 32px; color: #007bff; letter-spacing: -1px; }
    .logo-text-gray { font-size: 32px; color: #64748b; font-family: 'Helvetica Neue', sans-serif; }
    [data-testid="stMetric"] { background-color: var(--secondary-background-color); padding: 20px; border-radius: 12px; border: 1px solid rgba(128,128,128,0.2); }
    .stChatMessage p { font-size: 19px !important; line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. AI ENGINE (DUAL-BRAIN) ---
def ask_ai(prompt):
    try:
        genai.configure(api_key=st.secrets["general"]["gemini_api_key"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text, "Gemini 1.5"
    except Exception:
        try:
            client = Groq(api_key=st.secrets["general"]["groq_api_key"])
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content, "Groq (Llama 3.3)"
        except Exception as e:
            return f"AI Engine Offline: {e}", "Offline"

# --- 6. AUTHENTICATION PAGES ---
def auth_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("logo.png", width=150)
        if st.session_state['auth_mode'] == 'login':
            st.title("🔑 Clarity Books Login")
            user = st.text_input("Username")
            pw = st.text_input("Password", type='password')
            if st.button("Login", use_container_width=True):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id, password FROM users WHERE username = %s", (user,))
                result = cursor.fetchone()
                conn.close()
                if result and check_hashes(pw, result[1]):
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = result[0]
                    st.session_state['username'] = user
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
            if st.button("New Landlord? Register Here"):
                st.session_state['auth_mode'] = 'signup'
                st.rerun()
        else:
            st.title("📝 Landlord Registration")
            new_user = st.text_input("Choose Username")
            new_pw = st.text_input("Choose Password", type='password')
            if st.button("Create Account", use_container_width=True):
                if register_user(new_user, new_pw):
                    st.success("Registration Successful! Please Login.")
                    st.session_state['auth_mode'] = 'login'
                    st.rerun()
            if st.button("Back to Login"):
                st.session_state['auth_mode'] = 'login'
                st.rerun()

# --- 7. MAIN APP CONTROL ---
# --- 7. MAIN APP CONTROL ---
if not st.session_state['logged_in']:
    auth_page()
else:
    # 1. ALWAYS LOAD DATA FIRST
    try:
        conn = get_connection()
        user_id = st.session_state.get('user_id')
        
        # Load properties and expenses for the specific owner [cite: 17, 7]
        df = pd.read_sql_query("SELECT * FROM properties WHERE owner_id = %s", conn, params=(user_id,))
        exp_df = pd.read_sql_query("SELECT * FROM expenses WHERE owner_id = %s", conn, params=(user_id,))
        conn.close()
    except Exception as e:
        st.error(f"Data Loading Error: {e}")
        df = pd.DataFrame() # Create empty dataframe so the app doesn't crash
        exp_df = pd.DataFrame()

    # 2. NOW RUN THE NAVIGATION
    with st.sidebar:
        st.image("logo.png", width=150)
        st.divider()
        menu = st.radio("Navigation", ["📊 Dashboard", "🏠 Manage Assets", "⚖️ Legal AI", "🧠 Wealth AI"])
        if st.button("🚪 Log Out"):
            st.session_state['logged_in'] = False
            st.rerun()

    # SIDEBAR
  # SIDEBAR
    with st.sidebar:
        st.image("logo.png", width=150)
        st.divider()
        menu = st.radio("Navigation", ["📊 Dashboard", "🏠 Manage Assets", "⚖️ Legal AI", "🧠 Wealth AI"], key="main_nav")
        # Adding a unique key to the Log Out button
        if st.sidebar.button("🚪 Log Out", key="logout_btn"):
            st.session_state['logged_in'] = False
            st.rerun()
        st.caption(f"Logged in: {st.session_state['username']}")

    # PAGE 1: DASHBOARD
    if menu == "📊 Dashboard":
        st.title("Portfolio Insights")
        if not df.empty:
            rev = df['monthly_rent'].sum()
            exp = exp_df['amount'].sum() if not exp_df.empty else 0
            k1, k2, k3 = st.columns(3)
            k1.metric("Gross Revenue", f"R{rev:,.2f}") [cite: 8, 9]
            k2.metric("Total Expenses", f"R{exp:,.2f}") [cite: 7]
            k3.metric("Net Profit", f"R{(rev-exp):,.2f}") [cite: 8]
        else:
            st.info("Welcome! Please onboard your first asset to see analytics.")

    # PAGE 2: MANAGE ASSETS [cite: 5, 13]
    elif menu == "🏠 Manage Assets":
        st.title("Asset Inventory")
        t1, t2, t3, t4 = st.tabs(["Onboard", "Portfolio", "Expenses", "👤 Profile"])
        with t1:
            with st.form("p_form"):
                st.subheader("Add New Property")
                n = st.text_input("Nickname"); a = st.text_input("Address")
                r = st.number_input("Monthly Rent (R)"); b = st.number_input("Remaining Bond (R)")
                if st.form_submit_button("Save Asset"):
                    c = get_connection(); cur = c.cursor()
                    cur.execute("INSERT INTO properties (owner_id, name, address, monthly_rent, bond_balance) VALUES (%s,%s,%s,%s,%s)", (user_id, n, a, r, b))
                    c.commit(); c.close(); st.rerun()
        with t2:
            st.subheader("Current Holdings")
            st.dataframe(df, use_container_width=True)
        with t3:
            st.subheader("Log Monthly Outgoings")
            if not df.empty:
                with st.form("e_form"):
                    p = st.selectbox("Select Property", df['name'].tolist())
                    pid = df[df['name'] == p]['id'].values[0]
                    cat = st.selectbox("Category", ["Rates & Taxes", "Maintenance", "Levies", "Insurance", "Other"])
                    amt = st.number_input("Amount (R)")
                    if st.form_submit_button("Log Expense"):
                        c = get_connection(); cur = c.cursor()
                        cur.execute("INSERT INTO expenses (owner_id, property_id, category, amount, date) VALUES (%s,%s,%s,%s,CURDATE())", (user_id, pid, cat, amt))
                        c.commit(); c.close(); st.rerun()
            else: st.warning("Onboard an asset first.")
        with t4:
           with t4:
            st.subheader("👤 User Account") [cite: 5]
            # Use .get() to avoid NameError if the session key is missing
            current_user = st.session_state.get('username', 'Unknown Landlord') 
            current_id = st.session_state.get('user_id', 0)
            
            st.info(f"**Landlord ID:** {current_id} | **Username:** {current_user}")
            # Ensure df exists before calling len()
            total_props = len(df) if 'df' in locals() else 0
            st.write(f"**Total Managed Properties:** {total_props}")
    # PAGE 3: LEGAL AI [cite: 11]
    elif menu == "⚖️ Legal AI":
        st.title("⚖️ Smart Lease Architect")
        st.write("Drafting South African law-compliant clauses.")
        cl = st.selectbox("Select Clause Type", ["Pet Policy", "Late Payment Penalties", "Maintenance"])
        if st.button("Generate Draft"):
            with st.spinner("Consulting AI..."):
                ans, prov = ask_ai(f"Draft a formal {cl} clause for a SA lease based on the Rental Housing Act.")
                st.info(ans); st.caption(f"Engine: {prov}")

    # PAGE 4: WEALTH AI [cite: 10]
    elif menu == "🧠 Wealth AI":
        st.title("🤖 Strategy Engine")
        if not df.empty:
            if pmt := st.chat_input("Ask Clarity AI about your portfolio..."):
                with st.chat_message("user"): st.markdown(pmt)
                with st.chat_message("assistant"):
                    ans, prov = ask_ai(f"Portfolio Data: {df.to_string()}. User Question: {pmt}. Focus on SA bond math.")
                    st.markdown(ans); st.caption(f"Strategy Engine: {prov}")
        else: st.warning("Onboard an asset to activate AI strategy.")