function Message({ role, text }) {
  return (
    <div className={`message ${role}`}>
      <div className="bubble">{text}</div>
    </div>
  );
}

export default Message;