# PomeloGPT

**Your Private, State-of-the-Art AI Workspace**

PomeloGPT is a fully local, privacy-first AI chat application that runs entirely on your machine. It combines the power of modern Large Language Models (LLMs) with advanced Vision and Reranking technologies to enable secure and intelligent document interaction.

## Introduction

PomeloGPT is designed for users who demand privacy and performance. Unlike cloud-based solutions, PomeloGPT ensures that your data never leaves your device. All processing, from document analysis to response generation, occurs offline.

## Key Features

### Privacy-First Architecture
The application operates 100% locally. No data is transmitted to external servers, ensuring complete confidentiality of your documents and conversations.

### Ollama Model Manager
PomeloGPT includes a built-in manager for Ollama models, allowing users to seamlessly handle their AI models directly from the application interface.
- **Model Discovery**: View a curated list of high-performance models (e.g., Llama 3, Mistral, Gemma, Phi-3).
- **One-Click Installation**: Pull and install new models effortlessly.
- **Management**: View installed models, check details, and delete unused models to free up space.
- **Model Agnostic**: Switch between different models instantly to suit your specific task requirements.

### Dockerized Web Search
Integrated with SearXNG, PomeloGPT offers a privacy-respecting web search capability.
- **Containerized Deployment**: SearXNG runs in a dedicated Docker container, ensuring isolation and stability.
- **Real-Time Information**: Access up-to-date information from the web to augment the LLM's knowledge.
- **Privacy**: SearXNG acts as a metasearch engine that aggregates results without tracking your query history.

### Advanced Vision RAG
PomeloGPT utilizes state-of-the-art technologies for document understanding:
- **Florence-2 Vision Engine**: Capable of interpreting complex visual elements within documents, such as tables, charts, and layouts.
- **FlashRank Technology**: Employs advanced reranking algorithms to retrieve the most relevant information, significantly improving answer accuracy.

## System Architecture

The application is built on a modern, robust technology stack:
- **Frontend**: Electron and React provide a responsive and cross-platform user interface.
- **Backend**: FastAPI (Python) handles application logic and model interactions.
- **AI Engine**: Ollama serves the Large Language Models.
- **Search Engine**: SearXNG (via Docker) provides web search functionality.
- **Vector Database**: ChromaDB manages local vector storage for efficient document retrieval.

## Installation

### Prerequisites
Ensure the following software is installed on your system:
- **Python 3.10 or higher**
- **Node.js and npm**
- **Docker Desktop** (Required for Web Search)
- **Ollama** (Required for running LLMs)

### Setup Guide

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/nicorosaless/pomeloGPT.git
    cd pomeloGPT
    ```

2.  **Install Backend Dependencies**
    ```bash
    cd backend
    pip install -r requirements.txt
    cd ..
    ```

3.  **Install Frontend Dependencies**
    ```bash
    npm install
    ```

4.  **Start the Application**
    ```bash
    ./start.sh
    ```
    The startup script will automatically check for Docker, start the SearXNG container, and launch both the backend and frontend services.

## Usage

Upon launching, PomeloGPT provides a unified interface for chat, document analysis, and model management. Use the sidebar to navigate between chats, manage your model library, and configure application settings.

---
*Built for Privacy and Performance.*
