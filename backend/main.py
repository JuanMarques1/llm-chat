import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# ChatOpenAI (langchain-openai) lê a OPENAI_API_KEY automaticamente de os.environ.
# Validamos na inicialização para falhar de forma clara caso a env var não exista.
# Em produção, essa variável é injetada pelo Render (env var com sync: false).
if not os.environ.get("OPENAI_API_KEY"):
    print("[aviso] OPENAI_API_KEY não definida no ambiente — defina antes de chamar /chat.")

app = FastAPI(title="LangChain Chat")

# CORS — origens permitidas para o frontend.
# Pode-se sobrescrever via env var ALLOWED_ORIGINS (lista separada por vírgula).
default_origins = [
    "http://localhost:5173",
    "https://SEU-APP.vercel.app",  # TODO: trocar pela URL real da Vercel após o deploy do frontend
]
env_origins = os.environ.get("ALLOWED_ORIGINS")
origins = [o.strip() for o in env_origins.split(",") if o.strip()] if env_origins else default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LCEL: prompt | llm (sem LLMChain legado), com histórico de mensagens por sessão.
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, streaming=True)
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "Você é um assistente útil."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{message}"),
    ]
)
chain = prompt | llm

# Armazenamento de histórico em memória, indexado por session_id.
# Observação: por estar em memória, o histórico é perdido a cada restart do
# servidor e não é compartilhado entre múltiplos workers/instâncias. Para
# produção real, troque por Redis/Postgres (langchain tem integrações prontas).
_session_store: dict[str, BaseChatMessageHistory] = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in _session_store:
        _session_store[session_id] = InMemoryChatMessageHistory()
    return _session_store[session_id]


chain_with_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="message",
    history_messages_key="history",
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Mensagem do usuário.")
    session_id: str = Field(default="default", description="Identifica a conversa para manter histórico.")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(req: ChatRequest):
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY não configurada no servidor.")

    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="A mensagem não pode ser vazia.")

    async def event_stream():
        try:
            # Emite cada token no formato SSE: "data: <texto>\n\n".
            # O RunnableWithMessageHistory persiste a troca (humano + IA) no
            # histórico da sessão ao final do stream automaticamente.
            async for chunk in chain_with_history.astream(
                {"message": message},
                config={"configurable": {"session_id": req.session_id}},
            ):
                text = chunk.content
                if text:
                    yield f"data: {text}\n\n"
        except Exception as exc:  # noqa: BLE001 — qualquer falha vira evento de erro no stream
            # Sinaliza o erro ao cliente sem derrubar a conexão abruptamente.
            yield f"event: error\ndata: {str(exc)}\n\n"
        finally:
            # Finaliza o stream
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # evita buffering em proxies (mantém o streaming fluido)
        },
    )


@app.delete("/chat/{session_id}")
async def clear_session(session_id: str):
    """Limpa o histórico de uma sessão (ex.: botão 'nova conversa' no frontend)."""
    _session_store.pop(session_id, None)
    return {"status": "cleared", "session_id": session_id}
