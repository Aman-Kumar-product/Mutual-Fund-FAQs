# Mutual Fund FAQ Assistant (RAG)

A full-stack Retrieval-Augmented Generation (RAG) assistant designed to answer factual questions about HDFC Mutual Fund schemes. It ingests public documents, indexes them using local BGE embeddings in ChromaDB, and uses the Groq LLM API to generate concise, accurate answers with citations. The system includes strict guardrails to prevent giving investment advice and to filter out PII.

## Setup Instructions

1. **Clone the repository and enter the directory**:
   ```bash
   git clone <repository_url>
   cd "Mutual Fund RAG"
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the project root and add your Groq API key:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

## Running the Pipeline

Before starting the API, you must ingest the data and build the vector index.

1. **Ingest Data**:
   ```bash
   python -m ingestion.run_ingestion
   ```
   *This fetches raw HTML/text from the sources in `data/metadata.json` and saves them to `data/raw/`.*

2. **Build the Index**:
   ```bash
   python -m indexing.build_index
   ```
   *This chunks the data, generates embeddings using `BAAI/bge-base-en-v1.5`, and populates the local ChromaDB database.*

## Starting the API and UI

To interact with the assistant, you need to run both the FastAPI server and the UI.

1. **Start the API Server**:
   ```bash
   python -m uvicorn api.main:app --reload --port 8000
   ```

2. **Serve the UI** (in a new terminal window):
   ```bash
   python -m http.server 3000 --directory ui/
   ```

Open your browser and navigate to `http://localhost:3000`.

## Example Questions to Demo

Here are 6 example queries that demonstrate the assistant's capabilities and guardrails:

1. **"What is the expense ratio of HDFC Mid Cap Fund?"** (Factual question about a specific fund)
2. **"What is the minimum SIP amount for HDFC Equity Fund?"** (Factual data extraction)
3. **"How do I download a capital gains statement from Groww?"** (Procedural question)
4. **"What is the exit load for HDFC Defence Fund?"** (Another factual check)
5. **"Should I invest in HDFC Mid Cap?"** (Triggers the advisory guardrail refusal)
6. **"My PAN is ABCDE1234F. What is the minimum SIP?"** (Triggers the PII filter refusal)
