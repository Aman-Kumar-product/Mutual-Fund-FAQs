import streamlit as st
import asyncio
import os
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Import the core logic from the existing modules
from guardrails.pii_filter import contains_pii
from guardrails.classifier import classify
from retrieval.retriever import retrieve
from generation.prompt_builder import build_prompt
from generation.llm_client import generate_answer
from api.main import get_expected_sources_count

# Page config
st.set_page_config(
    page_title="MF FAQ Assistant",
    page_icon="🪙",
    layout="centered"
)

# Custom CSS for some minor styling tweaks
st.markdown("""
<style>
    .source-link {
        font-size: 0.85rem;
        color: #60a5fa;
        text-decoration: none;
    }
    .source-link:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

st.title("🪙 MF FAQ Assistant")
st.markdown("Facts-only. No investment advice. Ask me factual questions about our indexed Mutual Fund schemes.")

with st.expander("View Available Funds & Supported Facts"):
    st.markdown("""
    **Available Funds:**
    HDFC Mid Cap, HDFC Silver ETF, HDFC Defence, HDFC Equity, HDFC Small Cap, SBI Gold Fund, and more...
    
    **Supported Facts:**
    Expense Ratio, Minimum SIP & Investment, Exit Load, Riskometer Rating, Fund Manager, Benchmark & Category, Asset Allocation, Investment Objective, Inception Date & NAV.
    """)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display sources if they exist
        if "sources" in message and message["sources"]:
            st.divider()
            for source in message["sources"]:
                st.markdown(f"🔗 [{source['name']}]({source['url']}) (Last updated: {source.get('ingested_at', 'N/A')[:10]})")

def is_english(text: str) -> bool:
    if not text:
        return False
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    return (ascii_chars / len(text)) > 0.8

# Accept user input
if prompt := st.chat_input("Type your question..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # Validation Pipeline
        if not is_english(prompt):
            error_msg = "I can only process queries in English. Please ask your question in English."
            message_placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            st.stop()
            
        if contains_pii(prompt):
            error_msg = "Your query was refused because it contains personally identifiable information (PII)."
            message_placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            st.stop()
            
        if classify(prompt) == "advisory":
            error_msg = "I am a facts-only assistant and cannot provide investment advice or recommendations. Please consult a registered investment advisor or AMFI."
            message_placeholder.warning(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            st.stop()
            
        # RAG Pipeline
        with st.spinner("Searching knowledge base..."):
            try:
                # Retrieve chunks synchronously (Streamlit is sync by default)
                # Since retriever uses chromadb which is sync, we can just call it
                chunks = retrieve(prompt, 15)
                
                if not chunks:
                    no_info_msg = "I don't have verified information on this. Please check the official HDFC AMC website or AMFI."
                    message_placeholder.markdown(no_info_msg)
                    st.session_state.messages.append({"role": "assistant", "content": no_info_msg})
                else:
                    system_prompt, user_msg = build_prompt(prompt, chunks)
                    answer = generate_answer(system_prompt, user_msg)
                    
                    # Process sources
                    unique_urls = set()
                    sources = []
                    max_sources = get_expected_sources_count(prompt)
                    
                    for chunk in chunks:
                        meta = chunk.get("metadata", {})
                        url = meta.get("source_url")
                        if url and url not in unique_urls:
                            unique_urls.add(url)
                            sources.append({
                                "name": meta.get("source_name"),
                                "url": url,
                                "ingested_at": meta.get("ingested_at")
                            })
                            if len(sources) >= max_sources:
                                break
                    
                    # Display the answer
                    message_placeholder.markdown(answer)
                    
                    # Display sources immediately in the UI
                    if sources:
                        st.divider()
                        for source in sources:
                            st.markdown(f"🔗 [{source['name']}]({source['url']}) (Last updated: {source.get('ingested_at', 'N/A')[:10]})")
                    
                    # Save to state
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer,
                        "sources": sources
                    })
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
