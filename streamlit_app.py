# app.py
import streamlit as st
from elevenlabs import set_api_key, voices, generate, save, Voice, VoiceSettings
import requests
import tempfile
import os

# Load API key from Streamlit secrets
ELEVEN_KEY = st.secrets["ELEVENLABS_KEY"]
set_api_key(ELEVEN_KEY)

st.set_page_config(page_title="Voice Agent Platform", layout="wide")
st.title("🎙️ Open Voice Agent Platform")

# Sidebar navigation
menu = st.sidebar.radio("Navigation", ["Home", "Voices", "Create Agent", "Deploy Agent"])

# ------------------ HOME ------------------
if menu == "Home":
    st.markdown("""
    ### Welcome
    This is your open-source alternative to closed AI agent platforms.  
    - **Create Agents**: Clone voices with consent.  
    - **Deploy Agents**: Generate speech using those voices.  
    - **Manage Voices**: Browse available voices.  

    🔑 API key is securely loaded from Streamlit secrets.
    """)

# ------------------ VOICES ------------------
elif menu == "Voices":
    st.subheader("Available Voices")

    try:
        all_voices = voices()
        for v in all_voices:
            st.markdown(f"**{v.name}** ({v.voice_id}) — {v.labels.get('accent','N/A')} {v.labels.get('gender','')}")
    except Exception as e:
        st.error(f"Error fetching voices: {e}")

# ------------------ CREATE AGENT ------------------
elif menu == "Create Agent":
    st.subheader("Create New Voice Agent")

    with st.form("voice_form", clear_on_submit=True):
        agent_name = st.text_input("Agent Name")
        agent_desc = st.text_area("Agent Description")
        uploaded_file = st.file_uploader("Upload voice sample (WAV/MP3, consent required)", type=["wav", "mp3"])
        submit = st.form_submit_button("Create Agent")

    if submit and uploaded_file:
        try:
            files = {
                "files": (uploaded_file.name, uploaded_file, uploaded_file.type),
            }
            data = {"name": agent_name, "description": agent_desc}
            headers = {"xi-api-key": ELEVEN_KEY}

            resp = requests.post(
                "https://api.elevenlabs.io/v1/voices/add",
                headers=headers,
                files=files,
                data=data
            )

            if resp.status_code == 200:
                st.success("✅ Agent created successfully")
                st.json(resp.json())
            else:
                st.error(f"❌ Error: {resp.text}")
        except Exception as e:
            st.error(f"Error: {e}")

# ------------------ DEPLOY AGENT ------------------
elif menu == "Deploy Agent":
    st.subheader("Deploy & Test Agent")

    try:
        all_voices = voices()
        voice_options = {v.name: v.voice_id for v in all_voices}
    except Exception as e:
        st.error("Could not fetch voices.")
        st.stop()

    selected_voice = st.selectbox("Choose Agent Voice", list(voice_options.keys()))
    text_input = st.text_area("Enter agent script / reply text", "Hello! I am your AI agent.")

    if st.button("Generate Speech"):
        try:
            audio = generate(
                text=text_input,
                voice=Voice(
                    voice_id=voice_options[selected_voice],
                    settings=VoiceSettings(stability=0.6, similarity_boost=0.9),
                ),
                model="eleven_multilingual_v2"
            )

            # Save audio to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                save(audio, tmp.name)
                tmp_path = tmp.name

            # Playback
            audio_file = open(tmp_path, "rb")
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format="audio/mp3")

            os.remove(tmp_path)

        except Exception as e:
            st.error(f"Error generating audio: {e}")
