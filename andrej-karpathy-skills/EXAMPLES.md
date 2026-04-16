# 示例

展示四大原则的真实代码示例。每个示例展示 LLM 通常哪里做错了，以及如何修复。

---

## 1. 编码前先思考

### 示例 1：隐藏的假设

**用户请求：** "添加导出用户数据的功能"

**❌ LLM 常见做法（错误假设）**

```python
def export_users(format='json'):
    """Export all users to a file."""
    users = User.query.all()
    
    if format == 'json':
        with open('users.json', 'w') as f:
            json.dump([u.to_dict() for u in users], f)
    elif format == 'csv':
        with open('users.csv', 'w') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'email', 'name'])
            writer.writeheader()
            writer.writerows([u.to_dict() for u in users])
    
    return f"Exported {len(users)} users"
```

**问题：**
- 假设应该导出**所有**用户（分页呢？隐私呢？）
- 不询问就假设文件位置
- 假设应该包含哪些字段
- 不检查实际数据结构就假设 CSV 字段名

**✅ 应该怎么做（呈现假设）**

```
实现之前，我需要澄清：

1. **范围**：导出所有用户还是过滤子集？（隐私考虑）
2. **格式**：你说"导出"，具体是指：
   - 浏览器下载文件？
   - 带邮件通知的后台任务？
   - 返回数据的 API 端点？
3. **字段**：哪些用户字段？（有些可能敏感）
4. **数据量**：通常有多少用户？（影响实现方式）

最简单的方法：添加一个返回分页 JSON 的 API 端点。
基于文件导出需要更多信息。

你的偏好是什么？
```

### 示例 2：多种解释

**用户请求：** "让搜索更快"

**❌ LLM 常见做法（默默选择）**

```python
# Adds caching, database indexes, and async processing
# without asking which "faster" matters
@lru_cache(maxsize=1000)
async def search(query: str) -> List[Result]:
    # ... 200 行优化代码
```

**✅ 应该怎么做**

```
"让搜索更快"可能意味着：

1. **更快的响应时间**（< 100ms 而不是 500ms）
   - 添加数据库索引
   - 缓存频繁查询
   - 预估工作量：2 小时

2. **支持更多并发搜索**（吞吐量）
   - 添加 async/await
   - 连接池
   - 预估工作量：4 小时

3. **感知更快**（用户体验）
   - 立即显示部分结果
   - 渐进式加载
   - 预估工作量：3 小时

当前搜索典型查询需要 ~500ms。你的使用场景最关心哪个方面？
```

---

## 2. 简单优先

### 示例 1：过度抽象

**用户请求：** "添加一个计算折扣的函数"

**❌ LLM 常见做法（过度工程化）**

```python
from abc import ABC, abstractmethod
from enum import Enum
from typing import Protocol, Union
from dataclasses import dataclass

class DiscountStrategy(ABC):
    @abstractmethod
    def calculate(self, amount: float) -> float:
        pass

class PercentageDiscount(DiscountStrategy):
    def __init__(self, percentage: float):
        self.percentage = percentage
    
    def calculate(self, amount: float) -> float:
        return amount * (self.percentage / 100)

class FixedDiscount(DiscountStrategy):
    def __init__(self, fixed_amount: float):
        self.fixed_amount = fixed_amount
    
    def calculate(self, amount: float) -> float:
        return min(self.fixed_amount, amount)

@dataclass
class DiscountConfig:
    strategy: DiscountStrategy
    min_purchase: float = 0.0
    max_discount: float = float('inf')

class DiscountCalculator:
    def __init__(self, config: DiscountConfig):
        self.config = config
    
    def apply_discount(self, amount: float) -> float:
        if amount < self.config.min_purchase:
            return 0
        discount = self.config.strategy.calculate(amount)
        return min(discount, self.config.max_discount)

# 使用需要 30 多行设置就为了一个简单计算
```

**✅ 应该怎么做（简单）**

```python
def calculate_discount(amount: float, percent: float) -> float:
    """Calculate discount amount. percent should be 0-100."""
    return amount * (percent / 100)

# 使用
discount = calculate_discount(100.0, 10.0)  # 减 $10
```

**何时添加复杂度：** 只有当你真的需要多种折扣类型时。如果需求后来来了，再重构。

### 示例 2：推测性特性

**用户请求：** "保存用户偏好到数据库"

**❌ LLM 常见做法（不必要的功能）**

