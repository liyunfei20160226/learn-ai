#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from "@modelcontextprotocol/sdk/types.js";

/**
 * Entity definition
 */
interface Entity {
  name: string;
  entityType: string;
  observations: string[];
}

/**
 * Relation definition
 */
interface Relation {
  from: string;
  to: string;
  relationType: string;
}

/**
 * Knowledge Graph
 */
class KnowledgeGraph {
  private entities: Map<string, Entity>;
  private relations: Relation[];

  constructor() {
    this.entities = new Map();
    this.relations = [];
  }

  /**
   * Create multiple entities
   */
  createEntities(entities: Entity[]): Entity[] {
    for (const entity of entities) {
      this.entities.set(entity.name, {
        ...entity,
        observations: [...entity.observations],
      });
    }
    return entities;
  }

  /**
   * Create multiple relations
   */
  createRelations(relations: Relation[]): Relation[] {
    // Validate entities exist
    for (const relation of relations) {
      if (!this.entities.has(relation.from)) {
        throw new Error(`Entity '${relation.from}' does not exist`);
      }
      if (!this.entities.has(relation.to)) {
        throw new Error(`Entity '${relation.to}' does not exist`);
      }
    }

    this.relations.push(...relations);
    return relations;
  }

  /**
   * Add observations to existing entities
   */
  addObservations(
    observations: Array<{ entityName: string; contents: string[] }>
  ): Array<{ entityName: string; addedObservations: string[] }> {
    const result: Array<{ entityName: string; addedObservations: string[] }> = [];

    for (const { entityName, contents } of observations) {
      const entity = this.entities.get(entityName);
      if (!entity) {
        throw new Error(`Entity '${entityName}' does not exist`);
      }

      entity.observations.push(...contents);
      result.push({ entityName, addedObservations: contents });
    }

    return result;
  }

  /**
   * Delete entities and their associated relations
   */
  deleteEntities(entityNames: string[]): void {
    for (const name of entityNames) {
      this.entities.delete(name);
      // Remove relations involving this entity
      this.relations = this.relations.filter(
        (r) => r.from !== name && r.to !== name
      );
    }
  }

  /**
   * Delete specific observations from an entity
   */
  deleteObservations(
    deletions: Array<{ entityName: string; observations: string[] }>
  ): void {
    for (const { entityName, observations } of deletions) {
      const entity = this.entities.get(entityName);
      if (!entity) {
        throw new Error(`Entity '${entityName}' does not exist`);
      }

      entity.observations = entity.observations.filter(
        (obs) => !observations.includes(obs)
      );
    }
  }

  /**
   * Delete specific relations
   */
  deleteRelations(relationsToDelete: Relation[]): void {
    this.relations = this.relations.filter((r) => {
      return !relationsToDelete.some(
        (rt) =>
          rt.from === r.from && rt.to === r.to && rt.relationType === r.relationType
      );
    });
  }

  /**
   * Search for nodes matching query
   */
  searchNodes(query: string): { entities: Entity[]; relations: Relation[] } {
    const lowerQuery = query.toLowerCase();
    const matchingEntities: Entity[] = [];

    for (const entity of this.entities.values()) {
      if (
        entity.name.toLowerCase().includes(lowerQuery) ||
        entity.entityType.toLowerCase().includes(lowerQuery) ||
        entity.observations.some((o) => o.toLowerCase().includes(lowerQuery))
      ) {
        matchingEntities.push(entity);
      }
    }

    // Get all relations involving matching entities
    const matchingRelations = this.relations.filter(
      (r) =>
        matchingEntities.some((e) => e.name === r.from) ||
        matchingEntities.some((e) => e.name === r.to)
    );

    return {
      entities: matchingEntities,
      relations: matchingRelations,
    };
  }

  /**
   * Open specific nodes by name
   */
  openNodes(names: string[]): { entities: Entity[]; relations: Relation[] } {
    const entities: Entity[] = [];
    for (const name of names) {
      const entity = this.entities.get(name);
      if (entity) {
        entities.push(entity);
      }
    }

    const relations = this.relations.filter(
      (r) =>
        entities.some((e) => e.name === r.from) &&
        entities.some((e) => e.name === r.to)
    );

    return {
      entities,
      relations,
    };
  }

  /**
   * Read the entire graph
   */
  readGraph(): { entities: Entity[]; relations: Relation[] } {
    return {
      entities: Array.from(this.entities.values()),
      relations: this.relations,
    };
  }
}

// Global knowledge graph instance
const graph = new KnowledgeGraph();

/**
 * Create MCP Server
 */
