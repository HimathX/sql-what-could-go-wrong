# SQL What Could Go Wrong?

A project demonstrating SQL database interactions with safety considerations, featuring a Streamlit-based music database agent and data migration tools.

## 📋 Project Overview

This project showcases a secure SQL assistant for the Chinook Music Database using:

- **Streamlit** for the interactive web UI (with real-time agent thinking)
- **LangChain** with Google's Gemini AI for intelligent SQL interactions
- **Supabase** as the database backend
- **SQLite-to-PostgreSQL migration** tools

The agent is designed with built-in security constraints to prevent unintended data modifications while providing natural language querying capabilities.

## 📂 Project Structure

- **app.py** - Main Streamlit application with the SQL agent interface
- **production.py** - Streamlit app with runtime model/API-key inputs in the sidebar
- **prompt.py** - Agent prompt configuration
- **Archives/** - Earlier attempts and migration utilities
- **requirements.txt** - Python dependencies

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Google API credentials (for Gemini) — optional to preload via `.env` (can also be entered in the app sidebar)
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

4. (Optional) Create a `.env` file with your credentials:

```env
SUPABASE_URI=postgresql+psycopg2://user:password@host:5432/database
MIGRATION_URI=postgresql+psycopg2://user:password@host:5432/database
GOOGLE_API_KEY=your_google_api_key
```

## 🏃 Usage

### Run the Streamlit App

Development view (fixed model from environment variables):

```bash
streamlit run app.py
```

Production view (set model and API key in sidebar at runtime):

```bash
streamlit run production.py
```

In the production app sidebar you can set:

- **Model name** (default: `gemini-2.0-flash`)
- **API key** (overrides `GOOGLE_API_KEY` when provided)

### Migrate Data from SQLite

```bash
python migration.py
```

This script migrates the Chinook database from SQLite to PostgreSQL/Supabase.

## 🔒 Security Features

The SQL agent includes built-in safeguards:

- **Principle of least privilege**: Queries are validated and constrained
- **Keyword blocking**: Prevents dangerous operations (DROP/ALTER, etc.)
- **Schema awareness**: Limits to known Chinook tables

## 📦 Dependencies

- `streamlit` - Web application framework
- `langchain` - LLM orchestration
- `langchain-google-genai` - Google Gemini integration
- `sqlalchemy` - Database ORM
- `psycopg2-binary` - PostgreSQL adapter
- `python-dotenv` - Environment variable management


## 👨‍💻 Contributing

Contributions are welcome! Please feel free to submit a pull request.
