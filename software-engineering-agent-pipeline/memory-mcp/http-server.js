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
 *   - DELETE /relations        - delete relations
 *   - GET  /entities/{name}  - get entity
 *   - GET  /graph            - read full graph
 *   - POST /search           - search nodes
 *   - POST /open             - open nodes
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import http from "http";
import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const PORT = process.env.PORT || parseInt(process.argv[2]) || 8000;

// Define memory file path using environment variable with fallback
const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const defaultMemoryPath = path.join(__dirname, 'memory.jsonl');

// Handle backward compatibility: migrate memory.json to memory.jsonl if needed
export async function ensureMemoryFilePath() {
  if (process.env.MEMORY_FILE_PATH) {
    // Custom path provided, use it as-is (with absolute path resolution)
    return path.isAbsolute(process.env.MEMORY_FILE_PATH)
      ? process.env.MEMORY_FILE_PATH
      : path.join(__dirname, process.env.MEMORY_FILE_PATH);
  }
  // No custom path set, check for backward compatibility migration
  const oldMemoryPath = path.join(__dirname, 'memory.json');
  const newMemoryPath = defaultMemoryPath;
  try {
    // Check if old file exists and new file doesn't
    await fs.access(oldMemoryPath);
    try {
      await fs.access(newMemoryPath);
      // Both files exist, use new one (no migration needed)
      return newMemoryPath;
    } catch {
      // Old file exists, new file doesn't - migrate
      console.error('DETECTED: Found legacy memory.json file, migrating to memory.jsonl for JSONL format compatibility');
      await fs.rename(oldMemoryPath, newMemoryPath);
      console.error('COMPLETED: Successfully migrated memory.json to memory.jsonl');
      return newMemoryPath;
    }
  } catch {
    // Old file doesn't exist, use new path
    return newMemoryPath;
  }
}

// We are storing our memory using entities, relations, and observations in a graph structure
export class KnowledgeGraphManager {
  constructor(memoryFilePath) {
    this.memoryFilePath = memoryFilePath;
  }

  async loadGraph() {
    try {
      const data = await fs.readFile(this.memoryFilePath, "utf-8");
      const lines = data.split("\n").filter(line => line.trim() !== "");
      return lines.reduce((graph, line) => {
        const item = JSON.parse(line);
        if (item.type === "entity") {
          graph.entities.push({
            name: item.name,
            entityType: item.entityType,
            observations: item.observations
          });
        }
        if (item.type === "relation") {
          graph.relations.push({
            from: item.from,
            to: item.to,
            relationType: item.relationType
          });
        }
        return graph;
      }, { entities: [], relations: [] });
    } catch (error) {
      if (error instanceof Error && 'code' in error && error.code === "ENOENT") {
        return { entities: [], relations: [] };
      }
      throw error;
    }
  }

  async saveGraph(graph) {
    const lines = [
      ...graph.entities.map(e => JSON.stringify({
        type: "entity",
        name: e.name,
        entityType: e.entityType,
        observations: e.observations
      })),
      ...graph.relations.map(r => JSON.stringify({
        type: "relation",
        from: r.from,
        to: r.to,
        relationType: r.relationType
      })),
    ];
    await fs.writeFile(this.memoryFilePath, lines.join("\n"));
  }

  async createEntities(entities) {
    const graph = await this.loadGraph();
    const newEntities = entities.filter(e => !graph.entities.some(existingEntity => existingEntity.name === e.name));
    graph.entities.push(...newEntities);
    await this.saveGraph(graph);
    return newEntities;
  }

  async createRelations(relations) {
    const graph = await this.loadGraph();
    const newRelations = relations.filter(r => !graph.entities.some(existingRelation =>
      existingRelation.from === r.from &&
      existingRelation.to === r.to &&
      existingRelation.relationType === r.relationType
    ));
    graph.relations.push(...newRelations);
    await this.saveGraph(graph);
    return newRelations;
  }

  async addObservations(observations) {
    const graph = await this.loadGraph();
    const results = observations.map(o => {
      const entity = graph.entities.find(e => e.name === o.entityName);
      if (!entity) {
        throw new Error(`Entity with name ${o.entityName} not found`);
      }
      const newObservations = o.contents.filter(content => !entity.observations.includes(content));
      entity.observations.push(...newObservations);
      return { entityName: o.entityName, addedObservations: newObservations };
    });
    await this.saveGraph(graph);
    return results;
  }

