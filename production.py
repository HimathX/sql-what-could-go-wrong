import streamlit as st
import uuid
from typing_extensions import TypedDict
from typing import Annotated, List, Any, Dict
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.callbacks.base import BaseCallbackHandler
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.runnables import RunnableConfig
from langchain.chat_models import init_chat_model
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

st.set_page_config(page_title="Intelligent SQL Executor", layout="wide")
st.title("🎵 Intelligent SQL Executor")

# Initialize chat message history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize agent thinking steps (detailed chain logs)
if "thinking_steps" not in st.session_state:
    st.session_state.thinking_steps = []

# Initialize pending query for sidebar buttons
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

# Model and API key configuration
if "model_name" not in st.session_state:
    st.session_state.model_name = "gemini-2.0-flash"
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

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
    # Allow runtime overrides from the sidebar
    model_name = st.session_state.model_name or "gemini-2.0-flash"
    api_key = st.session_state.api_key 
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key  # ensure downstream client picks it up
    llm = init_chat_model(
        model=model_name,
        model_provider="google_genai",
        temperature=0,
        api_key=api_key if api_key else None,
    )
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
        model_name = st.session_state.model_name 
        api_key = st.session_state.api_key 
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
        llm = init_chat_model(
            model=model_name,
            model_provider="google_genai",
            temperature=0,
            api_key=api_key if api_key else None,
        )
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


# Sidebar with information and examples
with st.sidebar:
    st.header("About")
    st.markdown("""
**Intelligent SQL Executor** is an AI-powered agent that understands natural language queries and executes them against your database.
    """)
    
    st.subheader("How It Works")
    with st.expander("See details", expanded=False):
        st.markdown("""
1. **Ask a Question** - Type any database query in natural language
2. **Agent Analysis** - AI understands your intent and generates SQL
3. **Execution** - Query runs against the Chinook database
4. **Results** - Get answers with full reasoning visible
        """)
    
    st.divider()
    
    st.subheader("Model Settings")
    st.session_state.model_name = st.text_input(
        "Model name", value=st.session_state.model_name, help="e.g., gemini-2.0-flash"
    )
    st.session_state.api_key = st.text_input(
        "API key", value=st.session_state.api_key, type="password", help="Google GenAI API key"
    )

    st.divider()
    
    st.subheader("Try These")
    examples = [
        "Count total artists in the database",
        "Show top 5 genres by revenue",
        "List employees by hire date",
        "Show customer distribution by country"
    ]
    
    for example in examples:
        if st.button(example, key=f"example_{example}", use_container_width=True):
            st.session_state.pending_query = example
            st.rerun()


    st.divider()
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thinking_steps = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()
    
    st.divider()
    with st.expander("📊 Available Tables", expanded=False):
        st.caption("Album, Artist, Customer, Employee, Genre, Invoice, InvoiceLine, MediaType, Playlist, PlaylistTrack, Track")
