import streamlit as st
import requests
import pandas as pd
import base64

# Retrieve the password and DeepSeek API key from Streamlit secrets
PASSWORD = st.secrets["password"]
DEEPSEEK_API_KEY = st.secrets["deepseek_api_key"]
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"  # Adjust if DeepSeek's endpoint differs

# List of interview topics
interview_topics = [
    "Introduction and personal background",
    "Experiences using generative AI tools",
    "Perceived benefits of generative AI in coursework",
    "Challenges faced when integrating AI tools",
    "Impact on academic development and assessment performance",
    "Strategies for incorporating AI outputs into work",
    "Effectiveness of guidance on prompt design and AI competencies",
    "Generative AI's role in creating accessible educational environments"
]

total_questions = len(interview_topics)  # Total number of interview topics for progress bar

def generate_response(prompt, conversation_history=None):
    try:
        if conversation_history is None:
            conversation_history = []

        system_content = """You are an experienced and considerate interviewer in higher education, focusing on AI applications. Use British English in your responses, including spellings like 'democratised'. Ensure your responses are complete and not truncated. 
        After each user response, provide brief feedback and ask a relevant follow-up question based on their answer. Tailor your questions to the user's previous responses, avoiding repetition and exploring areas they haven't covered. Be adaptive and create a natural flow of conversation."""
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "system", "content": f"Interview topics: {interview_topics}"},
            *conversation_history[-6:],  # Include the last 6 exchanges for more context
            {"role": "user", "content": prompt}
        ]

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat-7b",  
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.6
        }

        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()
        return response_json["choices"][0]["message"]["content"]
    except Exception as e:
        return f"An error occurred in generate_response: {str(e)}"

def get_transcript_download_link(conversation):
    df = pd.DataFrame(conversation)
    markdown_content = '\n'.join([f"**{entry['role'].capitalize()}:** {entry['content']}" for entry in conversation])
    b64 = base64.b64encode(markdown_content.encode()).decode()
    href = f'<a href="data:file/markdown;base64,{b64}" download="interview_transcript.md">Download Transcript</a>'
    return href

def main():
    # Password authentication
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        password = st.text_input("Enter password to access the interview app:", type="password")
        if st.button("Submit"):
            if password == PASSWORD:
                st.session_state.authenticated = True
                st.success("Access granted.")
            else:
                st.error("Incorrect password.")
        return  # Stop the app here if not authenticated

    # Interview app content (only shown if authenticated)
    st.title("AI Interview Bot")

    if "conversation" not in st.session_state:
        st.session_state.conversation = []
    if "current_question" not in st.session_state:
        st.session_state.current_question = "Let's begin the interview. Can you please introduce yourself, your role in higher education, and your interest in AI?"
    if "submitted" not in st.session_state:
        st.session_state.submitted = False

    st.write("""
    Before we begin, please read the information sheet provided and understand that by ticking yes, you will be giving your written informed consent for your responses to be used for research purposes and may be anonymously quoted in publications.
    
    You can choose to end the interview at any time and request your data be removed by emailing tony.myers@staff.ac.uk. This interview will be conducted by an AI assistant who, along with asking set questions, will ask additional probing questions depending on your response.
    """)

    consent = st.checkbox("I have read the information sheet and give my consent to participate in this interview.")

    if consent:
        st.write(st.session_state.current_question)

        user_answer = st.text_area("Your response:", key=f"user_input_{len(st.session_state.conversation)}")

        # Progress bar with a label indicating interview progress
        completed_questions = len([entry for entry in st.session_state.conversation if entry['role'] == "user"])
        progress_percentage = min(completed_questions / total_questions, 1.0)
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
                
                st.rerun()
            else:
                st.warning("Please provide an answer before submitting.")

        # Option to end the interview
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

        # Option to restart the interview
        if st.button("Restart Interview"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()
