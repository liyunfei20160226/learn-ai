#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from "@modelcontextprotocol/sdk/types.js";
import axios from "axios";
import * as cheerio from "cheerio";

/**
 * Search result interface
 */
interface SearchResult {
  title: string;
  url: string;
  abstract: string;
}

/**
 * Baidu Search Client
 */
class BaiduSearchClient {
  private baseUrl = "https://www.baidu.com/s";
  private userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

  /**
   * Search Baidu and parse results
   */
  async search(query: string, limit: number = 10): Promise<SearchResult[]> {
    try {
      const url = `${this.baseUrl}?wd=${encodeURIComponent(query)}&pn=0`;
      
      const response = await axios.get(url, {
        headers: {
          "User-Agent": this.userAgent,
          "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
          "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
        timeout: 10000,
      });

      const $ = cheerio.load(response.data);
      const results: SearchResult[] = [];

      // Baidu search result items are in .c-container
      // Try multiple selectors for abstract to adapt to different Baidu layouts
      $(".c-container").each((index, element) => {
        if (results.length >= limit) return;

        const $el = $(element);
        const $title = $el.find("h3 a, .t a");
        let abstract = "";

        // Try multiple selectors for abstract to adapt to layout changes
        const abstractSelectors = [
          ".c-abstract",
          ".abstract",
          ".content-right_1VRdl p",
          ".c-span18 p",
          "p",
          ".result-abstract",
          ".mu"
        ];

        for (const selector of abstractSelectors) {
          const $abs = $el.find(selector);
          if ($abs.length > 0) {
            abstract = $abs.first().text().trim();
            if (abstract) break;
          }
        }

        const title = $title.text().trim();
        let url = $title.attr("href") || "";

        if (!title || !url) return;

        // Baidu uses redirect URLs, we keep them as-is
        results.push({
          title,
          url,
          abstract,
        });
      });

      return results;
    } catch (error) {
      throw new Error(`Search failed: ${(error as Error).message}`);
    }
  }
}

const searchClient = new BaiduSearchClient();

/**
 * Create MCP Server
 */
const server = new Server(
  {
    name: "baidu-search-mcp",
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
        name: "baidu_search",
        description: "Search the web using Baidu (Chinese search engine, suitable for domestic network). Use this to get the latest information, news, technology updates from Chinese internet.",
        inputSchema: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "The search query/keywords",
            },
            limit: {
              type: "number",
              description: "Maximum number of results to return (default: 10)",
              minimum: 1,
              maximum: 20,
            },
          },
          required: ["query"],
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
      case "baidu_search": {
        const { query, limit = 10 } = args as { query: string; limit?: number };
        const results = await searchClient.search(query, limit);

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  query,
                  count: results.length,
                  results: results,
                },
                null,
                2
              ),
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
      `Search failed: ${(error as Error).message}`
    );
  }
});

/**
 * Start the server
 */
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Baidu Search MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error in main:", error);
  process.exit(1);
});