  async deleteEntities(entityNames) {
    const graph = await this.loadGraph();
    graph.entities = graph.entities.filter(e => !entityNames.includes(e.name));
    graph.relations = graph.relations.filter(r => !entityNames.includes(r.from) && !entityNames.includes(r.to));
    await this.saveGraph(graph);
  }

  async deleteObservations(deletions) {
    const graph = await this.loadGraph();
    deletions.forEach(d => {
      const entity = graph.entities.find(e => e.name === d.entityName);
      if (entity) {
        entity.observations = entity.observations.filter(o => !d.observations.includes(o));
      }
    });
    await this.saveGraph(graph);
  }

  async deleteRelations(relations) {
    const graph = await this.loadGraph();
    graph.relations = graph.relations.filter(r => !relations.some(delRelation =>
      r.from === delRelation.from &&
      r.to === delRelation.to &&
      r.relationType === delRelation.relationType
    ));
    await this.saveGraph(graph);
  }

  async readGraph() {
    return this.loadGraph();
  }

  async searchNodes(query) {
    const graph = await this.loadGraph();

    // Filter entities
    const filteredEntities = graph.entities.filter(e =>
      e.name.toLowerCase().includes(query.toLowerCase()) ||
      e.entityType.toLowerCase().includes(query.toLowerCase()) ||
      e.observations.some(o => o.toLowerCase().includes(query.toLowerCase()))
    );

    // Create a Set of filtered entity names for quick lookup
    const filteredEntityNames = new Set(filteredEntities.map(e => e.name));

    // Include relations where at least one endpoint matches the search results.
    // This lets callers discover connections to nodes outside the result set.
    const filteredRelations = graph.relations.filter(r =>
      filteredEntityNames.has(r.from) || filteredEntityNames.has(r.to)
    );

    return { entities: filteredEntities, relations: filteredRelations };
  }

  async openNodes(names) {
    const graph = await this.loadGraph();

    // Filter entities
    const filteredEntities = graph.entities.filter(e => names.includes(e.name));

    // Create a Set of filtered entity names for quick lookup
    const filteredEntityNames = new Set(filteredEntities.map(e => e.name));

    // Include relations where at least one endpoint is in the requested set.
    // Previously this required BOTH endpoints, which meant relations from a
    // requested node to an unrequested node were silently dropped — making it
    // impossible to discover a node's connections without reading the full graph.
    const filteredRelations = graph.relations.filter(r =>
      filteredEntityNames.has(r.from) || filteredEntityNames.has(r.to)
    );

    return { entities: filteredEntities, relations: filteredRelations };
  }
}

// Zod schemas
const EntitySchema = z.object({
  name: z.string(),
  entityType: z.string(),
  observations: z.array(z.string())
});

const RelationSchema = z.object({
  from: z.string(),
  to: z.string(),
  relationType: z.string()
});

// Initialize
let memoryFilePath;
let knowledgeGraphManager;

// The MCP server instance
const server = new McpServer({
  name: "memory",
  version: "1.0.0"
});

// Register all tools same as the original index.ts
server.registerTool(
  "create_entities",
  {
    title: "Create Entities",
    description: "Create multiple new entities in the knowledge graph",
    inputSchema: {
      entities: z.array(EntitySchema)
    }
  },
  async ({ entities }) => {
    const result = await knowledgeGraphManager.createEntities(entities);
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }]
    };
  }
);

server.registerTool(
  "create_relations",
  {
    title: "Create Relations",
    description: "Create multiple new relations between entities in the knowledge graph",
    inputSchema: {
      relations: z.array(RelationSchema)
    }
  },
  async ({ relations }) => {
    const result = await knowledgeGraphManager.createRelations(relations);
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }]
    };
  }
);

server.registerTool(
  "add_observations",
  {
    title: "Add Observations",
    description: "Add new observations to existing entities in the knowledge graph",
    inputSchema: {
      observations: z.array(z.object({
        entityName: z.string(),
        contents: z.array(z.string())
      }))
    }
  },
  async ({ observations }) => {
    const result = await knowledgeGraphManager.addObservations(observations);
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }]
    };
  }
);

server.registerTool(
  "delete_entities",
  {
    title: "Delete Entities",
    description: "Delete multiple entities and their associated relations from the knowledge graph",
    inputSchema: {
      entityNames: z.array(z.string())
    }
  },
  async ({ entityNames }) => {
    await knowledgeGraphManager.deleteEntities(entityNames);
    return {
      content: [{ type: "text", text: "Entities deleted successfully" }]
    };
  }
);

