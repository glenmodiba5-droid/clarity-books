import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
from groq import Groq  # Make sure this is imported!

# --- THE "ASK AI" FUNCTION ---
def ask_ai(prompt):
    """The Dual-Brain Fallback System that works on Cloud and Local"""
    try:
        # 1. Pull keys directly from Streamlit's 'brain' (secrets)
        gemini_key = st.secrets["general"]["gemini_api_key"]
        groq_key = st.secrets["general"]["groq_api_key"]
        
        # 2. Try Gemini first
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text, "Gemini 1.5"
    
    except Exception as e:
        # 3. If Gemini fails or keys aren't ready, switch to Groq
        try:
            client = Groq(api_key=st.secrets["general"]["groq_api_key"])
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content, "Groq (Llama 3.3)"
        except Exception as groq_e:
            return f"Dual-Brain failure. Check secrets! Error: {groq_e}", "Offline"

# --- REST OF YOUR APP (Page Config, CSS, etc.) ---
st.set_page_config(page_title="Clarity Books", layout="wide")

# 1. PAGE CONFIG (Must be first)
st.set_page_config(
    page_title="Clarity Books | Wealth Management",
    page_icon="logo.png",
    layout="wide"
)

# 2. THEME-AWARE CSS (Dark & Light Mode Support)
# We use 'var(--secondary-background-color)' so the app flips colors automatically
st.markdown("""
    <style>
    /* Main Container Styling */
    .header-box {
        background-color: var(--secondary-background-color);
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        margin-bottom: 25px;
        border-left: 10px solid #007bff;
    }
    
    /* Branding Colors - Forced to stay consistent */
    .logo-text-blue {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 800;
        font-size: 32px;
        color: #007bff;
        letter-spacing: -1px;
    }
    
    .logo-text-gray {
        font-size: 32px; 
        color: #64748b; 
        font-family: 'Helvetica Neue', sans-serif;
    }

    /* Metric Card Styling */
    [data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border: 1px solid rgba(128,128,128,0.2);
    }

    /* Chat Text Size Fix */
    .stChatMessage p {
        font-size: 19px !important;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. SHARED HEADER (Logo + Title)
col1, col2 = st.columns([2, 10]) 
with col1:
    st.image("logo.png", width=160)
with col2:
    st.markdown("""
        <div style="margin-top: 10px;">
            <span class="logo-text-blue">CLARITY</span>
            <span class="logo-text-gray">BOOKS</span>
            <p style="color: #64748b; margin: 0; font-size: 14px; margin-top: -5px;">
                AI-Driven Property Portfolio Intelligence
            </p>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div style="margin-bottom: 20px;"></div>', unsafe_allow_html=True)

# 3. DATABASE INITIALIZATION
def init_db():
    conn = sqlite3.connect('clarity_books.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS properties 
                      (id INTEGER PRIMARY KEY, name TEXT, address TEXT, 
                       monthly_rent REAL, bond_balance REAL)''')
    conn.commit()
    return conn

# 4. SHARED HEADER (Logo + Title)
import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai

# 1. PAGE CONFIGURATION
st.set_page_config(
    page_title="Clarity Books | Wealth Management",
    page_icon="logo.png",
    layout="wide"
)

# 2. THEME-AWARE CSS (Ensure Dark Mode works perfectly)
st.markdown("""
    <style>
    .header-box {
        background-color: var(--secondary-background-color);
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        margin-bottom: 25px;
        border-left: 10px solid #007bff;
    }
    .logo-text-blue { font-family: 'Helvetica Neue', sans-serif; font-weight: 800; font-size: 32px; color: #007bff; letter-spacing: -1px; }
    .logo-text-gray { font-size: 32px; color: #64748b; font-family: 'Helvetica Neue', sans-serif; }
    [data-testid="stMetric"] { background-color: var(--secondary-background-color); padding: 20px; border-radius: 12px; border: 1px solid rgba(128,128,128,0.2); }
    .stChatMessage p { font-size: 19px !important; line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

# 3. DATABASE ENGINE
def init_db():
    conn = sqlite3.connect('clarity_books.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS properties 
                      (id INTEGER PRIMARY KEY, name TEXT, address TEXT, 
                       monthly_rent REAL, bond_balance REAL)''')
    conn.commit()
    return conn

# 5. SIDEBAR NAVIGATION
with st.sidebar:
    st.image("logo.png", width=150)
    st.divider()
    menu = st.radio("Management", [
        "📊 Executive Dashboard", 
        "🏠 Manage Assets", 
        "⚖️ AI Legal Assistant", 
        "🧠 AI Wealth Advisor"
    ])
    st.divider()
    st.caption("Developed by Glen Modiba")
    st.caption("Project for SF Residency 2026")

# LOAD GLOBAL DATA
conn = init_db()
df = pd.read_sql_query("SELECT * FROM properties", conn)
conn.close()

# --- PAGE 1: EXECUTIVE DASHBOARD ---
if menu == "📊 Executive Dashboard":
    st.title("Portfolio Insights")
    if not df.empty:
        total_rent = df['monthly_rent'].sum()
        total_debt = df['bond_balance'].sum()
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Assets", f"{len(df)} Units")
        k2.metric("Monthly Revenue", f"R{total_rent:,.2f}")
        k3.metric("Total Liabilities", f"R{total_debt:,.2f}", delta="-1.4%", delta_color="normal")
        k4.metric("DTI Ratio", f"{(total_debt/(total_rent*12)*100):.1f}%")

        st.divider()
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("Revenue Stream")
            st.area_chart(df.set_index('name')['monthly_rent'])
        with c2:
            st.subheader("Debt Split")
            st.bar_chart(df.set_index('name')['bond_balance'])
    else:
        st.info("Onboard an asset to view analytics.")

# --- PAGE 2: MANAGE ASSETS ---
elif menu == "🏠 Manage Assets":
    st.title("Asset Inventory")
    t1, t2 = st.tabs(["Onboard New Asset", "Current Portfolio"])
    with t1:
        with st.form("p_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            name = col_a.text_input("Property Nickname")
            addr = col_b.text_input("Physical Address")
            rent = col_a.number_input("Monthly Rent (R)")
            bond = col_b.number_input("Remaining Bond (R)")
            if st.form_submit_button("Finalize Onboarding"):
                conn = init_db(); cursor = conn.cursor()
                cursor.execute("INSERT INTO properties (name, address, monthly_rent, bond_balance) VALUES (?,?,?,?)", (name, addr, rent, bond))
                conn.commit(); conn.close()
                st.success("Asset synced to cloud."); st.rerun()
    with t2:
        st.dataframe(df, use_container_width=True)

# --- PAGE 3: AI LEGAL ASSISTANT (Finishing Touch) ---
# --- PAGE 3: AI LEGAL ASSISTANT ---
elif menu == "⚖️ AI Legal Assistant":
    st.title("⚖️ Smart Lease Architect")
    st.write("Drafting South African law-compliant clauses in seconds.")

    # Check for secrets before proceeding
    if "gemini_api_key" not in st.secrets["general"] or "groq_api_key" not in st.secrets["general"]:
        st.warning("⚠️ API Keys are missing. Please check your secrets.toml file.")

    col_l, col_r = st.columns([1, 1.2])
    
    with col_l:
        st.subheader("Parameters")
        clause_type = st.selectbox("Select Clause Type", ["Pet Policy", "Late Payment Penalties", "Maintenance", "Smoking Rules"])
        tenant = st.text_input("Tenant Name (Optional)")
        
        # FIXED: Ensure the AI call is indented inside the button click
        if st.button("Generate Legal Clause"):
            with st.spinner("Consulting AI Legal Models..."):
                legal_prompt = f"""
                You are a South African Legal Expert. 
                Draft a formal {clause_type} for a lease agreement involving tenant {tenant or 'the Tenant'}. 
                Reference the South African Rental Housing Act.
                """
                # This uses the Dual-Brain function we created
                answer, provider = ask_ai(legal_prompt) 
                st.session_state.legal_draft = answer
                st.session_state.last_provider = provider

    with col_r:
        st.subheader("Draft Preview")
        if 'legal_draft' in st.session_state:
            # Styled document box for a professional look
            st.info(st.session_state.legal_draft)
            st.caption(f"Generated via: {st.session_state.get('last_provider', 'Unknown')}")
            st.button("📋 Copy to Lease Agreement")
        else:
            st.caption("Your draft will appear here after clicking 'Generate'.")

# --- PAGE 4: AI WEALTH ADVISOR ---
elif menu == "🧠 AI Wealth Advisor":
    st.title("🤖 Strategy Engine")
    st.caption("AI-Powered Debt Acceleration Planning")

    if not df.empty:
        # Initialize Chat History
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": "Hello Glen! I've analyzed your portfolio. Ready to optimize your property wealth?"}]

        # Display Chat History
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat Input
        if prompt := st.chat_input("Message Clarity AI..."):
            # Add user message to history
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate Assistant Response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    wealth_prompt = f"Portfolio context: {df.to_string()}. User Question: {prompt}. Focus on South African bond math."
                    answer, provider = ask_ai(wealth_prompt)
                    
                    st.markdown(answer)
                    st.caption(f"Strategy Engine: {provider}")
                    
                    # Add assistant message to history
                    st.session_state.messages.append({"role": "assistant", "content": answer})
    else:
        st.warning("Please onboard an asset first to enable the AI Strategy Engine.")