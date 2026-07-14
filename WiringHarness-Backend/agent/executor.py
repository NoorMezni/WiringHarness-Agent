import os
from dotenv import load_dotenv
import httpx
import ollama
from tools.search_docs import search_docs
from tools.search_cases import search_cases
import re
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1",)
upload_path = os.getenv("upload_path")
email_path = os.getenv("email_path")
admin_email = os.getenv("admin_email")
ASK_RECIPIENT_MSG = ("There is no recipient's email provided previously. Could you please send a correct one, otherwise it the email will be automatically sent to the admin! ")



EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def is_valid_email(email: str):
    return bool(email) and bool(EMAIL_REGEX.match(email.strip()))

async def send_email(to, subject, body):
    if not to:
        return {"missing_recipient": True}
    if not is_valid_email(to):         
        return {"invalid_recipient": True, "recipient": to} 
 
    payload = {"to": to, "subject": subject, "body": body}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(email_path, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as e:
            return {"error": str(e)}
 
    if not response.text.strip():
        return {"status": "success"}
 
    try:
        return response.json()
    except ValueError:
        return {"error": response.text}



async def upload_document(file, session_id=None, message=None):
    file_bytes = await file.read()
    files = {"data": (file.filename, file_bytes, file.content_type)}
    data = {"session_id": session_id or "", "message": message or ""}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(upload_path, files=files, data=data)
            response.raise_for_status()
        except httpx.HTTPError as e:
            return {"error": str(e)}

    if not response.text.strip():
        return {"status": "success"}

    try:
        return response.json()
    except ValueError:
        return {"error": response.text}


TOOLS = { "search_docs": search_docs, "search_cases": search_cases, "upload_document": upload_document, "send_email": send_email,}
TOOL_NAMES = list(TOOLS.keys())


async def executor(step, user_file=None, session_id=None):
    tool = step.get("tool")
    query = step.get("query", "")

    if tool not in TOOLS:
        return {"error": f"Unknown tool: {tool}"}

    if tool == "upload_document":
        if user_file is None:
            return {"error": "no file was provided"}
        return await TOOLS[tool](user_file, session_id, query)
    
    
    if tool == "send_email":
        metadata = step.get("metadata") or {}
        to = metadata.get("to", "")
        subject = metadata.get("subject", "")
        body = metadata.get("body", "")
        return await TOOLS[tool](to, subject, body)

    return TOOLS[tool](query)

def generate_email_confirmation(email_result):
    if email_result.get("error"):
        return f"Error occurred while sending the email: {email_result['error']}"
    return "Your email has been submitted for delivery successfully!"
def generate_upload_confirmation(upload_result):
    if upload_result.get("error"):
        return f" Error occured during the upload of the document: {upload_result['error']}"
    return "Document uploaded successfully!"


def generate_answer(context, history, query):
    prompt = f"""
You are a technical expert in wiring harness manufacturing, electrical harness assembly, and troubleshooting in industrial environments.

Your role is to produce accurate, field-ready technical answers for engineers and technicians.

# STRICT RULES
1. Use ONLY the provided CONTEXT. If context is insufficient: say "Information not found in the provided documentation."
2. Do NOT guess or hallucinate technical data.
3. Combine information from multiple fragments into a single coherent explanation.
4. Cite sources using EXACT file names from context as follows: according to [filename] (if provided in the context)
5. Maintain engineering-level precision.
6. Respond in the SAME language as the user.
7. if the query is related to send_email or email address,


# CONTEXT (from tools)
{context}

# here is CHAT HISTORY (user conversation of previous questions and answer in the same conversation) in case the new user query and your response depend on the past history
{history}

# QUESTION
{query}
"""
    return call_qwen(prompt)


def call_qwen(prompt):
    try:
        response = ollama.chat(
            model="qwen2.5:7b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3}
        )
        return response["message"]["content"]

    except Exception as e:
        print("Qwen error:", e)
        return "docs"  
    
    
"""
def call_qwen(prompt):
    try:
        response = client.chat.completions.create(
            model="qwen/qwen3.6-flash",
            messages=[ {"role": "user", "content": prompt} ],
            temperature=0.3,
            max_tokens=9317)
        return response.choices[0].message.content

    except Exception as e:
        print("Qwen error:", e)
        return "docs" 
    """