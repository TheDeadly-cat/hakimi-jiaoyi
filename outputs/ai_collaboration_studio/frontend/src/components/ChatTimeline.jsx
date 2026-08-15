import { Reply } from "lucide-react";
import { useEffect, useRef } from "react";

function initials(name = "AI") {
  return name === "我" ? "我" : name.slice(0, 2);
}

function messageTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

export function ChatTimeline({ messages, members, typingMember, transientErrors }) {
  const bottomRef = useRef(null);
  const memberMap = new Map(members.map((member) => [member.id, member]));
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, typingMember?.id, transientErrors.length]);

  return (
    <div className="chat-timeline" aria-live="polite">
      {messages.map((message) => {
        const isUser = message.sender_type === "user";
        const isSystem = message.sender_type === "system";
        const member = memberMap.get(message.sender_id);
        if (isSystem) {
          return <div className="inline-error persisted" key={message.id}>{message.content}</div>;
        }
        return (
          <article key={message.id} className={isUser ? "message user" : "message ai"}>
            {!isUser && (
              <div className="avatar" style={{ background: member?.avatar_color || "#4f6b8a" }}>
                {initials(message.sender_name)}
              </div>
            )}
            <div className="message-body">
              <header>
                <strong>{message.sender_name}</strong>
                {message.identity && <span>{message.identity}</span>}
                <time>{messageTime(message.created_at)}</time>
              </header>
              <div className={isUser ? "message-copy user-bubble" : "message-copy"}>{message.content}</div>
              {message.reply_to && !isUser && (
                <div className="reply-line"><Reply size={13} />回应 {message.reply_to}</div>
              )}
            </div>
          </article>
        );
      })}
      {transientErrors.map((error) => (
        <div className="inline-error" key={error.id}>{error.name} 未完成发言：{error.message}</div>
      ))}
      {typingMember && (
        <article className="message ai typing-message">
          <div className="avatar" style={{ background: typingMember.avatar_color }}>{initials(typingMember.name)}</div>
          <div className="message-body">
            <header><strong>{typingMember.name}</strong><span>{typingMember.identity}</span></header>
            <div className="typing-indicator" aria-label={`${typingMember.name}正在输入`}><i /><i /><i /></div>
          </div>
        </article>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
