ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG PYTHON_VERSION=3.11

FROM gcr.io/distroless/python3-debian12:arm64 as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1 \
    DEBIAN_FRONTEND=noninteractive

# System packages with cache mounts
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        pkg-config \
        curl \
        ca-certificates \
        tini \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /build

# Copy requirements first for better caching
COPY gui/requirements.txt ./requirements.txt

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir -p /build/wheels && \
    echo "upgrading pip and setuptools" && \
    pip install --upgrade pip setuptools wheel &&\
    echo "upgrade complete" && \
    ls -lh /build/wheels/ | head -20 && \
    echo "total wheels built: $(ls -1 /build/wheels/ | wc -l)"


# make new dir structure for externals
RUN mkdir -p ./gui ./gui-api-bridge ./user-content ./RDP ./node ./contracts ./service-mesh ./sessions ./infrastructure/service-mesh ./infrastructure/kubernetes ./src/gui ./electron-gui \
&& printf "LUCID_GUI_RUNTIME_DIRECTORY" > ./gui/.keep && \
&& printf "LUCID_GUI_API_BRIDGE_RUNTIME_DIRECTORY" > ./gui-api-bridge/.keep && \
&& printf "LUCID_GUI_USER_CONTENT_RUNTIME_DIRECTORY" > ./user-content/.keep \
&& printf "LUCID_GUI_RDP_RUNTIME_DIRECTORY" > ./RDP/.keep \
&& printf "LUCID_GUI_NODE_RUNTIME_DIRECTORY" > ./node/.keep \
&& printf "LUCID_GUI_CONTRACTS_RUNTIME_DIRECTORY" > ./contracts/.keep \
&& printf "LUCID_GUI_SERVICE_MESH_RUNTIME_DIRECTORY" > ./service-mesh/.keep \
&& printf "LUCID_GUI_SESSIONS_RUNTIME_DIRECTORY" > ./sessions/.keep \
&& printf "LUCID_GUI_INFRASTRUCTURE_SERVICE_MESH_RUNTIME_DIRECTORY" > ./infrastructure/service-mesh/.keep \
&& printf "LUCID_GUI_INFRASTRUCTURE_KUBERNETES_RUNTIME_DIRECTORY" > ./infrastructure/kubernetes/.keep \
&& printf "LUCID_GUI_SRC_GUI_RUNTIME_DIRECTORY" > ./src/gui/.keep \
&& printf "LUCID_GUI_ELECTRON_GUI_RUNTIME_DIRECTORY" > ./electron-gui/.keep \
&& touch ./gui/.keep ./gui-api-bridge/.keep ./user-content/.keep ./RDP/.keep ./node/.keep ./contracts/.keep ./service-mesh/.keep ./sessions/.keep ./infrastructure/service-mesh/.keep ./infrastructure/kubernetes/.keep ./src/gui/.keep ./electron-gui/.keep \
&& echo "Externals directory structure created"


# Copy EXTERNALS to builder stage

COPY gui/ ./gui/
COPY ../gui-api-bridge/routers/ ./gui-api-bridge/routers/
COPY ../gui-api-bridge/services/ ./gui-api-bridge/services/
COPY ../gui-api-bridge/middleware/ ./gui-api-bridge/middleware/
COPY ../user-content/ ./user-content/
COPY ../RDP/ ./RDP/
COPY ../node/ ./node/
COPY ../contracts/ ./contracts/
COPY ../service-mesh/ ./service-mesh/

COPY ../sessions/ ./sessions/
COPY ../service-mesh/ ./service-mesh/
COPY ../infrastructure/service-mesh/ ./infrastructure/service-mesh/
COPY ../infrastructure/kubernetes/ ./infrastructure/kubernetes/
COPY ../src/gui/ ./src/gui/

FROM --platform=$TARGETPLATFORM gcr.io/distroless/java17-debian12:latest as runtime
#JAVA local/bin

