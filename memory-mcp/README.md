# Memory MCP Server

A Model Context Protocol (MCP) server that provides persistent memory capabilities through a knowledge graph.

## Features

- Create and manage entities in a knowledge graph
- Create relations between entities
- Add observations to existing entities
- Delete entities, observations, and relations
- Search for nodes
- Read the entire knowledge graph

## Installation

```bash
npm install
npm run build
npm start
```

## Development

```bash
npm run dev
npm test
```

## Tools

### create_entities
Create multiple new entities in the knowledge graph

### create_relations
Create multiple new relations between entities

### add_observations
Add new observations to existing entities

### delete_entities
Delete multiple entities and their associated relations

### delete_observations
Delete specific observations from entities

### delete_relations
Delete multiple relations from the knowledge graph

### read_graph
Read the entire knowledge graph

### search_nodes
Search for nodes in the knowledge graph based on a query

### open_nodes
Open specific nodes in the knowledge graph by their names

## License

MIT