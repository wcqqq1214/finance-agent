#!/bin/bash

# Use localhost proxy (works in WSL2)
PROXY_HOST="127.0.0.1"
PROXY_PORT=7890

echo "配置代理: http://${PROXY_HOST}:${PROXY_PORT}"

# 设置代理环境变量
export http_proxy="http://${PROXY_HOST}:${PROXY_PORT}"
export https_proxy="http://${PROXY_HOST}:${PROXY_PORT}"
export HTTP_PROXY="http://${PROXY_HOST}:${PROXY_PORT}"
export HTTPS_PROXY="http://${PROXY_HOST}:${PROXY_PORT}"
export no_proxy="localhost,127.0.0.1,10.*,192.168.*"
export NO_PROXY="localhost,127.0.0.1,10.*,192.168.*"

echo "✓ 代理已配置"
