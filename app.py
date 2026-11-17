import streamlit as st
import google.generativeai as genai
import requests
import time
import difflib

# Configure Gemini API using Streamlit Secrets
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("GEMINI_API_KEY is missing from Streamlit Secrets.")

# Track start time when session begins
if "start_time" not in st.session_state:
    st.session_state["start_time"] = time.time()

# Helper function to call Gemini with instructions (kept exactly as before)
def get_ai_response(original_essay):
    try:
        ai_prompt = f"""
        You are an English language writing assistant. Please review the following student essay draft:

        "{original_essay}"

        Provide your response in two clear parts:
        1. Feedback: Give brief, concise, readable feedback in bullet points. Start with positive points and move to points that need improvements. Do NOT mention coherence or cohesion.
        2. Rewrite: Provide a revised version of the essay that maintains a similar word count to the original draft.
        """
        model = genai.GenerativeModel("gemini-3.8-flash")
        response = model.generate_content(ai_prompt)
        return response.text
    except Exception as e:
        return f"Error generating AI response: {e}"

# App Title
st.title("AI Writing Assistant")

# Step 1: Student Number and Essay Input
student_id = st.text_input("Student #: *")

original_essay = st.text_area("Write/paste your opinion essay here: *")

# Word count validation for original essay (50 - 250 words)
original_word_count = len(original_essay.split()) if original_essay else 0

if original_essay:
    st.info(f"Current word count: {original_word_count} words")
    if original_word_count < 50 or original_word_count > 250:
        st.warning("Please ensure your essay is between 50 and 250 words before generating feedback.")
    else:
        if st.button("Generate AI Feedback & Rewrite"):
            with st.spinner("Generating personalized feedback and rewrite..."):
                st.session_state["ai_output"] = get_ai_response(original_essay)
                st.rerun()

# Display AI Feedback & Rewrite if generated
if "ai_output" in st.session_state:
    st.markdown("### AI Feedback & Rewrite:")
    st.write(st.session_state["ai_output"])
    
    st.markdown("---")
    st.markdown("Now, take a moment to reread the feedback, compare the AI rewrite with your original draft. Decide what to change, adapt, add, remove, or keep. Then revise your essay and submit your final version.")
    
    # Final revised essay text area
    revised_essay = st.text_area("Write/paste your revised essay here: *")
    revised_word_count = len(revised_essay.split()) if revised_essay else 0
    
    if revised_essay:
        st.info(f"Current word count: {revised_word_count} words")
        if revised_word_count < 50 or revised_word_count > 250:
            st.warning("Please ensure your revised essay is between 50 and 250 words.")

    st.markdown("---")
    
    # Final reflection and rating questions
    experience_rating = st.slider("From 1 to 5 when 1 is the worst and 5 is the best, my experience was:", 1, 5, 3)
    experience_comment = st.text_input("If you’d like to say why, you’re most welcome to do so (you may use Arabic or Hebrew); otherwise, feel free to submit (Optional):")
    
    if st.button("Submit Final Version"):
        # Validate mandatory fields (omitting Q1-Q5 as requested for the control group)
        missing_fields = []
        if not student_id.strip():
            missing_fields.append("Student #")
        if not original_essay.strip():
            missing_fields.append("Original Essay")
        elif original_word_count < 50 or original_word_count > 250:
            missing_fields.append("Original Essay word count (must be 50-250 words)")
        if "ai_output" not in st.session_state or not st.session_state["ai_output"].strip():
            missing_fields.append("AI Feedback (Please click 'Generate AI Feedback & Rewrite')")
        if not revised_essay.strip():
            missing_fields.append("Revised Essay")
        elif revised_word_count < 50 or revised_word_count > 250:
            missing_fields.append("Revised Essay word count (must be 50-250 words)")

        if missing_fields:
            st.error(f"Please complete the following required fields before submitting: {', '.join(missing_fields)}")
        else:
            # --- AUTOMATED REVISION METRICS & DIFF CALCULATIONS ---
            total_time_seconds = int(time.time() - st.session_state.get("start_time", time.time()))
            word_count_difference = revised_word_count - original_word_count
            
            matcher = difflib.SequenceMatcher(None, original_essay, revised_essay)
            text_similarity_score = round(matcher.ratio(), 2)
            
            original_words = original_essay.split()
            revised_words = revised_essay.split()
            diff_list = list(difflib.ndiff(original_words, revised_words))
            word_changes_log = "\n".join(diff_list)
            # ----------------------------------------------------

            formspree_url = "https://formspree.io/f/mnpnokpq"
            
            # Clean payload without the experimental Q1-Q5 judgment questions
            payload = {
                "Student_ID": student_id,
                "Original_Essay": original_essay,
                "AI_Output": st.session_state["ai_output"],
                "Revised_Essay": revised_essay,
                # Research Metrics:
                "Revision_Time_Seconds": total_time_seconds,
                "Original_Word_Count": original_word_count,
                "Revised_Word_Count": revised_word_count,
                "Word_Count_Change": word_count_difference,
                "Text_Similarity_Score": text_similarity_score,
                "Word_Changes_Log": word_changes_log,
                "Experience_Rating": experience_rating,
                "Experience_Comment": experience_comment
            }
            
            try:
                response = requests.post(formspree_url, data=payload)
                if response.status_code == 200:
                    st.success("Thank you so much!")
                    st.balloons()
                else:
                    st.error("There was an error submitting your response. Please try again.")
            except Exception as e:
                st.error(f"Connection error: {e}")
