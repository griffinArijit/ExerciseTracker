 
import cv2
import streamlit as st
import mediapipe as mp
from pymongo import MongoClient
from datetime import date
from utils import *
from body_part_angle import BodyPartAngle
from types_of_exercise import TypeOfExercise

# === Custom CSS Injection ===
def inject_custom_css():
    st.markdown("""
    <style>
        /* Main background */
        [data-testid="stAppViewContainer"] {
            background-color: #000000;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #121212 !important;
            border-right: 1px solid #FF6B00;
        }
        
        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            color: #FF6B00 !important;
        }
        
        /* Text */
        p, .stMarkdown {
            color: #FFFFFF !important;
        }
        
        /* Buttons */
        .stButton>button {
            background-color: #FF6B00 !important;
            color: #000000 !important;
            border: none !important;
            font-weight: bold;
        }
        
        .stButton>button:hover {
            background-color: #FF8C00 !important;
            color: #000000 !important;
        }
        
        /* Select boxes */
        .stSelectbox>div>div>select {
            background-color: #121212 !important;
            color: #FF6B00 !important;
        }
        
        /* Text inputs */
        .stTextInput>div>div>input {
            background-color: #121212 !important;
            color: #FF6B00 !important;
            border: 1px solid #FF6B00 !important;
        }
        
        /* Status messages */
        .stAlert {
            background-color: rgba(255, 107, 0, 0.2) !important;
            border-left: 4px solid #FF6B00 !important;
        }
    </style>
    """, unsafe_allow_html=True)

# Call the CSS injection at the start
inject_custom_css()

#=== Check for Special User ID in Query Parameters ===
user_id = st.query_params["user_id"]
if not user_id:
    st.error("User ID not provided. Please access the link with a valid user id (e.g. ?user_id=yourID).")
    st.stop()

# === Connect to MongoDB ===
from urllib.parse import quote_plus

# === Connect to MongoDB ===
from pymongo import MongoClient
from urllib.parse import quote_plus
import ssl

username = "Amritesh"
password = "OpPgCVoOPpakzgoc"
encoded_username = quote_plus(username)
encoded_password = quote_plus(password)

connection_string = (
    f"mongodb+srv://{encoded_username}:{encoded_password}@"
    "cluster0.rdwmp.mongodb.net/exercise_app?"
    "retryWrites=true&w=majority&"
    "tls=true&"
    "tlsAllowInvalidCertificates=false&"
    "ssl_cert_reqs=CERT_NONE&"
    "connectTimeoutMS=30000&"
    "socketTimeoutMS=30000"
)

try:
    client = MongoClient(
        connection_string,
        ssl=True,
        ssl_cert_reqs=ssl.CERT_NONE,
        serverSelectionTimeoutMS=30000
    )
    # Test the connection
    client.server_info()
    collection = client.exercise_app
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    


# Get today's date for tracking
today_str = date.today().isoformat()

# === Initialize Session State Variables ===
if 'detection_active' not in st.session_state:
    st.session_state.detection_active = False
if 'cap' not in st.session_state:
    st.session_state.cap = None
if 'exercise_summary' not in st.session_state:
    # Check if user exists and has data for today
    existing_user = collection.find_one({"user_id": user_id})
    
    if existing_user:
        # Find today's summary if it exists
        today_summary = next(
            (item for item in existing_user.get("exercise_summary", []) 
            if item["date"] == today_str),
            None
        )
        
        if today_summary:
            # Case 1: User exists and has data for today - use existing summary
            st.session_state.exercise_summary = today_summary
        else:
            # Case 2: User exists but no data for today - create new empty summary
            st.info(f"Welcome back {user_id}! Starting a new session for today.")
            st.session_state.exercise_summary = {
                "date": today_str,
                "sit-up": 0,
                "pull-up": 0,
                "push-up": 0,
                "squat": 0,
                "walk": 0
            }
    else:
        # Case 3: User doesn't exist - create new user with empty summary for today
        st.info(f"New user detected: {user_id}. Creating your profile.")
        st.session_state.exercise_summary = {
            "date": today_str,
            "sit-up": 0,
            "pull-up": 0,
            "push-up": 0,
            "squat": 0,
            "walk": 0
        }
        collection.insert_one({
            "user_id": user_id,
            "exercise_summary": [st.session_state.exercise_summary]
        })

