"""
app.py - Streamlit Voice Agent Platform (ElevenLabs)
Single-file application demonstrating:
- Agent creation (local/in-memory; swap to Supabase later)
- Voice listing, cloning, TTS generation via ElevenLabs
- Test console to synthesize agent reply and playback
- Deploy/embed snippet generator
- Uses st.secrets["ELEVENLABS_API_KEY"]
"""

import streamlit as st
import requests
import json
import base64
from typing import Dict, Any
from io import BytesIO
import time
import uuid

# ------- Config -------
ELEVENLABS_API_KEY = st.secrets.get("ELEVENLABS_API_KEY", None)
if not ELEVENLABS_API_KEY:
    st.warning("ELEVENLABS_API_KEY not found in streamlit secrets. Add it to run TTS features.")
HEADERS = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}

ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"

# ---------- Simple in-memory DB for agents (swap to Supabase later) ----------
if "agents" not in st.session_state:
    st.session_state.agents = {}  # agent_id -> dict

# ---------- Helper functions to call ElevenLabs ----------
def list_voices() -> Dict[str, Any]:
    """Retrieve available voices from ElevenLabs Voices API"""
    url = f"{ELEVENLABS_BASE}/voices"
    r = requests.get(url, headers=HEADERS, timeout=15)
    if r.status_code == 200:
        return r.json()
    else:
        st.error(f"Error listing voices: {r.status_code} {r.text}")
        return {}

def synthesize_text_to_audio_bytes(text: str, voice: str = None, model: str = None) -> bytes:
    """
    Convert text to speech using ElevenLabs TTS endpoint (returns raw audio bytes).
    model_id defaults to eleven_multilingual_v2 if not provided by ElevenLabs.
    See ElevenLabs docs for parameter details. :contentReference[oaicite:1]{index=1}
    """
    url = f"{ELEVENLABS_BASE}/text-to-speech/{voice or 'eleven_multilingual_v2'}"
    payload = {"text": text}
    if model:
        payload["model_id"] = model
    r = requests.post(url, headers=HEADERS, json=payload, timeout=30)
    if r.status_code == 200:
        return r.content
    else:
        st.error(f"TTS error {r.status_code}: {r.text}")
        return b""

def create_instant_voice_clone(voice_name: str, voice_samples_wav_bytes: bytes) -> Dict[str, Any]:
    """
    Create Instant Voice Clone via ElevenLabs API.
    The real API expects a multipart/form-data with voice sample(s). See docs for details. :contentReference[oaicite:2]{index=2}
    NOTE: This is a minimal representation. The production client should use SDK / correct multipart form.
    """
    url = f"{ELEVENLABS_BASE}/voices/add"
    # Example simple json approach; the official API may require multipart/form-data
    # We'll send a base64 sample for demonstration; production should follow docs.
    b64 = base64.b64encode(voice_samples_wav_bytes).decode("utf-8")
    payload = {"name": voice_name, "samples_base64": [b64]}
    r = requests.post(url, headers=HEADERS, json=payload, timeout=60)
    if r.status_code in (200,201):
        return r.json()
    else:
        st.error(f"Voice clone error {r.status_code}: {r.text}")
        return {}

# ---------- Streamlit UI ----------
st.set_page_config(page_title="OpenVoice Agents (Streamlit + ElevenLabs)", layout="wide")
st.title("OpenVoice Agents — Streamlit voice agents powered by ElevenLabs")

left, right = st.columns([2,1])

with left:
    st.header("1) Agent list & creation")
    with st.form("create_agent_form"):
        agent_name = st.text_input("Agent name", value=f"Agent-{str(uuid.uuid4())[:6]}")
        agent_persona = st.text_area("Persona / system prompt (how agent should behave)",
                                    value="You are a helpful, concise voice assistant specialized in onboarding.")
        default_voice_choice = st.text_input("Default voice id (leave empty to choose later)", value="")
        create_agent = st.form_submit_button("Create agent")
    if create_agent:
        agent_id = str(uuid.uuid4())
        st.session_state.agents[agent_id] = {
            "id": agent_id,
            "name": agent_name,
            "persona": agent_persona,
            "default_voice": default_voice_choice or None,
            "created_at": time.time(),
        }
        st.success(f"Created agent {agent_name} ({agent_id}) — saved in session. Replace this with Supabase later.")

    if st.session_state.agents:
        st.subheader("Existing agents (session)")
        for aid, ag in st.session_state.agents.items():
            with st.expander(f"{ag['name']} — id: {aid}"):
                st.text_area("Persona", value=ag["persona"], key=f"persona_{aid}", height=120)
                new_voice = st.text_input("Default voice id", value=ag.get("default_voice") or "", key=f"voice_{aid}")
                if st.button("Save agent changes", key=f"save_{aid}"):
                    ag["default_voice"] = new_voice or None
                    ag["persona"] = st.session_state[f"persona_{aid}"]
                    st.success("Saved (session).")

with right:
    st.header("2) ElevenLabs voices")
    st.caption("Get available voices from ElevenLabs. (Requires ELEVENLABS_API_KEY in streamlit secrets)")
    if st.button("Refresh voices"):
        voices_resp = list_voices()
        if voices_resp:
            st.session_state._voices = voices_resp.get("voices", voices_resp)
    voices = st.session_state.get("_voices", None)
    if voices:
        st.write("Voices (preview):")
        # show a compact list
        for v in voices[:20]:
            st.markdown(f"**{v.get('name','-')}** — id: `{v.get('voice_id', v.get('id',''))}` — language: {v.get('language_code', 'n/a')}")
    else:
        st.info("No voices loaded yet. Click 'Refresh voices' to load from ElevenLabs.")

