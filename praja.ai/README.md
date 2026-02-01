# Nagrik.AI - Citizen Grievance Redressal Portal

**Nagrik.AI** is an AI-powered platform designed to streamline citizen grievance reporting and resolution for the Government of Manipur. It creates a bridge between citizens and government departments, utilizing Artificial Intelligence to automatically analyze, categorize, and prioritize grievances for faster resolution.

## 🚀 Features

- **Smart Grievance Reporting**: Citizens can easily report issues (e.g., infrastructure, sanitation) with location data and detailed descriptions.
- **AI-Powered Analysis**: The system uses AI to automatically:
    - **Categorize** the grievance (e.g., "Public Works", "Health").
    - **Prioritize** the issue based on severity.
    - **Draft** professional complaints for users.
    - **Summarize** issues for officials.
- **Real-time Status Tracking**: Users can track the status of their complaints (Pending, Resolved) in real-time.
- **Admin Dashboard**: A comprehensive dashboard for government officials to view, manage, and update the status of grievances.
- **User Dashboard**: A personal dashboard for citizens to view their history and profile.
- **WhatsApp Integration**: Support for reporting grievances via WhatsApp (integrated with Twilio).

## 🛠️ Tech Stack

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python) - High-performance, easy-to-learn, fast to code, ready for production.
- **Database**: MySQL - Relational database for storing user and grievance data.
- **ORM**: SQLAlchemy - SQL Toolkit and Object Relational Mapper.
- **Migrations**: Alembic - Lightweight database migration tool.
- **Validation**: Pydantic - Data validation and settings management using python type hinting.
- **AI/ML**: Custom AI modules for text analysis.

### Frontend
- **Core**: HTML5, CSS3, Vanilla JavaScript.
- **Styling**: Custom CSS with a government-themed color palette.
- **Maps**: [Leaflet.js](https://leafletjs.com/) - Open-source JavaScript library for mobile-friendly interactive maps.
- **Fonts**: Google Fonts (Merriweather, Plus Jakarta Sans).

## 📂 Project Structure

```bash
nagrik.ai/
├── backend/                # FastAPI Backend
│   ├── app/                # Application source code
│   │   ├── api/            # API endpoints
│   │   ├── auth/           # Authentication routes
│   │   ├── core/           # Core config and settings
│   │   ├── models/         # Database models
│   │   └── main.py         # Entry point
│   ├── migrations/         # Database migrations (Alembic)
│   ├── .env.example        # Environment variables template
│   └── requirements.txt    # Python dependencies
├── frontend/               # Web Frontend
│   ├── assets/             # Images and static assets
│   ├── index.html          # Landing/Reporting page
│   ├── admin.html          # Admin dashboard
│   ├── app.js              # Main frontend logic
│   └── style.css           # Global styles
└── data/                   # Data storage (if applicable)
```

## ⚡ Getting Started

### Prerequisites
- Python 3.8 or higher
- MySQL Server
- Git

### 1. Clone the Repository
```bash
git clone <repository-url>
cd citizen-grievance-ai/nagrik.ai
```

### 2. Backend Setup
Navigate to the backend directory and set up the environment.

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

**Configure Environment Variables:**
Copy `.env.example` to `.env` and update the `DATABASE_URL` with your MySQL credentials.

```bash
cp .env.example .env
# Edit .env: DATABASE_URL=mysql+pymysql://user:password@localhost/nagrik_ai
```

**Run Database Migrations:**
Initialize the database tables.
```bash
alembic upgrade head
```

**Start the Backend Server:**
```bash
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.
API Documentation (Swagger UI): `http://localhost:8000/docs`.

### 3. Frontend Setup
The frontend is built with static HTML/JS/CSS. You can serve it using any static file server.

**Option A: Simple Python Server**
```bash
cd ../frontend
python -m http.server 3000
```
Visit `http://localhost:3000` in your browser.

**Option B: Open File Directly**
You can also simply open `frontend/index.html` in your web browser, but some features (like API calls) might require a proper local server context to avoid CORS issues if not configured strictly.

## 🤝 Contributing
1. Fork the repository.
2. Create feature branch (`git checkout -b feature/NewFeature`).
3. Commit changes (`git commit -m 'Add NewFeature'`).
4. Push to branch (`git push origin feature/NewFeature`).
5. Open a Pull Request.

## � Author

**Abinash Heishnam**
B.Tech CSE | 6th Semester
Royal Global University, Guwahati

## �📄 License
[MIT License](LICENSE)
