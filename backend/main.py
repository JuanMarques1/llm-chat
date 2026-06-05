import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# ChatOpenAI (langchain-openai) lê a OPENAI_API_KEY automaticamente de os.environ.
# Validamos na inicialização para falhar de forma clara caso a env var não exista.
# Em produção, essa variável é injetada pelo Render (env var com sync: false).
if not os.environ.get("OPENAI_API_KEY"):
    print("[aviso] OPENAI_API_KEY não definida no ambiente — defina antes de chamar /chat.")

app = FastAPI(title="LangChain Chat")

# CORS — origens permitidas para o frontend.
origins = [
    "http://localhost:5173",
    "https://SEU-APP.vercel.app",  # TODO: trocar pela URL real da Vercel após o deploy do frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LCEL: prompt | llm (sem LLMChain legado).
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, streaming=True)
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "Você é um assistente útil."),
        ("human", "{message}"),
    ]
)
chain = prompt | llm


class ChatRequest(BaseModel):
    message: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(req: ChatRequest):
    async def event_stream():
        # Emite cada token no formato SSE: "data: <texto>\n\n"
        async for chunk in chain.astream({"message": req.message}):
            text = chunk.content
            if text:
                yield f"data: {text}\n\n"
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
