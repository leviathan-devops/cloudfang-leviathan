FROM debian:bookworm-slim

ENV OPENFANG_HOME=/data
EXPOSE 4200

CMD ["/bin/sh", "-c", "echo CONTAINER_START && sleep 300"]
