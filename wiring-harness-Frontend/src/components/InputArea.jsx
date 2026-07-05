import { useRef, useState } from "react";
//import { uploadFile } from "../services/api";
import { sendToAgent } from "../services/api";

function InputArea({ onSend, disabled }) {
  const [text, setText] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null); // "success" | "error" | null
  const fileRef = useRef(null);

  const handleSend = () => {
    if (!text.trim() || disabled) return;
    onSend(text);
    setText("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFile = async (e) => {
    const file = e.target.files[0];
    const sessionId = sessionStorage.getItem("session_id");
    if (!file) return;
    e.target.value = "";

    setUploading(true);
    setUploadStatus(null);

    try {
      const result = await sendToAgent(sessionId,"",file);
      console.log("Upload result:", result);
      setUploadStatus("success");
    } catch (err) {
      console.error("Upload error:", err);
      setUploadStatus("error");
    } finally {
      setUploading(false);
      // Clear status badge after 4 seconds
      setTimeout(() => setUploadStatus(null), 4000);
    }
  };

  return (
    <div className="input-area">

      {/* Upload status badge */}
      {uploadStatus === "success" && (
        <span style={{ fontSize: "12px", color: "green" }}>✓ Uploaded</span>
      )}
      {uploadStatus === "error" && (
        <span style={{ fontSize: "12px", color: "red" }}>✗ Upload failed</span>
      )}

      {/* File button — shows spinner while uploading */}
      <button
        className="icon-btn"
        onClick={() => fileRef.current.click()}
        disabled={uploading || disabled}
      >
        {uploading ? "⏳" : "+"}
      </button>

      <input
        type="file"
        ref={fileRef}
        style={{ display: "none" }}
        onChange={handleFile}
      />

      <textarea
        value={text}
        placeholder="Message..."
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={1}
        disabled={disabled || uploading}
      />

      <button className="send-btn" onClick={handleSend} disabled={disabled || uploading}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="12" y1="19" x2="12" y2="5" />
          <polyline points="5 12 12 5 19 12" />
        </svg>
      </button>

    </div>
  );
}

export default InputArea;