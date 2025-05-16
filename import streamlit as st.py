import streamlit as st
import requests
from PyPDF2 import PdfReader
import docx
import re
import json

# Constants
MAX_UPLOAD_SIZE_MB = 5

# Your OpenRouter API key here or via environment variables (recommended)
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

st.set_page_config(page_title="Teleserye Script Enhancer", layout="wide")

def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

def extract_text_from_docx(file):
    try:
        doc = docx.Document(file)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading DOCX: {e}")
        return ""

def extract_text_from_txt(file):
    try:
        return file.read().decode("utf-8")
    except Exception as e:
        st.error(f"Error reading TXT: {e}")
        return ""

def extract_text(file):
    if file.type == "application/pdf":
        return extract_text_from_pdf(file)
    elif file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
        return extract_text_from_docx(file)
    elif file.type.startswith("text"):
        return extract_text_from_txt(file)
    else:
        st.warning("Unsupported file type. Please upload PDF, DOCX, or TXT.")
        return ""

def call_openrouter_chat(script_text, user_question=None):
    system_prompt = {
        "role": "system",
        "content": (
            "You are a teleserye script expert. "
            "Detect cliché plot points in the following script and return a JSON object with two keys: "
            "'cliches' as a list of cliché sentences or plot points detected, and "
            "'suggestions' as detailed suggestions to improve the script."
        )
    }

    user_content = f"Script:\n{script_text}\n"
    if user_question:
        user_content += f"\nUser question: {user_question}"

    messages = [
        system_prompt,
        {"role": "user", "content": user_content}
    ]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0
    }

    try:
        response = requests.post(OPENROUTER_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        # Extract model response text
        reply = data["choices"][0]["message"]["content"]
        return reply
    except Exception as e:
        st.error(f"Error calling OpenRouter API: {e}")
        return None

def parse_cliches_from_response(response_text):
    """
    Parse JSON part from the response text.
    Expecting something like:
    {
      "cliches": ["sentence 1", "sentence 2", ...],
      "suggestions": "long suggestion text"
    }
    """
    try:
        # Attempt to find JSON object inside the text response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        json_str = response_text[json_start:json_end]
        data = json.loads(json_str)
        return data.get("cliches", []), data.get("suggestions", "")
    except Exception:
        # If parsing fails, fallback to no cliches and entire response as suggestion
        return [], response_text

def highlight_cliches(script, cliches):
    """Return script with cliché sentences highlighted."""
    # Escape special regex characters in clichés
    escaped_cliches = [re.escape(c) for c in cliches if c.strip() != ""]

    # Build a regex pattern that matches any cliché phrase
    if not escaped_cliches:
        return script  # no highlights

    pattern = "(" + "|".join(escaped_cliches) + ")"

    # Replace clichés with highlighted HTML span
    highlighted_script = re.sub(pattern,
                                r'<mark style="background-color: #ffcccc;">\1</mark>',
                                script, flags=re.IGNORECASE)
    return highlighted_script

def main():
    st.title("📜 Teleserye Script Enhancer with AI")

    st.sidebar.header("Upload Script")
    uploaded_file = st.sidebar.file_uploader(
        "Choose a file (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"],
        help="Max file size: 5 MB"
    )

    if uploaded_file:
        if uploaded_file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            st.sidebar.error(f"File too large! Max size is {MAX_UPLOAD_SIZE_MB} MB.")
            return

        with st.spinner("Extracting text from file..."):
            script_text = extract_text(uploaded_file)

        if not script_text or script_text.strip() == "":
            st.error("Failed to extract any text from the uploaded file.")
            return

        # Show preview
        st.subheader("Script Preview (first 1500 characters):")
        st.text_area("", script_text[:1500], height=250)

        # Analyze button
        if st.button("Analyze and Highlight Cliché Plots"):
            with st.spinner("Calling AI to analyze script..."):
                response = call_openrouter_chat(script_text)
                if response:
                    cliches, suggestions = parse_cliches_from_response(response)
                    st.subheader("💡 Detected Cliché Plot Points:")
                    if cliches:
                        for idx, c in enumerate(cliches, 1):
                            st.markdown(f"{idx}. {c}")
                    else:
                        st.write("No obvious clichés detected!")

                    st.subheader("🔧 Suggestions to Improve:")
                    st.write(suggestions)

                    st.subheader("📖 Script with Highlighted Clichés:")
                    highlighted = highlight_cliches(script_text, cliches)
                    st.markdown(f"<div style='white-space: pre-wrap; font-family: monospace;'>{highlighted}</div>", unsafe_allow_html=True)

        # Optional chat input for more questions
        user_question = st.text_input("Ask more about your script or get specific suggestions:")
        if user_question:
            with st.spinner("Getting AI response..."):
                answer = call_openrouter_chat(script_text, user_question=user_question)
                if answer:
                    st.markdown("### 🤖 AI Response")
                    st.write(answer)

if __name__ == "__main__":
    main()
