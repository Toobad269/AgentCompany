"use client";

import { Send, Sparkles } from "lucide-react";
import { FormEvent, useState, useTransition } from "react";
import type { ChatThreadView } from "@/lib/chat-data";

type Props = {
  initialThread: ChatThreadView;
};

export function CeoChat({ initialThread }: Props) {
  const [thread, setThread] = useState(initialThread);
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextMessage = message.trim();
    if (!nextMessage || isPending) {
      return;
    }

    setError(null);
    setMessage("");

    startTransition(async () => {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: nextMessage })
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error ?? "The CEO chat could not process the message.");
        return;
      }

      setThread(data);
    });
  }

  return (
    <article className="panel chatPanel">
      <div className="panelHeader">
        <div>
          <span>Chat</span>
          <h2>{thread.title}</h2>
        </div>
        <Sparkles aria-hidden="true" size={22} />
      </div>

      <div className="messages" aria-live="polite">
        {thread.messages.map((item) => (
          <div className={`message ${item.role}`} key={item.id}>
            <strong>{item.authorName}</strong>
            <p>{item.content}</p>
          </div>
        ))}
      </div>

      {error ? <div className="formError">{error}</div> : null}

      <form className="chatForm" onSubmit={submit}>
        <input
          aria-label="Message the CEO"
          disabled={isPending}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Ask the CEO to plan a product, project, or agent workflow..."
          value={message}
        />
        <button aria-label="Send message" disabled={isPending || !message.trim()} type="submit">
          <Send aria-hidden="true" size={18} />
        </button>
      </form>
    </article>
  );
}