```python
class PreferenceManager:
    def __init__(self, db, cache=None, validator=None):
        self.db = db
        self.cache = cache or InMemoryCache()
        self.validator = validator or DefaultValidator()
    
    def save(self, user_id: int, prefs: dict, 
             merge: bool = True, 
             validate: bool = True,
             notify: bool = False) -> bool:
        """Save preferences with optional merging, validation, and notifications."""
        
        if validate:
            errors = self.validator.validate(prefs)
            if errors:
                raise ValidationError(errors)
        
        existing = self.get(user_id) if merge else {}
        
        if merge:
            existing.update(prefs)
            prefs = existing
        
        self.db.execute(
            "UPDATE users SET preferences = ? WHERE id = ?",
            (json.dumps(prefs), user_id)
        )
        
        if self.cache:
            self.cache.set(f"prefs:{user_id}", prefs)
        
        if notify:
            self.notify_preference_change(user_id, prefs)
        
        return True
    
    def notify_preference_change(self, user_id: int, prefs: dict):
        # 又一个没人要求的功能，又 30 行代码
        pass
```

**✅ 应该怎么做（只做被要求的）**

```python
def save_preferences(db, user_id: int, preferences: dict):
    """Save user preferences to database."""
    db.execute(
        "UPDATE users SET preferences = ? WHERE id = ?",
        (json.dumps(preferences), user_id)
    )
```

**需要时再添加：** 缓存（当性能需要时）、验证（当出现坏数据时）、合并（当需求出现时）。

---

## 3. 外科手术式更改

### 示例 1：顺路重构

**用户请求：** "修复空邮箱导致验证器崩溃的 bug"

**❌ LLM 常见做法（改太多）**

```diff
  def validate_user(user_data):
-     # Check email format
-     if not user_data.get('email'):
+     """Validate user data."""
+     email = user_data.get('email', '').strip()
+     
+     # Validate email
+     if not email:
          raise ValueError("Email required")
-     
-     # Basic email validation
-     if '@' not in user_data['email']:
+     if '@' not in email or '.' not in email.split('@')[1]:
          raise ValueError("Invalid email")
      
-     # Check username
-     if not user_data.get('username'):
+     # Validate username
+     username = user_data.get('username', '').strip()
+     if not username:
          raise ValueError("Username required")
+     if len(username) < 3:
+         raise ValueError("Username too short")
+     if not username.isalnum():
+         raise ValueError("Username must be alphanumeric")
      
      return True
```

**问题：**
- "改进"了邮箱验证，超出 bug 修复范围
- 添加了没人要求的用户名验证
- 修改了注释
- 添加了文档字符串

**✅ 应该怎么做（外科手术式）**

```diff
  def validate_user(user_data):
      # Check email format
-     if not user_data.get('email'):
+     email = user_data.get('email', '')
+     if not email or not email.strip():
          raise ValueError("Email required")
      
      # Basic email validation
-     if '@' not in user_data['email']:
+     if '@' not in email:
          raise ValueError("Invalid email")
      
      # Check username
      if not user_data.get('username'):
          raise ValueError("Username required")
      
      return True
```

**只修改了：** 修复空邮箱处理的特定行。

### 示例 2：风格漂移

**用户请求：** "给上传函数添加日志"

**❌ LLM 常见做法（重新格式化一切）**

```diff
- def upload_file(file_path, destination):
+ def upload_file(file_path: str, destination: str) -> bool:
+     """Upload file to destination with logging."""
+     logger.info(f"Uploading {file_path} to {destination}")
+     
      try:
-         with open(file_path, 'rb') as f:
-             data = f.read()
-         
-         response = requests.post(destination, files={'file': data})
-         
-         if response.status_code == 200:
-             return True
-         else:
-             return False
+         with open(file_path, "rb") as f:
+             data = f.read()
+         response = requests.post(destination, files={"file": data})
+         success = response.status_code == 200
+         
+         if success:
+             logger.info(f"Upload successful: {file_path}")
+         else:
+             logger.error(f"Upload failed: {file_path}, status={response.status_code}")
+         
+         return success
      except Exception as e:
-         print(f"Error: {e}")
+         logger.exception(f"Upload error for {file_path}: {e}")
          return False
```

**问题：**
- 修改了引号风格（'' 改成 ""）
- 添加了没人要求的类型提示
- 添加了文档字符串
- 重新格式化了空白
- 修改了布尔返回逻辑

**✅ 应该怎么做（匹配现有风格）**

```diff
+ import logging
+ 
+ logger = logging.getLogger(__name__)
+ 
  def upload_file(file_path, destination):
+     logger.info(f'Starting upload: {file_path}')
      try:
          with open(file_path, 'rb') as f:
              data = f.read()
          
          response = requests.post(destination, files={'file': data})
          
          if response.status_code == 200:
+             logger.info(f'Upload successful: {file_path}')
              return True
          else:
+             logger.error(f'Upload failed: {file_path}, status={response.status_code}')
              return False
      except Exception as e:
-         print(f"Error: {e}")
+         logger.exception(f'Upload error for {file_path}')
          return False
```