COPY /usr/local/lib/java/openjdk-17/ ./runtime/usr/local/lib/java/openjdk-17/
COPY /usr/local/bin/java ./usr/local/bin/java
COPY /usr/local/bin/javac ./usr/local/bin/javac
COPY /usr/local/bin/jar ./usr/local/bin/jar
COPY /usr/local/bin/jtsdk ./usr/local/bin/jtsdk
COPY /usr/local/bin/jps ./usr/local/bin/jps
COPY /usr/local/bin/jstat ./usr/local/bin/jstat
COPY /usr/local/bin/jmap ./usr/local/bin/jmap
COPY /usr/local/bin/jhat ./usr/local/bin/jhat
COPY /usr/local/bin/jtool ./usr/local/bin/jtool
COPY /usr/local/bin/jinfo ./usr/local/bin/jinfo
COPY /usr/local/bin/jstack ./usr/local/bin/jstack
COPY /usr/local/bin/jconsole ./usr/local/bin/jconsole
COPY /usr/local/bin/jvisualvm ./usr/local/bin/jvisualvm
#JAVA lib
COPY /var/lib/sbin/java ./var/lib/sbin/java
COPY /var/lib/sbin/jtsdk ./var/lib/sbin/jtsdk
COPY /var/lib/sbin/javac ./var/lib/sbin/javac
COPY /var/lib/sbin/jar ./var/lib/sbin/jar
COPY /var/lib/sbin/jps ./var/lib/sbin/jps
COPY /var/lib/sbin/jstat ./var/lib/sbin/jmap
COPY /var/lib/sbin/jhat ./var/lib/sbin/jhat
COPY /var/lib/sbin/jtool ./var/lib/sbin/jtool
COPY /var/lib/sbin/jinfo ./var/lib/sbin/jinfo
COPY /var/lib/sbin/jstack ./var/lib/sbin/jstack
COPY /var/lib/sbin/jconsole ./var/lib/sbin/jconsole
COPY /var/lib/sbin/jvisualvm ./var/lib/sbin/jvisualvm
#JAVA run
COPY /var/run/javac ./var/run/javac
COPY /var/run/jar ./var/run/jar
COPY /var/run/jps ./var/run/jps
COPY /var/run/jstat ./var/run/jstat
COPY /var/run/jmap ./var/run/jmap
COPY /var/run/jhat ./var/run/jhat
COPY /var/run/jtool ./var/run/jtool
COPY /var/run/jinfo ./var/run/jinfo
#COPY to runtime builder stage
COPY ../electron-gui/ ./electron-gui/
COPY ../
# Set non-root user for security
USER nonroot
WORKDIR /app
COPY --from=builder --chown=65532:65532 /build/gui /app/gui
COPY --from=builder --chown=65532:65532 /build/gui-api-bridge/routers /app/gui-api-bridge/routers
COPY --from=builder --chown=65532:65532 /build/gui-api-bridge/services /app/gui-api-bridge/services
COPY --from=builder --chown=65532:65532 /build/gui-api-bridge/middleware /app/gui-api-bridge/middleware
COPY --from=builder --chown=65532:65532 /build/user-content/ /app/user-content/
COPY --from=builder --chown=65532:65532 /build/RDP/ /app/RDP/
COPY --from=builder --chown=65532:65532 /build/node/ /app/node/
COPY --from=builder --chown=65532:65532 /build/contracts/ /app/contracts/
COPY --from=builder --chown=65532:65532 /build/service-mesh/ /app/service-mesh
COPY --from=builder --chown=65532:65532 /build/sessions/ /app/sessions/
COPY --from=builder --chown=65532:65532 /build/infrastructure/service-mesh/ /app/infrastructure/service-mesh/
COPY --from=builder --chown=65532:65532 /build/infrastructure/kubernetes/ /app/infrastructure/kubernetes/
COPY --from=builder --chown=65532:65532 /build/src/gui/ /app/src/gui/