# Sidebar for Exercise Selection
exercise_type = st.sidebar.selectbox(
    "Select Exercise Type",
    ["sit-up", "pull-up", "push-up", "squat", "walk"]
)

video_source = st.sidebar.text_input("Enter Video Source (optional)", "0")

# Placeholders for video frame display and session summary output
frame_placeholder = st.empty()

def start_detection():
    st.session_state.detection_active = True
    counter = st.session_state.exercise_summary.get(exercise_type, 0)
    status = True

    # Initialize MediaPipe Pose
    mp_drawing = mp.solutions.drawing_utils
    mp_pose = mp.solutions.pose

    # Initialize video capture
    st.session_state.cap = cv2.VideoCapture(int(video_source) if video_source.isdigit() else video_source)
    st.session_state.cap.set(3, 800)  # width
    st.session_state.cap.set(4, 480)  # height

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while st.session_state.detection_active and st.session_state.cap.isOpened():
            ret, frame = st.session_state.cap.read()
            if not ret:
                st.error("Failed to read video source.")
                break

            frame = cv2.resize(frame, (800, 480), interpolation=cv2.INTER_AREA)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame.flags.writeable = False
            results = pose.process(frame)
            frame.flags.writeable = True
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            try:
                landmarks = results.pose_landmarks.landmark
                counter, status = TypeOfExercise(landmarks).calculate_exercise(exercise_type, counter, status)
            except Exception as e:
                pass

            st.session_state.exercise_summary[exercise_type] = counter
            frame = score_table(exercise_type, frame, counter, status)

            mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(255, 255, 255)),
                mp_drawing.DrawingSpec(color=(174, 139, 45))
            )

            frame_placeholder.image(frame, channels="BGR", use_container_width=True)

def stop_detection():
    st.session_state.detection_active = False
    if st.session_state.cap:
        st.session_state.cap.release()
    cv2.destroyAllWindows()
    frame_placeholder.empty()

    # Update MongoDB with today's exercise data
    # collection.update_one(
    #     {"user_id": user_id, "exercise_summary.date": today_str},
    #     {"$set": {"exercise_summary.$": st.session_state.exercise_summary}},
    #     upsert=True
    # )
    # First check if the document exists
existing = collection.find_one({"user_id": user_id})

if existing:
    # Check if today's entry exists
    today_entry_exists = any(
        entry.get("date") == today_str 
        for entry in existing.get("exercise_summary", [])
    )
    
    if today_entry_exists:
        # Update existing entry
        collection.update_one(
            {"user_id": user_id, "exercise_summary.date": today_str},
            {"$set": {"exercise_summary.$": st.session_state.exercise_summary}}
        )
    else:
        # Add new entry to array
        collection.update_one(
            {"user_id": user_id},
            {"$push": {"exercise_summary": st.session_state.exercise_summary}}
        )
else:
    # Create new document with today's entry
    collection.insert_one({
        "user_id": user_id,
        "exercise_summary": [st.session_state.exercise_summary]
    })

    # Display today's summary
    summary_md = "### Today's Exercise Summary\n"
    for ex, reps in st.session_state.exercise_summary.items():
        if ex != "date":
            summary_md += f"- **{ex.capitalize()}**: {reps} reps\n"
    st.sidebar.markdown(summary_md)

def end_session():
    st.session_state.detection_active = False
    if st.session_state.cap:
        st.session_state.cap.release()
    cv2.destroyAllWindows()
    frame_placeholder.empty()

    # Get all exercise data for the user
    user_data = collection.find_one({"user_id": user_id})
    if not user_data or "exercise_summary" not in user_data:
        st.sidebar.warning("No exercise data found for this user.")
        return
    
    session_md = "### Your Exercise History\n"
    for summary in sorted(user_data["exercise_summary"], key=lambda x: x["date"], reverse=True):
        session_md += f"**{summary['date']}**\n"
        for ex, reps in summary.items():
            if ex != "date" and reps > 0:
                session_md += f"- {ex.capitalize()}: {reps} reps\n"
        session_md += "\n"
    
    st.sidebar.markdown(session_md)
    st.success("Session Ended. Check the sidebar for your complete exercise history.")

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

# Display current status
if st.session_state.detection_active:
    st.success("Detection is running...")
else:
    st.info("Detection is stopped. Press 'Start Detection' to begin.")
