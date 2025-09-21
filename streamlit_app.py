# app.py
import streamlit as st
from elevenlabs import ElevenLabs
import tempfile
import os

# ---------------------------------------------------------
# Initialize ElevenLabs client
# ---------------------------------------------------------
client = ElevenLabs(api_key=st.secrets["ELEVENLABS_KEY"])

st.set_page_config(page_title="🎙️ Voice Agent Platform", layout="wide")
st.title("🎙️ Open Voice Agent Platform")

menu = st.sidebar.radio(
    "Navigation", 
    ["Home", "Voices", "Create Agent", "Deploy Agent"]
)

# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------
if menu == "Home":
    st.markdown("""
    ## Welcome to the Open Voice Agent Platform
    This app lets you create and deploy AI voice agents using ElevenLabs.

    **Features:**
    - 🔑 Secure key storage with `st.secrets`
    - 🎭 List and browse built-in + custom voices
    - 🛠️ Create your own agents (voice clones with consent)
    - 🚀 Deploy agents and generate speech instantly
    """)

# ---------------------------------------------------------
# VOICES
# ---------------------------------------------------------
elif menu == "Voices":
    st.subheader("Available Voices")

    try:
        all_voices = client.voices.get_all()
        if not all_voices.voices:
            st.info("No voices found.")
        else:
            for v in all_voices.voices:
                st.markdown(f"**{v.name}**  \nID: `{v.voice_id}`  \nCategory: {v.category}")
    except Exception as e:
        st.error(f"Error fetching voices: {e}")

# ---------------------------------------------------------
# CREATE AGENT
# ---------------------------------------------------------
elif menu == "Create Agent":
    st.subheader("Create New Voice Agent")

    agent_name = st.text_input("Agent Name")
    agent_desc = st.text_area("Agent Description")
    uploaded_file = st.file_uploader("Upload voice sample (WAV/MP3)", type=["wav", "mp3"])

    if st.button("Create Agent"):
        if not agent_name:
            st.warning("Please provide an agent name.")
        elif not uploaded_file:
            st.warning("Please upload a sample file.")
        else:
            try:
                # Save upload to a temp file
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(uploaded_file.read())
                    tmp.flush()
                    with open(tmp.name, "rb") as f:
                        resp = client.voices.add(
                            name=agent_name,
                            description=agent_desc,
                            files=[f]
                        )
                    st.success("✅ Agent created successfully")
                    st.json(resp.model_dump())
                    os.remove(tmp.name)
            except Exception as e:
                st.error(f"Error creating agent: {e}")

# ---------------------------------------------------------
# DEPLOY AGENT
# ---------------------------------------------------------
elif menu == "Deploy Agent":
    st.subheader("Deploy & Test Agent")

    try:
        all_voices = client.voices.get_all()
        if not all_voices.voices:
            st.info("No voices available. Create one first.")
        else:
            voice_map = {v.name: v.voice_id for v in all_voices.voices}
            selected = st.selectbox("Choose Agent Voice", list(voice_map.keys()))
            text_input = st.text_area("Agent Script", "Hello! I am your AI agent.")

            if st.button("Generate Speech"):
                try:
                    audio = client.text_to_speech.convert(
                        voice_id=voice_map[selected],
                        model_id="eleven_multilingual_v2",
                        text=text_input
                    )

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                        for chunk in audio:
                            tmp.write(chunk)
                        tmp.flush()

                        # Play back the audio
                        st.audio(tmp.name, format="audio/mp3")
                        os.remove(tmp.name)

                except Exception as e:
                    st.error(f"Error generating audio: {e}")

    except Exception as e:
        st.error(f"Error loading voices: {e}")
