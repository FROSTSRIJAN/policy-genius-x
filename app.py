import streamlit as st
import requests
import json
import time
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import pandas as pd
import os
import tempfile
from gtts import gTTS
from deep_translator import GoogleTranslator
import base64

# Page configuration
st.set_page_config(
    page_title="PolicyGenius X - AI Insurance Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enhanced CSS with modern glassmorphism and animations
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        font-family: 'Poppins', sans-serif;
        overflow-x: hidden;
    }
    
    /* Animated Background Elements */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: 
            radial-gradient(circle at 20% 50%, rgba(102, 126, 234, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(240, 147, 251, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 40% 80%, rgba(118, 75, 162, 0.3) 0%, transparent 50%);
        animation: floatBg 15s ease-in-out infinite;
        z-index: -1;
    }
    
    @keyframes floatBg {
        0%, 100% { transform: translateY(0px) rotate(0deg); }
        33% { transform: translateY(-20px) rotate(1deg); }
        66% { transform: translateY(10px) rotate(-1deg); }
    }
    
    /* Main Container with Advanced Glassmorphism */
    .main .block-container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(30px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 25px;
        padding: 2.5rem;
        margin-top: 1rem;
        box-shadow: 
            0 25px 50px rgba(0, 0, 0, 0.1),
            0 0 0 1px rgba(255, 255, 255, 0.1) inset;
        position: relative;
        overflow: hidden;
    }
    
    .main .block-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
        animation: shimmer 8s infinite;
    }
    
    @keyframes shimmer {
        0% { left: -100%; }
        100% { left: 100%; }
    }
    
    /* Enhanced Header with Gradient Text */
    .main-header {
        font-size: 3.5rem;
        font-weight: 700;
        background: linear-gradient(45deg, #fff, #f0f9ff, #e0f2fe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        text-shadow: 0 0 30px rgba(255, 255, 255, 0.5);
        animation: glow 3s ease-in-out infinite alternate;
        position: relative;
        z-index: 1;
    }
    
    @keyframes glow {
        from { filter: drop-shadow(0 0 20px rgba(255, 255, 255, 0.3)); }
        to { filter: drop-shadow(0 0 40px rgba(255, 255, 255, 0.6)); }
    }
    
    .sub-header {
        font-size: 1.3rem;
        color: rgba(255, 255, 255, 0.9);
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 400;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
    }
    
    /* Language Selector Styling */
    .language-selector {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 15px;
        padding: 1rem;
        margin-bottom: 2rem;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
    }
    
    /* Enhanced Answer Box with Audio Controls */
    .answer-box {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.9), rgba(118, 75, 162, 0.9));
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: white;
        padding: 2.5rem;
        border-radius: 20px;
        margin: 1.5rem 0;
        box-shadow: 
            0 20px 40px rgba(102, 126, 234, 0.3),
            0 0 0 1px rgba(255, 255, 255, 0.1) inset;
        position: relative;
        overflow: hidden;
        animation: slideUp 0.6s ease-out;
    }
    
    @keyframes slideUp {
        from { transform: translateY(30px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    
    .answer-box::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(255,255,255,0.1), transparent);
        animation: rotate 4s linear infinite;
        z-index: 0;
    }
    
    @keyframes rotate {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .answer-content {
        position: relative;
        z-index: 1;
    }
    
    /* Audio Player Styling */
    .audio-player {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 15px;
        padding: 1rem;
        margin-top: 1rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    .audio-controls {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: white;
        font-weight: 500;
    }
    
    /* Success Box with Celebration Animation */
    .success-box {
        background: linear-gradient(135deg, #4ade80, #22c55e);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        text-align: center;
        box-shadow: 0 15px 30px rgba(34, 197, 94, 0.3);
        animation: celebrate 0.8s ease-out;
        position: relative;
        overflow: hidden;
    }
    
    @keyframes celebrate {
        0% { transform: scale(0.8) rotate(-5deg); opacity: 0; }
        50% { transform: scale(1.05) rotate(2deg); }
        100% { transform: scale(1) rotate(0deg); opacity: 1; }
    }
    
    .success-box::after {
        content: '🎉';
        position: absolute;
        top: 10px;
        right: 20px;
        font-size: 2rem;
        animation: bounce 1s ease-in-out infinite;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    
    /* Enhanced Button Styling */
    .stButton > button {
        background: linear-gradient(45deg, #667eea, #764ba2, #f093fb);
        background-size: 200% 200%;
        color: white;
        border: none;
        border-radius: 30px;
        padding: 1rem 2.5rem;
        font-weight: 600;
        font-size: 1.2rem;
        transition: all 0.4s ease;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        position: relative;
        overflow: hidden;
        animation: gradientShift 3s ease infinite;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 15px 40px rgba(102, 126, 234, 0.6);
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: all 0.5s;
    }
    
    .stButton > button:hover::before {
        left: 100%;
    }
    
    /* Quick Suggestion Buttons */
    .suggestion-btn {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: white;
        padding: 0.8rem 1.5rem;
        border-radius: 20px;
        margin: 0.3rem;
        transition: all 0.3s ease;
        cursor: pointer;
        font-weight: 500;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
    }
    
    .suggestion-btn:hover {
        background: rgba(255, 255, 255, 0.2);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
    }
    
    /* Text Area Styling */
    .stTextArea > div > div > textarea {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 2px solid rgba(255, 255, 255, 0.2);
        border-radius: 15px;
        color: white;
        padding: 1rem;
        font-size: 1.1rem;
        transition: all 0.3s ease;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: rgba(255, 255, 255, 0.5);
        box-shadow: 0 0 30px rgba(255, 255, 255, 0.2);
        background: rgba(255, 255, 255, 0.15);
    }
    
    .stTextArea > div > div > textarea::placeholder {
        color: rgba(255, 255, 255, 0.7);
    }
    
    /* Select Box Styling */
    .stSelectbox > div > div > select {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        color: white;
        padding: 0.5rem;
    }
    
    /* Loading Animation */
    .loading-container {
        text-align: center;
        padding: 2rem;
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        margin: 1rem 0;
    }
    
    .loading-brain {
        font-size: 4rem;
        animation: brainPulse 1.5s ease-in-out infinite;
        margin-bottom: 1rem;
    }
    
    @keyframes brainPulse {
        0%, 100% { transform: scale(1) rotate(0deg); }
        50% { transform: scale(1.2) rotate(5deg); }
    }
    
    .loading-text {
        color: white;
        font-size: 1.2rem;
        font-weight: 500;
        margin-top: 1rem;
    }
    
    /* Footer Enhancement */
    .footer-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 15px;
        padding: 1.5rem;
        text-align: center;
        color: white;
        transition: all 0.3s ease;
        margin: 0.5rem;
    }
    
    .footer-card:hover {
        transform: translateY(-5px);
        background: rgba(255, 255, 255, 0.15);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
    }
    
    /* History Section */
    .history-item {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(5px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        color: white;
        transition: all 0.3s ease;
    }
    
    .history-item:hover {
        background: rgba(255, 255, 255, 0.1);
        transform: translateX(5px);
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .main-header {
            font-size: 2.5rem;
        }
        
        .main .block-container {
            padding: 1.5rem;
            margin-top: 0.5rem;
        }
        
        .answer-box {
            padding: 1.5rem;
        }
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.3);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.5);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'audio_files' not in st.session_state:
    st.session_state.audio_files = []

# Language configuration
LANGUAGES = {
    "English": {"code": "en", "flag": "🇺🇸", "name": "English"},
    "Hindi": {"code": "hi", "flag": "🇮🇳", "name": "हिंदी"},
    "Marathi": {"code": "mr", "flag": "🇮🇳", "name": "मराठी"},
    "Tamil": {"code": "ta", "flag": "🇮🇳", "name": "தமிழ்"}
}

# Translation functions
def translate_text(text, target_lang="en", source_lang="auto"):
    """Translate text using Google Translator with fallback"""
    try:
        if target_lang == "en" and source_lang == "en":
            return text
        
        # Use GoogleTranslator (more reliable)
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        result = translator.translate(text)
        return result
    except Exception as e:
        st.error(f"Translation failed: {str(e)}")
        return text

def generate_speech(text, lang_code="en"):
    """Generate speech using gTTS and return file path"""
    try:
        # Clean up previous audio files
        for audio_file in st.session_state.audio_files:
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
            except:
                pass
        st.session_state.audio_files = []
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_file.close()
        
        # Generate speech
        tts = gTTS(text=text, lang=lang_code, slow=False)
        tts.save(temp_file.name)
        
        # Store file reference for cleanup
        st.session_state.audio_files.append(temp_file.name)
        
        return temp_file.name
    except Exception as e:
        st.error(f"Speech generation failed: {str(e)}")
        return None

def get_audio_player(audio_file, text="🎵 Play Response"):
    """Create an audio player widget"""
    if audio_file and os.path.exists(audio_file):
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()
        
        # Create audio player with custom styling
        st.markdown(f"""
        <div class="audio-player">
            <div class="audio-controls">
                <span>🎵</span>
                <span>{text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.audio(audio_bytes, format="audio/mp3")
        return True
    return False

# Header with enhanced styling
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h1 class="main-header">🧠 PolicyGenius X</h1>
    <p class="sub-header">🌍 Multilingual AI Insurance Assistant | Built for HackRx 6.0</p>
</div>
""", unsafe_allow_html=True)

# Language Selector with enhanced UI
st.markdown('<div class="language-selector">', unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("### 🌐 Select Your Language")
    selected_lang = st.selectbox(
        "Choose your preferred language:",
        list(LANGUAGES.keys()),
        format_func=lambda x: f"{LANGUAGES[x]['flag']} {LANGUAGES[x]['name']}",
        key="language_selector"
    )
    
    lang_code = LANGUAGES[selected_lang]["code"]
    st.markdown(f"**Selected:** {LANGUAGES[selected_lang]['flag']} {LANGUAGES[selected_lang]['name']}")
st.markdown('</div>', unsafe_allow_html=True)

# Main Interface
st.markdown("---")

# API Configuration
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### 💬 Ask Your Insurance Question")
with col2:
    api_base = st.selectbox("API:", ["Local (8000)", "Custom"], index=0)
    if api_base == "Local (8000)":
        api_url = "http://localhost:8000"
    else:
        api_url = st.text_input("API URL:", "http://localhost:8000")

# Question Input with language support
if selected_lang == "English":
    placeholder_text = "Example: What is the waiting period for pre-existing diseases?"
elif selected_lang == "Hindi":
    placeholder_text = "उदाहरण: पहले से मौजूद बीमारियों के लिए प्रतीक्षा अवधि क्या है?"
elif selected_lang == "Marathi":
    placeholder_text = "उदाहरण: आधीपासून असलेल्या आजारांसाठी प्रतीक्षा कालावधी काय आहे?"
else:  # Tamil
    placeholder_text = "உदாहரণம்: ஏற்கனவே உள்ள நோய்களுக்கான காத்திருப்பு காலம் என்ன?"

query = st.text_area(
    f"Your Question in {LANGUAGES[selected_lang]['name']}:",
    height=120,
    placeholder=placeholder_text,
    help=f"Ask any question about insurance policies in {LANGUAGES[selected_lang]['name']}. It will be automatically translated for processing."
)

# Quick suggestions in selected language
st.markdown("**💡 Quick Questions:**")
if selected_lang == "English":
    suggestions = [
        "🏥 What treatments are covered?",
        "⏱️ What are the waiting periods?", 
        "🚫 What is excluded from coverage?",
        "💰 How do I file a claim?"
    ]
elif selected_lang == "Hindi":
    suggestions = [
        "🏥 कौन सा उपचार कवर है?",
        "⏱️ प्रतीक्षा अवधि क्या है?",
        "🚫 कवरेज से क्या बाहर है?",
        "💰 क्लेम कैसे फाइल करें?"
    ]
elif selected_lang == "Marathi":
    suggestions = [
        "🏥 कोणते उपचार समाविष्ट आहेत?",
        "⏱️ प्रतीक्षा कालावधी काय आहे?",
        "🚫 कव्हरेजमधून काय वगळले आहे?",
        "💰 दावा कसा दाखल करावा?"
    ]
else:  # Tamil
    suggestions = [
        "🏥 என்ன சிகிச்சைகள் உள்ளடக்கப்பட்டுள்ளன?",
        "⏱️ காத்திருப்பு காலங்கள் என்ன?",
        "🚫 கவரேஜிலிருந்து என்ன விலக்கப்பட்டுள்ளது?",
        "💰 உரிமைகோரலை எப்படி தாக்கல் செய்வது?"
    ]

col1, col2, col3, col4 = st.columns(4)
for i, (col, suggestion) in enumerate(zip([col1, col2, col3, col4], suggestions)):
    with col:
        if st.button(suggestion, key=f"suggestion_{i}"):
            st.session_state.suggested_query = suggestion

# Use suggested query if available
if 'suggested_query' in st.session_state and st.session_state.suggested_query:
    query = st.session_state.suggested_query
    st.session_state.suggested_query = ""  # Clear after use

# Document Configuration
with st.expander("📄 Document Settings (Optional)"):
    col1, col2 = st.columns(2)
    with col1:
        document_url = st.text_input(
            "PDF Document URL:",
            value="http://localhost:8080/Arogya%20Sanjeevani%20Policy%20-%20CIN%20-%20U10200WB1906GOI001713%201.pdf"
        )
    with col2:
        auth_token = st.text_input(
            "Auth Token:",
            value="hackrx2024_token",
            type="password"
        )

# Enhanced Ask Button
st.markdown("<br>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    ask_button = st.button("🚀 ASK POLICYGENIUS X", type="primary", use_container_width=True)

# Process Query with Translation and TTS
if ask_button and query.strip():
    # Enhanced loading animation
    loading_placeholder = st.empty()
    with loading_placeholder:
        st.markdown("""
        <div class="loading-container">
            <div class="loading-brain">🧠</div>
            <div class="loading-text">AI is analyzing your question...</div>
            <div style="margin-top: 1rem; color: rgba(255,255,255,0.8);">
                🌐 Translating • 🔍 Processing • 🤖 Generating Response
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    start_time = time.time()
    
    try:
        # Step 1: Translate query to English if needed
        original_query = query
        if lang_code != "en":
            status_text.text("🌐 Translating your question to English...")
            progress_bar.progress(20)
            time.sleep(0.5)
            query_english = translate_text(query, target_lang="en", source_lang=lang_code)
        else:
            query_english = query
        
        # Step 2: Process with API
        status_text.text("🔍 Processing document...")
        progress_bar.progress(40)
        time.sleep(0.5)
        
        status_text.text("🧠 AI analyzing content...")
        progress_bar.progress(60)
        time.sleep(0.5)
        
        status_text.text("⚡ Generating response...")
        progress_bar.progress(80)
        
        # Make API call
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(
            f"{api_url}/hackrx/run",
            headers=headers,
            json={
                "documents": document_url,
                "questions": [query_english]
            },
            timeout=60
        )
        
        progress_bar.progress(100)
        response_time = time.time() - start_time
        
        # Clear loading elements
        loading_placeholder.empty()
        progress_bar.empty()
        status_text.empty()
        
        if response.status_code == 200:
            result = response.json()
            
            # Success notification with celebration
            st.markdown(f"""
            <div class="success-box">
                <strong>🎉 Query Processed Successfully!</strong><br>
                Response Time: {response_time:.2f}s | Language: {LANGUAGES[selected_lang]['flag']} {LANGUAGES[selected_lang]['name']}
            </div>
            """, unsafe_allow_html=True)
            
            # Display Answer(s) with translation and TTS
            answers = result.get('answers', [])
            if answers:
                st.markdown("### 🤖 AI Response")
                
                for i, answer_english in enumerate(answers):
                    # Step 3: Translate answer to selected language
                    if lang_code != "en":
                        answer_translated = translate_text(answer_english, target_lang=lang_code, source_lang="en")
                    else:
                        answer_translated = answer_english
                    
                    # Step 4: Generate speech
                    audio_file = generate_speech(answer_translated, lang_code)
                    
                    # Display answer with enhanced styling
                    st.markdown(f"""
                    <div class="answer-box">
                        <div class="answer-content">
                            <h4 style="margin-top: 0; color: white; display: flex; align-items: center; justify-content: space-between;">
                                <span>🧠 PolicyGenius X Says:</span>
                                <span style="font-size: 0.8rem; opacity: 0.8;">{LANGUAGES[selected_lang]['flag']} {LANGUAGES[selected_lang]['name']}</span>
                            </h4>
                            <div style="font-size: 1.2rem; line-height: 1.8; margin-bottom: 1rem;">
                                {answer_translated}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Audio player
                    if audio_file:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            get_audio_player(audio_file, f"🎵 Listen in {LANGUAGES[selected_lang]['name']}")
                        with col2:
                            st.markdown(f"""
                            <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px; text-align: center; color: white;">
                                <div style="font-size: 1.5rem;">🎧</div>
                                <div style="font-size: 0.9rem;">Audio Ready</div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Show original English if translated
                    if lang_code != "en":
                        with st.expander("🇺🇸 View Original English Response"):
                            st.markdown(f"""
                            <div style="background: rgba(255,255,255,0.1); padding: 1.5rem; border-radius: 10px; color: white;">
                                {answer_english}
                            </div>
                            """, unsafe_allow_html=True)
                
                # Source Information
                source_chunks = result.get('source_chunks', [])
                if source_chunks:
                    with st.expander(f"📚 View Sources ({len(source_chunks)} found)"):
                        for i, chunk in enumerate(source_chunks[:3]):
                            st.markdown(f"**Source {i+1}** (Relevance: {chunk.get('score', 0):.3f})")
                            st.text(chunk.get('text', '')[:300] + "...")
                            st.markdown("---")
                
                # Store in history
                st.session_state.query_history.append({
                    'original_question': original_query,
                    'english_question': query_english,
                    'answer': answer_translated,
                    'language': selected_lang,
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'response_time': response_time
                })
                
            else:
                st.error("❌ No answer received from AI")
                
        else:
            st.error(f"❌ API Error: {response.status_code}")
            st.code(response.text)
            
    except requests.exceptions.Timeout:
        loading_placeholder.empty()
        progress_bar.empty()
        status_text.empty()
        st.error("⏰ Request timed out. Please try again.")
    except Exception as e:
        loading_placeholder.empty()
        progress_bar.empty()
        status_text.empty()
        st.error(f"💥 Error: {str(e)}")

elif ask_button and not query.strip():
    st.warning("⚠️ Please enter a question!")

# Query History with multilingual support
if st.session_state.query_history:
    st.markdown("---")
    st.markdown("### 📝 Recent Questions")
    
    # Show last 3 queries
    for i, item in enumerate(st.session_state.query_history[-3:]):
        with st.expander(f"Q{len(st.session_state.query_history)-2+i}: {item['original_question'][:60]}... ({item['language']})"):
            st.markdown(f"""
            <div class="history-item">
                <strong>🌐 Language:</strong> {LANGUAGES[item['language']]['flag']} {item['language']}<br>
                <strong>❓ Question:</strong> {item['original_question']}<br>
                <strong>🤖 Answer:</strong> {item['answer']}<br>
                <strong>⏰ Time:</strong> {item['time']} (Response: {item['response_time']:.2f}s)
            </div>
            """, unsafe_allow_html=True)

# Enhanced Footer
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="footer-card">
        <h4>🏆 HackRx 6.0</h4>
        <p>Competition Ready!</p>
        <div style="margin-top: 0.5rem;">🥇 Advanced Features</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="footer-card">
        <h4>🌍 Multilingual</h4>
        <p>4 Languages Supported</p>
        <div style="margin-top: 0.5rem;">🇺🇸 🇮🇳 Voice Support</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="footer-card">
        <h4>🤖 AI Powered</h4>
        <p>Gemini + Translation</p>
        <div style="margin-top: 0.5rem;">⚡ Sub-10s Response</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="footer-card">
        <h4>🎵 Voice Ready</h4>
        <p>Text-to-Speech</p>
        <div style="margin-top: 0.5rem;">🎧 Audio Responses</div>
    </div>
    """, unsafe_allow_html=True)
