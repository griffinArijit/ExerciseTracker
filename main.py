import cv2
import streamlit as st
import mediapipe as mp
from pymongo import MongoClient
from datetime import date
from urllib.parse import quote_plus
import os

# === Streamlit UI Setup ===
st.set_page_config(page_title="Exercise Tracker", layout="wide")

# === Custom CSS for Styling ===
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #000000; }
        [data-testid="stSidebar"] { background-color: #121212 !important; border-right: 1px solid #FF6B00; }
        h1, h2, h3, h4, h5, h6 { color: #FF6B00 !important; }
        p, .stMarkdown { color: #FFFFFF !important; }
        .stButton>button { background-color: #FF6B00 !important; color: #000000 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# === MongoDB Connection ===
try:
    username = "arijitpal"
    password = "Arijitpal@987"
    encoded_username = quote_plus(username)
    encoded_password = quote_plus(password)
    connection_string = f"mongodb+srv://{encoded_username}:{encoded_password}@cluster0.aiqxn.mongodb.net/exercise_app?retryWrites=true&w=majority"
    client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
    client.server_info()
    db = client["exercise_app"]
    collection = db["exercise_data"]
except Exception as e:
    st.error(f"Failed to connect to MongoDB: {str(e)}")
    st.stop()

# === Session State Setup ===
if 'detection_active' not in st.session_state:
    st.session_state.detection_active = False
if 'cap' not in st.session_state:
    st.session_state.cap = None
if 'exercise_summary' not in st.session_state:
    st.session_state.exercise_summary = {"date": date.today().isoformat(), "sit-up": 0, "pull-up": 0, "push-up": 0, "squat": 0, "walk": 0}

# === Sidebar for Exercise Selection ===
exercise_type = st.sidebar.selectbox("Select Exercise Type", ["sit-up", "pull-up", "push-up", "squat", "walk"])
video_source = st.sidebar.text_input("Enter Video Source (optional)", "0")
frame_placeholder = st.empty()

# === Start Detection ===
def start_detection():
    st.session_state.detection_active = True
    cap = cv2.VideoCapture(int(video_source) if video_source.isdigit() else video_source)
    if not cap.isOpened():
        st.error("Failed to access video source.")
        return
    
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    
    while st.session_state.detection_active:
        ret, frame = cap.read()
        if not ret:
            st.error("Failed to read video frame.")
            break
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        frame_placeholder.image(frame, channels="BGR", use_container_width=True)
    
    cap.release()
    cv2.destroyAllWindows()
    
# === Stop Detection ===
def stop_detection():
    st.session_state.detection_active = False
    frame_placeholder.empty()

# === Button Controls ===
col1, col2 = st.columns(2)
with col1:
    if st.button("Start Detection") and not st.session_state.detection_active:
        start_detection()
with col2:
    if st.button("Stop Detection") and st.session_state.detection_active:
        stop_detection()

# Display current status
if st.session_state.detection_active:
    st.success("Detection is running...")
else:
    st.info("Detection is stopped. Press 'Start Detection' to begin.")