server.registerTool(
  "delete_observations",
  {
    title: "Delete Observations",
    description: "Delete specific observations from entities in the knowledge graph",
    inputSchema: {
      deletions: z.array(z.object({
        entityName: z.string(),
        observations: z.array(z.string())
      }))
    }
  },
  async ({ deletions }) => {
    await knowledgeGraphManager.deleteObservations(deletions);
    return {
      content: [{ type: "text", text: "Observations deleted successfully" }]
    };
  }
);

server.registerTool(
  "delete_relations",
  {
    title: "Delete Relations",
    description: "Delete multiple relations from the knowledge graph",
    inputSchema: {
      relations: z.array(RelationSchema)
    }
  },
  async ({ relations }) => {
    await knowledgeGraphManager.deleteRelations(relations);
    return {
      content: [{ type: "text", text: "Relations deleted successfully" }]
    };
  }
);

server.registerTool(
  "read_graph",
  {
    title: "Read Graph",
    description: "Read the entire knowledge graph",
    inputSchema: {}
  },
  async () => {
    const graph = await knowledgeGraphManager.readGraph();
    return {
      content: [{ type: "text", text: JSON.stringify(graph, null, 2) }]
    };
  }
);

server.registerTool(
  "search_nodes",
  {
    title: "Search Nodes",
    description: "Search for nodes in the knowledge graph based on a query",
    inputSchema: {
      query: z.string()
    }
  },
  async ({ query }) => {
    const graph = await knowledgeGraphManager.searchNodes(query);
    return {
      content: [{ type: "text", text: JSON.stringify(graph, null, 2) }]
    };
  }
);

server.registerTool(
  "open_nodes",
  {
    title: "Open Nodes",
    description: "Open specific nodes in the knowledge graph by their names",
    inputSchema: {
      names: z.array(z.string())
    }
  },
  async ({ names }) => {
    const graph = await knowledgeGraphManager.openNodes(names);
    return {
      content: [{ type: "text", text: JSON.stringify(graph, null, 2) }]
    };
  }
);

// Connect memory server to stdio for MCP (but we don't use that for HTTP)
const transport = new StdioServerTransport();
server.connect(transport);

// Initialize the knowledge graph manager
(async () => {
  memoryFilePath = await ensureMemoryFilePath();
  knowledgeGraphManager = new KnowledgeGraphManager(memoryFilePath);
})();

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

      // Handle different endpoints
      switch (req.url) {
        case "/entities":
          if (req.method === "POST") {
            // { entities: [{ name, entityType, observations }] }
            const { entities } = JSON.parse(body);
            result = await server.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "create_entities",
              params: { entities },
            });
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/relations":
          if (req.method === "POST") {
            // { relations: [{ from, to, relationType }] }
            const { relations } = JSON.parse(body);
            result = await server.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "create_relations",
              params: { relations },
            });
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/observations":
          if (req.method === "POST") {
            // { observations: [{ entityName, contents }] }
            const { observations } = JSON.parse(body);
            result = await server.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "add_observations",
              params: { observations },
            });
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/entities":
          if (req.method === "DELETE") {
            // { entityNames: string[] }
            const { entityNames } = JSON.parse(body);
            result = await server.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "delete_entities",
              params: { entityNames },
            });
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/observations":
          if (req.method === "DELETE") {
            // { deletions: [{ entityName, observations }] }
            const { deletions } = JSON.parse(body);
            result = await server.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "delete_observations",
              params: { deletions },
            });
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/relations":
          if (req.method === "DELETE") {
            // { relations: [{ from, to, relationType }] }
            const { relations: deleteRelations } = JSON.parse(body);
            result = await server.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "delete_relations",
              params: { relations: deleteRelations },
            });
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/graph":
          if (req.method === "GET") {
            result = await server.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "read_graph",
              params: {},
            });
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/search":
          if (req.method === "POST") {
            // { query: string }
            const { query } = JSON.parse(body);
            result = await server.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "search_nodes",
              params: { query },
            });
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(result));
          }
          break;

        case "/open":
          if (req.method === "POST") {
            // { names: string[] }
            const { names } = JSON.parse(body);
            result = await server.handleRequest({
              jsonrpc: "2.0",
              id: 1,
              method: "open_nodes",
              params: { names },
            });
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
