/**
 * HTTP Server wrapper for memory-mcp
 *
 * Usage:
 *   node memory-mcp/http-server.js [port]
 *
 * Default port: 8000
 *
 * Provides REST HTTP API for the memory-mcp knowledge graph:
 *   - POST /entities           - create entities
 *   - POST /relations          - create relations
 *   - POST /observations       - add observations
 *   - DELETE /entities        - delete entities
 *   - DELETE /observations    - delete observations
 * - DELETE /relations        - delete relations
 *   - GET  /entities/{name}  - get entity
 *   - GET  /graph            - read full graph
 *   - POST /search           - search nodes
 *   - POST /open            - open nodes
 */

const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/transport.js");
const { createMemoryServer } = require("./dist/index.js");
const http = require("http");

const PORT = process.env.PORT || parseInt(process.argv[2]) || 8000;

// Create the memory MCP server
const memoryServer = createMemoryServer();

// We need to handle MCP requests over HTTP, so we wrap it
const mcpServer = new Server({
  name: "memory",
  version: "1.0.0",
}, {
  capabilities: {
    tools: {},
  },
});

// Connect memory server to stdio for MCP (but we don't use that for HTTP)
const transport = new StdioServerTransport();
memoryServer.connect(transport);

// Create HTTP server that translates HTTP requests to MCP tool calls
const httpServer = http.createServer(async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    res.writeHead(200);
    res.end();
    return;
  }

  let body = "";
  req.on("data", chunk => {
    body += chunk;
  });

  req.on("end", async () => {
    try {
      let result;

      switch (req.url) {
        case "/entities":
          if (req.method === "POST") {
            // { entities: [{ name, entityType, observations }] }
            const { entities } = JSON.parse(body);
            result = await memoryServer.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "create_entities",
              params: { entities },
            }, transport);
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/relations":
          if (req.method === "POST") {
            // { relations: [{ from, to, relationType }] }
            const { relations } = JSON.parse(body);
            result = await memoryServer.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "create_relations",
              params: { relations },
            }, transport);
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/observations":
          if (req.method === "POST") {
            // { observations: [{ entityName, contents }] }
            const { observations } = JSON.parse(body);
            result = await memoryServer.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "add_observations",
              params: { observations },
            }, transport);
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/entities":
          if (req.method === "DELETE") {
            // { entityNames: string[] }
            const { entityNames } = JSON.parse(body);
            result = await memoryServer.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "delete_entities",
              params: { entityNames },
            }, transport);
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/observations":
          if (req.method === "DELETE") {
            // { deletions: [{ entityName, observations }] }
            const { deletions } = JSON.parse(body);
            result = await memoryServer.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "delete_observations",
              params: { deletions },
            }, transport);
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/relations":
          if (req.method === "DELETE") {
            // { relations: [{ from, to, relationType }] }
            const { relations } = JSON.parse(body);
            result = await memoryServer.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "delete_relations",
              params: { relations },
            }, transport);
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/graph":
          if (req.method === "GET") {
            result = await memoryServer.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "read_graph",
              params: {},
            }, transport);
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/search":
          if (req.method === "POST") {
            // { query: string }
            const { query } = JSON.parse(body);
            result = await memoryServer.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "search_nodes",
              params: { query },
            }, transport);
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/open":
          if (req.method === "POST") {
            // { names: string[] }
            const { names } = JSON.parse(body);
            result = await memoryServer.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "open_nodes",
              params: { names },
            }, transport);
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        default:
          res.writeHead(404, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Not found" }));
          break;
      }
    } catch (error) {
      console.error("Error handling request:", error);
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: String(error) }));
    }
  });
});

httpServer.listen(PORT, () => {
  console.log(`Memory MCP HTTP server running on http://localhost:${PORT}`);
  console.log("API endpoints:");
  console.log("  POST /entities   - Create entities");
  console.log("  POST /relations  - Create relations");
  console.log("  POST /observations - Add observations");
  console.log("  DELETE /entities  - Delete entities");
  console.log("  DELETE /observations - Delete observations");
  console.log("  DELETE /relations  - Delete relations");
  console.log("  GET /graph      - Read full graph");
  console.log("  POST /search     - Search nodes");
  console.log("  POST /open       - Open nodes by name");
});
