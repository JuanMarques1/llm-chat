import { useEffect, useRef, useState } from "react";
import { streamChat, clearSession } from "./api";

// Gera um id de sessão estável por aba para o backend manter o histórico.
function newSessionId() {
  return `web-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function App() {
  const [sessionId, setSessionId] = useState(newSessionId);
  const [messages, setMessages] = useState([]); // { role: "user" | "assistant", content }
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const listRef = useRef(null);
  const abortRef = useRef(null);

  // Rola para o fim sempre que chegam novas mensagens/tokens.
  useEffect(() => {
    listRef.current?.scrollTo(0, listRef.current.scrollHeight);
  }, [messages]);

  async function handleSend(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setError("");
    setInput("");
    setLoading(true);

    // Adiciona a mensagem do usuário e um placeholder vazio do assistente.
    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
      { role: "assistant", content: "" },
    ]);

    abortRef.current = new AbortController();

    try {
      await streamChat(
        text,
        sessionId,
        (token) => {
          // Anexa cada token ao conteúdo da última mensagem (a do assistente).
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = {
              ...next[next.length - 1],
              content: next[next.length - 1].content + token,
            };
            return next;
          });
        },
        abortRef.current.signal
      );
    } catch (err) {
      if (err.name !== "AbortError") setError(err.message);
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }

  function handleStop() {
    abortRef.current?.abort();
  }

  async function handleNewChat() {
    abortRef.current?.abort();
    await clearSession(sessionId);
    setSessionId(newSessionId());
    setMessages([]);
    setError("");
  }

  return (
    <div className="app">
      <header className="header">
        <h1>LangChain Chat</h1>
        <button className="ghost" onClick={handleNewChat} disabled={loading && !messages.length}>
          Nova conversa
        </button>
      </header>

      <main className="messages" ref={listRef}>
        {messages.length === 0 && (
          <p className="empty">Comece a conversa enviando uma mensagem 👇</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            {m.content || (m.role === "assistant" && loading ? <span className="cursor">▍</span> : null)}
          </div>
        ))}
        {error && <div className="bubble error">⚠️ {error}</div>}
      </main>

      <form className="composer" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          placeholder="Digite sua mensagem..."
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          autoFocus
        />
        {loading ? (
          <button type="button" className="stop" onClick={handleStop}>
            Parar
          </button>
        ) : (
          <button type="submit" disabled={!input.trim()}>
            Enviar
          </button>
        )}
      </form>
    </div>
  );
}
