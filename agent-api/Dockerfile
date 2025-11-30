FROM python:3.11-slim

ARG USER=app
ARG APP_DIR=/app
ARG INSTALL_RUST=false
ENV APP_DIR=${APP_DIR}

# Install system dependencies required by Manim and its extras, including TeX Live for LaTeX rendering
# - cairo/pango (pycairo/manimpango)
# - ffmpeg (video encoding)
# - OpenGL dev libs (moderngl / pyopengl)
# - BLAS/LAPACK/gfortran (scipy / numpy wheels fallback)
# - TeX Live toolchain (pdflatex/xelatex, latexmk, dvisvgm, fonts, utilities)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      pkg-config \
      python3-dev \
      libffi-dev \
      libcairo2 \
      libcairo2-dev \
      libpango-1.0-0 \
      libpango1.0-dev \
      libglib2.0-0 \
      ffmpeg \
      fonts-dejavu-core \
      git \
      curl \
      ca-certificates \
      wget \
      unzip \
      postgresql-client \
      # OpenGL / moderngl deps
      libgl1-mesa-dev \
      libglu1-mesa-dev \
      libx11-dev \
      libxrandr-dev \
      libxinerama-dev \
      libxcursor-dev \
      libxi-dev \
      # SciPy / numeric libs (help build or provide optimized libs)
      gfortran \
      libopenblas-dev \
      liblapack-dev \
      # TeX Live (LaTeX) for Manim's tex rendering
      texlive \
      texlive-latex-recommended \
      texlive-latex-extra \
      texlive-fonts-recommended \
      texlive-fonts-extra \
      texlive-xetex \
      texlive-pictures \
      texlive-science \
      latexmk \
      dvisvgm \
      lmodern \
      dvipng \
      ghostscript \
      poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install dockerize (used by entrypoint to wait for DB)
ENV DOCKERIZE_VERSION=v0.7.0
RUN wget -q https://github.com/jwilder/dockerize/releases/download/${DOCKERIZE_VERSION}/dockerize-linux-amd64-${DOCKERIZE_VERSION}.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-${DOCKERIZE_VERSION}.tar.gz \
    && rm dockerize-linux-amd64-${DOCKERIZE_VERSION}.tar.gz

# Optional: install Rust toolchain if requested (for building Rust-based pip packages)
RUN if [ "$INSTALL_RUST" = "true" ] ; then \
      curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y ; \
      export PATH="/root/.cargo/bin:$PATH" ; \
    fi

# Create non-root user and home directory
RUN groupadd -g 61000 ${USER} \
  && useradd -g 61000 -u 61000 -ms /bin/bash -d ${APP_DIR} ${USER}

WORKDIR ${APP_DIR}

# Copy requirements and install into a virtualenv placed outside /app (so bind-mounting /app does not hide installed packages)
COPY requirements.txt /tmp/requirements.txt

# Create virtualenv outside of /app to avoid mount collisions, and install requirements deterministically at build time.
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

# Ensure the virtualenv is on PATH for subsequent container runs
ENV PATH="/opt/venv/bin:$PATH"

# Copy project files
COPY . .

# Set ownership on the application directory to the non-root user
RUN chown -R ${USER}:${USER} ${APP_DIR}

# Switch to non-root user for runtime
USER ${USER}

# Keep existing entrypoint / CMD used by the project
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["chill"]
