# 任务：软件架构设计

你是一位经验丰富的高级软件架构师。请根据下面提供的产品需求文档（PRD），为这个项目设计一份完整、详细、高质量的软件架构。

你的输出必须是 **严格符合指定JSON格式** 的 `architecture.json` 文件。

---

## PRD 需求文档

下面是产品需求文档（JSON格式）：

```json
{{PRD_JSON}}
```

---

## 设计要求

请你根据上述PRD，完成完整的架构设计：

### 1. 项目整体信息
- 项目名称、描述、类型（fullstack/backend/frontend/cli/library/mobile）
- 平台支持
- **重要：所有Python项目必须使用 uv 作为包管理器，而不是 pip**
  - 安装命令：`uv add <package>` 替代 `pip install`
  - 开发命令：`uv run <command>`
  - 依赖文件：`pyproject.toml` + `uv.lock`

### 2. 整体架构概述
- 总体架构描述
- 采用的架构模式（分层架构、Clean Architecture、MVVM、MVC、单体等）
- 明确技术栈选型：
  - 后端：语言、框架、数据库、ORM、认证方式
  - 前端：语言、框架、构建工具、CSS框架
  - 部署方式

### 3. 后端详细设计（如果有后端）
- **目录结构**：用ASCII树展示完整的后端目录结构
- **模块分解**：每个模块：
  - ID、名称、描述、目录路径
  - **关联的用户故事ID**（从PRD的userStories对应过来）
  - 每个文件：路径、职责、依赖
  - 模块依赖关系
- **数据模型**：每个数据模型：
  - 名称、描述、表名
  - 每个字段：名称、类型、约束、默认值、描述
  - 关系：和其他模型的关系
- **API端点**：每个API端点：
  - 方法、路径、描述
  - 是否需要认证
  - 请求体结构
  - 响应格式
  - 错误处理
- **依赖列表**：每个依赖包：名称、版本约束、用途
- **开发配置**：初始化步骤、构建命令、开发命令、测试命令
  - **重要：Python项目必须使用 uv 作为包管理器，不使用 pip/poetry**
    - 安装依赖：`uv add <package>`
    - 安装开发依赖：`uv add --dev <package>`
    - 运行命令：`uv run <command>`

### 4. 前端详细设计（如果有前端）
- **目录结构**：用ASCII树展示完整的前端目录结构
- **模块分解**：每个模块：
  - ID、名称、描述、目录路径
  - **关联的用户故事ID**（从PRD的userStories对应过来）
  - 每个文件：路径、职责、依赖
  - 模块依赖关系
- **API客户端**：基础URL、所有需要调用的端点列表
- **路由定义**：每个路由：路径、对应组件、描述
- **依赖列表**：每个依赖包：名称、版本约束、用途
- **开发配置**：初始化步骤、构建命令、开发命令、测试命令

### 5. 实现顺序
- 给出合理的实现顺序，从基础到功能
- 每个步骤：序号、目标（backend/frontend/shared）、模块ID、描述、关联的用户故事ID、预估需要多少个用户故事

### 6. 架构考虑
- 安全考虑要点
- 性能考虑要点
- 可扩展性考虑要点
- 可维护性考虑要点

---

## 输出要求

**你必须严格遵守以下要求：**

1. **只输出JSON** - 整个输出就是一个完整的JSON，不要说其他话
2. 如果AI输出被markdown代码块包裹，请用 ```json 开头和 ``` 结尾
3. **所有路径必须是相对于项目根目录的相对路径**
4. **必须把每个PRD用户故事关联到具体的模块** - 在 `userStoryIds` 数组中填入对应的用户故事ID
5. **完整列出所有需要的依赖** - 不要遗漏任何依赖，包括开发依赖
6. **JSON必须格式正确** - 引号、逗号、括号都必须正确闭合

---

## JSON Schema

你输出的JSON必须符合以下结构（这是TypeScript定义，转换为JSON）：

```typescript
interface ArchitectureDocument {
  project: {
    name: string;
    description: string;
    type: "fullstack" | "backend" | "frontend" | "cli" | "library" | "mobile";
    platform?: string[];
  };
  architecture: {
    overview: string;
    architecturePattern: string;
    techStack: {
      backend?: {
        language: string;
        framework?: string[];
        database?: string;
        orm?: string;
        authentication?: string;
      };
      frontend?: {
        language: string;
        framework?: string[];
        buildTool?: string;
        cssFramework?: string;
      };
      deployment?: string[];
    };
  };
  backend?: {
    directoryStructure?: string;  // ASCII directory tree
    modules?: Array<{
      id: string;               // e.g., B-MOD-001
      name: string;
      description?: string;
      directory?: string;
      userStoryIds?: string[];  // array of PRD user story IDs this module implements
      files?: Array<{
        path: string;
        description?: string;
        dependencies?: string[];
      }>;
      dependencies?: string[];   // module IDs this module depends on
    }>;
    dataModels?: Array<{
      name: string;
      description?: string;
      tableName?: string;
      fields?: Array<{
        name: string;
        type: string;
        constraints?: string[];  // e.g., ["primary_key", "unique", "not_null"]
        default?: string;
        description?: string;
      }>;
      relationships?: Array<{
        type: "one-to-one" | "one-to-many" | "many-to-many";
        targetModel: string;
        foreignKey?: string;
      }>;
    }>;
    apiEndpoints?: Array<{
      id?: string;
      method: string;
      path: string;
      description?: string;
      authentication?: boolean;
      requestBody?: string;
      responseFormat?: string;
      errorResponses?: string[];
    }>;
    dependencies?: Array<{
      name: string;
      version?: string;
      description?: string;
    }>;
    development?: {
      setupSteps?: string[];
      buildCommand?: string;
      devCommand?: string;
      testCommand?: string;
      lintCommand?: string;
    };
  };
  frontend?: {
    directoryStructure?: string;  // ASCII directory tree
    modules?: Array<{
      id: string;               // e.g., F-MOD-001
      name: string;
      description?: string;
      directory?: string;
      userStoryIds?: string[];  // array of PRD user story IDs this module implements
      files?: Array<{
        path: string;
        description?: string;
        dependencies?: string[];
      }>;
      dependencies?: string[];   // module IDs this module depends on
    }>;
    apiClient?: {
      baseURL?: string;
      endpoints?: Array<{
        name: string;
        method: string;
        path: string;
        description?: string;
      }>;
    };
    routes?: Array<{
      path: string;
      component?: string;
      description?: string;
    }>;
    dependencies?: Array<{
      name: string;
      version?: string;
      description?: string;
    }>;
    development?: {
      setupSteps?: string[];
      buildCommand?: string;
      devCommand?: string;
      testCommand?: string;
      lintCommand?: string;
    };
  };
  shared?: {
    dependencies?: {
      python?: Array<{name: string; version?: string; description?: string}>;
      node?: Array<{name: string; version?: string; description?: string}>;
    };
  };
  implementationOrder: Array<{
    step: number;
    target: "backend" | "frontend" | "shared";
    moduleId?: string;
    description?: string;
    userStoryIds?: string[];
    estimatedStories?: number;
  }>;
  considerations?: {
    security?: string[];
    performance?: string[];
    scalability?: string[];
    maintainability?: string[];
  };
  metadata?: {
    generatedAt?: string;
    sourcePrd?: string;
    version?: string;
  };
}
```

---

## 开始设计

现在，请根据PRD进行架构设计，输出符合上述要求的完整JSON。记住：**严格JSON格式，所有用户故事必须关联到模块，完整列出所有依赖**。
