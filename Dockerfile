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

# Pre-bake config.toml with correct TOML structure.
# CRITICAL: api_listen MUST be at root level (before any [section] header).
# If placed inside [default_model], TOML parses it as default_model.api_listen
# and the server falls back to 127.0.0.1:4200 which Railway can't reach.
RUN mkdir -p /root/.openfang \
 && printf 'api_listen = "0.0.0.0:4200"\n\n[default_model]\nprovider = "gemini"\nmodel = "gemini-2.5-flash"\napi_key_env = "GEMINI_API_KEY"\n\n[memory]\ndecay_rate = 0.05\n' \
    > /root/.openfang/config.toml

ENV OPENFANG_HOME=/data
ENV RUST_BACKTRACE=1
EXPOSE 4200
CMD ["/bin/sh", "-c", "openfang init --quick && openfang start"]
