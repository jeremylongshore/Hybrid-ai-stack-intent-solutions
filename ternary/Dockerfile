FROM ubuntu:22.04

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    clang \
    llvm \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone and build BitNet.cpp
RUN git clone --recursive https://github.com/microsoft/BitNet.git bitnet.cpp && \
    cd bitnet.cpp && \
    python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    mkdir -p build && \
    cd build && \
    cmake .. -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ && \
    make -j$(nproc)

# Install Flask for server
RUN pip3 install flask requests

# Copy server script (will be mounted at runtime)
# COPY ternary_server.py .

# Expose port
EXPOSE 8003

# Set environment variables
ENV BITNET_PATH=/app/bitnet.cpp
ENV MODEL_PATH=/models
ENV PYTHONUNBUFFERED=1

# Start server
CMD ["python3", "/app/ternary_server.py"]
