 import cv2
import streamlit as st
import mediapipe as mp
from pymongo import MongoClient
from datetime import date
import os
from urllib.parse import quote_plus

# Custom CSS for Styling
def inject_custom_css():
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #000000; }
        [data-testid="stSidebar"] { background-color: #121212 !important; border-right: 1px solid #FF6B00; }
        h1, h2, h3, h4, h5, h6 { color: #FF6B00 !important; }
        p, .stMarkdown { color: #FFFFFF !important; }
        .stButton>button { background-color: #FF6B00 !important; color: #000000 !important; border: none !important; font-weight: bold; }
        .stButton>button:hover { background-color: #FF8C00 !important; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# === Check User ID from URL ===
user_id = st.query_params.get("user_id")
if not user_id:
    st.error("User ID not provided. Please access the link with ?user_id=yourID.")
    st.stop()

# === MongoDB Connection ===
try:
    username = "arijitpal"
    password = "Arijitpal@987"
    encoded_username = quote_plus(username)
    encoded_password = quote_plus(password)
    
    connection_string = (
        f"mongodb+srv://{encoded_username}:{encoded_password}@"
        f"cluster0.aiqxn.mongodb.net/exercise_app?"
        f"retryWrites=true&w=majority&tls=true"
    )
    
    client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
    client.server_info()  # Test connection
    db = client["exercise_app"]
    collection = db["exercise_data"]

except Exception as e:
    st.error(f"Failed to connect to MongoDB: {str(e)}")
    st.stop()

# === Session State Management ===
today_str = date.today().isoformat()
if 'detection_active' not in st.session_state:
    st.session_state.detection_active = False
if 'cap' not in st.session_state:
    st.session_state.cap = None

# === Sidebar Controls ===
exercise_type = st.sidebar.selectbox("Select Exercise Type", ["sit-up", "pull-up", "push-up", "squat", "walk"])
video_source = st.sidebar.text_input("Enter Video Source (optional)", "0")

frame_placeholder = st.empty()

# === Start Detection Function ===
def start_detection():
    st.session_state.detection_active = True
    st.session_state.cap = cv2.VideoCapture(int(video_source) if video_source.isdigit() else video_source)
    
    if not st.session_state.cap.isOpened():
        st.error("Failed to access video source.")
        return

    while st.session_state.detection_active and st.session_state.cap.isOpened():
        ret, frame = st.session_state.cap.read()
        if not ret:
            st.error("Failed to capture frame.")
            break
        
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_placeholder.image(frame, channels="RGB", use_column_width=True)

# === Stop Detection Function ===
def stop_detection():
    st.session_state.detection_active = False
    if 'cap' in st.session_state and st.session_state.cap:
        st.session_state.cap.release()
        st.session_state.cap = None
    if not os.getenv("STREAMLIT_SERVER_RUNNING"):
        cv2.destroyAllWindows()
    frame_placeholder.empty()

# === End Session Function ===
def end_session():
    stop_detection()
    st.success("Session Ended.")

# === Button Controls ===
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Start Detection") and not st.session_state.detection_active:
        start_detection()

with col2:
    if st.button("Stop Detection") and st.session_state.detection_active:
        stop_detection()

with col3:
    if st.button("End Session"):
        end_session()

# Display Status
if st.session_state.detection_active:
    st.success("Detection is running...")
else:
    st.info("Detection is stopped. Press 'Start Detection' to begin.")
