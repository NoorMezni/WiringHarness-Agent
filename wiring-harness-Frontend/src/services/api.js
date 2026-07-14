const BASE_URL = "/webhook";
//const BASE_URL = import.meta.env.VITE_API_URL;


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
