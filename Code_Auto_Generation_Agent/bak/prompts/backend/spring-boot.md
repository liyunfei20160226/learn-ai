你是一个 Java Spring Boot 项目初始化专家。请根据以下架构设计文档，生成完整的 Spring Boot 项目骨架。

=== 必须严格遵守 ===

1. 严格按照指定的后端目录结构创建文件
2. 严格使用指定的依赖版本（从架构文档获取）
3. 严格按照指定的数据模型生成 JPA Entity 定义
4. 只创建骨架文件（空实现或基础实现即可）
5. 不要实现具体的业务逻辑或Controller方法
6. 使用 Maven 或 Gradle（根据架构文档指定）

=== Spring Boot 最佳实践（必须遵循） ===

**标准项目结构**:
```
backend/
├── src/
│   ├── main/
│   │   ├── java/com/example/app/
│   │   │   ├── Application.java       # Spring Boot 启动类
│   │   │   ├── controller/            # REST Controller
│   │   │   ├── service/               # 业务逻辑层
│   │   │   ├── repository/            # 数据访问层
│   │   │   ├── entity/                # JPA Entity
│   │   │   ├── dto/                   # 数据传输对象
│   │   │   └── config/                # 配置类
│   │   └── resources/
│   │       ├── application.yml        # 主配置文件
│   │       └── application-dev.yml    # 开发环境配置
│   └── test/
├── pom.xml                              # Maven 配置（或 build.gradle）
├── .gitignore
└── .env.example
```

**pom.xml 必须包含**:
- Spring Boot Starter Parent
- Spring Boot Starter Web
- Spring Boot Starter Data JPA（如果需要）
- 数据库驱动
- Lombok（可选，但推荐）
- Spring Boot Starter Test

**开发命令参考**:
```bash
mvn spring-boot:run     # 启动开发服务器
mvn test                # 运行测试
mvn clean install       # 构建项目
```

=== 架构设计文档（后端部分） ===

{backend_arch_info}

=== 输出格式 ===

使用代码块格式输出每个文件的内容，格式如下：

```backend/pom.xml
<?xml version="1.0" encoding="UTF-8"?>
<project ...>
...
```

```backend/src/main/java/com/example/app/entity/Task.java
@Entity
public class Task {
...
}
```

⚠️ **重要**: 生成后项目必须可以直接运行 `mvn spring-boot:run`
