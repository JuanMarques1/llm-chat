# LangChain Chat

Chat com streaming token a token usando **FastAPI + LangChain (LCEL)** no backend e **React + Vite** no frontend. O backend mantém histórico de conversa por sessão.

```
.
├── backend/        # API FastAPI (deploy no Render)
│   ├── main.py
│   ├── requirements.txt
│   └── Procfile
├── frontend/       # App React + Vite (deploy na Vercel)
│   └── src/
├── render.yaml     # Infra-as-code do backend no Render
└── README.md
```

## Backend (Render)

Endpoints:

| Método | Rota                  | Descrição                                         |
| ------ | --------------------- | ------------------------------------------------- |
| GET    | `/health`             | Healthcheck.                                      |
| POST   | `/chat`               | Recebe `{ message, session_id }` e devolve um stream SSE de tokens. |
| DELETE | `/chat/{session_id}`  | Limpa o histórico de uma sessão.                  |

### Rodar localmente

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
set OPENAI_API_KEY=sk-...        # Windows;  no Linux/macOS: export OPENAI_API_KEY=sk-...
uvicorn main:app --reload --port 8000
```

### Variáveis de ambiente

- `OPENAI_API_KEY` (obrigatória) — chave da OpenAI. No Render está como `sync: false`, então defina no dashboard.
- `ALLOWED_ORIGINS` (opcional) — lista de origens CORS separadas por vírgula. Ex.: `https://meu-app.vercel.app,http://localhost:5173`. Se não definida, usa os padrões do `main.py`.

## Frontend (Vercel)

### Rodar localmente

```bash
cd frontend
npm install
npm run dev        # abre em http://localhost:5173
```

Por padrão o frontend chama `http://localhost:8000`. Para apontar a outro backend, crie um `.env` (veja `.env.example`) com:

```
VITE_API_URL=https://SEU-BACKEND.onrender.com
```

### Deploy na Vercel

1. Importe o repositório na Vercel e defina **Root Directory = `frontend`**.
2. Em *Environment Variables*, adicione `VITE_API_URL` com a URL do backend no Render.
3. Após o deploy, pegue a URL da Vercel e adicione-a ao CORS do backend — defina `ALLOWED_ORIGINS` no Render (ou edite a lista em `backend/main.py`).

## Notas

- O histórico fica **em memória** no backend: é perdido ao reiniciar o servidor e não é compartilhado entre múltiplas instâncias. Para produção, troque o `_session_store` por Redis/Postgres (LangChain tem integrações prontas).
- O plano free do Render hiberna após inatividade; a primeira requisição depois disso pode demorar alguns segundos.
