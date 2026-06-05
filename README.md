# LangChain Chat 📚

> ⚠️ **Projeto de estudo.** Este repositório foi criado para fins de aprendizado — explorando como integrar **FastAPI + LangChain** com um frontend **React + Vite**, streaming de respostas token a token e deploy em nuvem. Não é um produto pronto para produção (veja as [limitações](#limitações)).

Um chat simples com IA, com respostas em streaming (token a token) e histórico de conversa por sessão.

## O que eu aprendi / pratiquei aqui

- Construir uma API com **FastAPI** e respostas em streaming via **SSE** (Server-Sent Events).
- Usar **LangChain (LCEL)**: encadear `prompt | llm` e gerenciar histórico de conversa com `RunnableWithMessageHistory`.
- Consumir um stream no **React** e renderizar a resposta conforme ela chega.
- Configurar **CORS**, variáveis de ambiente e deploy (backend no **Render**, frontend na **Vercel**).

## Stack

| Camada    | Tecnologias                                   |
| --------- | --------------------------------------------- |
| Backend   | Python, FastAPI, LangChain (LCEL), OpenAI     |
| Frontend  | React 18, Vite                                |
| Deploy    | Render (backend), Vercel (frontend)           |

## Estrutura

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

## Backend

Endpoints:

| Método | Rota                  | Descrição                                                           |
| ------ | --------------------- | ------------------------------------------------------------------- |
| GET    | `/health`             | Healthcheck.                                                        |
| POST   | `/chat`               | Recebe `{ message, session_id }` e devolve um stream SSE de tokens. |
| DELETE | `/chat/{session_id}`  | Limpa o histórico de uma sessão.                                    |

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

## Frontend

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

## Limitações

Por ser um projeto de estudo, há simplificações intencionais:

- O histórico fica **em memória** no backend: é perdido ao reiniciar o servidor e não é compartilhado entre múltiplas instâncias. Para produção, trocaria o `_session_store` por Redis/Postgres (LangChain tem integrações prontas).
- O plano free do Render hiberna após inatividade; a primeira requisição depois disso pode demorar alguns segundos.
- Sem autenticação, rate limiting ou testes automatizados.
