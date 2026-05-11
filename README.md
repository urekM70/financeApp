# Finance Flow - Full Stack Application Architecture & Technical Documentation

This document serves as the comprehensive technical documentation for **Finance Flow**, a full-stack personal finance application. This project provides intelligent, automated management of personal finances by heavily leveraging Large Language Models (LLMs) to parse, classify, and analyze transaction data from various formats (CSVs, Excel, PDFs).

The application is built using a modern, decoupled architecture featuring a **React (TypeScript)** frontend and a **FastAPI (Python)** backend.

---

## Table of Contents

1. [System Architecture & Tech Stack](#1-system-architecture--tech-stack)
2. [Frontend Documentation](#2-frontend-documentation)
   - [Core Features & State Management](#core-features--state-management)
   - [Key Pages & Components](#key-pages--components)
3. [Backend Documentation](#3-backend-documentation)
   - [Database Schema & Models](#database-schema--models)
   - [Transaction Processing & LLM Integration](#transaction-processing--llm-integration)
   - [Advanced PDF Parsing](#advanced-pdf-parsing)
   - [Authentication & Security](#authentication--security)
   - [API Endpoints Reference](#api-endpoints-reference)
4. [Project Setup & Installation](#4-project-setup--installation)

---

## 1. System Architecture & Tech Stack

The project utilizes a decoupled client-server architecture. The frontend SPA communicates with the backend REST API using standard HTTP methods and JSON payloads, secured by JWTs.

### Frontend Tech Stack
*   **Core:** React (v19), TypeScript, Vite
*   **Routing:** React Router v7 (`react-router-dom`)
*   **State Management:** TanStack React Query (`@tanstack/react-query`)
*   **Styling:** Tailwind CSS (v4)
*   **UI Primitives:** Radix UI (`shadcn/ui` based), Lucide React
*   **Data Visualization:** Recharts
*   **Localization:** `i18next`, `react-i18next`

### Backend Tech Stack
*   **Framework:** FastAPI (Asynchronous Python REST framework)
*   **Database & ORM:** MySQL, SQLAlchemy (v2.0+), `pymysql`
*   **Data Processing:** Pandas (tabular manipulation), PyMuPDF (PDF coordinate extraction)
*   **Authentication:** JWT (JSON Web Tokens), `passlib` (bcrypt)
*   **AI Integrations:** `openai` and `zhipuai` Python clients for OpenRouter/Zhipu endpoints.

---

## 2. Frontend Documentation

The frontend (`frontend/`) is a highly modular, localized, and responsive Single Page Application. 

### Core Features & State Management

*   **Authentication & Protected Routes:** Managed globally via `AuthContext.tsx`. An Axios interceptor automatically attaches the JWT (stored in `localStorage`) to outgoing requests. Unauthenticated users are redirected to `/login` via a custom `<ProtectedRoute>` wrapper.
*   **Data Fetching (React Query):** `@tanstack/react-query` is used to fetch, cache, and synchronize data with the FastAPI backend. It abstracts loading states, handles errors, and caches data (default 5-minute stale time) to ensure UI responsiveness.
*   **Preferences Context:** `PreferencesContext.tsx` manages user-specific settings like preferred Currency (USD, EUR, GBP) and Language, persisting them across sessions.
*   **Internationalization (i18n):** Implemented with `react-i18next`. The app auto-detects browser language and passes the chosen locale to the backend via the `Accept-Language` header for synchronized server-side error translation.

### Key Pages & Components

*   **`Dashboard.tsx`**: The main landing page post-login, displaying KPIs, recent transactions, and AI insights.
*   **`Transactions.tsx`**: A comprehensive data table of parsed transactions with CRUD capabilities.
*   **`Upload.tsx`**: The interface for uploading Bank statements (CSV/PDF). It hits the backend `/preview` endpoint to let users verify LLM parsing before committing to the database.
*   **`Budgeting.tsx`**: Visualizes spending against user-defined hard limits per category.
*   **`Reports.tsx`**: Utilizes **Recharts** for dynamic charts (Pie, Bar, Line) visualizing cash flow, accompanied by an LLM-generated narrative summary.

---

## 3. Backend Documentation

The backend (`backend/`) handles complex heuristic document parsing, AI-driven data insights, and standard CRUD operations.

### Database Schema & Models
*(Implemented in `backend/db/models.py`)*

*   **`users`**: Manages authentication (email, hashed password).
*   **`accounts`**: Groups transactions by financial institution.
*   **`transactions`**: The core entity (date, amount, description, category, account_id).
*   **`budgets`**: Spending limits mapped to unique categories.
*   **`report_cache`**: A highly optimized caching table for LLM reports. It stores a SHA-256 hash of the transaction dataset to bypass expensive LLM recalculations if the data hasn't changed.

### Transaction Processing & LLM Integration
*(Implemented in `backend/processing/transaction_parser.py` & `core/llm_service.py`)*

*   **Intelligent Column Mapping:** The system sends raw CSV/Excel headers to an LLM to map foreign/proprietary column names (e.g., "Datum", "Breme") to the standardized schema.
*   **Auto-Categorization:** Uncategorized transactions are batched (50 at a time to manage API costs) and sent to the LLM to map descriptions to strict standard categories.
*   **Insights & Narratives:** LLMs translate raw Pandas calculations into actionable JSON insights and natural language reports.
*   **Caching Strategy:** The service layer utilizes in-memory dictionaries (`_category_cache`, `_structure_cache`, `_insights_cache`) keyed by string hashes to prevent exhausting API quotas during duplicate requests.

### Advanced PDF Parsing
*(Implemented in `backend/processing/pdf_parser.py`)*

Financial PDFs are visually rendered, not tabular. Standard parsers often fail. The backend solves this by:
1.  **Coordinate Extraction:** Using `pymupdf` to extract the raw text and exact X/Y bounding box coordinates for every word on the page.
2.  **LLM Structural Detection:** Sending a layout sample to an LLM to act as an optical layout detector, returning the ordered names of headers and amount formatting (single vs. debit/credit columns).
3.  **Zone Calculation:** Calculating vertical "Zones" (column boundaries) based on the midpoint X-coordinates of detected headers.
4.  **Data Alignment:** Mapping words to columns based on their geometric intersection with the calculated Zones.

### Authentication & Security
*   Implements an OAuth2 Password Bearer flow.
*   Passwords are irreversibly hashed using `bcrypt`.
*   Protected endpoints utilize a `Depends(get_current_user)` dependency injection that decodes the JWT and validates signatures.

### API Endpoints Reference

*   **Auth:** `POST /auth/register`, `POST /auth/token`, `GET /auth/me`
*   **Transactions:** `GET /`, `POST /`, `PUT /{id}`, `DELETE /{id}`, `POST /bulk/delete`
*   **Processing:** 
    *   `POST /preview`: Runs parsing logic and returns a preview *without* mutating the database.
    *   `POST /upload`: Commits an uploaded file to the database.
    *   `GET /report/summary`: Aggregates data and generates an LLM narrative (utilizing SHA-256 DB caching).
*   **Budgets:** `GET /`, `POST /`, `PUT /{id}`, `DELETE /{id}`

---

## 4. Project Setup & Installation

### Prerequisites
*   Node.js (v18+) & npm (v9+)
*   Python (v3.9+)
*   MySQL Server (local or remote)

### Step 1: Backend Setup
1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Configure Environment Variables:
    Copy `.env.example` to `.env` (or create a new `.env` file in the `backend/` directory):
    ```env
    DB_USER=root
    DB_PASSWORD=your_mysql_password
    DB_HOST=localhost
    DB_PORT=3306
    DB_NAME=finance_db
    SECRET_KEY=your-secure-random-string
    LLM_API_KEY=your_api_key
    OPENROUTER_API_KEY=your_openrouter_api_key
    LLM_MODEL=gpt-4-turbo # Or preferred model
    ```
5.  Create the MySQL database:
    ```sql
    CREATE DATABASE finance_db;
    ```
6.  Start the backend server:
    ```bash
    python main.py
    # API available at http://localhost:8000
    # Swagger Docs at http://localhost:8000/docs
    ```

### Step 2: Frontend Setup
1.  Open a new terminal and navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Start the frontend development server:
    ```bash
    npm run dev
    # App available at http://localhost:5173
    ```

### Optional: Full Stack Quick Start
If both environments are configured and dependencies are installed, you can start **both** the frontend and backend simultaneously from the `frontend` directory using the custom convenience script:
```bash
cd frontend
npm run dev:full