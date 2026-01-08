# 📘 Clarity Books: AI-Driven Property Intelligence

**Clarity Books** is an AI-native wealth management engine designed for the South African property market. It transforms static rental data into dynamic debt-acceleration strategies while providing real-time, law-compliant legal assistance.



## 🚀 Live Demo
[🔗 View Live App](PASTE_YOUR_STREAMLIT_URL_HERE)

## 🛠️ Tech Stack
- **Frontend/UI:** Streamlit (Python)
- **Intelligence:** Google Gemini 1.5 & Groq (Llama 3.3)
- **Database:** SQLite
- **Deployment:** GitHub & Streamlit Community Cloud

## 💡 Key Features
- **Smart Lease Architect:** Generates clauses compliant with the RSA Rental Housing Act using AI.
- **Strategy Engine:** Calculates DTI ratios and debt-acceleration plans (Snowball/Avalanche).
- **Dual-Brain Architecture:** Implemented a failover system to route requests between AI providers, ensuring 100% uptime during API rate-limiting (429 errors).

## 🇿🇦 Local Innovation
This project bridges the gap between **Legal Studies** (LLB at UNISA) and **Data Science**. By prompt-engineering models with South African specific legislation, it provides localized value that generic global AIs miss.

## 🛠️ Installation & Setup
1. Clone the repo: `git clone https://github.com/YOUR_USERNAME/clarity-books.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Add API keys to `.streamlit/secrets.toml`
4. Run: `python -m streamlit run app.py`