# runtime local.bin COPY
COPY --from=runtime --chown=65532:65532 /runtime/usr/local/lib/java/openjdk-17/ /usr/local/lib/java/openjdk-17/
COPY --from=runtime --chown=65532:65532 /runtime/usr/local/bin/java /usr/local/bin/java
COPY --from=runtime --chown=65532:65532 /runtime/usr/local/bin/javac /usr/local/bin/javac
COPY --from=runtime --chown=65532:65532 /runtime/usr/local/bin/jar /usr/local/bin/jar
COPY --from=runtime --chown=65532:65532 /runtime/usr/local/bin/jps /usr/local/bin/jps
COPY --from=runtime --chown=65532:65532 /runtime/usr/local/bin/jstat /usr/local/bin/jstat
COPY --from=runtime --chown=65532:65532 /runtime/usr/local/bin/jmap /usr/local/bin/jmap
COPY --from=runtime --chown=65532:65532 /runtime/usr/local/bin/jhat /usr/local/bin/jhat
COPY --from=runtime --chown=65532:65532 /runtime/usr/local/bin/jtool /usr/local/bin/jtool
COPY --from=runtime --chown=65532:65532 /runtime/usr/local/bin/jinfo /usr/local/bin/jinfo
COPY --from=runtime --chown=65532:65532 /runtime/usr/local/bin/jstack /usr/local/bin/jstack
COPY --from=runtime --chown=65532:65532 /runtime/usr/local/bin/jconsole /usr/local/bin/jconsole
COPY --from=runtime --chown=65532:65532 /runtime/usr/local/bin/jvisualvm /usr/local/bin/jvisualvm
# runtime sbin COPY 
COPY --from=runtime --chown=65532:65532 /runtime/var/lib/sbin/java /var/lib/sbin/java
COPY --from=runtime --chown=65532:65532 /runtime/var/lib/sbin/jtsdk /var/lib/sbin/jtsdk
COPY --from=runtime --chown=65532:65532 /runtime/var/lib/sbin/javac /var/lib/sbin/javac
COPY --from=runtime --chown=65532:65532 /runtime/var/lib/sbin/jar /var/lib/sbin/jar
COPY --from=runtime --chown=65532:65532 /runtime/var/lib/sbin/jps /var/lib/sbin/jps
COPY --from=runtime --chown=65532:65532 /runtime/var/lib/sbin/jstat /var/lib/sbin/jstat
COPY --from=runtime --chown=65532:65532 /runtime/var/lib/sbin/jmap /var/lib/sbin/jmap
COPY --from=runtime --chown=65532:65532 /runtime/var/lib/sbin/jhat /var/lib/sbin/jhat
COPY --from=runtime --chown=65532:65532 /runtime/var/lib/sbin/jtool /var/lib/sbin/jtool
COPY --from=runtime --chown=65532:65532 /runtime/var/lib/sbin/jinfo /var/lib/sbin/jinfo
COPY --from=runtime --chown=65532:65532 /runtime/var/lib/sbin/jstack /var/lib/sbin/jstack
COPY --from=runtime --chown=65532:65532 /runtime/var/lib/sbin/jconsole /var/lib/sbin/jconsole
COPY --from=runtime --chown=65532:65532 /runtime/var/lib/sbin/jvisualvm /var/lib/sbin/jvisualvm
# runtime run COPY
COPY --from=runtime --chown=65532:65532 /runtime/var/run/javac /var/run/javac
COPY --from=runtime --chown=65532:65532 /runtime/var/run/jar /var/run/jar
COPY --from=runtime --chown=65532:65532 /runtime/var/run/jps /var/run/jps
COPY --from=runtime --chown=65532:65532 /runtime/var/run/jstat /var/run/jstat
COPY --from=runtime --chown=65532:65532 /runtime/var/run/jmap /var/run/jmap
COPY --from=runtime --chown=65532:65532 /runtime/var/run/jhat /var/run/jhat
COPY --from=runtime --chown=65532:65532 /runtime/var/run/jtool /var/run/jtool
COPY --from=runtime --chown=65532:65532 /runtime/var/run/jinfo /var/run/jinfo
COPY --from=runtime --chown=65532:65532 /runtime/var/run/jstack /var/run/jstack
COPY --from=runtime --chown=65532:65532 /runtime/var/run/jconsole /var/run/jconsole
COPY --from=runtime --chown=65532:65532 /runtime/var/run/jvisualvm /var/run/jvisualvm

COPY --from=runtime --chown=65532:65532 /runtime/electron-gui/ /app/electron-gui/
# Expose port
EXPOSE 8000

# Run the application
CMD ["python3", "app/gui/entrypoint.py"]
