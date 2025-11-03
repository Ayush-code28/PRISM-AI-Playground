import os
import time
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from litellm import completion

# Load .env automatically
load_dotenv()

# Default models
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini/gemini-2.0-flash")
GROQ_MODEL_HIGH = os.getenv("GROQ_MODEL_HIGH", "groq/llama-3.3-70b-versatile")
GROQ_MODEL_FAST = os.getenv("GROQ_MODEL_FAST", "groq/llama-3.1-8b-instant")

# Attempt to read keys from environment
ENV_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
ENV_GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()

# page config & theme
st.set_page_config(page_title="PRISM — AI Playground", layout="wide", initial_sidebar_state="auto")
st.markdown("""
<style>
/* Dark background + indigo/gold accents */
body { background-color: #0b0f1a; color: #E8EEF6; }
.main > div { background-color: transparent; }
h1, h2, h3, .stMarkdown { color: #E8EEF6; }
.prism-header { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
.card {
  background: linear-gradient(180deg, rgba(20,18,28,0.55), rgba(10,8,18,0.4));
  border: 1px solid rgba(153,122,56,0.18);
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 6px 18px rgba(7,10,20,0.6);
}
.model-badge {
  background: rgba(153,122,56,0.12);
  color: #EFD48A;
  padding: 4px 8px;
  border-radius: 8px;
  font-weight: 600;
}
.small-muted { color: #9aa3b2; font-size:13px; }
.response-box {
  background: rgba(255,255,255,0.02);
  border-radius: 8px;
  padding: 10px;
  color: #E8EEF6;
  min-height: 100px;
  white-space: pre-wrap;
}
.copy-btn {
  background: linear-gradient(90deg, #3b2b6d, #5b3f0b);
  color: white;
  border-radius: 6px;
  padding: 6px 10px;
  border: none;
  cursor: pointer;
}
.clear-btn {
  background: rgba(200,80,80,0.12);
  color: #f78a8a;
  border-radius: 6px;
  padding: 6px 10px;
  border: none;
  cursor: pointer;
}
</style>
""", unsafe_allow_html=True)

# PRISM header
st.markdown('<div class="prism-header"><h1>PRISM — AI Playground</h1>'
            '<div class="small-muted">Indigo & Gold theme · Compare models side-by-side · Retry on rate limits</div></div>', unsafe_allow_html=True)
st.markdown("---")

# Top info row: env badges + quick actions
col1, col2, col3 = st.columns([2, 3, 1])
with col1:
    st.markdown(f"<div class='card'><b>Keys loaded from .env</b><br>"
                f"<span class='small-muted'>Gemini:</span> <span class='model-badge'>{'Yes' if ENV_GEMINI_KEY else 'No'}</span> &nbsp;"
                f"<span class='small-muted'>Groq:</span> <span class='model-badge'>{'Yes' if ENV_GROQ_KEY else 'No'}</span></div>", unsafe_allow_html=True)
with col2:
    st.markdown("<div class='card'><b>Active Models</b><div class='small-muted'>Primary → Gemini 2.0 Flash</div>"
                f"<div style='margin-top:6px'><span class='model-badge'>Gemini</span> &nbsp; <span class='model-badge'>Llama 3.3</span> &nbsp; <span class='model-badge'>Llama 3.1 8B</span></div></div>", unsafe_allow_html=True)
with col3:
    # Clear history button
    if 'history' not in st.session_state: st.session_state['history'] = []
    if st.button("Clear History", key="clear_history"):
        st.session_state['history'] = []
        st.success("History cleared")

# Inputs: keys (prefilled from env but editable) and system prompt
st.markdown("<div class='card'><b>Authentication & Prompt</b></div>", unsafe_allow_html=True)
g_col1, g_col2 = st.columns(2)
with g_col1:
    google_api_key = st.text_input("🔑 Google / Gemini API Key (auto-loaded from .env if available)", value=ENV_GEMINI_KEY, type="password")
with g_col2:
    groq_api_key = st.text_input("🚀 Groq API Key (auto-loaded from .env if available)", value=ENV_GROQ_KEY, type="password")

system_prompt = st.text_area("💡 System Prompt (applies to all models)",
                             value="You are a helpful AI assistant that provides clear and concise responses.",
                             height=80)
if not system_prompt.strip():
    system_prompt = "You are a helpful AI assistant that provides clear and concise responses."

# helper: copy-to-clipboard JS component
def copy_to_clipboard(text: str):
    safe_text = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    components.html(f"""
        <button class="copy-btn" onclick="navigator.clipboard.writeText('{safe_text}').then(()=>{{document.getElementById('copy-msg').innerText='Copied!'}})">
            Copy
        </button>
        <span id="copy-msg" style="margin-left:8px;color:#EFD48A"></span>
    """, height=36)

