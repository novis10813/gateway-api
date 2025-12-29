FROM ghcr.io/astral-sh/uv:python3.9-alpine

WORKDIR /workspace

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY app ./app

# Set PYTHONPATH so imports from app/ work correctly
ENV PYTHONPATH=/workspace/app

# Expose the API port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
