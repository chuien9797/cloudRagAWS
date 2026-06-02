FROM ollama/ollama:latest

ENV OLLAMA_MODELS=/models

RUN mkdir -p /models && ollama serve & OLLAMA_PID=$! && \
    sleep 8 && \
    ollama pull qwen2:1.5b && \
    kill $OLLAMA_PID; exit 0