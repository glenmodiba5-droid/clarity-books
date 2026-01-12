import streamlit as st
import mysql.connector
import pandas as pd
import google.generativeai as genai
import hashlib
from groq import Groq

# --- 1. DATABASE UTILITIES ---
def get_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"]
    )

def init_aiven_mysql():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(255) UNIQUE, password TEXT);")
        cursor.execute("CREATE TABLE IF NOT EXISTS properties (id INT AUTO_INCREMENT PRIMARY KEY, owner_id INT, name VARCHAR(255), address TEXT, monthly_rent DECIMAL(15, 2), bond_balance DECIMAL(15, 2));")
        cursor.execute("CREATE TABLE IF NOT EXISTS expenses (id INT AUTO_INCREMENT PRIMARY KEY, owner_id INT, property_id INT, category VARCHAR(255), amount DECIMAL(15, 2), date DATE);")
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"MySQL Init Error: {e}")
        return False

init_aiven_mysql()

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="Clarity Books | Wealth Management", page_icon="logo.png", layout="wide")

# --- 3. SECURITY ---
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

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'auth_mode' not in st.session_state:
    st.session_state['auth_mode'] = 'login'

# --- 4. CSS ---
st.markdown("""
    <style>
    [data-testid="stMetric"] { background-color: var(--secondary-background-color); padding: 20px; border-radius: 12px; border: 1px solid rgba(128,128,128,0.2); }
    </style>
    """, unsafe_allow_html=True)

# --- 5. AI ENGINE ---
def ask_ai(prompt):
    try:
        genai.configure(api_key=st.secrets["general"]["gemini_api_key"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text, "Gemini 1.5"
    except Exception:
        try:
            client = Groq(api_key=st.secrets["general"]["groq_api_key"])
            completion = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
            return completion.choices[0].message.content, "Groq (Llama 3.3)"
        except Exception as e:
            return f"AI Offline: {e}", "Offline"

# --- 6. AUTH PAGES ---
def auth_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("logo.png", width=150)
        if st.session_state['auth_mode'] == 'login':
            st.title("🔑 Login")
            user = st.text_input("Username", key="login_user")
            pw = st.text_input("Password", type='password', key="login_pw")
            if st.button("Login", use_container_width=True, key="login_btn"):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id, password FROM users WHERE username = %s", (user,))
                res = cursor.fetchone()
                conn.close()
                if res and check_hashes(pw, res[1]):
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = res[0]
                    st.session_state['username'] = user
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
            if st.button("New Landlord? Register Here", key="goto_signup"):
                st.session_state['auth_mode'] = 'signup'
                st.rerun()
        else:
            st.title("📝 Register")
            new_user = st.text_input("Choose Username", key="reg_user")
            new_pw = st.text_input("Choose Password", type='password', key="reg_pw")
            if st.button("Create Account", use_container_width=True, key="reg_btn"):
                if register_user(new_user, new_pw):
                    st.success("Account created! Please Login.")
                    st.session_state['auth_mode'] = 'login'
                    st.rerun()
            if st.button("Back to Login", key="goto_login"):
                st.session_state['auth_mode'] = 'login'
                st.rerun()

# --- 7. MAIN APP ---
if not st.session_state['logged_in']:
    auth_page()
else:
    # Always load data first to avoid NameErrors
    try:
        conn = get_connection()
        user_id = st.session_state.get('user_id')
        df = pd.read_sql_query("SELECT * FROM properties WHERE owner_id = %s", conn, params=(user_id,))
        exp_df = pd.read_sql_query("SELECT * FROM expenses WHERE owner_id = %s", conn, params=(user_id,))
        conn.close()
    except Exception:
        df = pd.DataFrame()
        exp_df = pd.DataFrame()

    # Unified Sidebar
    with st.sidebar:
        st.image("logo.png", width=150)
        st.divider()
        menu = st.radio("Navigation", ["📊 Dashboard", "🏠 Manage Assets", "⚖️ Legal AI", "🧠 Wealth AI"], key="nav_radio")
        st.divider()
        if st.button("🚪 Log Out", key="sidebar_logout"):
            st.session_state['logged_in'] = False
            st.rerun()
        st.caption(f"Logged in: {st.session_state.get('username')}")

    # Page Logic
    if menu == "📊 Dashboard":
        st.title("Portfolio Insights")
        if not df.empty:
            rev = df['monthly_rent'].sum()
            exp = exp_df['amount'].sum() if not exp_df.empty else 0
            k1, k2, k3 = st.columns(3)
            k1.metric("Gross Revenue", f"R{rev:,.2f}")
            k2.metric("Total Expenses", f"R{exp:,.2f}")
            k3.metric("Net Profit", f"R{(rev-exp):,.2f}")
        else:
            st.info("Welcome! Please onboard your first asset to see analytics.")

    elif menu == "🏠 Manage Assets":
        st.title("Asset Inventory")
        t1, t2, t3, t4 = st.tabs(["Onboard", "Portfolio", "Expenses", "👤 Profile"])
        with t1:
            with st.form("p_form", clear_on_submit=True):
                st.subheader("Add New Property")
                n = st.text_input("Nickname"); a = st.text_input("Address")
                r = st.number_input("Monthly Rent (R)", min_value=0.0)
                b = st.number_input("Remaining Bond (R)", min_value=0.0)
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
                with st.form("e_form", clear_on_submit=True):
                    p = st.selectbox("Select Property", df['name'].tolist())
                    pid = df[df['name'] == p]['id'].values[0]
                    cat = st.selectbox("Category", ["Rates & Taxes", "Maintenance", "Levies", "Insurance", "Other"])
                    amt = st.number_input("Amount (R)", min_value=0.0)
                    if st.form_submit_button("Log Expense"):
                        c = get_connection(); cur = c.cursor()
                        cur.execute("INSERT INTO expenses (owner_id, property_id, category, amount, date) VALUES (%s,%s,%s,%s,CURDATE())", (user_id, pid, cat, amt))
                        c.commit(); c.close(); st.rerun()
            else: st.warning("Onboard an asset first.")
        with t4:
            st.subheader("👤 User Account")
            st.info(f"**Landlord ID:** {user_id} | **Username:** {st.session_state.get('username')}")
            st.write(f"**Total Managed Properties:** {len(df)}")

    elif menu == "⚖️ Legal AI":
        st.title("⚖️ Smart Lease Architect")
        cl = st.selectbox("Select Clause Type", ["Pet Policy", "Late Payment Penalties", "Maintenance"])
        if st.button("Generate Draft", key="legal_btn"):
            with st.spinner("Drafting..."):
                ans, prov = ask_ai(f"Draft a formal {cl} clause for a SA lease based on the Rental Housing Act.")
                st.info(ans); st.caption(f"Engine: {prov}")

    elif menu == "🧠 Wealth AI":
        st.title("🤖 Strategy Engine")
        if not df.empty:
            if pmt := st.chat_input("Ask Clarity AI about your portfolio..."):
                with st.chat_message("user"): st.markdown(pmt)
                with st.chat_message("assistant"):
                    ans, prov = ask_ai(f"Portfolio Data: {df.to_string()}. Question: {pmt}. Focus on SA bond math.")
                    st.markdown(ans); st.caption(f"Engine: {prov}")
        else: st.warning("Onboard an asset to activate AI strategy.")