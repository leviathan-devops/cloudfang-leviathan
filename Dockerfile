# syntax=docker/dockerfile:1
FROM rust:1-slim-bookworm AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y pkg-config libssl-dev && rm -rf /var/lib/apt/lists/*
COPY Cargo.toml Cargo.lock ./
COPY crates ./crates
COPY xtask ./xtask
COPY agents ./agents
COPY packages ./packages
RUN cargo build --release --bin openfang

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/target/release/openfang /usr/local/bin/
COPY --from=builder /build/agents /opt/openfang/agents

# Pre-bake config.toml so startup doesn't depend on env-var detection.
# Two critical fixes:
#   1. api_listen = 0.0.0.0:4200  →  Railway needs 0.0.0.0, not 127.0.0.1
#   2. provider = gemini           →  avoids groq MissingApiKey crash on boot
# User must set GEMINI_API_KEY in Railway service variables.
RUN mkdir -p /root/.openfang \
 && printf '[default_model]\nprovider = "gemini"\nmodel = "gemini-2.5-flash"\napi_key_env = "GEMINI_API_KEY"\n\napi_listen = "0.0.0.0:4200"\n\n[memory]\ndecay_rate = 0.05\n' \
    > /root/.openfang/config.toml

ENV OPENFANG_HOME=/data
EXPOSE 4200
# init is idempotent -- config.toml already exists, so init skips creation.
# start boots the kernel + HTTP server on 0.0.0.0:4200.
CMD ["/bin/sh", "-c", "openfang init --quick && openfang start"]
