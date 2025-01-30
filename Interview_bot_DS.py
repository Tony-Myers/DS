import streamlit as st
from openai import OpenAI  # Ensure this is the correct package name if it exists
import pandas as pd
import requests
import re
import tiktoken
import os
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_ORIENT
from docx.shared import Pt, Inches, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import nsdecls
from io import BytesIO, StringIO
from PyPDF2 import PdfReader

# Configuration
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
ALLOWED_EXTENSIONS = ["docx", "pdf"]
MAX_TOKENS = 7000
PROMPT_BUFFER = 1000

# Initialize encoding
try:
    encoding = tiktoken.encoding_for_model("deepseek-chat")
except KeyError:
    encoding = tiktoken.get_encoding("cl100k_base")

def count_tokens(text):
    return len(encoding.encode(text))

def truncate_text(text, max_tokens):
    tokens = encoding.encode(text)
    return encoding.decode(tokens[:max_tokens]) if len(tokens) > max_tokens else text

def call_deepseek_api(prompt, system_prompt):
    headers = {
        "Authorization": f"Bearer {st.secrets['DEEPSEEK_API_KEY']}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-reasoner",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 3000
    }
    
    response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
    response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code
    return response.json()['choices'][0]['message']['content']

def generate_response(prompt, conversation_history=None):
    try:
        if conversation_history is None:
            conversation_history = []

        system_content = """You are an experienced and considerate interviewer in higher education, focusing on AI applications. Use British English in your responses, including spellings like 'democratised'. Ensure your responses are complete and not truncated.
        After each user response, provide brief feedback and ask a relevant follow-up question based on their answer. Tailor your questions to the user's previous responses, avoiding repetition and exploring areas they haven't covered. Be adaptive and create a natural flow of conversation."""

        messages = [
            {"role": "system", "content": system_content},
            *conversation_history[-6:],  # Include the last 6 exchanges for more context
            {"role": "user", "content": prompt}
        ]

        response = call_deepseek_api(prompt, system_content)
        return response

    except Exception as e:
        return f"An error occurred in generate_response: {str(e)}"

def get_transcript_download_link(conversation):
    df = pd.DataFrame(conversation)
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="interview_transcript.csv">Download Transcript</a>'
    return href

def main():
    # Password authentication
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        password = st.text_input("Enter password to access the interview app:", type="password")
        if st.button("Submit"):
            if password == PASSWORD:  # Ensure you have defined PASSWORD correctly
                st.session_state.authenticated = True
                st.success("Access granted.")
            else:
                st.error("Incorrect password.")
        return

    # Interview app content (only shown if authenticated)
    st.title("AI Interview Bot")

    if "conversation" not in st.session_state:
        st.session_state.conversation = []
    if "current_question" not in st.session_state:
        st.session_state.current_question = "Let's begin the interview. Can you please introduce yourself, your role in higher education, and your interest in AI?"
    if "submitted" not in st.session_state:
        st.session_state.submitted = False

    consent = st.checkbox("I have read the information sheet and give my consent to participate in this interview.")

    if consent:
        st.write(st.session_state.current_question)

        user_answer = st.text_area("Your response:", key=f"user_input_{len(st.session_state.conversation)}")

        # Progress bar with a label indicating interview progress
        completed_questions = len([entry for entry in st.session_state.conversation if entry['role'] == "user"])
        total_questions = len(interview_topics)
        progress_percentage = completed_questions / total_questions
        st.write(f"**Interview Progress: {completed_questions} out of {total_questions} questions answered**")
        st.progress(progress_percentage)

        if st.button("Submit Answer"):
            if user_answer:
                # Add user's answer to conversation history
                st.session_state.conversation.append({"role": "user", "content": user_answer})
                
                # Generate AI response
                ai_prompt = f"User's answer: {user_answer}\nProvide feedback and ask a follow-up question."
                ai_response = generate_response(ai_prompt, st.session_state.conversation)
                
                # Add AI's response to conversation history
                st.session_state.conversation.append({"role": "assistant", "content": ai_response})
                
                # Update current question with AI's follow-up
                st.session_state.current_question = ai_response
                
                # Set submitted flag to true
                st.session_state.submitted = True
                
                st.experimental_rerun()
            else:
                st.warning("Please provide an answer before submitting.")

        if st.button("End Interview"):
            st.success("Interview completed! Thank you for your insights on AI in education.")
            st.session_state.current_question = "Interview ended"

        # Display conversation history and download link
        if st.checkbox("Show Interview Transcript"):
            st.write("Interview Transcript:")
            for entry in st.session_state.conversation:
                st.write(f"{entry['role'].capitalize()}: {entry['content']}")
                st.write("---")
            
            st.markdown(get_transcript_download_link(st.session_state.conversation), unsafe_allow_html=True)

        if st.button("Restart Interview"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.experimental_rerun()

if __name__ == "__main__":
    main()

