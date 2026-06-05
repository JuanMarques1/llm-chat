// URL do backend. Em dev usa localhost; em produção, defina VITE_API_URL na Vercel.
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Envia uma mensagem para o backend e consome o stream SSE token a token.
 *
 * Como o endpoint /chat é um POST, não dá para usar EventSource (que só faz GET).
 * Por isso lemos o corpo da resposta manualmente com um ReadableStream e
 * parseamos as linhas "data: <texto>" no formato Server-Sent Events.
 *
 * @param {string} message      Texto do usuário.
 * @param {string} sessionId    Identifica a conversa (mantém histórico no backend).
 * @param {(token: string) => void} onToken  Chamado a cada pedaço de texto recebido.
 * @param {AbortSignal} [signal] Permite cancelar a requisição.
 */
export async function streamChat(message, sessionId, onToken, signal) {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
    signal,
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Erro ${res.status}: ${detail || res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Eventos SSE são separados por linha em branco (\n\n).
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? ""; // último pedaço pode estar incompleto

    for (const evt of events) {
      const lines = evt.split("\n");
      let isError = false;
      let data = "";

      for (const line of lines) {
        if (line.startsWith("event: error")) isError = true;
        else if (line.startsWith("data: ")) data += line.slice(6);
      }

      if (data === "[DONE]") return;
      if (isError) throw new Error(data || "Erro no servidor.");
      if (data) onToken(data);
    }
  }
}

/** Limpa o histórico da sessão no backend (botão "nova conversa"). */
export async function clearSession(sessionId) {
  try {
    await fetch(`${API_URL}/chat/${sessionId}`, { method: "DELETE" });
  } catch {
    // Limpeza de histórico é best-effort; ignoramos falhas de rede aqui.
  }
}
