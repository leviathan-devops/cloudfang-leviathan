# Leviathan DevOps — OpenFang deployment
# Uses .deb package for correct dependency resolution (libssl, libsqlite3 etc.)
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y ca-certificates curl && rm -rf /var/lib/apt/lists/*

# Install OpenFang via .deb — handles all dynamic lib deps automatically
RUN curl -fsSL \
  "https://github.com/RightNow-AI/openfang/releases/download/v0.1.1/OpenFang_0.1.0_amd64.deb" \
  -o /tmp/openfang.deb \
  && dpkg -i /tmp/openfang.deb \
  && rm /tmp/openfang.deb

# Bake in Leviathan config at /etc/openfang/config.toml
# CRITICAL: api_listen MUST be at root level, before any [section] header
RUN mkdir -p /etc/openfang && cat > /etc/openfang/config.toml << 'TOML'
api_listen = "0.0.0.0:4200"
usage_footer = "Full"

[default_model]
provider = "deepseek"
model = "deepseek-chat"
api_key_env = "DEEPSEEK_API_KEY"

[memory]
decay_rate = 0.05

[compaction]
threshold = 80
keep_recent = 20
max_summary_tokens = 1024

[channels.discord]
bot_token_env = "DISCORD_BOT_TOKEN"
guild_ids = ["1475947548811202613"]

[channels.discord.overrides]
dm_policy = "respond"
group_policy = "respond"
TOML

# /data = OPENFANG_HOME (db, workspace, logs)
RUN mkdir -p /data
ENV OPENFANG_HOME=/data
ENV RUST_BACKTRACE=1
EXPOSE 4200

# Start directly — OpenFang auto-inits db on first run
CMD ["/bin/sh", "-c", "openfang start --config /etc/openfang/config.toml"]
