# SQL What Could Go Wrong?

A project demonstrating SQL database interactions with safety considerations, featuring a Streamlit-based music database agent and data migration tools.

## 📋 Project Overview

This project showcases a secure, read-only SQL assistant for the Chinook Music Database using:

- **Streamlit** for the interactive web UI
- **LangChain** with Google's Gemini AI for intelligent SQL interactions
- **Supabase** as the database backend
- **SQLite-to-PostgreSQL migration** tools

The agent is designed with built-in security constraints to prevent unintended data modifications while providing natural language querying capabilities.

## 📂 Project Structure

- **app.py** - Main Streamlit application with the SQL agent interface
- **migration.py** - SQLite to PostgreSQL/Supabase migration script
- **old.py** - Legacy/reference code
- **test.py** - Testing utilities
- **requirements.txt** - Python dependencies

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Google API credentials (for Gemini)
- Supabase account (or PostgreSQL database)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/sql-what-could-go-wrong.git
cd sql-what-could-go-wrong
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your credentials:

```env
SUPABASE_URI=postgresql+psycopg2://user:password@host:5432/database
MIGRATION_URI=postgresql+psycopg2://user:password@host:5432/database
GOOGLE_API_KEY=your_google_api_key
```

## 🏃 Usage

### Run the Streamlit App

```bash
streamlit run app.py
```

The app will open in your browser, providing an interactive interface to query the music database.

### Migrate Data from SQLite

```bash
python migration.py
```

This script migrates the Chinook database from SQLite to PostgreSQL/Supabase.

## 🔒 Security Features

The SQL agent includes built-in safeguards:

- **Read-Only Mode**: Query-only access, no modifications allowed
- **Keyword Blocking**: Prevents execution of DELETE, UPDATE, INSERT, DROP, ALTER, CREATE, etc.
- **Schema Protection**: No triggers, views, or table structure changes

## 📦 Dependencies

- `streamlit` - Web application framework
- `langchain` - LLM orchestration
- `langchain-google-genai` - Google Gemini integration
- `sqlalchemy` - Database ORM
- `psycopg2-binary` - PostgreSQL adapter
- `python-dotenv` - Environment variable management

## 📝 License

[Add your license here]

## 👨‍💻 Contributing

Contributions are welcome! Please feel free to submit a pull request.
