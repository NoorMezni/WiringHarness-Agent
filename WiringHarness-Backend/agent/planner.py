import json
import re
from agent.executor import TOOL_NAMES, call_qwen
def planner(history, user_message, user_file, session_id,chat_history ):
    already_uploaded = any(
        (step.get("action") or {}).get("tool") == "upload_document"
        for step in history
    )

    if user_file is None:
        doc_status = "no document provided"
    elif already_uploaded:
        doc_status = "a document was provided AND already uploaded - do NOT choose upload_document again"
    else:
        doc_status = "a document was provided and needs to be uploaded using upload_document"

    prompt = f"""
You are an AI planner for a wiring harness manufacturing, electrical harness assembly, and troubleshooting agent.

You MUST choose ONLY ONE action.

Available tools:
- search_docs(query)
- search_cases(query)
- upload_document(file) (only if a document needs to be uploaded)
- send_email(to, subject, body)

Rules:
- You can only output valid JSON, nothing else.
- Choose ONE tool at a time.
- If the user's request is to send/report/inform something by email, choose send_email immediately. Never choose search_docs or search_cases for an email request - write the subject and body yourself from what the user described.
- For send_email: set "metadata.to" ONLY if the user explicitly wrote an email address (and only an address not just words) in their message or in the conversation history. Never invent an address; leave it empty if not given.
- For all other tools, "metadata" must be an empty object {{}}.
- When enough information is collected, return finish.
- For send_email "to": copy the address EXACTLY as typed by the user, or leave it "" if no literal @-address was typed. Never invent a placeholder address (e.g. example.com), an empty "to" is always safer than a guessed one
- If the user's message is ONLY an email address (a correction/retry after you asked for a valid recipient), reuse the subject and body from the most recent send_email attempt found in the conversation history below. Do not blank them out.


Return format:
{{
  "action": "tool" or "finish",
  "tool": "search_docs | search_cases | upload_document | send_email",
  "query": "string",
  "metadata": {{
    "to": "string",
    "subject": "string",
    "body": "string"
  }}
}}

---
document status:
{doc_status}

tools used so far (this turn):
{history}

chat history so far and previous user queries:
{chat_history }

Current User request:
{user_message}

Return ONLY valid JSON. No text. No markdown. No explanation.
"""

    response = call_qwen(prompt)
    print("RAW MODEL RESPONSE:", response)
    try:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        decision = json.loads(match.group(0) if match else response)
        print ("decisionnnnnn:", decision)
    except Exception:
        decision = {}

    if decision.get("action") in TOOL_NAMES:
        decision["tool"] = decision["action"]
        decision["action"] = "tool"
    decision["query"]=user_message

    valid = decision.get("action") in ("tool", "finish") and (
        decision.get("action") != "tool" or decision.get("tool") in TOOL_NAMES)

    if not valid:
        return {"action": "tool", "tool": "search_docs", "query": user_message}

    return decision
