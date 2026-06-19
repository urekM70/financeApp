# financeApp

A full-stack personal finance application built to automate expense tracking. Instead of manually entering data, this app uses Large Language Models (LLMs) to automatically parse, classify, and analyze transaction data directly from bank statement PDFs, CSVs, and Excel files.

## Key Features

- **AI-Powered PDF Parsing**: Extracts complex data from bank PDFs using a custom coordinate-based parsing engine combined with an LLM for structure detection.
- **Smart Categorization**: Automatically maps transaction descriptions to standardized spending categories, saving time on manual tagging.
- **Financial Insights**: Uses AI to generate natural language summaries and actionable insights based on your cash flow and spending habits.
- **Modern UI**: Built with React, Tailwind CSS, and Recharts for clean, responsive data visualization.

## Tech Stack

**Frontend**
- React with TypeScript & Vite
- Tailwind CSS & Radix UI
- TanStack React Query

**Backend**
- FastAPI (Python)
- SQLite / MySQL with SQLAlchemy
- PyMuPDF & Pandas for data processing
- OpenAI / OpenRouter API integrations

## How to Run Locally

### 1. Backend Setup

```bash
cd backend
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory and add your API key for the AI features:
```env
OPENAI_API_KEY=your_api_key_here
```

Start the backend server:
```bash
python main.py
```

### 2. Frontend Setup

Open a new terminal window:

```bash
cd frontend
npm install
npm run dev
```

*Note: If both environments are set up, you can run `npm run dev:full` from the `frontend` directory to start both servers at the same time.*
