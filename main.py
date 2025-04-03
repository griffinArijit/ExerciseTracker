import cv2
import streamlit as st
import mediapipe as mp
import numpy as np
from PIL import Image
from pymongo import MongoClient
from datetime import date
import os
from utils import *
from body_part_angle import BodyPartAngle
from types_of_exercise import TypeOfExercise

# === Custom CSS for UI Styling ===
def inject_custom_css():
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #000000; }
        [data-testid="stSidebar"] { background-color: #121212 !important; border-right: 1px solid #FF6B00; }
        h1, h2, h3, h4, h5, h6 { color: #FF6B00 !important; }
        p, .stMarkdown { color: #FFFFFF !important; }
        .stButton>button { background-color: #FF6B00 !important; color: #000000 !important; border: none !important; font-weight: bold; }
        .stButton>button:hover { background-color: #FF8C00 !important; color: #000000 !important; }
        .stSelectbox>div>div>select, .stTextInput>div>div>input { background-color: #121212 !important; color: #FF6B00 !important; border: 1px solid #FF6B00 !important; }
        .stAlert { background-color: rgba(255, 107, 0, 0.2) !important; border-left: 4px solid #FF6B00 !important; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# === MongoDB Connection ===
from urllib.parse import quote_plus  # Add this import

# === MongoDB Connection ===
try:
    username = quote_plus("arijitpal")  # Encode username
    password = quote_plus("Arijitpal@987")  # Encode password
    connection_string = f"mongodb+srv://{username}:{password}@cluster0.aiqxn.mongodb.net/exercise_app?retryWrites=true&w=majority"

    client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
    client.server_info()  # Test connection
    db = client["exercise_app"]
    collection = db["exercise_data"]
except Exception as e:
    st.error(f"Failed to connect to MongoDB: {str(e)}")
    st.stop()

# === Get User ID from Query Params ===
user_id = st.query_params.get("user_id", None)
if not user_id:
    st.error("User ID not provided. Please access the link with ?user_id=yourID.")
    st.stop()

# === Initialize Session State ===
today_str = date.today().isoformat()

if 'detection_active' not in st.session_state:
    st.session_state.detection_active = False
if 'cap' not in st.session_state:
    st.session_state.cap = None
if 'exercise_summary' not in st.session_state:
    existing_user = collection.find_one({"user_id": user_id})
    
    if existing_user:
        today_summary = next((item for item in existing_user.get("exercise_summary", []) if item["date"] == today_str), None)
        if today_summary:
            st.session_state.exercise_summary = today_summary
        else:
            st.session_state.exercise_summary = {"date": today_str, "sit-up": 0, "pull-up": 0, "push-up": 0, "squat": 0, "walk": 0}
    else:
        st.session_state.exercise_summary = {"date": today_str, "sit-up": 0, "pull-up": 0, "push-up": 0, "squat": 0, "walk": 0}
        collection.insert_one({"user_id": user_id, "exercise_summary": [st.session_state.exercise_summary]})

# === Sidebar UI ===
exercise_type = st.sidebar.selectbox("Select Exercise Type", ["sit-up", "pull-up", "push-up", "squat", "walk"])
video_source = st.sidebar.text_input("Enter Video Source (default webcam)", "0")

frame_placeholder = st.empty()

# === Function: Start Detection ===
def start_detection():
    st.session_state.detection_active = True
    counter = st.session_state.exercise_summary.get(exercise_type, 0)
    status = True

    # Streamlit Cloud Warning
    if "STREAMLIT_SERVER_RUNNING" in os.environ:
        st.warning("Streamlit Cloud does not support OpenCV webcam access. Use st.camera_input() instead.")
        return

    # Initialize Video Capture
    st.session_state.cap = cv2.VideoCapture(int(video_source) if video_source.isdigit() else video_source)
    if not st.session_state.cap.isOpened():
        st.error("Failed to access video source. Ensure webcam is not in use by another application.")
        return

    st.session_state.cap.set(3, 800)
    st.session_state.cap.set(4, 480)

    mp_drawing = mp.solutions.drawing_utils
    mp_pose = mp.solutions.pose

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while st.session_state.detection_active:
            ret, frame = st.session_state.cap.read()
            if not ret:
                st.error("Failed to read video source.")
                break

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(frame)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            try:
                landmarks = results.pose_landmarks.landmark
                counter, status = TypeOfExercise(landmarks).calculate_exercise(exercise_type, counter, status)
            except:
                pass

            st.session_state.exercise_summary[exercise_type] = counter
            frame = score_table(exercise_type, frame, counter, status)

            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                      mp_drawing.DrawingSpec(color=(255, 255, 255)),
                                      mp_drawing.DrawingSpec(color=(174, 139, 45)))

            frame_placeholder.image(frame, channels="BGR", use_container_width=True)

# === Function: Stop Detection ===
def stop_detection():
    st.session_state.detection_active = False
    if st.session_state.cap:
        st.session_state.cap.release()
    cv2.destroyAllWindows()
    frame_placeholder.empty()

# === Function: End Session & Save Data ===
def end_session():
    stop_detection()
    
    existing = collection.find_one({"user_id": user_id})
    if existing:
        today_entry_exists = any(entry.get("date") == today_str for entry in existing.get("exercise_summary", []))
        if today_entry_exists:
            collection.update_one({"user_id": user_id, "exercise_summary.date": today_str},
                                  {"$set": {"exercise_summary.$": st.session_state.exercise_summary}})
        else:
            collection.update_one({"user_id": user_id}, {"$push": {"exercise_summary": st.session_state.exercise_summary}})
    else:
        collection.insert_one({"user_id": user_id, "exercise_summary": [st.session_state.exercise_summary]})

    st.sidebar.markdown("### Today's Summary")
    for ex, reps in st.session_state.exercise_summary.items():
        if ex != "date":
            st.sidebar.markdown(f"- *{ex.capitalize()}*: {reps} reps")

# === Buttons ===
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

if st.session_state.detection_active:
    st.success("Detection is running...")
else:
    st.info("Detection is stopped.")
