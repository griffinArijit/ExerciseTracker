import streamlit as st
import mediapipe as mp
import cv2
import numpy as np
from pymongo import MongoClient
from datetime import date
from urllib.parse import quote_plus
from types_of_exercise import TypeOfExercise
from utils import *

# === Inject Custom CSS ===
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

# === User Authentication (via URL) ===
user_id = st.query_params.get("user_id", None)
if not user_id:
    st.error("User ID not provided. Please access the link with ?user_id=yourID")
    st.stop()

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

# === Initialize Session State ===
today_str = date.today().isoformat()

if "exercise_summary" not in st.session_state:
    existing_user = collection.find_one({"user_id": user_id})
    if existing_user:
        today_summary = next(
            (item for item in existing_user.get("exercise_summary", []) if item["date"] == today_str), None
        )
        if today_summary:
            st.session_state.exercise_summary = today_summary
        else:
            st.session_state.exercise_summary = {"date": today_str, "sit-up": 0, "pull-up": 0, "push-up": 0, "squat": 0, "walk": 0}
    else:
        st.session_state.exercise_summary = {"date": today_str, "sit-up": 0, "pull-up": 0, "push-up": 0, "squat": 0, "walk": 0}
        collection.insert_one({"user_id": user_id, "exercise_summary": [st.session_state.exercise_summary]})

# === Sidebar for Exercise Selection ===
exercise_type = st.sidebar.selectbox("Select Exercise Type", ["sit-up", "pull-up", "push-up", "squat", "walk"])
video_source = st.sidebar.radio("Choose Input Source", ["Camera", "Upload Video"])

frame_placeholder = st.empty()

# === Start Detection ===
def start_detection():
    st.session_state.detection_active = True
    counter = st.session_state.exercise_summary.get(exercise_type, 0)
    status = True

    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils

    if video_source == "Camera":
        image = st.camera_input("Take a Picture")
        if image:
            frame = np.array(bytearray(image.read()), dtype=np.uint8)
            frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
    else:
        uploaded_video = st.file_uploader("Upload a Video", type=["mp4", "mov", "avi"])
        if uploaded_video:
            st.video(uploaded_video)

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while st.session_state.detection_active:
            if video_source == "Camera" and image:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame.flags.writeable = False
                results = pose.process(frame)
                frame.flags.writeable = True
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

                try:
                    landmarks = results.pose_landmarks.landmark
                    counter, status = TypeOfExercise(landmarks).calculate_exercise(exercise_type, counter, status)
                except Exception:
                    pass

                st.session_state.exercise_summary[exercise_type] = counter
                frame = score_table(exercise_type, frame, counter, status)
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

                frame_placeholder.image(frame, channels="BGR", use_container_width=True)

# === Stop Detection ===
def stop_detection():
    st.session_state.detection_active = False
    frame_placeholder.empty()

    existing = collection.find_one({"user_id": user_id})
    if existing:
        today_entry_exists = any(entry.get("date") == today_str for entry in existing.get("exercise_summary", []))
        if today_entry_exists:
            collection.update_one(
                {"user_id": user_id, "exercise_summary.date": today_str},
                {"$set": {"exercise_summary.$": st.session_state.exercise_summary}}
            )
        else:
            collection.update_one({"user_id": user_id}, {"$push": {"exercise_summary": st.session_state.exercise_summary}})
    else:
        collection.insert_one({"user_id": user_id, "exercise_summary": [st.session_state.exercise_summary]})

    summary_md = "### Today's Exercise Summary\n"
    for ex, reps in st.session_state.exercise_summary.items():
        if ex != "date":
            summary_md += f"- {ex.capitalize()}: {reps} reps\n"
    st.sidebar.markdown(summary_md)

# === End Session ===
def end_session():
    st.session_state.detection_active = False
    frame_placeholder.empty()

    try:
        user_data = collection.find_one({"user_id": user_id})
        if user_data and "exercise_summary" in user_data:
            session_md = "### Your Exercise History\n"
            for summary in sorted(user_data["exercise_summary"], key=lambda x: x["date"], reverse=True):
                session_md += f"{summary['date']}\n"
                for ex, reps in summary.items():
                    if ex != "date" and reps > 0:
                        session_md += f"- {ex.capitalize()}: {reps} reps\n"
                session_md += "\n"
            st.sidebar.markdown(session_md)
            st.success("Session Ended. Check the sidebar for your complete exercise history.")
    except Exception as e:
        st.error(f"Failed to fetch exercise history: {e}")

# === Button Controls ===
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Start Detection") and not st.session_state.get("detection_active", False):
        start_detection()

with col2:
    if st.button("Stop Detection") and st.session_state.get("detection_active", False):
        stop_detection()

with col3:
    if st.button("End Session"):
        end_session()

# === Status Display ===
if st.session_state.get("detection_active", False):
    st.success("Detection is running...")
else:
    st.info("Detection is stopped. Press 'Start Detection' to begin.")