**匹配了：** 单引号，没有类型提示，现有的布尔模式，间距风格。

---

## 4. 目标驱动执行

### 示例 1：模糊 vs 可验证

**用户请求：** "修复认证系统"

**❌ LLM 常见做法（模糊方法）**

```
我会通过以下步骤修复认证系统：
1. 审查代码
2. 识别问题
3. 做出改进
4. 测试修改

[在没有清晰成功标准的情况下继续修改]
```

**✅ 应该怎么做（可验证目标）**

```
要"修复认证"，我需要定义成功标准。
我们在解决什么具体问题？

如果问题是"密码修改后用户仍然保持登录"：

计划：
1. 编写测试：修改密码 → 验证旧会话失效
   验证：测试失败（复现 bug）

2. 实现：密码修改时使会话失效
   验证：测试通过

3. 检查边界情况：多个活跃会话，并发修改
   验证：附加测试通过

4. 验证没有回归：现有认证测试仍然通过
   验证：完整测试套件全绿

当前认证测试覆盖率：[显示覆盖率]

你看到的具体认证问题是什么？
```

### 示例 2：带验证的多步骤

**用户请求：** "给 API 添加限流"

**❌ LLM 常见做法（一下子全做）**

```python
# 一次性用 300 行提交实现完整限流，包含 Redis、多种策略、
# 配置系统和监控
# 没有清晰的验证步骤
```

**✅ 应该怎么做（增量式带验证）**

```
限流计划：

1. 添加基础内存限流（单个端点）
   验证：
   - 测试：100 个请求 → 前 10 个成功，其余得到 429
   - 手动：curl 端点 11 次，看到限流错误

2. 提取到中间件（应用到所有端点）
   验证：
   - 测试：限流应用到 /users 和 /posts
   - 现有端点测试仍然通过

3. 添加 Redis 后端（适用于多服务器）
   验证：
   - 测试：限流在应用重启后仍然保持
   - 测试：两个应用实例共享限流计数器

4. 添加配置（每个端点速率）
   验证：
   - 测试：/search 允许 10/分钟，/users 允许 100/分钟
   - 配置文件解析正确

每一步都可以独立验证和部署。
从第一步开始吗？
```

### 示例 3：测试优先验证

**用户请求：** "当有重复分数时排序会出问题"

**❌ LLM 常见做法（不复现就修复）**

```python
# 不确认 bug 就立即修改排序逻辑
def sort_scores(scores):
    return sorted(scores, key=lambda x: (-x['score'], x['name']))
```

**✅ 应该怎么做（先复现）**

```python
# 1. 首先，编写一个复现问题的测试
def test_sort_with_duplicate_scores():
    """Test sorting when multiple items have same score."""
    scores = [
        {'name': 'Alice', 'score': 100},
        {'name': 'Bob', 'score': 100},
        {'name': 'Charlie', 'score': 90},
    ]
    
    result = sort_scores(scores)
    
    # bug：重复值的顺序不确定
    # 运行这个测试多次，应该保持一致
    assert result[0]['score'] == 100
    assert result[1]['score'] == 100
    assert result[2]['score'] == 90

# 验证：运行测试 10 次 → 不一致排序时失败
```

```python
# 2. 现在用稳定排序修复
def sort_scores(scores):
    """Sort by score descending, then name ascending for ties."""
    return sorted(scores, key=lambda x: (-x['score'], x['name']))

# 验证：测试持续通过
```

---

## 反模式总结

| 原则 | 反模式 | 修复方法 |
|-----------|-------------|-----|
| 编码前先思考 | 默默假设文件格式、字段、范围 | 明确列出假设，请求澄清 |
| 简单优先 | 策略模式处理单次折扣计算 | 先用一个函数，真正需要复杂度时再抽象 |
| 外科手术式更改 | 修复 bug 时重新格式化引号、添加类型提示 | 只修改修复报告问题的行 |
| 目标驱动 | "我会审查并改进代码" | "为 bug X 编写测试 → 让它通过 → 验证没有回归" |

## 核心洞见

这些"过度复杂"的例子不是明显错误 — 它们遵循设计模式和最佳实践。问题在于**时机**：它们在需要之前就添加了复杂度，这会：

- 让代码更难理解
- 引入更多 bug
- 实现耗时更长
- 更难测试

而"简单"版本：

- 更容易理解
- 实现更快
- 更容易测试
- 真正需要复杂度时可以再重构

**好代码是简单解决今天问题的代码，而不是提前解决明天问题的代码。**
