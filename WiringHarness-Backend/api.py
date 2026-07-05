from fastapi import FastAPI, File, Form, UploadFile
from agent.loop import run_agent
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/agent")
async def chatbot2(
    session_id: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    history: str = Form(""),
    file: UploadFile | None = File(None),
):
    print("Message:", message)
    print("File:", file.filename if file else "No file")

    result = await run_agent(
        user_message=message,
        chat_history=history,
        user_file=file,
        session_id=session_id,
    )

    return {
        "session_id": session_id,
        "role": "assistant",
        "answer": result["answer"],
    }






