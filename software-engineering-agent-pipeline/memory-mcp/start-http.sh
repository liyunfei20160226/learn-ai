#!/bin/bash
# Start memory-mcp HTTP server
# Usage: ./start-http.sh [port]
# Default port: 8000

PORT=${1:-8000}
node $(dirname $0)/http-server.js $PORT