const server = new Server(
  {
    name: "memory-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * List available tools
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "create_entities",
        description: "Create multiple new entities in the knowledge graph",
        inputSchema: {
          type: "object",
          properties: {
            entities: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  name: {
                    type: "string",
                    description: "The name of the entity",
                  },
                  entityType: {
                    type: "string",
                    description: "The type of the entity",
                  },
                  observations: {
                    type: "array",
                    items: {
                      type: "string",
                      description: "An array of observation contents associated with the entity",
                    },
                  },
                },
                required: ["name", "entityType", "observations"],
              },
            },
          },
          required: ["entities"],
        },
      },
      {
        name: "create_relations",
        description: "Create multiple new relations between entities in the knowledge graph",
        inputSchema: {
          type: "object",
          properties: {
            relations: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  from: {
                    type: "string",
                    description: "The name of the entity where the relation starts",
                  },
                  to: {
                    type: "string",
                    description: "The name of the entity where the relation ends",
                  },
                  relationType: {
                    type: "string",
                    description: "The type of the relation",
                  },
                },
                required: ["from", "to", "relationType"],
              },
            },
          },
          required: ["relations"],
        },
      },
      {
        name: "add_observations",
        description: "Add new observations to existing entities in the knowledge graph",
        inputSchema: {
          type: "object",
          properties: {
            observations: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  entityName: {
                    type: "string",
                    description: "The name of the entity to add the observations to",
                  },
                  contents: {
                    type: "array",
                    items: {
                      type: "string",
                      description: "An array of observation contents to add",
                    },
                  },
                },
                required: ["entityName", "contents"],
              },
            },
          },
          required: ["observations"],
        },
      },
      {
        name: "delete_entities",
        description: "Delete multiple entities and their associated relations from the knowledge graph",
        inputSchema: {
          type: "object",
          properties: {
            entityNames: {
              type: "array",
              items: {
                type: "string",
                description: "An array of entity names to delete",
              },
            },
          },
          required: ["entityNames"],
        },
      },
      {
        name: "delete_observations",
        description: "Delete specific observations from entities in the knowledge graph",
        inputSchema: {
          type: "object",
          properties: {
            deletions: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  entityName: {
                    type: "string",
                    description: "The name of the entity containing the observations",
                  },
                  observations: {
                    type: "array",
                    items: {
                      type: "string",
                      description: "An array of observations to delete",
                    },
                  },
                },
                required: ["entityName", "observations"],
              },
            },
          },
          required: ["deletions"],
        },
      },
      {
        name: "delete_relations",
        description: "Delete multiple relations from the knowledge graph",
        inputSchema: {
          type: "object",
          properties: {
            relations: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  from: {
                    type: "string",
                    description: "The name of the entity where the relation starts",
                  },
                  to: {
                    type: "string",
                    description: "The name of the entity where the relation ends",
                  },
                  relationType: {
                    type: "string",
                    description: "The type of the relation",
                  },
                },
                required: ["from", "to", "relationType"],
              },
            },
          },
          required: ["relations"],
        },
      },
      {
        name: "read_graph",
        description: "Read the entire knowledge graph",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "search_nodes",
        description: "Search for nodes in the knowledge graph based on a query",
        inputSchema: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "The search query to match against entity names, types, and observation content",
            },
          },
          required: ["query"],
        },
      },
      {
        name: "open_nodes",
        description: "Open specific nodes in the knowledge graph by their names",
        inputSchema: {
          type: "object",
          properties: {
            names: {
              type: "array",
              items: {
                type: "string",
                description: "An array of entity names to retrieve",
              },
            },
          },
          required: ["names"],
        },
      },
    ],
  };
});

/**
 * Handle tool calls
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "create_entities": {
        const { entities } = args as { entities: Entity[] };
        const result = graph.createEntities(entities);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ success: true, created: result }, null, 2),
            },
          ],
        };
      }

      case "create_relations": {
        const { relations } = args as { relations: Relation[] };
        const result = graph.createRelations(relations);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ success: true, created: result }, null, 2),
            },
          ],
        };
      }

      case "add_observations": {
        const { observations } = args as {
          observations: Array<{ entityName: string; contents: string[] }>;
        };
        const result = graph.addObservations(observations);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ success: true, added: result }, null, 2),
            },
          ],
        };
      }

      case "delete_entities": {
        const { entityNames } = args as { entityNames: string[] };
        graph.deleteEntities(entityNames);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                { success: true, deleted: entityNames },
                null,
                2
              ),
            },
          ],
        };
      }

      case "delete_observations": {
        const { deletions } = args as {
          deletions: Array<{ entityName: string; observations: string[] }>;
        };
        graph.deleteObservations(deletions);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ success: true }, null, 2),
            },
          ],
        };
      }

      case "delete_relations": {
        const { relations } = args as { relations: Relation[] };
        graph.deleteRelations(relations);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ success: true }, null, 2),
            },
          ],
        };
      }

      case "read_graph": {
        const result = graph.readGraph();
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "search_nodes": {
        const { query } = args as { query: string };
        const result = graph.searchNodes(query);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "open_nodes": {
        const { names } = args as { names: string[] };
        const result = graph.openNodes(names);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      default:
        throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
    }
  } catch (error) {
    throw new McpError(
      ErrorCode.InternalError,
      `Error executing ${name}: ${(error as Error).message}`
    );
  }
});

/**
 * Start the server
 */
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Memory MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error in main:", error);
  process.exit(1);
});
