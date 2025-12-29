import streamlit as st
import uuid
from typing_extensions import TypedDict
from typing import Annotated, List, Any, Dict
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.callbacks.base import BaseCallbackHandler
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from operator import add
import os
from dotenv import load_dotenv
from prompt import agent_prompt

load_dotenv()


class StreamlitCallbackHandler(BaseCallbackHandler):
    """Custom callback handler to capture agent thinking for Streamlit display"""
    
    def __init__(self):
        self.steps = []
        self.current_chain = None
    
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs) -> None:
        chain_name = serialized.get("name", "Chain")
        if "Agent" in str(serialized) or "agent" in str(chain_name).lower():
            self.steps.append({
                "type": "chain_start",
                "content": "🔗 Entering new SQL Agent Executor chain..."
            })
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
        if self.steps and self.steps[-1].get("type") == "chain_start":
            self.steps.append({
                "type": "chain_end", 
                "content": "✅ Finished chain."
            })
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        tool_name = serialized.get("name", "unknown_tool")
        self.steps.append({
            "type": "tool_start",
            "tool": tool_name,
            "input": input_str,
            "content": f"🔧 Invoking: `{tool_name}` with `{input_str}`"
        })
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        # Truncate long outputs
        display_output = output[:500] + "..." if len(output) > 500 else output
        self.steps.append({
            "type": "tool_output",
            "content": display_output
        })
    
    def on_tool_error(self, error: Exception, **kwargs) -> None:
        self.steps.append({
            "type": "error",
            "content": f"❌ Error: {str(error)}"
        })
    
    def on_agent_action(self, action, **kwargs) -> None:
        self.steps.append({
            "type": "agent_action",
            "content": f"🎯 Agent action: {action.tool}"
        })
    
    def get_steps(self):
        return self.steps
    
    def clear(self):
        self.steps = []

SUPABASE_URI = os.getenv("SUPABASE_URI")

class State(TypedDict):
    messages: Annotated[List[BaseMessage], add]

st.set_page_config(page_title="Supabase Music Database Agent", layout="wide")
st.title("🎵 Supabase Music Database Agent")

# Initialize chat message history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize agent thinking steps (detailed chain logs)
if "thinking_steps" not in st.session_state:
    st.session_state.thinking_steps = []

# Initialize pending query for sidebar buttons
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

# Initialize callback handler
if "callback_handler" not in st.session_state:
    st.session_state.callback_handler = StreamlitCallbackHandler()

@st.cache_resource
def get_checkpointer():
    """Single shared checkpointer across app lifetime"""
    return InMemorySaver()

def run_sql_agent(query: str, callback_handler: StreamlitCallbackHandler):
    """Run the SQL agent with callback handler to capture thinking"""
    db = SQLDatabase.from_uri(SUPABASE_URI)
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    agent_executor = create_sql_agent(
        llm=llm, 
        db=db, 
        agent_type="tool-calling", 
        verbose=True, 
        prefix=agent_prompt
    )
    
    # Clear previous steps and run with callback
    callback_handler.clear()
    response = agent_executor.invoke(
        {"input": query},
        config={"callbacks": [callback_handler]}
    )
    
    return response["output"], callback_handler.get_steps()

@st.cache_resource
def setup_graph(_checkpointer):
    """Build the LangGraph workflow"""
    def sql_agent_node(state: State):
        db = SQLDatabase.from_uri(SUPABASE_URI)
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
        agent_executor = create_sql_agent(
            llm=llm, 
            db=db, 
            agent_type="tool-calling", 
            verbose=True, 
            prefix=agent_prompt
        )
        
        response = agent_executor.invoke({"input": state["messages"][-1].content})
        return {"messages": [AIMessage(content=response["output"])]}
    
    workflow = StateGraph(State)
    workflow.add_node("sql_agent", sql_agent_node)
    workflow.add_edge(START, "sql_agent")
    workflow.add_edge("sql_agent", END)
    
    return workflow.compile(checkpointer=_checkpointer)

# Initialize session thread_id
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

checkpointer = get_checkpointer()
graph = setup_graph(checkpointer)

if "executor" not in st.session_state:
    st.session_state.executor = graph
    st.success("✅ Connected to Supabase with LangGraph memory!")

# Display chat history from session state
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # Show thinking expander for assistant messages that have thinking steps
        if message["role"] == "assistant" and "thinking_steps" in message and message["thinking_steps"]:
            with st.expander("🧠 Show Agent Thinking", expanded=False):
                for step in message["thinking_steps"]:
                    step_type = step.get("type", "")
                    content = step.get("content", "")
                    
                    if step_type == "chain_start":
                        st.markdown(f"**{content}**")
                    elif step_type == "chain_end":
                        st.markdown(f"**{content}**")
                        st.divider()
                    elif step_type == "tool_start":
                        st.code(content, language="text")
                    elif step_type == "tool_output":
                        st.text(content)
                    elif step_type == "error":
                        st.error(content)
                    elif step_type == "llm_thinking":
                        st.info(content)
                    else:
                        st.markdown(content)

# Get prompt from chat input or pending query from sidebar
prompt = st.chat_input("Ask about artists, albums, tracks... 🎵")

# Check if there's a pending query from sidebar
if st.session_state.pending_query:
    prompt = st.session_state.pending_query
    st.session_state.pending_query = None

# Chat input handling
if prompt:
    config: RunnableConfig = {"configurable": {"thread_id": st.session_state.thread_id}}
    
    # Add user message to session state
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        # Create expander for thinking that updates in real-time
        thinking_expander = st.expander("🧠 Agent Thinking...", expanded=True)
        response_placeholder = st.empty()
        
        with st.spinner("Querying database..."):
            # Run agent with callback handler to capture thinking
            callback_handler = st.session_state.callback_handler
            response_content, thinking_steps = run_sql_agent(prompt, callback_handler)
            
            # Display thinking steps in expander
            with thinking_expander:
                for step in thinking_steps:
                    step_type = step.get("type", "")
                    content = step.get("content", "")
                    
                    if step_type == "chain_start":
                        st.markdown(f"**{content}**")
                    elif step_type == "chain_end":
                        st.markdown(f"**{content}**")
                        st.divider()
                    elif step_type == "tool_start":
                        st.code(content, language="text")
                    elif step_type == "tool_output":
                        st.text(content)
                    elif step_type == "error":
                        st.error(content)
                    elif step_type == "llm_thinking":
                        st.info(content)
                    else:
                        st.markdown(content)
            
            # Display final response
            response_placeholder.markdown(response_content)
            
            # Add assistant message to session state with thinking steps
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response_content,
                "thinking_steps": thinking_steps.copy()
            })
    
    st.rerun()


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
            st.session_state.pending_query = example
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
            st.session_state.pending_query = example
            st.rerun()

    st.divider()
    st.info("**Chinook Tables:** Album, Artist, Customer, Employee, Genre, Invoice, InvoiceLine, MediaType, Playlist, PlaylistTrack, Track")
    
    st.divider()
    if st.button("🔄 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thinking_steps = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()
