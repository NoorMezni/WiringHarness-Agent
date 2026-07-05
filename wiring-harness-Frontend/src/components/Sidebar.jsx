import { useState } from "react";

function Sidebar({ loggedIn, setLoggedIn ,onNewConversation }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="sidebar">
<div className="new-thread" onClick={onNewConversation}>        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        New Conversation
      </div>

      <div className="sidebar-bottom">
        {open && (
          <div className="account-menu">
            {loggedIn ? (
              <div onClick={() => { setLoggedIn(false); setOpen(false); }}>Log out</div>
            ) : (
              <div onClick={() => { setLoggedIn(true); setOpen(false); }}>Log in</div>
            )}
          </div>
        )}
        <div className="account-btn" onClick={() => setOpen(!open)}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
          {loggedIn ? "Account" : "Log in"}
        </div>
      </div>
    </div>
  );
}

export default Sidebar;