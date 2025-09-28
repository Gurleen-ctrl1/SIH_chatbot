import streamlit as st
import openai
import os
from dotenv import load_dotenv
import pyttsx3
import speech_recognition as sr
import tempfile

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")



# ---- Streamlit Page ----
st.set_page_config(page_title="Healthcare Chatbot", page_icon="🏥")
st.title("🏥 Healthcare Chatbot")
st.write("I am your health assistant. I can speak English, Hindi, and Punjabi.")
st.write("⚠️ Safety Notice: This bot provides only general advice. In emergencies, seek professional help immediately.")

# ---- Session State ----
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "consultation_complete" not in st.session_state:
    st.session_state.consultation_complete = False

# ---- Emergency keywords ----
EMERGENCY_KEYWORDS = ["chest pain", "difficulty breathing", "shortness of breath", "severe pain", "unconscious"]

# ---- Helper Functions ----
def detect_emergency(user_input):
    return any(word.lower() in user_input.lower() for word in EMERGENCY_KEYWORDS)

def get_gpt_response(user_input):
    """
    GPT handles both conversation flow and advice.
    """
    system_prompt = """
You are a professional, friendly, empathetic healthcare assistant.
Simulate a doctor consultation dynamically:
- Collect patient's Name, Age, Gender, How they are feeling, Main symptoms, Severity, Duration, Associated symptoms, Past medical history, Allergies, and current medications.
- Ask any additional questions needed to provide safe and accurate recommendations.
- Use the patient's name in replies once known.
- Provide only safe general advice: hydration, rest, diet, safe OTC medicines (paracetamol, ibuprofen).
- Detect emergencies: if user mentions dangerous symptoms (chest pain, difficulty breathing, severe pain, unconsciousness), alert immediately: "This may be an emergency. Seek urgent medical help immediately."
- Keep context memory of all previous replies.
- Provide a comprehensive final summary after all info is collected including:
  1. Patient profile
  2. Symptoms & severity
  3. Likely condition / general explanation
  4. Recommended OTC medications
  5. Dietary recommendations
  6. Precautions & lifestyle advice
  7. Follow-up instructions
- Respond in the same language the patient uses (English, Hindi, Punjabi).
- Keep a friendly, empathetic tone.
- Never provide prescription-only medicines or a formal diagnosis.
"""
    # Build messages including history
    messages = [{"role": "system", "content": system_prompt}]
    for c in st.session_state.conversation:
        messages.append({"role": "user", "content": c['user']})
        messages.append({"role": "assistant", "content": c['bot']})
    messages.append({"role": "user", "content": user_input})

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=600
    )
    return response.choices[0].message.content.strip()

def speak_text(text, lang="en"):
    """Convert text to speech and play it in Streamlit"""
    with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as f:
        from gtts import gTTS
        tts = gTTS(text, lang=lang)
        tts.save(f.name)
        st.audio(f.name, format="audio/mp3")

def detect_language(user_input):
    """Simple heuristic for language selection for TTS"""
    if any("\u0900" <= c <= "\u097F" for c in user_input):  # Devanagari
        return "hi"
    elif any("\u0A00" <= c <= "\u0A7F" for c in user_input):  # Gurmukhi
        return "pa"
    else:
        return "en"

# ---- User Input (Text) ----
st.subheader("💬 Text Input")
user_text = st.text_input("Type your message here:")

# ---- User Input (Voice) ----
st.subheader("🎤 Voice Input")
if st.button("Record Voice"):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening...")
        audio = r.listen(source)
    try:
        # Automatic language detection can be added here
        user_voice_input = r.recognize_google(audio, language="hi-IN")  # Change dynamically if needed
        st.success(f"**You said:** {user_voice_input}")
        user_input_final = user_voice_input
    except Exception as e:
        st.error("Could not recognize speech: " + str(e))
        user_input_final = ""
else:
    user_input_final = user_text

# ---- Process Input ----
if user_input_final:
    # Emergency check
    if detect_emergency(user_input_final):
        bot_reply = "⚠️ This may be an emergency. Please seek urgent medical help immediately."
        st.session_state.consultation_complete = True
    else:
        bot_reply = get_gpt_response(user_input_final)
        # Simple heuristic: if GPT mentions final summary, mark consultation complete
        if "final summary" in bot_reply.lower() or "comprehensive summary" in bot_reply.lower():
            st.session_state.consultation_complete = True

    # Save conversation
    st.session_state.conversation.append({"user": user_input_final, "bot": bot_reply})

    # ---- Detect language for TTS ----
    lang = detect_language(user_input_final)
    speak_text(bot_reply, lang=lang)

# ---- Display Chat ----
st.markdown("---")
for c in st.session_state.conversation:
    if c['user']:
        st.markdown(f"**You:** {c['user']}")
    st.markdown(f"**Bot:** {c['bot']}")

# ---- Start conversation automatically ----
if not st.session_state.conversation:
    first_prompt = "Hello! I’m your health assistant. May I know your name?"
    st.session_state.conversation.append({"user": "", "bot": first_prompt})
    speak_text(first_prompt)