st.markdown("---")
st.header("3) Agent test & TTS console")

agent_choice = st.selectbox("Select agent to test", options=["--choose--"] + list(st.session_state.agents.keys()))
user_input = st.text_area("User input (say something to the agent)", value="Hello, I want to sign up.")
synthesize_button = st.button("Generate agent reply & synthesize audio")

if synthesize_button:
    if agent_choice == "--choose--":
        st.error("Pick an agent first.")
    else:
        agent = st.session_state.agents[agent_choice]
        # Simple policy: agent reply = persona + user input -> pass to LLM (here stubbed)
        # TODO: Replace stub with Gemini or Cloudflare Workers AI call for real responses (AutoRAG).
        # For now we craft a deterministic reply for demo.
        prompt = f"Persona: {agent['persona']}\n\nUser: {user_input}\n\nAssistant (short reply):"
        # Simple deterministic "LLM" reply (placeholder)
        assistant_reply = f"[Simulated reply based on persona] Thanks for your message. I will help you with onboarding steps for '{user_input[:60]}'."
        st.markdown("**Assistant reply (simulated)**")
        st.write(assistant_reply)

        # Choose voice
        chosen_voice = agent.get("default_voice") or st.text_input("Voice id to use for TTS (leave blank to use default model id)", value="")
        # Synthesize via ElevenLabs
        with st.spinner("Calling ElevenLabs TTS..."):
            audio_bytes = synthesize_text_to_audio_bytes(assistant_reply, voice=(chosen_voice or None))
        if audio_bytes:
            st.audio(audio_bytes, format="audio/mpeg")
            st.success("Audio generated and playable below. Save audio or attach to deployable agent flows.")

st.markdown("---")
st.header("4) Voice cloning (instant demo)")

with st.expander("Upload a short WAV sample to clone (demo; production uses correct multipart flow)"):
    uploaded = st.file_uploader("Upload WAV file (short sample for demo)", type=["wav","mp3","m4a"], accept_multiple_files=False)
    clone_name = st.text_input("New voice name (for clone)", value=f"clone-{str(uuid.uuid4())[:6]}")
    if st.button("Create instant clone (demo)"):
        if not uploaded:
            st.error("Upload sample first.")
        else:
            sample_bytes = uploaded.read()
            with st.spinner("Creating voice clone (demo API call)..."):
                clone_resp = create_instant_voice_clone(clone_name, sample_bytes)
                if clone_resp:
                    st.json(clone_resp)
                    st.success("Voice clone requested. In production read the API docs for proper sample upload format. :contentReference[oaicite:3]{index=3}")

st.markdown("---")
st.header("5) Deployment / Embed snippet")

st.markdown("""
This section provides a basic embeddable widget snippet (iframe) that you can host and embed in client apps.
For production: host this Streamlit app behind an authenticated endpoint and use a small JS widget to open an iframe + postMessage for chat events.
""")

embed_url = st.text_input("Publicly accessible URL for your hosted Streamlit app", value="https://your-hosted-app.example.com")
widget_html = f"""
<!-- Simple embeddable voice-agent iframe widget -->
<div id="openvoice-widget">
  <iframe src="{embed_url}?embed=true" width="400" height="600" style="border:1px solid #ddd;border-radius:8px"></iframe>
</div>
<script>
  // Example: send an event to the iframe to start a conversation
  function startAgent(iframeEl, agentId, initialText) {{
    iframeEl.contentWindow.postMessage({{type:'openvoice-start', agentId: agentId, text: initialText}}, '*');
  }}
</script>
"""
st.code(widget_html, language="html")

st.markdown("**Note:** For secure production embed, use signed JWTs or server-side tokens to avoid exposing API keys in the browser. Store keys server-side (Workers / Edge functions) and proxy TTS requests.")

st.markdown("---")
st.header("6) Next steps & production hooks (how you scale this)")

st.markdown("""
**Short list to go production:**
- Move agent storage to Supabase (or your DB). Add `SUPABASE_URL` + `SUPABASE_KEY` to `st.secrets`. Use `supabase-py` to persist agents and evidence.
- Replace the simulated assistant reply with real LLM calls (Gemini / Cloudflare Workers AI). Use AutoRAG to RAG internal docs & regulatory DB for context-aware replies.
- For calls/phone agents: integrate Twilio or SIP gateway; generate TTS audio and stream to call leg; capture call audio -> run speech-to-text for transcripts.
- For secure embed: host behind Cloudflare, create short-lived signed tokens for widget access; use Worker as an API proxy so the browser never sees the ElevenLabs key.
- Add rate-limiting, caching, & usage metering (ElevenLabs has quotas and auth rules). :contentReference[oaicite:4]{index=4}
""")

# Footer / dev notes
st.sidebar.header("Dev notes & links")
st.sidebar.markdown("""
- ElevenLabs docs: text-to-speech, voices, cloning. :contentReference[oaicite:5]{index=5}
- Example: use `requests` or ElevenLabs Python SDK for multipart / official usage. See ElevenLabs quickstart. :contentReference[oaicite:6]{index=6}
""")
