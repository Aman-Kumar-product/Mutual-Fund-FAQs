@echo off
echo Starting Mutual Fund RAG Data Pipeline...
echo ===========================================

cd /d "C:\Mutual Fund RAG"
set PYTHON_EXE=.venv\Scripts\python.exe

echo [1/4] Updating Metadata...
%PYTHON_EXE% update_metadata.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo [2/4] Running Ingestion (Scraping)...
%PYTHON_EXE% ingestion\run_ingestion.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo [3/4] Running Extraction (Groq LLM)...
%PYTHON_EXE% ingestion\extractor.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo [4/4] Building Index (Chunking and Embedding)...
%PYTHON_EXE% -m indexing.build_index
if %errorlevel% neq 0 exit /b %errorlevel%

echo ===========================================
echo Pipeline Complete!
