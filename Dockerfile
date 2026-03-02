FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for Document Parsing and OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces require running as a non-root user for security.
# We map this to UID 1000 and bind to port 7860.
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Switch to the new user and set working directory
WORKDIR $HOME/app
COPY --chown=user . $HOME/app

# Install python dependencies locally (for the user)
RUN pip install --no-cache-dir --user -r requirements.txt

# Download the spaCy model explicitly
RUN python -m spacy download en_core_web_md

# Hugging Face Spaces standard port is 7860
EXPOSE 7860

# Run the FastAPI app with uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
