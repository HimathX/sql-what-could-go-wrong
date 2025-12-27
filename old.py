import streamlit as st
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent


# Load environment variables (Make sure GOOGLE_API_KEY is in your .env)
load_dotenv()


# Configure Streamlit
st.set_page_config(page_title="Chinook Music Database Agent", layout="wide")
st.title("🎵 Chinook Music Database Agent")


# Initialize database and model
@st.cache_resource
def setup_agent():
    # 1. Database connection - CHINOOK.DB (SQLite file)
    # Make sure Chinook.db is in the same directory or provide full path
    db = SQLDatabase.from_uri("sqlite:///Chinook.db")
    
    # 2. LLM Configuration (Gemini 2.0 Flash)
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    
    # 3. Create the SQL Agent
    agent_executor = create_sql_agent(
        llm=llm,
        db=db,
        agent_type="tool-calling",  # Best for Gemini/OpenAI in 2025
        verbose=True,
        prefix="""You are a professional SQL assistant for the Chinook Music Database.


Your purpose:
- Provide factual, helpful, and clear answers about the database contents.
- Execute SQL queries to analyze, read, and modify database data.
- Analyze and describe albums, artists, tracks, playlists, customers, invoices, and related entities.
- Support both data retrieval and data modification operations.


Capabilities:
- You can READ/QUERY data from any table to analyze and provide insights.
- You can WRITE/MODIFY data including INSERT, UPDATE, DELETE operations when requested.
- You can CREATE or ALTER tables, indexes, and other schema objects when needed.
- You have full SQL capability to perform comprehensive database operations.


Best practices:
- Always confirm destructive operations (DELETE, DROP, TRUNCATE) before executing.
- Use transactions appropriately for data integrity.
- Provide clear explanations of what queries will do before execution.
- Summarize results logically and concisely.
- Use SQL knowledge responsibly and efficiently.


Always be factual, clear, and helpful in your explanations."""
    )
    
    return agent_executor


# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []


# Instantiate the agent once and cache it
if "executor" not in st.session_state:
    try:
        st.session_state.executor = setup_agent()
        st.success("✅ Connected to Chinook database successfully!")
        
        # Show quick stats
        with st.expander("📊 Quick Database Overview"):
            db = SQLDatabase.from_uri("sqlite:///Chinook.db")
            tables = db.get_usable_table_names()
            st.info(f"**Tables available:** {', '.join(tables)}")
            st.warning("⚠️ **Note:** This agent has full read and write access to the database. Use with caution.")
            
    except Exception as e:
        st.error(f"❌ Failed to connect to Chinook.db: {e}")
        st.info("💡 Make sure `Chinook.db` file is in the same directory as this app")
        st.stop()


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
    st.warning("**Full Access Mode:** This agent can read and write to the database. Be careful with destructive operations!")