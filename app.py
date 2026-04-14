import streamlit as st
import os
import time
import datetime
import html
from dotenv import load_dotenv
from core.models import AgentConfig
from core.llm_provider import LLMFactory
from core.agent import Agent, Orchestrator
from utils.history import save_to_history, load_history

# --- APP SETUP ---
st.set_page_config(page_title="AgentVerse: Pac-Man Edition", page_icon="🟡", layout="wide")
load_dotenv()

# --- CUSTOM CSS (Glassmorphism & Pac-Man) ---
st.markdown("""
<style>
    /* Global Glassmorphism */
    .main {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(15px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .stButton>button {
        background: linear-gradient(90deg, #f0db4f 0%, #e5c100 100%);
        color: #000 !important;
        border: none;
        border-radius: 20px;
        font-weight: bold;
        transition: 0.3s;
    }
    
    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 0 15px #f0db4f;
    }

    /* Pac-Man Agent Cards - Now Full Width & High Contrast */
    .pacman-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 25px;
        margin: 15px 0;
        width: 100% !important; 
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
    }
    
    .pacman-icon {
        width: 40px;
        height: 40px;
        background: #f0db4f;
        border-radius: 50%;
        position: relative;
        margin-right: 15px;
        display: inline-block;
        vertical-align: middle;
        animation: chomp 0.5s infinite;
    }
    
    .pacman-icon::after {
        content: "";
        position: absolute;
        top: 5px;
        left: 20px;
        width: 5px; height: 5px;
        background: #000;
        border-radius: 50%;
    }

    @keyframes chomp {
        0%, 100% { clip-path: polygon(100% 50%, 100% 0%, 0% 0%, 0% 100%, 100% 100%, 100% 50%, 50% 50%); }
        50% { clip-path: polygon(100% 50%, 100% 20%, 0% 0%, 0% 100%, 100% 80%, 100% 50%, 50% 50%); }
    }

    .agent-header {
        font-size: 1.2rem;
        font-weight: bold;
        color: #f0db4f;
        margin-bottom: 10px;
    }
    
    .thought-bubble {
        color: #e0e0e0;
        font-size: 1.1rem;
        line-height: 1.6;
        font-style: italic;
        border-left: 3px solid #f0db4f;
        padding-left: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- WORKFLOW LOGIC ---
def run_agent_workflow(goal, provider_type, config):
    provider = LLMFactory.get_provider(provider_type, config)
    
    def ui_callback(name, thought, action, step=None):
        if st.session_state.get("emergency_stop"):
            raise InterruptedError("Emergency Stop Triggered by User")
            
        safe_name = html.escape(name)
        safe_thought = html.escape(thought)
        
        step_label = f"Step {step}: " if step else ""
        
        st.markdown(f"""
        <div class="pacman-card">
            <div class="pacman-icon"></div>
            <span class="agent-header">{step_label}{safe_name}</span>
            <div class="thought-bubble">{safe_thought}</div>
            <div style="margin-top:10px; font-size: 0.8rem; color: #888;">Action: {action}</div>
        </div>
        """, unsafe_allow_html=True)
        st.session_state.logs.append({"name": name, "thought": thought, "action": action, "step": step})

    universe = Orchestrator(step_callback=ui_callback)
    
    # 4. Register Agents with FULL backstories for quality
    sarah = AgentConfig(
        name="Sarah", 
        role="Chief Project Manager", 
        goal="Coordinate complex projects and ALWAYS provide the final summary. You are the CLOSER.", 
        backstory="A decisive leader. When you have research from others, you stop delegating and write the final comprehensive report yourself."
    )
    dr_data = AgentConfig(
        name="Dr. Data", 
        role="Lead Researcher", 
        goal="Provide deep technical insights. Do not ask for management advice.", 
        backstory="A meticulous researcher. You provide the facts and let Sarah handle the project direction."
    )
    poet = AgentConfig(
        name="Poet", 
        role="Technical Writer", 
        goal="Produce polished, professional reports.", 
        backstory="A master of synthesis and clarity."
    )

    universe.register_agent(Agent(sarah, provider))
    universe.register_agent(Agent(dr_data, provider))
    universe.register_agent(Agent(poet, provider))

    try:
        result = universe.run_task(goal, initial_role="Chief Project Manager")
        save_to_history(goal, result)
        return result
    except InterruptedError:
        error_result = f"MISSION INTERRUPTED. Progress so far:\n\n{universe.global_context}"
        save_to_history(goal, error_result)
        return error_result

# --- SIDEBAR ---
with st.sidebar:
    st.title("🟡 AgentVerse Pro")
    
    st.subheader("📜 Mission History")
    history_entries = load_history()
    if history_entries:
        history_options = [f"{e['timestamp']} - {e['topic']}" for e in history_entries]
        selected_history = st.selectbox("Load previous mission", ["None"] + history_options)
        
        if selected_history != "None":
            idx = history_options.index(selected_history)
            st.session_state.loaded_mission = history_entries[idx]
            st.session_state.final_result = history_entries[idx]['result']
    else:
        st.info("No past missions found.")

    st.divider()
    st.subheader("⚙️ Provide & Model")
    provider_type = st.selectbox("API Provider", ["groq", "ollama", "gemini"], index=0)
    
    if provider_type == "groq":
        api_key = st.text_input("Groq API Key (Hidden)", value=os.getenv("GROQ_API_KEY", ""), type="password")
        model_name = st.text_input("Model ID", value="llama-3.1-8b-instant")
    elif provider_type == "gemini":
        api_key = st.text_input("Gemini API Key (Hidden)", value=os.getenv("GEMINI_API_KEY", ""), type="password")
        model_name = st.text_input("Model ID", value="gemini-2.0-flash")
    else:
        api_key = ""
        host = st.text_input("Ollama Host", value="http://localhost:11434")
        model_name = st.text_input("Model ID", value="llama3")

# --- MAIN INTERFACE ---
st.title("Universal Agent Universe")
st.write("Secure. Fast. Retro-Modern.")

if 'logs' not in st.session_state:
    st.session_state.logs = []

current_goal = "Analyze the impact of hydrogen fuel cells in aviation by 2030."
if 'loaded_mission' in st.session_state and st.session_state.loaded_mission:
    current_goal = st.session_state.loaded_mission['goal']

goal = st.text_area("What is your current goal?", value=current_goal, height=100)

st.subheader("Live Agent Activity")
stop_mission = st.checkbox("🛑 EMERGENCY STOP", key="emergency_stop")

# Process Launch
if st.button("🚀 LAUNCH UNIVERSE"):
        st.session_state.logs = []
        st.session_state.final_result = None
        
        config = {"model_name": model_name}
        if provider_type != "ollama": config["api_key"] = api_key
        else: config["host"] = host

        with st.status("Agents are collaborating...", expanded=True) as status:
            try:
                # Call the centralized workflow function
                final_result = run_agent_workflow(goal, provider_type, config)
                status.update(label="Mission Accomplished!", state="complete")
                st.session_state.final_result = final_result
            except InterruptedError as e:
                status.update(label="Manual Shutdown", state="error")
                st.warning(f"⚠️ {e}")
            except Exception as e:
                status.update(label="Mission Aborted!", state="error")
                st.error(f"❌ **Collaboration Error:**\n\n{e}")
                st.stop()

# Display Final Result in a BIG wide box
if st.session_state.get('final_result'):
    st.divider()
    st.subheader("🏁 Final Technical Report")
    st.success(st.session_state.final_result)
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("💾 Download Report", st.session_state.final_result, file_name="agent_report.md")
    with col2:
        if st.button("➕ START NEW MISSION", use_container_width=True):
            st.session_state.logs = []
            st.session_state.final_result = None
            st.session_state.loaded_mission = None
            st.rerun()

# FOLLOW-UP SECTION (Bottom Search Bar)
st.divider()
follow_up = st.chat_input("Is there anything more you need to ask or modify?")
if follow_up:
    st.info(f"Adding follow-up instruction: '{follow_up}'")
    # Add to history and rerun
    new_goal = f"{goal}\n\nAdditional Instruction: {follow_up}"
    st.session_state.logs = []
    st.session_state.final_result = None
    
    config = {"model_name": model_name}
    if provider_type != "ollama": config["api_key"] = api_key
    else: config["host"] = host

    with st.status("Agents are revising...", expanded=True) as status:
        try:
            final_result = run_agent_workflow(new_goal, provider_type, config)
            status.update(label="Revision Complete!", state="complete")
            st.session_state.final_result = final_result
            st.rerun()
        except Exception as e:
            status.update(label="Revision Failed!", state="error")
            st.error(f"❌ **Collaboration Error:**\n\n{e}")
            if "Groq Access Denied" in str(e):
                st.warning("Switching to **Gemini** or **Ollama** in the sidebar might solve this connection issue.")
            st.stop()

# Display logs at bottom if replaying
if st.session_state.logs and not st.session_state.get('final_result'):
    for log in st.session_state.logs:
        st.markdown(f"""
        <div class="pacman-card">
            <div class="pacman-icon"></div>
            <span class="agent-header">{log['name']}</span>
            <div class="thought-bubble">{log['thought']}</div>
        </div>
        """, unsafe_allow_html=True)
