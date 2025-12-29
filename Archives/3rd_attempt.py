import streamlit as st
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
# Ensure you have installed: pip install psycopg2-binary sqlalchemy

load_dotenv()

# --- NEW SUPABASE CONFIGURATION ---
# Using the Pooler URI provided with the correct SQLAlchemy prefix
SUPABASE_URI = os.getenv("SUPABASE_URI")

st.set_page_config(page_title="Supabase Music Database Agent", layout="wide")
st.title("🎵 Supabase Music Database Agent")

@st.cache_resource
def setup_agent():
    # 1. Database connection - Updated to use Supabase URI
    db = SQLDatabase.from_uri(SUPABASE_URI)
    
    # 2. LLM Configuration
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    
    # 3. Create the SQL Agent
    agent_executor = create_sql_agent(
        llm=llm,
        db=db,
        agent_type="tool-calling",
        verbose=True,
        prefix="""You are a secure and read-only SQL assistant for the Chinook Music Database.

Your purpose:
- Provide factual, helpful, and clear answers about the database contents.
- Analyze and describe albums, artists, tracks, playlists, customers, invoices, and related entities.

Security enforcement:
- You operate in a QUERY-ONLY mode.
- You must **NEVER** attempt to modify, update, insert, or delete any data.
- You must **NEVER** write or execute any statement containing keywords such as:
  `DELETE`, `UPDATE`, `INSERT`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `REPLACE`,
  `EXEC`, `ATTACH`, `DETACH`, or `WRITE`.
- You must **NOT** make schema changes or alter any tables, triggers, or views.

Always be factual and clear in your explanations.
Summarize insights logically and concisely, using SQL knowledge responsibly."""
    )
    
    return agent_executor

# --- Update the Session State initialization to use the new URI ---
if "executor" not in st.session_state:
    try:
        st.session_state.executor = setup_agent()
        st.success("✅ Connected to Supabase PostgreSQL successfully!")
        
        with st.expander("📊 Quick Database Overview"):
            # Use the new URI here as well
            db = SQLDatabase.from_uri(SUPABASE_URI)
            tables = db.get_usable_table_names()
            st.info(f"**Tables available in Supabase:** {', '.join(tables)}")
            
    except Exception as e:
        st.error(f"❌ Failed to connect to Supabase: {e}")
        st.stop()

# Initialize chat message history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# User input
if prompt := st.chat_input("Ask about artists, albums, tracks, sales... or modify data 🎵"):
    # Add user message to UI and state
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate AI response
    with st.chat_message("assistant"):
        with st.spinner("Querying Chinook Database..."):
            try:
                # In 2025, invoke is the standard method over run()
                response = st.session_state.executor.invoke({"input": prompt})
                result = response["output"]
            except Exception as e:
                result = f"⚠️ **Error processing request:** {str(e)}"
        
        st.markdown(result)
    
    # Add assistant message to state
    st.session_state.messages.append({"role": "assistant", "content": result})


# Sidebar with example questions
with st.sidebar:
    st.header("💡 Example Questions")
    
    st.subheader("📖 Read Operations")
    read_examples = [
        "Which genre has the longest tracks on average?",
        "Top 5 best-selling artists?",
        "How many customers from each country?",
        "What are the most expensive albums?",
        "Which tracks are over 5 minutes long?",
        "Total sales by genre?"
    ]
    
    for example in read_examples:
        if st.button(example, key=f"read_{example}"):
            st.session_state.messages.append({"role": "user", "content": example})
            st.rerun()
    
    st.divider()
    
    st.subheader("✏️ Write Operations")
    write_examples = [
        "Add a new genre called 'Synthwave'",
        "Update the price of album ID 1 to $15.99",
        "Delete the track with ID 100",
        "Create a new playlist called 'Summer Hits'",
        "Insert a new artist named 'Indie Legends'"
    ]
    
    for example in write_examples:
        if st.button(example, key=f"write_{example}"):
            st.session_state.messages.append({"role": "user", "content": example})
            st.rerun()

    st.divider()
    st.info("**Chinook Tables:** Album, Artist, Customer, Employee, Genre, Invoice, InvoiceLine, MediaType, Playlist, PlaylistTrack, Track")