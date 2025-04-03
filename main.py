import cv2
import streamlit as st
import mediapipe as mp
from pymongo import MongoClient
from datetime import date
from urllib.parse import quote_plus
import os
import numpy as np

# === Custom CSS for Styling ===
def inject_custom_css():
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #000000; }
        [data-testid="stSidebar"] { background-color: #121212 !important; border-right: 1px solid #FF6B00; }
        h1, h2, h3, h4, h5, h6 { color: #FF6B00 !important; }
        p, .stMarkdown { color: #FFFFFF !important; }
        .stButton>button { background-color: #FF6B00 !important; color: #000000 !important; font-weight: bold; }
        .stButton>button:hover { background-color: #FF8C00 !important; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# === Connect to MongoDB ===
try:
    username = "arijitpal"
    password = "Arijitpal@987"
    encoded_username = quote_plus(username)
    encoded_password = quote_plus(password)
    connection_string = f"mongodb+srv://{encoded_username}:{encoded_password}@cluster0.aiqxn.mongodb.net/exercise_app?retryWrites=true&w=majority"
    
    client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
    client.server_info()  # Test connection
    db = client["exercise_app"]
    collection = db["exercise_data"]
except Exception as e:
    st.error(f"Failed to connect to MongoDB: {str(e)}")
    st.stop()

# === User Session Handling ===
user_id = st.query_params.get("user_id", "guest")
today_str = date.today().isoformat()

# Initialize session state
if 'exercise_summary' not in st.session_state:
    existing_user = collection.find_one({"user_id": user_id})
    st.session_state.exercise_summary = next((item for item in existing_user.get("exercise_summary", []) if item["date"] == today_str), 
                                              {"date": today_str, "sit-up": 0, "pull-up": 0, "push-up": 0, "squat": 0, "walk": 0})

# === Sidebar for Exercise Selection ===
st.sidebar.header("Exercise Settings")
exercise_type = st.sidebar.selectbox("Select Exercise Type", ["sit-up", "pull-up", "push-up", "squat", "walk"])
video_source = st.sidebar.text_input("Enter Video Source (default: webcam)", "0")

# === Video Processing ===
frame_placeholder = st.empty()
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

def start_detection():
    st.session_state.detection_active = True
    cap = cv2.VideoCapture(int(video_source) if video_source.isdigit() else video_source)
    if not cap.isOpened():
        st.error("❌ Failed to access video source. Ensure webcam is not in use.")
        return
    
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while st.session_state.detection_active and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                st.error("❌ Unable to read from camera. Try restarting.")
                break
            
            frame = cv2.cvtColor(cv2.resize(frame, (800, 480)), cv2.COLOR_BGR2RGB)
            results = pose.process(frame)
            
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            frame_placeholder.image(frame, channels="RGB", use_column_width=True)
            if st.button("Stop Detection"):
                break
    
    cap.release()
    cv2.destroyAllWindows()

def stop_detection():
    st.session_state.detection_active = False
    frame_placeholder.empty()
    
# === Buttons ===
if st.button("Start Detection"):
    start_detection()
if st.button("Stop Detection"):
    stop_detection()

# === Streamlit Camera Input (For Deployment) ===
st.sidebar.header("Streamlit Camera Input")
image_file = st.camera_input("Take a picture for tracking")
if image_file is not None:
    file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
    frame = cv2.imdecode(file_bytes, 1)
    frame_placeholder.image(frame, channels="RGB", use_column_width=True)

# === MongoDB Data Update ===
if st.button("Save Session"):
    collection.update_one({"user_id": user_id}, {"$push": {"exercise_summary": st.session_state.exercise_summary}}, upsert=True)
    st.success("✅ Session saved!")
