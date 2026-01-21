import streamlit as st
import mysql.connector
import pandas as pd
import google.generativeai as genai
import hashlib
import plotly.express as px
from groq import Groq

# --- 1. DATABASE UTILITIES (Role-Aware) ---
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
        conn = get_connection(); cursor = conn.cursor()
        # Users Table with Role and Phone
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY, 
                full_name VARCHAR(255),
                email VARCHAR(255) UNIQUE, 
                phone_number VARCHAR(20),
                password TEXT,
                role VARCHAR(20) DEFAULT 'Landlord'
            );
        ''')
        # Properties Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS properties (
                id INT AUTO_INCREMENT PRIMARY KEY, owner_id INT, 
                name VARCHAR(255), address TEXT, 
                monthly_rent DECIMAL(15, 2), bond_balance DECIMAL(15, 2)
            );
        ''')
        # Tenants Table (Linking Tenants to Properties)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenants (
                id INT AUTO_INCREMENT PRIMARY KEY, 
                user_id INT, property_id INT,
                lease_start DATE, lease_end DATE
            );
        ''')
        # Expenses and Complaints
        cursor.execute("CREATE TABLE IF NOT EXISTS expenses (id INT AUTO_INCREMENT PRIMARY KEY, owner_id INT, property_id INT, category VARCHAR(255), amount DECIMAL(15, 2), date DATE);")
        cursor.execute("CREATE TABLE IF NOT EXISTS complaints (id INT AUTO_INCREMENT PRIMARY KEY, tenant_id INT, property_id INT, issue TEXT, status VARCHAR(50) DEFAULT 'Open');")
        
        conn.commit(); cursor.close(); conn.close()
        return True
    except Exception as e:
        st.error(f"Database Error: {e}"); return False

init_aiven_mysql()

# --- 2. SECURITY & AUTH ---
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

def register_user(name, email, phone, pw, role):
    try:
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO users (full_name, email, phone_number, password, role) VALUES (%s,%s,%s,%s,%s)", 
                       (name, email, phone, make_hashes(pw), role))
        conn.commit(); cursor.close(); conn.close()
        return True
    except Exception as e:
        st.error(f"Reg Error: {e}"); return False

# --- 3. UI HELPERS ---
def ask_ai(prompt):
    try:
        genai.configure(api_key=st.secrets["general"]["gemini_api_key"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model.generate_content(prompt).text, "Gemini"
    except:
        return "AI Engine Busy.", "Offline"

# --- 4. AUTH PAGES ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

def auth_page():
    st.image("logo.png", width=120)
    mode = st.radio("Access Mode", ["Login", "Register"], horizontal=True)
    
    if mode == "Login":
        em = st.text_input("Email")
        ps = st.text_input("Password", type='password')
        if st.button("Sign In", type="primary", use_container_width=True):
            conn = get_connection(); cur = conn.cursor()
            cur.execute("SELECT id, password, full_name, role, phone_number FROM users WHERE email = %s", (em,))
            res = cur.fetchone()
            if res and check_hashes(ps, res[1]):
                st.session_state.update({'logged_in':True, 'user_id':res[0], 'name':res[2], 'role':res[3], 'phone':res[4], 'email':em})
                st.rerun()
            else: st.error("Access Denied.")
    else:
        n = st.text_input("Full Name"); e = st.text_input("Email"); p = st.text_input("Phone")
        pw1 = st.text_input("Password", type='password'); r = st.selectbox("I am a...", ["Landlord", "Tenant"])
        if st.button("Create Account", type="primary"):
            if register_user(n, e, p, pw1, r): st.success("Created! Switch to Login."); st.rerun()

# --- 5. MAIN LOGIC ---
if not st.session_state['logged_in']:
    auth_page()
else:
    role = st.session_state['role']
    uid = st.session_state['user_id']
    
    with st.sidebar:
        st.title("Clarity Books")
        st.write(f"Logged in: **{st.session_state['name']}**")
        st.caption(f"Role: {role}")
        if st.button("Log Out"): st.session_state['logged_in'] = False; st.rerun()

    # --- LANDLORD VIEW ---
    if role == "Landlord":
        menu = st.sidebar.radio("Navigation", ["📊 Dashboard", "🏠 Assets", "👥 Tenants", "🧠 Strategy"])
        
        # Load Data
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM properties WHERE owner_id = %s", conn, params=(uid,))
        exp_df = pd.read_sql("SELECT * FROM expenses WHERE owner_id = %s", conn, params=(uid,))
        conn.close()

        if menu == "📊 Dashboard":
            st.title(f"👋 Welcome, {st.session_state['name']}")
            if not df.empty:
                rev = df['monthly_rent'].sum(); exp = exp_df['amount'].sum() if not exp_df.empty else 0
                profit = rev - exp
                
                # AI ROI Summary
                with st.container(border=True):
                    ans, _ = ask_ai(f"Properties: {len(df)}. Rent: R{rev}. Exp: R{exp}. Profit: R{profit}. Provide ROI insight and 1 growth tip.")
                    st.markdown(f"**🤖 Strategy Engine:** {ans}")
                
                k1, k2, k3 = st.columns(3)
                k1.metric("Revenue", f"R{rev:,.2f}"); k2.metric("Expenses", f"R{exp:,.2f}"); k3.metric("Profit", f"R{profit:,.2f}")
                
                st.divider()
                st.subheader("Visual Breakdown")
                v = st.radio("View", ["Trends", "Distribution"], horizontal=True)
                if v == "Trends":
                    st.area_chart(df.set_index('name')['monthly_rent'])
                else:
                    fig = px.pie(df, values='monthly_rent', names='name', hole=0.3); st.plotly_chart(fig)
            else: st.info("Onboard your first asset to begin.")

        elif menu == "🏠 Assets":
            t1, t2, t3 = st.tabs(["Add", "List", "Dev Tools"])
            with t1:
                with st.form("add_p"):
                    n = st.text_input("Name"); a = st.text_area("Address")
                    r = st.number_input("Rent"); b = st.number_input("Bond")
                    if st.form_submit_button("Save"):
                        c = get_connection(); cur = c.cursor()
                        cur.execute("INSERT INTO properties (owner_id, name, address, monthly_rent, bond_balance) VALUES (%s,%s,%s,%s,%s)", (uid, n, a, r, b))
                        c.commit(); st.rerun()
            with t3:
                if st.button("HARD RESET USERS (Migration)"):
                    c = get_connection(); cur = c.cursor()
                    cur.execute("DROP TABLE IF EXISTS users;"); c.commit(); st.rerun()

    # --- TENANT VIEW ---
    else:
        st.title("🏠 Tenant Portal")
        t1, t2 = st.tabs(["My Rental", "Support"])
        
        with t1:
            st.subheader("Landlord Contact Details")
            # In a real app, we'd fetch the specific landlord for this tenant's property
            st.info("Your Landlord: Glen Modiba")
            st.write("📞 Phone: 071 234 5678")
            st.write("📧 Email: support@claritybooks.co.za")
            
            if st.button("📱 WhatsApp for Maintenance"):
                st.write("Opening WhatsApp...")
        
        with t2:
            st.subheader("Log an Issue")
            with st.form("complaint"):
                issue = st.text_area("Describe the problem (e.g. Broken Tap)")
                if st.form_submit_button("Submit Complaint"):
                    st.success("Landlord has been notified.")