# LLM call with retry (minimal change from your logic)
def get_llm_response(model_name: str, api_key: str, user_input: str) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    max_retries = 3
    delay = 1  # 1s -> 2s -> 4s
    for attempt in range(max_retries):
        try:
            resp = completion(model=model_name, messages=messages, api_key=api_key)
            if hasattr(resp, "choices") and len(resp.choices) > 0:
                choice = resp.choices[0]
                text = getattr(choice, "message", None)
                if text and hasattr(text, "content"):
                    return text.content
                body = choice.__dict__ if hasattr(choice, "__dict__") else choice
                if isinstance(body, dict):
                    return (body.get("message", {}) or {}).get("content") or body.get("text") or str(body)
            return str(resp)
        except Exception as e:
            err = str(e)
            if ("429" in err or "RESOURCE_EXHAUSTED" in err) and attempt < max_retries - 1:
                st.warning(f"⚠️ Rate limit for {model_name}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
                continue
            return f"❌ Error: {err}"
    return "❌ Failed after retries due to rate limit."

# Main tabs: Chat / Compare / History
tab1, tab2, tab3 = st.tabs(["Chat", "Compare (Side-by-Side)", "History"])

with tab1:
    st.markdown("<div class='card'><b>Single Chat</b></div>", unsafe_allow_html=True)
    chat_input = st.text_area("Enter prompt:", height=120, key="chat_input")
    if st.button("Send (Chat)"):
        if not chat_input.strip():
            st.warning("Please enter a message.")
        else:
            if not google_api_key.strip() and not groq_api_key.strip():
                st.warning("No API keys provided. Put keys in .env or enter them above.")
            else:
                st.subheader("Response")
                # call primary (Gemini) first, fallback to groq if needed (Gemini preferred)
                if google_api_key.strip():
                    out = get_llm_response(GEMINI_MODEL, google_api_key.strip(), chat_input)
                elif groq_api_key.strip():
                    out = get_llm_response(GROQ_MODEL_HIGH, groq_api_key.strip(), chat_input)
                else:
                    out = "No API keys available."
                st.markdown(f"<div class='response-box'>{out}</div>", unsafe_allow_html=True)
                copy_to_clipboard(out)
                # save to history
                st.session_state.history.append({"prompt": chat_input, "gemini": out})

with tab2:
    st.markdown("<div class='card'><b>Compare Models</b></div>", unsafe_allow_html=True)
    compare_input = st.text_area("Enter prompt to compare across models:", height=120, key="compare_input")
    if st.button("Compare Now"):
        if not compare_input.strip():
            st.warning("Please enter a message.")
        else:
            if not google_api_key.strip() and not groq_api_key.strip():
                st.warning("No API keys provided. Put keys in .env or enter them above.")
            else:
                # show three model cards side-by-side
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("<div class='card'><b>🌟 Gemini 2.0 Flash (FREE)</b></div>", unsafe_allow_html=True)
                    if google_api_key.strip():
                        resp_g = get_llm_response(GEMINI_MODEL, google_api_key.strip(), compare_input)
                        st.markdown(f"<div class='response-box'>{resp_g}</div>", unsafe_allow_html=True)
                        copy_to_clipboard(resp_g)
                    else:
                        st.info("No Gemini API key provided. Add it above.")
                with c2:
                    st.markdown("<div class='card'><b>🦙 Llama 3.3 70B (Groq)</b></div>", unsafe_allow_html=True)
                    if groq_api_key.strip():
                        resp_l = get_llm_response(GROQ_MODEL_HIGH, groq_api_key.strip(), compare_input)
                        st.markdown(f"<div class='response-box'>{resp_l}</div>", unsafe_allow_html=True)
                        copy_to_clipboard(resp_l)
                    else:
                        st.info("No Groq API key provided. Add it above.")
                with c3:
                    st.markdown("<div class='card'><b>⚡ Llama 3.1 8B Instant (Groq)</b></div>", unsafe_allow_html=True)
                    if groq_api_key.strip():
                        resp_f = get_llm_response(GROQ_MODEL_FAST, groq_api_key.strip(), compare_input)
                        st.markdown(f"<div class='response-box'>{resp_f}</div>", unsafe_allow_html=True)
                        copy_to_clipboard(resp_f)
                    else:
                        st.info("No Groq API key provided. Add it above.")
                # save to history
                st.session_state.history.append({"prompt": compare_input,
                                                "gemini": resp_g if 'resp_g' in locals() else "",
                                                "llama3_3": resp_l if 'resp_l' in locals() else "",
                                                "llama3_1": resp_f if 'resp_f' in locals() else ""})

with tab3:
    st.markdown("<div class='card'><b>Conversation History</b></div>", unsafe_allow_html=True)
    if not st.session_state.get('history'):
        st.info("No history yet. Run some queries from Chat or Compare tabs.")
    else:
        for i, item in enumerate(reversed(st.session_state.history[-50:])):
            st.markdown(f"**Prompt:** {item.get('prompt','')}")
            if 'gemini' in item and item['gemini']:
                st.markdown(f"- **Gemini:**")
                st.markdown(f"<div class='response-box'>{item['gemini']}</div>", unsafe_allow_html=True)
            if 'llama3_3' in item and item['llama3_3']:
                st.markdown(f"- **Llama 3.3:**")
                st.markdown(f"<div class='response-box'>{item['llama3_3']}</div>", unsafe_allow_html=True)
            if 'llama3_1' in item and item['llama3_1']:
                st.markdown(f"- **Llama 3.1:**")
                st.markdown(f"<div class='response-box'>{item['llama3_1']}</div>", unsafe_allow_html=True)
            st.markdown("---")

# Footer
st.markdown("<div class='small-muted' style='text-align:center;padding:10px'>PRISM — built for comparison and research · Indigo & Gold theme</div>", unsafe_allow_html=True)
