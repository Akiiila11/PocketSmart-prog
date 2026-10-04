# PocketSmart AI

A Naan Mudhalvan project starter matching the supplied project document:
- FastAPI backend
- SQLite database
- Register/Login/Logout
- Home Interior Planner
- Party Planner
- Jewelry Planner with optional image upload
- Gemini AI integration with a safe fallback recommendation engine
- Recommendation history
- HTML/CSS/JavaScript frontend

## Run
1. Install Python 3.11+.
2. Create a virtual environment:
   `python -m venv .venv`
3. Activate it:
   Windows: `.venv\Scripts\activate`
   Linux/macOS: `source .venv/bin/activate`
4. Install:
   `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and add your Gemini API key if available.
6. Start:
   `uvicorn app.main:app --reload`
7. Open http://127.0.0.1:8000

The application works without a Gemini key by using deterministic demo recommendations.
For a real deployment, add your API key and use the model available to your account.
