import os
from agent.planner import planner
from agent.executor import executor,is_valid_email, ASK_RECIPIENT_MSG, generate_answer, generate_email_confirmation, generate_upload_confirmation
import time

MAX_STEPS = 4
INVALID_RECIPIENT_MSG = "The recipient's email address doesn't look valid. Could you please send a correct one, otherwise the email will be automatically sent to the admin!"
_pending_emails = {}

async def run_agent(user_message, chat_history="", user_file=None, session_id=None):
    tool_history = []
    step_count = 0
    pending = _pending_emails.get(session_id)
    stripped_msg = (user_message or "").strip()
    if pending and is_valid_email(stripped_msg):
        decision = {
            "action": "tool",
            "tool": "send_email",
            "query": "",
            "metadata": {
                "to": stripped_msg,
                "subject": pending["subject"],
                "body": pending["body"],
            },
        }
        result = await executor(decision, user_file=user_file, session_id=session_id)
        tool_history.append({"step": 1, "action": decision, "result": result})

        if not result.get("missing_recipient") and not result.get("invalid_recipient"):
            _pending_emails.pop(session_id, None)
            return {
                "answer": generate_email_confirmation(result),
                "context": "",
                "tool_history": tool_history,
            }
        # still invalid -> let it fall through to the normal loop/attempts logic below
        step_count = 1
    while True:
        step_count += 1
        decision = planner(tool_history, user_message, user_file, session_id,chat_history )
        print("PLANNER:", decision)

        if decision.get("action") == "finish":
            break

        try:
            result = await executor(decision, user_file=user_file, session_id=session_id)
        except Exception as e:
            result = {"error": f"Tool execution failed: {e}"}
        print("EXECUTOR:", result)

        tool_history.append({"step": step_count, "action": decision, "result": result})

        if decision.get("tool") == "send_email":
            if not result.get("missing_recipient") and not result.get("invalid_recipient"):
                _pending_emails.pop(session_id, None)
                return {
                    "answer": generate_email_confirmation(result),
                    "context": "",
                    "tool_history": tool_history,
                }

            # recipient missing or invalid -> track how many times this has
            # happened for this session
            metadata = decision.get("metadata", {})
            prev = _pending_emails.get(session_id)
            attempts = (prev["attempts"] + 1) if prev else 1
            subject = metadata.get("subject") or (prev["subject"] if prev else "")
            body = metadata.get("body") or (prev["body"] if prev else "")
            _pending_emails[session_id] = {
                "subject": subject,
                "body": body,
                "attempts": attempts,
            }

            if attempts >= 3:
                fallback_decision = {
                    **decision,
                    "metadata": {
                        "to": os.getenv("ADMIN_EMAIL", ""),
                        "subject": subject,
                        "body": body,
                    },
                }
                result = await executor(fallback_decision, user_file=user_file, session_id=session_id)
                tool_history[-1] = {"step": step_count, "action": fallback_decision, "result": result}
                _pending_emails.pop(session_id, None)
                return {
                    "answer": generate_email_confirmation(result),
                    "context": "",
                    "tool_history": tool_history,
                }
            else:
                prompt_msg = ASK_RECIPIENT_MSG if result.get("missing_recipient") else INVALID_RECIPIENT_MSG
                return {
                    "answer": prompt_msg,
                    "context": "",
                    "tool_history": tool_history,
                }
        if step_count >= MAX_STEPS:
            break

    if user_file is not None and len(tool_history) == 1:
        return {
            "answer": generate_upload_confirmation(tool_history[0]["result"]),
            "context": "",
            "tool_history": tool_history, }

    context = build_context(tool_history)
    print (context)
    final_answer = generate_answer(context=context, history=chat_history, query=user_message)

    return {
        "answer": final_answer,
        "context": context,
        "tool_history": tool_history, }


def build_context(tool_history):
    parts = []
    for item in tool_history:
        action = item.get("action", {})
        parts.append(f"[Source: {action.get('tool', '')} | Query: \"{action.get('query', '')}\"]\n{item['result']}")
    return "\n\n".join(parts)