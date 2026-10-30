# One image for every run: Blender + xvfb + ffmpeg (as in BVB's sandbox) plus the
# Claude Code and Codex CLIs. It holds no credentials; each run mounts one file.
#
#   docker build -t erroragent:latest --build-arg UID=$(id -u) --build-arg GID=$(id -g) docker/
FROM --platform=linux/amd64 ubuntu:22.04

ARG BLENDER_MAJOR=5.2
ARG BLENDER_VERSION=5.2.3
# pinned to the versions logged in on the host when this suite was written
ARG CLAUDE_CODE_VERSION=2.1.312
ARG CODEX_VERSION=0.157.0
ARG UID=1000
ARG GID=1000
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl xz-utils xvfb xauth ffmpeg python3 python3-pip \
        git ripgrep procps \
        libgl1-mesa-glx libgl1-mesa-dri libegl1 libxi6 libxrender1 libxxf86vm1 libxfixes3 libxkbcommon0 libsm6 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fSL "https://download.blender.org/release/Blender${BLENDER_MAJOR}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
        -o /tmp/blender.tar.xz \
    && mkdir -p /opt/blender \
    && tar -xf /tmp/blender.tar.xz -C /opt/blender --strip-components=1 \
    && rm /tmp/blender.tar.xz \
    && ln -s /opt/blender/blender /usr/local/bin/blender

RUN python3 -m pip install --no-cache-dir numpy Pillow

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION} @openai/codex@${CODEX_VERSION} \
    && rm -rf /var/lib/apt/lists/*

RUN printf '#!/bin/bash\nexec xvfb-run -a blender --background "$@"\n' > /usr/local/bin/blender_run \
    && chmod +x /usr/local/bin/blender_run

# The agent runs as the host user, so everything it writes belongs to that user
# and Claude Code accepts bypassPermissions (it refuses it as root).
RUN groupadd -g ${GID} agent && useradd -m -u ${UID} -g ${GID} -s /bin/bash agent

WORKDIR /workspace
