import streamlit as st
import mysql.connector
import pandas as pd
import google.generativeai as genai
import hashlib
import plotly.express as px
from groq import Groq

# --- 1. DATABASE UTILITIES (Updated for Full Name) ---
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
        # Create Users Table with FULL NAME and EMAIL
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY, 
                full_name VARCHAR(255),
                email VARCHAR(255) UNIQUE, 
                password TEXT
            );
        ''')
        # Create Properties Table
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
        # Create Expenses Table
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

init_aiven_mysql()

# --- 2. PAGE CONFIGURATION ---
st.set_page_config(page_title="Clarity Books | Wealth Management", page_icon="logo.png", layout="wide")

# --- 3. SECURITY & AUTH UTILITIES ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def register_user(full_name, new_email, new_password):
    try:
        if not full_name or not new_email or not new_password:
            st.error("All fields are required.")
            return False
        if "@" not in new_email or "." not in new_email:
            st.error("Please enter a valid email address.")
            return False
            
        conn = get_connection()
        cursor = conn.cursor()
        hashed_pw = make_hashes(new_password)
        cursor.execute("INSERT INTO users (full_name, email, password) VALUES (%s, %s, %s)", 
                       (full_name, new_email, hashed_pw))
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

# --- 4. AI ENGINE ---
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

# --- 5. AUTHENTICATION PAGES (Legit UI) ---
def auth_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("logo.png", width=150)
        
        if st.session_state['auth_mode'] == 'login':
            st.title("🔑 Welcome Back")
            email = st.text_input("Email Address", placeholder="landlord@example.com")
            pw = st.text_input("Password", type='password')
            
            if st.button("Sign In", use_container_width=True, type="primary"):
                conn = get_connection(); cursor = conn.cursor()
                cursor.execute("SELECT id, password, full_name, email FROM users WHERE email = %s", (email,))
                res = cursor.fetchone()
                conn.close()
                if res and check_hashes(pw, res[1]):
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = res[0]
                    st.session_state['full_name'] = res[2]
                    st.session_state['username'] = res[3] 
                    st.rerun()
                else:
                    st.error("Invalid Email or Password")
            
            if st.button("New Landlord? Register Here"):
                st.session_state['auth_mode'] = 'signup'
                st.rerun()

        else:
            st.title("📝 Create Account")
            name = st.text_input("Full Name", placeholder="e.g. Glen Modiba")
            email = st.text_input("Email Address")
            p1 = st.text_input("Create Password", type='password')
            p2 = st.text_input("Confirm Password", type='password')
            tos = st.checkbox("I agree to the Terms of Service & Privacy Policy")
            
            if st.button("Register Now", use_container_width=True, type="primary"):
                if not tos:
                    st.warning("Please agree to the terms.")
                elif p1 != p2:
                    st.error("Passwords do not match.")
                elif len(p1) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    if register_user(name, email, p1):
                        st.success("Account created! Please Login.")
                        st.session_state['auth_mode'] = 'login'
                        st.rerun()
            
            if st.button("Back to Login"):
                st.session_state['auth_mode'] = 'login'
                st.rerun()

# --- 6. MAIN APPLICATION CONTROL ---
if not st.session_state['logged_in']:
    auth_page()
else:
    try:
        conn = get_connection()
        user_id = st.session_state.get('user_id')
        df = pd.read_sql_query("SELECT * FROM properties WHERE owner_id = %s", conn, params=(user_id,))
        exp_df = pd.read_sql_query("SELECT * FROM expenses WHERE owner_id = %s", conn, params=(user_id,))
        conn.close()
    except Exception:
        df = pd.DataFrame(); exp_df = pd.DataFrame()

    with st.sidebar:
        st.image("logo.png", width=150)
        st.divider()
        menu = st.radio("Navigation", ["📊 Dashboard", "🏠 Manage Assets", "⚖️ Legal AI", "🧠 Wealth AI"], key="nav_radio")
        st.divider()
        if st.button("Log Out", key="logout_btn"):
            st.session_state['logged_in'] = False
            st.rerun()
        st.caption(f"Landlord: {st.session_state.get('full_name')}")

    # --- PAGE 1: DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title(f"👋 Welcome, {st.session_state.get('full_name', 'Landlord')}")
        if not df.empty:
            rev = df['monthly_rent'].sum()
            exp = exp_df['amount'].sum() if not exp_df.empty else 0
            profit = rev - exp
            
            with st.container(border=True):
                summary, _ = ask_ai(f"Brief for {st.session_state.get('full_name')}: {len(df)} properties. Rent: R{rev}. Exp: R{exp}. Profit: R{profit}. 2-line professional summary.")
                st.markdown(f"**🤖 AI Insights:** {summary}")

            k1, k2, k3 = st.columns(3)
            k1.metric("Gross Revenue", f"R{rev:,.2f}")
            k2.metric("Total Expenses", f"R{exp:,.2f}")
            k3.metric("Net Profit", f"R{profit:,.2f}")
            
            st.divider()
            st.subheader("Visual Analysis")
            view_type = st.radio("Toggle View:", ["Trends", "Distribution"], horizontal=True)
            
            c1, c2 = st.columns(2)
            if view_type == "Trends":
                with c1: st.area_chart(df.set_index('name')['monthly_rent'])
                with c2: st.bar_chart(df.set_index('name')['bond_balance'])
            else:
                with c1:
                    fig_rev = px.pie(df, values='monthly_rent', names='name', hole=0.3, title="Revenue Share")
                    st.plotly_chart(fig_rev, use_container_width=True)
                with c2:
                    if not exp_df.empty:
                        fig_exp = px.pie(exp_df, values='amount', names='category', hole=0.3, title="Expense Split")
                        st.plotly_chart(fig_exp, use_container_width=True)
        else:
            st.info("Welcome! Onboard your first asset to see analytics.")

    # --- PAGE 2: ASSETS ---
    elif menu == "🏠 Manage Assets":
        st.title("Asset Inventory")
        t1, t2, t3, t4 = st.tabs(["Onboard", "Portfolio", "Expenses", "👤 Profile"])
        
        with t1:
            with st.form("p_form", clear_on_submit=True):
                st.subheader("Add New Property")
                n = st.text_input("Nickname"); a = st.text_input("Address")
                r = st.number_input("Monthly Rent (R)"); b = st.number_input("Bond Balance (R)")
                if st.form_submit_button("Save Asset"):
                    c = get_connection(); cur = c.cursor()
                    cur.execute("INSERT INTO properties (owner_id, name, address, monthly_rent, bond_balance) VALUES (%s,%s,%s,%s,%s)", (user_id, n, a, r, b))
                    c.commit(); c.close(); st.rerun()
        
        with t2:
            st.dataframe(df, use_container_width=True)
        
        with t3:
            if not df.empty:
                with st.form("e_form", clear_on_submit=True):
                    p = st.selectbox("Property", df['name'].tolist())
                    pid = int(df[df['name'] == p]['id'].values[0])
                    cat = st.selectbox("Category", ["Maintenance", "Rates", "Insurance", "Other"])
                    amt = float(st.number_input("Amount (R)"))
                    if st.form_submit_button("Log Expense"):
                        c = get_connection(); cur = c.cursor()
                        cur.execute("INSERT INTO expenses (owner_id, property_id, category, amount, date) VALUES (%s,%s,%s,%s,CURDATE())", (int(user_id), pid, cat, amt))
                        c.commit(); c.close(); st.rerun()

        with t4:
            st.subheader("Account Management")
            st.info(f"**Email:** {st.session_state.get('username')}")
            with st.expander("🛠️ Developer Settings"):
                if st.button("RESET USERS (Column Sync Migration)", type="primary"):
                    c = get_connection(); cur = c.cursor()
                    cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
                    cur.execute("DROP TABLE IF EXISTS users;") # Drop to recreate with Full Name column
                    c.commit(); c.close(); st.success("Re-initializing tables... Refresh the app.")
                    init_aiven_mysql()

    # --- PAGE 3: LEGAL ---
    elif menu == "⚖️ Legal AI":
        st.title("⚖️ Legal Architect")
        cl = st.selectbox("Clause", ["Pet Policy", "Late Payment", "Maintenance"])
        if st.button("Generate"):
            ans, prov = ask_ai(f"Draft a {cl} clause for a SA lease.")
            st.info(ans); st.caption(f"Source: {prov}")

    # --- PAGE 4: WEALTH ---
    elif menu == "🧠 Wealth AI":
        st.title("🤖 Strategy Engine")
        if not df.empty:
            pmt = st.chat_input("Ask about your portfolio...")
            if pmt:
                with st.chat_message("user"): st.write(pmt)
                with st.chat_message("assistant"):
                    ans, prov = ask_ai(f"Data: {df.to_string()}. Question: {pmt}")
                    st.write(ans); st.caption(f"Source: {prov}")
        else: st.warning("Onboard an asset to activate AI strategy.")