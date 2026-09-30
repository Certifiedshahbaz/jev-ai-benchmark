# Serali Jev AI Benchmark & Workforce Lab

An engineering benchmark and comparison laboratory evaluating **TypeSafe Jev** architecture against standard **LLM baselines** (e.g. Groq / Llama 3.3 70B, OpenAI) across accuracy, inference cost, latency, schema compliance, and decision determinism.

---

## 🚀 Key Features

- **Side-by-Side Live Benchmarking**: Compare TypeSafe Jev against LLM baselines on real-world IT & customer support triage workflows.
- **Accuracy & Ground-Truth Scoring**: Measure category classification accuracy, priority assignment, SLA risk detection, and policy compliance.
- **Cost & Token Economics**: Real-time tracking of token usage, input/output costs, and cost reduction ratios ($0.042/M tokens vs standard LLM rates).
- **Latency Benchmarking**: P50 / P95 / P99 latency tracking for high-throughput decision pipelines.
- **Interactive UI Dashboard**: Modern React + TypeScript + Recharts dashboard with dark mode, interactive charts, and live testing.
- **Modular FastAPI Backend**: Asynchronous architecture with clean separation of services, benchmarks, and analytics.

---

## 🏗️ System Architecture

```
jev_ai/
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── analytics/        # Run aggregators and metrics calculation
│   │   ├── benchmarks/       # Accuracy and latency benchmark runners
│   │   ├── models/           # Pydantic schemas (requests & responses)
│   │   ├── routers/          # API routes (health, analyze, benchmark)
│   │   ├── services/         # TypeSafe & LLM integrations
│   │   └── workflows/        # Support triage & deterministic policies
│   └── requirements.txt
├── frontend/                 # React + Vite + TypeScript Dashboard
│   ├── src/
│   │   ├── assets/           # Icons and illustrations
│   │   ├── App.tsx           # Benchmark & analysis dashboard UI
│   │   └── index.css         # Modern design system
│   └── package.json
├── data/                     # Benchmark datasets & stored test runs
└── .env.example              # Template configuration
```

---

## 🛠️ Getting Started

### 1. Prerequisites

- Python 3.10+
- Node.js 18+ & npm
- TypeSafe API Key
- LLM API Key (e.g. Groq, OpenAI, or compatible endpoint)

---

### 2. Backend Setup

1. Navigate to the backend directory and create a virtual environment:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate    # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp ../.env.example .env
   ```
   Edit `backend/.env` with your actual credentials:
   ```env
   TYPESAFE_API_KEY=your_typesafe_api_key_here
   JEV_MODEL=jev-1.13.0
   JEV_INPUT_PRICE_PER_MILLION=0.042

   LLM_PROVIDER=groq
   LLM_MODEL=llama-3.3-70b-versatile
   LLM_API_KEY=your_groq_api_key_here
   LLM_BASE_URL=https://api.groq.com/openai/v1
   ```

4. Start the backend development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   The backend API documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

### 3. Frontend Setup

1. In a new terminal, navigate to the frontend directory:
   ```bash
   cd frontend
   npm install
   ```

2. Start the Vite development server:
   ```bash
   npm run dev
   ```
   Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 📊 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check and provider connectivity status |
| `POST` | `/api/analyze` | Run single-ticket comparative analysis |
| `POST` | `/api/benchmark/accuracy` | Execute batch accuracy benchmark |
| `GET` | `/api/benchmark/runs` | Retrieve historical benchmark runs and stats |

---

## 🔒 Security Note

Never commit `.env` or files containing secret API keys. Both `.env` and `backend/.env` are ignored by Git via `.gitignore`. Always use `.env.example` as a template for team onboarding.

---

## 📜 License

MIT License. See individual files for additional details.
