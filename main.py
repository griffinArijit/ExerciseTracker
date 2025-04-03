import cv2
import streamlit as st
import mediapipe as mp
from pymongo import MongoClient
from datetime import datetime, date
from urllib.parse import quote_plus
import os
import certifi
from utils import *
from body_part_angle import BodyPartAngle
from types_of_exercise import TypeOfExercise

# === Custom CSS Injection ===
def inject_custom_css():
    st.markdown("""
    <style>
        /* Your existing CSS styles */
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# === Secure MongoDB Connection ===
@st.cache_resource
def init_mongo_connection():
    try:
        username = os.getenv("MONGO_USER", "Amritesh")
        password = os.getenv("MONGO_PASS", "OpPgCVoOPpakzgoc")
        
        if not username or not password:
            st.error("MongoDB credentials not configured")
            return None

        connection_string = (
            f"mongodb+srv://{quote_plus(username)}:{quote_plus(password)}@"
            "cluster0.rdwmp.mongodb.net/exercise_app?"
            "retryWrites=true&w=majority&"
            "tls=true&"
            "tlsCAFile={certifi.where()}&"
            "connectTimeoutMS=30000"
        )

        client = MongoClient(connection_string)
        client.admin.command('ping')  # Test connection
        return client.exercise_app
    except Exception as e:
        st.error(f"Failed to connect to database: {str(e)}")
        return None

# Initialize MongoDB connection
if 'db' not in st.session_state:
    st.session_state.db = init_mongo_connection()
    if st.session_state.db is None:
        st.stop()  # Stop execution if connection failed

# === Check for User ID ===
user_id = st.query_params.get("user_id")
if not user_id:
    st.error("User ID not provided in URL parameters")
    st.stop()

# === Initialize Session State ===
if 'exercise_summary' not in st.session_state:
    try:
        # Check if user exists and has data for today
        existing_user = st.session_state.db.users.find_one({"user_id": user_id})
        today_str = date.today().isoformat()

        if existing_user:
            # Find today's summary if it exists
            today_summary = next(
                (item for item in existing_user.get("exercise_summary", []) 
                if item["date"] == today_str),
                None
            )
            
            if today_summary:
                st.session_state.exercise_summary = today_summary
            else:
                st.session_state.exercise_summary = {
                    "date": today_str,
                    "sit-up": 0, "pull-up": 0, 
                    "push-up": 0, "squat": 0, "walk": 0
                }
        else:
            st.session_state.exercise_summary = {
                "date": today_str,
                "sit-up": 0, "pull-up": 0,
                "push-up": 0, "squat": 0, "walk": 0
            }
            st.session_state.db.users.insert_one({
                "user_id": user_id,
                "exercise_summary": [st.session_state.exercise_summary]
            })
    except Exception as e:
        st.error(f"Failed to initialize user data: {str(e)}")
        st.stop()

# Rest of your application code...
