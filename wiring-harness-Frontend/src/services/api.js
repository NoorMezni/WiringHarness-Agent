const BASE_URL = "/webhook";
//const BASE_URL = import.meta.env.VITE_API_URL;


export async function sendMessage(sessionId,message) {
  try {
    const res = await fetch(`${BASE_URL}/chatbot`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
    session_id: sessionId,
    message: message
  }),
    });

    if (!res.ok) throw new Error(`HTTP error: ${res.status}`);

    const data = await res.json();

    // Handle all possible shapes
    if (Array.isArray(data)) return data[0]?.content ?? "No response";
    if (data?.answer) return data.answer;    
    return JSON.stringify(data);

  } catch (err) {
    console.error("sendMessage error:", err);
    throw err;
  }
}





export async function sendToAgent(sessionId, message=null, file = null) {

    const formData = new FormData();
    formData.append("session_id", sessionId);
    formData.append("message", message);
    if (file) {
        console.log("there is a file:", file);
        formData.append("file", file);
    }
    const res = await fetch(`${BASE_URL}/webhook/chatbot2`, {
        method: "POST",
        body: formData
    });

    return await res.json();
}
