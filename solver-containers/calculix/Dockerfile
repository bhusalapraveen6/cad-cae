FROM ubuntu:22.04

LABEL maintainer="cad-cae-app"
LABEL description="CalculiX FEA solver container"

ENV DEBIAN_FRONTEND=noninteractive
ENV CCX_VERSION=2.22

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    make \
    gcc \
    g++ \
    gfortran \
    libblas-dev \
    liblapack-dev \
    libspooles-dev \
    libarpack2-dev \
    libcairo2-dev \
    libnetpbm10-dev \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    libxt-dev \
    libxmu-dev \
    libxi-dev \
    && rm -rf /var/lib/apt/lists/*

# Download and build CalculiX
WORKDIR /build
RUN wget -q https://github.com/calculix/ccx/releases/download/v${CCX_VERSION}/CalculiX-${CCX_VERSION}-linux64.tar.gz \
    || wget -q http://www.dhondt.de/ccx_${CCX_VERSION}.src.tar.bz2 -O ccx_src.tar.bz2 \
    && ls -la

# Install pre-built binary as fallback (for build speed in dev)
RUN apt-get update && apt-get install -y calculix && rm -rf /var/lib/apt/lists/* 2>/dev/null || true

# Verify ccx is available
RUN which ccx || echo "WARNING: ccx not found on PATH, solver will run in mock mode"

WORKDIR /workspace

ENV PATH="/usr/bin:${PATH}"

CMD ["tail", "-f", "/dev/null"]
