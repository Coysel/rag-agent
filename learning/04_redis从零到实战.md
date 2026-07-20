# 第四部分：Redis

> **学习目标**：这一部分的目标是让你真正理解 Redis —— 不再把它当作一个"黑盒缓存"，而是理解它为什么快、每种数据结构的设计思想、以及如何合理地使用它。学完之后，你应该能回答"为什么 Redis 是单线程却这么快"、"String 和 Hash 分别适合存什么"、"缓存雪崩和缓存穿透的根本区别是什么"这类深层问题。

---

## 一、Redis 概述：它到底是什么

### 1.1 什么是 Redis

**Redis（Remote Dictionary Server，远程字典服务）** 是一个开源的、基于内存的键值对（Key-Value）存储系统。它的名字已经揭示了本质：一个"远程的字典"——你通过网络（Remote）访问一个存储在内存中的"字典"（Dictionary），这个字典的键可以是字符串，值可以是多种数据结构。

但 Redis 远不止是一个缓存：

- **内存数据库**：数据主要存储在内存中，读写速度极快（微秒级）
- **数据结构服务器**：支持 String、List、Hash、Set、Zset 等多种数据结构
- **可选持久化**：可以将内存中的数据持久化到磁盘，重启后恢复
- **支持分布式**：提供主从复制、哨兵模式、Cluster 模式

### 1.2 为什么 Redis 这么快？

这是面试中最经典的问题之一。我们来逐一拆解原因：

**原因一：基于内存**

Redis 的数据存储在内存中，而传统数据库（如 MySQL）的数据存储在磁盘上。内存的随机读取速度比磁盘快几个数量级：

| 存储介质 | 典型延迟 | 相对速度 |
|---------|---------|---------|
| 内存 (DDR4) | ~50-100ns | 1x |
| SSD | ~10-100μs | 慢 ~200 倍 |
| 机械硬盘 | ~5-10ms | 慢 ~50000 倍 |

**这意味什么？** 当你在 Redis 中读取一个键时，CPU 直接访问内存地址获取数据，不需要经过磁盘 I/O 的寻道、旋转、读取等机械动作。

**原因二：单线程模型**

很多人刚听说 Redis 是单线程时都会感到困惑："单线程怎么能处理高并发？" 这恰恰是 Redis 设计中最精妙的地方。

**核心思路**：Redis 使用单线程事件循环（Event Loop）来处理所有客户端的请求。所有请求在一个线程中串行执行，没有线程切换和锁竞争的开销。

```
传统多线程服务器:           Redis 单线程:
┌─────┐   ┌─────┐          ┌──────────────┐
│线程1 │   │线程2 │          │  事件循环线程 │
│请求A │   │请求B │          │  请求A → 请求B│
│  ↕   │   │  ↕   │          │  串行执行     │
│加锁  │   │加锁  │          │  无需加锁     │
│  ↕   │   │  ↕   │          │              │
└─────┘   └─────┘          └──────────────┘
```

**为什么单线程反而更快？**

1. **无上下文切换开销**：多线程下，CPU 需要在线程之间切换，保存和恢复上下文（寄存器、栈等），这些操作有成本。单线程完全没有这个问题。
2. **无锁竞争**：多线程操作共享数据需要加锁（互斥锁、读写锁等），锁的获取和释放、线程的阻塞和唤醒都有开销。Redis 单线程串行执行，天然不需要锁。
3. **内存操作足够快**：既然操作本身就是微秒级的，多线程带来的收益远不如锁竞争和上下文切换的成本。瓶颈不在 CPU，而在网络 I/O。

> **但 Redis 真的完全是单线程的吗？** 从 Redis 6.0 开始，网络 I/O（读取请求、发送响应）使用了多线程，但命令的执行仍然在单线程中串行完成。这样既解决了网络 I/O 的瓶颈，又保持了单线程执行命令的简单性和原子性。

**原因三：I/O 多路复用**

Redis 使用 epoll（Linux）/ kqueue（macOS）等 I/O 多路复用技术，用一个线程同时监听多个套接字（Socket）上的事件：

```
┌────────── Redis 主线程 ──────────┐
│  while (1) {                      │
│    events = epoll_wait()          │  ← 同时监听所有客户端连接
│    for (event in events) {        │
│      if (event == 可读)           │
│        read_from_client()          │
│      if (event == 可写)           │
│        write_to_client()           │
│    }                               │
│  }                                 │
└────────────────────────────────────┘
```

客户端不需要主动轮询 Redis，Redis 会在数据准备好时主动通知客户端。这种方式让一个线程可以处理成千上万个并发连接。

**原因四：高效的数据结构**

Redis 的每种数据类型底层都使用了精心优化的数据结构（后面各节会详细讲），比如压缩列表（ziplist）、跳表（skiplist）、字典（hashtable）等。这些数据结构在内存占用和操作速度之间做了良好的平衡。

### 1.3 Redis 和 Memcached 的区别

Memcached 是另一个流行的内存缓存系统。了解它们的区别能帮你更好地理解 Redis 的定位：

| 维度 | Redis | Memcached |
|------|-------|-----------|
| 数据类型 | 5+ 种复杂数据结构 | 仅支持 String |
| 持久化 | RDB + AOF，重启可恢复 | 不支持，重启数据丢失 |
| 主从复制 | 支持 | 不支持 |
| 事务 | 支持（弱事务） | 不支持 |
| 线程模型 | 单线程 + 事件循环 | 多线程 |
| 内存使用 | 可配置淘汰策略 | LRU 淘汰 |

**为什么有了 Memcached 还需要 Redis？** Memcached 的设计极其简单——它就是一个分布式的键值哈希表。但实际业务中，我们需要的不只是"存字符串"：我们需要排行榜（Zset）、需要去重（Set）、需要对象缓存（Hash）、需要在服务器重启后不丢失数据（持久化）。Redis 正是为了满足这些更丰富的需求而诞生的。

---

## 二、五种基本数据类型（上）

Redis 的核心魅力在于：它不只是一个缓存，更是一个数据结构服务器。理解每种数据结构的设计意图和适用场景，是使用 Redis 的关键。

### 2.1 String（字符串）

#### 什么是 String

String 是 Redis 中最基础的数据类型，也是其他四种类型的基础。一个 Redis String 可以存储：

- 字符串（UTF-8 编码的文本）
- 整数（最大 2^63-1）
- 浮点数
- 二进制数据（图片、序列化对象等，最大 512 MB）

**为什么 String 能存二进制数据？** Redis 的 String 是二进制安全的（Binary Safe）。这意味着它不依赖于任何特殊的字符串结束符（如 C 语言的 `\0`），而是使用长度字段来记录字符串的长度。所以任何二进制数据——包括包含 `\0` 字节的图片、压缩文件——都可以安全地存储和读取。

#### 常用命令

```bash
# 设置键值
SET name "张三"

# 获取值
GET name                     # → "张三"

# 设置过期时间（秒）
SET session:token "abc123" EX 3600

# 同时设置多个键值
MSET name "张三" age "25" city "北京"

# 同时获取多个键值
MGET name age city            # → ["张三", "25", "北京"]

# 原子递增（用于计数器）
INCR page:view:article:42     # → 1
INCR page:view:article:42     # → 2
INCRBY page:view:article:42 10  # → 12
```

**为什么不使用 `GET` 和 `SET` 来同时存储多个字段？** 假设你要存储一个用户对象：

```
SET user:1001:name "张三"
SET user:1001:age "25"
SET user:1001:city "北京"
```

这种方式的问题在于：每个属性都是一个独立的键，要获取用户的所有信息需要三次网络请求。更好的方式是用 Hash 类型（后面会讲）。

#### 内部编码

Redis 的 String 有三种内部编码方式，根据字符串的长度和内容自动选择：

| 编码方式 | 说明 | 触发条件 |
|---------|------|---------|
| int | 整数编码 | 值可以被解析为 64 位整数 |
| embstr | 嵌入式字符串 | 字符串长度 ≤ 44 字节 |
| raw | 原始字符串 | 字符串长度 > 44 字节 |

**为什么是 44 字节？** 这和 Redis 的内存分配有关。Redis 使用 jemalloc 内存分配器，一次内存分配的最小单位是 64 字节。在 embstr 编码中，64 字节中需要减去 RedisObject 头部（16 字节）和 SDS 头部（至少 4 字节），剩下 44 字节给实际数据。超过 44 字节就需要两次内存分配（一次分配 RedisObject，一次分配 SDS），因此使用 raw 编码。

#### 典型应用场景

**场景一：缓存** — 把数据库查询结果缓存到 Redis 中，下次请求直接从缓存读取：

```python
def get_user(user_id):
    # 1. 先从 Redis 读取
    user = redis.get(f"user:{user_id}")
    if user:
        return json.loads(user)
    
    # 2. 缓存未命中，从数据库读取
    user = db.query("SELECT * FROM users WHERE id = ?", user_id)
    
    # 3. 写入缓存，设置过期时间（秒）
    redis.setex(f"user:{user_id}", 3600, json.dumps(user))
    
    return user
```

**为什么先查缓存而不是直接查数据库？** 数据库的磁盘 I/O 比 Redis 的内存访问慢几个数量级。如果每次请求都查数据库，高并发下数据库会不堪重负。缓存层的作用就是"挡住"大部分请求，只有缓存未命中时才穿透到数据库。

**场景二：计数器** — INCR 命令是原子的，适用于点赞数、访问量、库存计数等：

```python
def like_article(article_id):
    # 原子递增，并发安全
    count = redis.incr(f"like:{article_id}")
    return count

# 两个客户端同时执行 incr：
# 客户端 A: incr like:42 → 读取 100 → +1 → 写入 101
# 客户端 B: incr like:42 → 读取 101 → +1 → 写入 102
# 结果永远是 102，不会出现 101（竞态条件）
```

**为什么 INCR 是原子的？** 因为 Redis 是单线程的。当 INCR 命令执行时，其他所有命令都在排队等待。所以 INCR 的"读取 → +1 → 写入"三步之间不会有其他命令插入。这也回答了前面的问题：单线程的最大好处就是所有操作天然原子。

**场景三：分布式会话（Session）共享** — 在多台服务器的集群中，用户的登录状态不能存在单台服务器的内存中（否则其他服务器不认识这个用户），而应该存在共享的 Redis 中：

```python
# 用户登录后
session_id = uuid4()
redis.setex(f"session:{session_id}", 7200, json.dumps({
    "user_id": 123,
    "role": "admin",
    "login_time": time.time()
}))
# 后续请求携带这个 session_id，任何一台服务器都可以从 Redis 读取会话信息
```

---

### 2.2 List（列表）

#### 什么是 List

Redis 的 List 是一个**有序的字符串列表**，底层实现是一个双向链表（linkedlist）或压缩列表（ziplist）。它支持在两端插入和删除元素，因此非常适合用做**队列**（Queue）或**栈**（Stack）。

**为什么用双向链表？** 因为 Redis 需要在两端（左端和右端）都能高效地插入和删除。数组在头部插入/删除需要移动所有元素（O(n)），而双向链表在两端操作都是 O(1)——只需要调整指针。

#### 常用命令

```bash
# 从右侧插入（向队尾追加）
RPUSH logs "2026-07-13 10:00:00 用户登录"
RPUSH logs "2026-07-13 10:05:00 用户下单"
RPUSH logs "2026-07-13 10:10:00 用户支付"

# 从左侧取出（从队头取出）
LPOP logs                   # → "2026-07-13 10:00:00 用户登录"

# 从左侧插入（向队头插入，栈的行为）
LPUSH stack "任务1"
LPUSH stack "任务2"          # → ["任务2", "任务1"]

# 获取列表长度
LLEN logs                    # → 2

# 获取范围内的元素
LRANGE logs 0 -1             # 获取所有元素
LRANGE logs 0 9              # 获取前10个元素
```

#### 阻塞操作：BRPOP / BLPOP

这是 List 类型最具特色的功能。想象一个场景：有一个后台 Worker 不停从列表中获取任务，但列表可能为空。如果使用 `RPOP`，Worker 需要不断轮询（循环请求），浪费 CPU 和网络资源。

```python
# Worker 端：使用 BRPOP 阻塞读取
while True:
    # 如果列表为空，Worker 会阻塞等待，直到有新任务到来
    # 超时时间设置为 0（永不超时）
    task = redis.brpop("task:queue", timeout=0)
    process_task(task)
```

**为什么需要阻塞操作？** 想象一下生产者-消费者模式：
- 生产者每隔几分钟才生产一个任务
- 消费者如果使用 `RPOP` 轮询，每秒钟需要发送几十次请求，99.9% 都是徒劳的
- 使用 `BRPOP`，消费者"挂起"在 Redis 上，当新元素到来时 Redis 主动通知消费者

这类似于操作系统的阻塞 I/O 和 epoll 的区别——从"我来看看有没有"变成了"有了叫我"。

#### 典型应用场景

**场景：消息队列**

List 的 LPUSH + BRPOP 组合天然适合做简单的消息队列：

```
生产者 A ──→ LPUSH task:queue "任务1"
生产者 B ──→ LPUSH task:queue "任务2"

消费者 1 ──→ BRPOP task:queue 0  → 取出 "任务1"
消费者 2 ──→ BRPOP task:queue 0  → 取出 "任务2"
```

> **为什么不用专业的消息队列如 RabbitMQ？** Redis List 作为消息队列的好处是轻量——不需要额外部署消息队列系统，你的团队只需要管理 Redis 就够了。但它的局限性也很明显：不支持消息确认机制（ACK），消费者取出消息后如果崩溃，消息就丢失了。对于需要严格保证不丢消息的场景（如支付、订单处理），应该使用 RabbitMQ 或 Kafka。

---

### 2.3 Hash（哈希/散列）

#### 什么是 Hash

Redis 的 Hash 是一个 **field-value 映射表**，相当于一个嵌套的键值对。你可以把它理解为"对象"的扁平表示：

```
键: user:1001
┌─────────────────────────┐
│ field    │ value        │
├─────────┼──────────────┤
│ name    │ "张三"        │
│ age     │ "25"          │
│ city    │ "北京"        │
│ email   │ "z@example.com"│
└─────────────────────────┘
```

#### 为什么需要 Hash？

回想一下 String 的部分，如果我们用 String 存储用户对象：

```bash
# 方式一：序列化整个对象为 JSON
SET user:1001 '{"name":"张三","age":25,"city":"北京"}'
# 缺点：要修改 age 需要整个读出 → 反序列化 → 修改 → 序列化 → 写入
```

```bash
# 方式二：每个属性一个键
SET user:1001:name "张三"
SET user:1001:age 25
# 缺点：占用更多键名空间，获取所有属性需要多次网络请求
```

Hash 就是为了解决这个问题而设计的：

```bash
HSET user:1001 name "张三" age 25 city "北京"

# 只获取 name 字段
HGET user:1001 name              # → "张三"

# 获取所有字段
HGETALL user:1001                # → {name: "张三", age: "25", city: "北京"}

# 只修改 age，不需要传输整个对象
HSET user:1001 age 26
```

**Hash 的核心理念**：将一组相关的属性聚合成一个键，通过 field 区分不同属性。这样既节省了键名空间，又支持对单个属性的高效读写。

#### 内部编码

Hash 有两种内部编码方式：

| 编码方式 | 说明 | 触发条件 |
|---------|------|---------|
| ziplist | 压缩列表 | field 数量 < 512 且所有 value 长度 < 64 字节 |
| hashtable | 哈希表 | 超过 ziplist 的限制 |

**为什么先用 ziplist？** 当 Hash 较小的时候，用 ziplist（压缩列表）可以节省大量内存。ziplist 是一段连续的内存块，数据挨个排列，没有额外的指针开销。而 hashtable 需要为每个键值对维护额外的哈希表结构。Redis 在数据量小时自动选择 ziplist，数据量增大后转换为 hashtable，这是典型的"空间换时间"和"时间换空间"的动态平衡。

#### 典型应用场景

**场景：对象缓存**

```python
# 缓存一篇博客文章的元信息
article_id = 42
redis.hset(f"article:{article_id}", mapping={
    "title": "Redis 详解",
    "author": "张三",
    "publish_time": "2026-07-13",
    "view_count": 0
})

# 只更新 view_count（原子递增）
redis.hincrby(f"article:{article_id}", "view_count", 1)

# 只获取标题
title = redis.hget(f"article:{article_id}", "title")
```

**和 String 序列化方式的对比**：

| 维度 | String + JSON | Hash |
|------|-------------|------|
| 获取单个字段 | 需要反序列化整个 JSON | O(1) 直接读取 |
| 修改单个字段 | 需要读出、反序列化、修改、序列化、写入 | O(1) 直接修改 |
| 内存效率 | 整体序列化可能更紧凑 | 字段名会重复存储（但 ziplist 优化后不错）|

> **什么时候用 String + JSON，什么时候用 Hash？** 如果你总是需要读写整个对象（如缓存页面 HTML），用 String 序列化更方便。如果你只需要读写对象的个别字段（如更新计数器、获取标题），用 Hash 更高效。没有绝对的对错，取决于你的访问模式。

---

## 三、五种基本数据类型（下）

### 3.1 Set（集合）

#### 什么是 Set

Set 是一个**无序的、不可重复的字符串集合**。它类似于数学中的"集合"概念——元素互不相同，支持集合运算（交集、并集、差集）。

```bash
SADD tags:article:42 "Redis" "数据库" "缓存"
SADD tags:article:42 "Redis"    # ← 第二次添加相同的元素，被忽略
SMEMBERS tags:article:42        # → ["Redis", "数据库", "缓存"]（顺序不保证）
```

**为什么 Set 能保证元素不重复？** Set 的底层是哈希表（hashtable）或整数集合（intset）。哈希表的键就是存储的元素，哈希表的特性保证了键的唯一性。当你尝试添加一个已存在的元素时，哈希表发现键已存在，直接返回 0（添加失败）。

#### 集合运算

Set 最强大的功能是支持集合间的运算：

```bash
# 用户 A 关注的标签
SADD user:a:tags "Redis" "Python" "Linux" "Docker"

# 用户 B 关注的标签
SADD user:b:tags "Python" "Docker" "Kubernetes" "MySQL"

# 交集：两人都关注的标签
SINTER user:a:tags user:b:tags    # → ["Python", "Docker"]

# 并集：两人关注的所有标签（去重）
SUNION user:a:tags user:b:tags    # → ["Redis", "Python", "Linux", "Docker", "Kubernetes", "MySQL"]

# 差集：A 关注但 B 不关注的
SDIFF user:a:tags user:b:tags     # → ["Redis", "Linux"]
```

#### 为什么集合运算需要 O(N) 的时间？

以交集（SINTER）为例，Redis 的实现是：
1. 找出元素数量最少的集合（假设有 m 个元素）
2. 遍历这个最小集合，检查每个元素是否也在其他集合中存在
3. 存在则加入结果集

所以时间复杂度是 O(m × n)，其中 m 是最小集合的大小，n 是其他集合的数量。这也意味着：**如果两个集合都很大（比如百万级别），交集运算会比较慢**。在实际系统中，应该对大型集合的交并集运算有性能意识。

#### 典型应用场景

**场景一：标签系统**

```python
# 给文章打标签
redis.sadd(f"article:{article_id}:tags", "Redis", "缓存", "数据库")

# 根据标签查找文章
redis.sadd("tag:Redis:articles", 1001, 1002, 1005)
redis.sadd("tag:缓存:articles", 1001, 1003)

# 查找同时包含"Redis"和"缓存"标签的文章
articles = redis.sinter("tag:Redis:articles", "tag:缓存:articles")
# → [1001]
```

**场景二：UV（独立访客）统计**

```python
def record_visit(user_id, page_id):
    redis.sadd(f"uv:page:{page_id}:{today}", user_id)

def get_uv(page_id):
    return redis.scard(f"uv:page:{page_id}:{today}")  # SCARD 返回集合大小
```

**为什么 Set 适合 UV 统计？** UV（Unique Visitor）的核心要求是"去重"——同一个用户一天内多次访问只算一次。Set 天然去重。但这也意味着 Set 会记住所有访问过的用户 ID，如果 UV 非常大（比如千万级），内存消耗会很大。对于超大规模的 UV 统计，通常使用 HyperLogLog（一种 Redis 的概率数据结构，用固定 12KB 内存就能统计 2^64 个元素的基数，误差约 0.81%）。

---

### 3.2 Zset (Sorted Set，有序集合)

#### 什么是 Zset

Zset 是 Redis 中最复杂也最强大的数据类型。它和 Set 一样，元素唯一且不重复，但每个元素关联了一个 **score（分数）**，元素按照 score 从小到大排序。

```
ZADD leaderboard 100 "玩家A"
ZADD leaderboard 200 "玩家B"
ZADD leaderboard 150 "玩家C"

内部存储结构（逻辑视图）：
┌─────────┬───────┐
│ 成员    │ 分数  │
├─────────┼───────┤
│ 玩家A   │ 100   │  ← 分数最低，排第一
│ 玩家C   │ 150   │
│ 玩家B   │ 200   │  ← 分数最高，排第三
└─────────┴───────┘
```

#### 底层实现：跳表（Skip List）

Zset 的核心数据结构是**跳表（skiplist） + 哈希表（hashtable）** 的组合：

- **跳表**：维护元素的排序顺序，支持范围查询（如"返回排名前 10 的元素"）
- **哈希表**：通过元素值 O(1) 查找分数

**为什么 Zset 选择跳表而不是平衡树（如红黑树）？**

这是 Redis 作者 antirez 的设计选择，原因如下：

1. **实现简单**：跳表的实现比平衡树简单得多，代码量约为红黑树的 1/3
2. **调试容易**：跳表的结构可以用多级链表直观理解，出现 Bug 时更容易定位
3. **范围查询友好**：跳表在范围查询（ZRANGE、ZRANK 等）上效率很高，因为底层是一个有序链表
4. **性能可接受**：跳表的 CRUD 操作平均 O(log N)，与平衡树同级

```
普通链表（只能顺序查找）:
A → C → E → G → H → J → K  查找 H 需要遍历 5 步

跳表（多级索引）:
Level 2: A → E → H → K
Level 1: A → C → E → G → H → J → K

查找 H: L2 先定位到 E→H（2步），然后在 L1 找到 H（1步），共 3 步
如果没有跳表，需要 5 步
```

跳表通过在有序链表上增加多级"索引"来实现快速查找，每层索引的元素数量约为下层的一半。这个过程类似于二分查找，但不需要像数组那样移动元素来插入数据。

#### Zset 的核心操作

```bash
# 添加元素（如果已存在则更新分数）
ZADD leaderboard 100 "玩家A"

# 获取排名（按分数从低到高，0 为第一名）
ZRANK leaderboard "玩家A"        # → 0
ZRANK leaderboard "玩家C"        # → 1

# 获取逆序排名（从高到低）
ZREVRANK leaderboard "玩家B"     # → 0（第一名）

# 获取分数
ZSCORE leaderboard "玩家A"       # → "100"

# 增加分数（原子操作）
ZINCRBY leaderboard 50 "玩家A"   # → 150（玩家A的分数变为 150）

# 获取排名前 3 的元素（按分数从高到低）
ZREVRANGE leaderboard 0 2 WITHSCORES
# → ["玩家B", 200, "玩家A", 150, "玩家C", 150]
```

#### 典型应用场景

**场景一：实时排行榜**

这是 Zset 最经典的用例。比如一个游戏需要实时显示玩家的得分排行：

```python
def update_score(player_id, delta):
    """玩家获得 delta 分"""
    redis.zincrby("game:leaderboard:2026-07-13", delta, player_id)

def get_top_10():
    """获取排行榜前十"""
    return redis.zrevrange("game:leaderboard:2026-07-13", 0, 9, withscores=True)

def get_my_rank(player_id):
    """获取我的排名"""
    rank = redis.zrevrank("game:leaderboard:2026-07-13", player_id)
    return rank + 1 if rank is not None else None
```

**为什么排行榜用 Zset 而不是 MySQL 的 ORDER BY？** MySQL 的 ORDER BY score DESC LIMIT 10 在数据量大时（比如百万行）需要对 score 字段做全表扫描或文件排序（filesort），性能很差。即使建了索引，每次查询也需要 B+ 树的遍历。Zset 的内部结构天然维护了排序顺序，获取前 N 名只需要遍历跳表的前 N 个节点，时间复杂度 O(log N + N)。

**场景二：延迟队列**

利用 Zset 的 score 作为时间戳，可以实现延迟任务：

```python
def schedule_task(task_id, delay_seconds):
    """延迟执行一个任务"""
    execute_at = time.time() + delay_seconds
    redis.zadd("delay:queue", {task_id: execute_at})

def poll_tasks():
    """轮询到期的任务"""
    now = time.time()
    # 获取所有 score 小于等于 now 的元素（即应该执行的任务）
    tasks = redis.zrangebyscore("delay:queue", 0, now)
    for task in tasks:
        # 尝试移除任务（原子操作，防止多个 Worker 重复执行）
        removed = redis.zrem("delay:queue", task)
        if removed:
            execute_task(task)
```

**为什么用 ZREM 而不是 ZRANGEBYSCORE 后直接执行？** 因为可能有多个 Worker 同时调用 poll_tasks()，如果只用 ZRANGEBYSCORE 获取任务而不原子地移除，两个 Worker 会拿到同一个任务。ZREM 是原子的，只保证一个 Worker 能成功移除并执行任务。

**场景三：带权重的限流**

```python
def is_rate_limited(user_id, max_requests=100, window_seconds=60):
    """在时间窗口内限制用户请求频率"""
    key = f"ratelimit:{user_id}:{int(time.time() / window_seconds)}"
    current = redis.get(key)
    if current and int(current) >= max_requests:
        return True  # 被限流
    redis.incr(key)
    redis.expire(key, window_seconds + 1)
    return False
```

---

### 3.3 数据类型速查表

| 类型 | 底层实现 | 有序？ | 唯一？ | 最大元素数 | 典型场景 |
|------|---------|--------|--------|-----------|---------|
| String | int / embstr / raw | - | 键唯一 | 512 MB/值 | 缓存、计数器、Session |
| List | ziplist / linkedlist | 是（插入顺序） | 否 | 2^32-1 | 消息队列、最新消息 |
| Hash | ziplist / hashtable | 字段无序 | 字段名唯一 | 2^32-1 字段 | 对象缓存 |
| Set | intset / hashtable | 否 | 是 | 2^32-1 | 标签、UV、交友推荐 |
| Zset | ziplist / skiplist | 是（按分数） | 是 | 2^32-1 | 排行榜、延迟队列 |

---

## 四、过期删除策略

### 4.1 为什么需要过期删除？

在实际系统中，我们很少希望一个缓存键永远存在：

- **用户会话**：登录状态应该在用户一段时间不活动后自动清除
- **临时数据**：验证码 5 分钟有效
- **缓存失效**：数据库查询结果缓存 1 小时后应该刷新

Redis 提供了设置过期时间的能力：

```bash
# 设置 10 秒后过期
SET code:13800138000 "123456" EX 10

# 查看剩余存活时间（秒）
TTL code:13800138000        # → 5（还剩 5 秒）

# 查看剩余存活时间（毫秒）
PTTL code:13800138000       # → 4987

# 取消过期时间（永不过期）
PERSIST code:13800138000    # → 返回 Key 还有 -1（永不过期）
```

### 4.2 三种删除策略

Redis 使用**定期删除 + 惰性删除**两种策略的组合。理解这两种策略的互补关系比单纯记住它们的名字更重要。

#### 策略一：惰性删除（Lazy Deletion）

**工作原理**：当一个键过期后，Redis 不会立即将其从内存中删除。而是等到有请求访问这个键时，Redis 发现它已经过期，才将其删除并返回空值。

```python
# Redis 内部逻辑（伪代码）
def get(key):
    value = lookup(key)
    if value and value.is_expired():
        delete(key)        # 发现过期了，删除
        return None
    return value
```

**优点**：
- **CPU 友好**：只删除真正被访问到的过期键，不做无用功。如果一个键过期后从未再被访问，Redis 就不需要花 CPU 去删除它。

**缺点**：
- **内存不友好**：如果大量过期键一直不被访问，它们会一直占用内存，造成"内存泄漏"。

想象一个场景：用户系统中有 1000 万个过期的 Session 键，但实际只有 1 万个活跃用户每天登录。惰性删除只处理那 1 万个被访问的过期 Session，剩下 999 万个过期 Session 继续占用内存。

#### 策略二：定期删除（Active / Periodic Deletion）

**工作原理**：每隔一段时间（默认 100ms），Redis 随机抽取一部分设置了过期时间的键进行检查，删除其中已过期的键。

```python
# Redis 内部逻辑（伪代码）
def active_expire_cycle():
    for _ in range(20):    # 每次检查 20 个键
        key = random_key_with_ttl()  # 从设置了过期时间的键中随机选一个
        if key and key.is_expired():
            delete(key)
    
    # 如果超过 25% 的检查键已过期，说明过期键很多，继续检查
    if expired_count > 5:
        active_expire_cycle()  # 递归（但总耗时有限制）
```

**关键参数**：
- `ACTIVE_EXPIRE_CYCLE_LOOKUPS_PER_LOOP`：每次检查的键数量，默认 20
- 如果检查的键中超过 25% 已过期，则继续检查

**优点**：
- **内存友好**：主动清理过期键，避免过期键无限堆积

**缺点**：
- **CPU 有开销**：需要额外的时间去扫描键
- **不是精确的**：只能"尽力"清理，不能保证所有过期键都被及时清理

#### 为什么需要两种策略组合？

看下面的对比就能理解为什么两者缺一不可：

```
只有惰性删除：
┌─────────────────────────────────┐
│ 过期键慢慢堆积，越来越多        │
│ 内存被无效数据占用，可能 OOM    │
└─────────────────────────────────┘

只有定期删除：
┌─────────────────────────────────┐
│ 每 100ms 扫描一次，CPU 开销大   │
│ 扫描太频繁 → CPU 被浪费        │
│ 扫描太少 → 过期键还是堆积       │
└─────────────────────────────────┘

两种组合：
┌─────────────────────────────────┐
│ 定期删除：兜底清理              │
│ 惰性删除：精确清理（被访问时）  │
│ CPU 和内存达到平衡              │
└─────────────────────────────────┘
```

### 4.3 一个关键问题：如果大量键同时过期会怎样？

这是**缓存雪崩**的根源之一（后面会详细讲）。当大量键设置了相同的过期时间（比如都是凌晨 0 点过期），会发生：

1. 大量键同时过期
2. Redis 定期删除扫描发现大量过期键
3. CPU 忙于删除操作
4. 同时，请求无法命中缓存，全部穿透到数据库
5. 数据库压力骤增，可能崩溃

**解决方案**：在设置过期时间时加入随机偏移量：

```python
# 不要这样：所有缓存统一 1 小时过期
redis.setex(key, 3600, value)

# 而是这样：在 3600 秒基础上加减随机值
import random
ttl = 3600 + random.randint(-300, 300)  # ±5 分钟随机
redis.setex(key, ttl, value)
```

---

## 五、内存淘汰策略（8 种）

### 5.1 淘汰 vs. 过期：根本区别

在讲淘汰策略之前，必须搞清楚一个容易混淆的概念：

| 概念 | 触发条件 | 目的 |
|------|---------|------|
| **过期删除** | 键的 TTL 到期 | 释放无效数据 |
| **内存淘汰** | Redis 内存用完（达到 maxmemory 限制） | 腾出空间给新数据 |

简单来说：**过期删除**是"这个键自己死了，我清理掉它"；**内存淘汰**是"内存满了，我不得不杀掉一些键来腾空间"。

### 5.2 配置最大内存

```bash
# redis.conf 中设置
maxmemory 4gb

# 或者运行时设置
CONFIG SET maxmemory 4gb
```

当 Redis 使用的内存达到这个上限后，再写入新数据就会触发淘汰策略。

> **为什么不设置 maxmemory？** 如果不设置，Redis 会一直使用内存直到系统内存用完（OOM），然后被操作系统杀死。这会导致所有缓存数据丢失，并且重启 Redis 可能需要从 RDB/AOF 恢复大量数据。**生产环境必须设置 maxmemory**。

### 5.3 八种淘汰策略详解

淘汰策略分为三大类，按"淘汰谁"来划分：

```
淘汰策略分类：
├── 不淘汰
│   └── noeviction —— 内存满了直接报错
│
├── 只淘汰设置了过期时间的键
│   ├── volatile-lru     —— 淘汰最近最少使用的
│   ├── volatile-lfu     —— 淘汰使用频率最低的
│   ├── volatile-random  —— 随机淘汰
│   └── volatile-ttl     —— 淘汰剩余存活时间最短的
│
└── 淘汰所有键（不管有没有过期时间）
    ├── allkeys-lru      —— 淘汰最近最少使用的
    ├── allkeys-lfu      —— 淘汰使用频率最低的
    └── allkeys-random   —— 随机淘汰
```

下面逐一详细解释：

#### noeviction（默认策略）

**行为**：内存达到上限后，所有写操作（SET、LPUSH、SADD 等）都返回错误，读操作不受影响。

**适用场景**：需要确保缓存数据不丢失的场景，或者你对自己的内存使用量有精确的控制。

**为什么默认是 noeviction？** 因为这是一个"保守的默认值"——与其默默地淘汰掉数据导致程序行为异常，不如让开发者明确意识到内存不足，主动选择合适的策略。

#### allkeys-lru（最常用的策略）

**行为**：在所有键中，淘汰最近最少使用的键。

**工作原理**：Redis 维护一个近似 LRU 算法（后面详解），追踪每个键的最后访问时间。当需要淘汰时，淘汰掉最久未被访问的键。

**适用场景**：**大多数应用的首选**。它假设"过去访问多的数据，将来也可能被访问"。

```bash
CONFIG SET maxmemory-policy allkeys-lru
```

#### volatile-lru

**行为**：只在设置了过期时间的键中，淘汰最近最少使用的键。

**适用场景**：你希望缓存即使用不完内存，也会根据 TTL 自动清理；同时给那些"永不过期"的键（如固定配置）保留空间。

**和 allkeys-lru 的区别**：
```
allkeys-lru:
所有键都参与淘汰，不分"有没有 TTL"

volatile-lru:
只淘汰有 TTL 的键，没 TTL 的键永远不被淘汰
这可能导致：缓存数据被淘汰了，但"垃圾数据"因为没设 TTL 而一直占用内存
```

#### allkeys-lfu（Redis 4.0 新增）

**行为**：在所有键中，淘汰使用频率最低的键。

**和 LRU 的区别**：

| 策略 | 关注什么 | 举例 |
|------|---------|------|
| LRU | 最近有没有被访问 | 一个键昨天被访问 100 次，今天没被访问 → LRU 认为它不热了 |
| LFU | 历史上被访问的频率 | 一个键昨天被访问 100 次，今天没被访问 → LFU 还记得它曾经很热 |

**为什么需要 LFU？** 有些场景，一个键被"集中访问"后可能很久不再访问，但它的历史热度仍然说明它是重要的。比如"新年祝福语"缓存，只在元旦当天被大量访问，但每年元旦都会被访问——LRU 会在年后很快将其淘汰，而 LFU 能记住它的历史热度。

#### volatile-lfu

**行为**：只在设置了过期时间的键中，淘汰使用频率最低的键。

#### allkeys-random

**行为**：在所有键中随机淘汰。

**适用场景**：键的访问概率比较均匀，没有明显的冷热差异。Redis 开发者中很少使用此策略，因为大多数场景下 LRU 或 LFU 效果更好。

#### volatile-random

**行为**：只在设置了过期时间的键中随机淘汰。

#### volatile-ttl

**行为**：只在设置了过期时间的键中，淘汰剩余存活时间（TTL）最短的键。

**适用场景**：你希望"快过期的先淘汰"，给那些新设置的缓存更多存活机会。

### 5.4 如何选择合适的策略

```python
def choose_eviction_policy(cache_type, has_ttl=True):
    if cache_type == "通用缓存 (用 Redis 当缓存层)":
        return "allkeys-lru"  # 最通用、最常用
    elif cache_type == "混合数据 (缓存 + 持久数据共存)":
        return "volatile-lru" if has_ttl else "allkeys-lru"
    elif cache_type == "Session 存储":
        return "allkeys-lfu"  # Session 的访问频率比较稳定
    elif cache_type == "不可丢失的数据":
        return "noeviction"   # 内存预警比淘汰数据更安全
```

### 5.5 近似 LRU 算法

Redis 没有实现标准的 LRU（需要精确记录每个键的访问时间，维护一个大的链表，开销大），而是使用了**近似 LRU 算法**：

```
标准 LRU:
┌───┐ ┌───┐ ┌───┐ ┌───┐
│A  │→│B  │→│C  │→│D  │  → 淘汰尾部（最近最少使用的）
└───┘ └───┘ └───┘ └───┘
每次访问，把节点移到头部

近似 LRU (Redis):
1. 随机采样 N 个键（默认 N=5）
2. 淘汰采样中 idle time（闲置时间）最长的那个
   ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐
   │A 3s│ │B 1s│ │C 8s│ │D 2s│ │E 5s│  → 淘汰 C（8 秒未被访问）
   └────┘ └────┘ └────┘ └────┘ └────┘
```

**为什么用采样而不是精确 LRU？** 精确 LRU 需要维护一个全局的有序链表——每次访问一个键，都要把这个键移到链表头部。这对 Redis 的单线程模型来说是一个 O(1) 但常数较大的操作，而且会引入大量的指针更新和内存操作。近似 LRU 只需要在淘汰时采样几个键，比较它们的闲置时间即可，代价小得多。

**Redis 3.0 的改进**：Redis 3.0 引入了"淘汰池"（Eviction Pool）的概念——每次淘汰后，把采样结果中最好的几个键放入一个池子，下次淘汰时先在池子中比较，再从全局采样补充。这个改进让近似 LRU 的效果几乎达到了精确 LRU。

| 版本 | 实现 | 与精确 LRU 的接近程度 |
|------|------|---------------------|
| 2.x | 每次随机采样 N 个 | 较远 |
| 3.0+ | 采样 + 淘汰池 | 非常接近（N=10 池大小=16 时几乎等价） |

---

## 六、缓存穿透、缓存击穿、缓存雪崩

这三个问题是缓存系统的三大经典问题，也是面试中的高频考点。很多人在面试中能背出定义和解决方案，但真正理解了它们的区别和根因的人不多。

### 6.1 三者的核心区别

在看具体解释之前，先建立一个直观的区分：

| 问题 | 简单理解 | 核心原因 |
|------|---------|---------|
| **缓存穿透** | 我查了一个肯定不存在的数据 | 查询不存在的数据 |
| **缓存击穿** | 一个超热门数据突然过期了 | 热点 Key 过期 |
| **缓存雪崩** | 大量数据同时过期或 Redis 挂了 | 大面积缓存失效 |

---

### 6.2 缓存穿透（Cache Penetration）

#### 什么是缓存穿透

**定义**：请求查询一个**缓存和数据库中都不存在**的数据。由于缓存中没有（因为数据本就不存在），请求直接穿透缓存层到达数据库。

```
正常流程：
客户端 → 查缓存 → 命中 → 返回
                 ↓ 未命中
               查数据库 → 存在 → 写入缓存 → 返回

穿透流程：
客户端 → 查缓存 → 未命中（因为数据不存在）
                 ↓
               查数据库 → 不存在 → 返回 null
                 ↓
            下次同样的请求：再次穿透
```

**这为什么是个问题**？如果攻击者构造大量不存在的 ID 并发请求（比如 `GET /user?id=-1`、`GET /user?id=-2`、...），每个请求都会穿透到数据库。数据库对这些不存在的 ID 做全表扫描，CPU 和磁盘 I/O 被拖垮。

#### 解决方案一：缓存空值

```python
def get_user(user_id):
    # 1. 从缓存读取
    user = redis.get(f"user:{user_id}")
    if user is not None:
        if user == "NULL":          # 缓存中存了空值标记
            return None             # 直接返回不存在
        return json.loads(user)

    # 2. 从数据库读取
    user = db.query("SELECT * FROM users WHERE id = ?", user_id)

    # 3. 无论是否存在，都写入缓存
    if user:
        redis.setex(f"user:{user_id}", 3600, json.dumps(user))
    else:
        # ★ 关键：把"不存在"也缓存起来，设置较短的过期时间
        redis.setex(f"user:{user_id}", 60, "NULL")

    return user
```

**为什么缓存空值有效？** 第一次请求不存在的 ID 后，Redis 中存入了 "NULL" 标记。后续相同的请求直接命中缓存，返回不存在，不再穿透到数据库。

**为什么空值缓存要设置短的过期时间？** 假设用户 ID = 9999 目前不存在，我们缓存了空值（60秒过期）。但在 60 秒内，新的用户 9999 被注册了——如果空值缓存还在，新注册的用户就查不到。所以空值缓存的过期时间应该在"数据可能被创建的时间"和"保护数据库"之间取得平衡。通常设置为 30-120 秒。

#### 解决方案二：布隆过滤器（Bloom Filter）

**布隆过滤器是什么？** 一种概率型数据结构，它可以非常确定地告诉你"一个元素一定不存在"，但只能概率性地告诉你"一个元素可能存在"。

```
        元素 → [哈希函数1] ─→ 位数组位置 [0, 1, 1, 0, ...]
               [哈希函数2] ─→ 位数组位置
               [哈希函数3] ─→ 位数组位置

判断 "张三" 是否存在：
  三个哈希函数计算出的三个位置都是 1 → 可能存在（可能有误判）
  任一位置是 0              → 一定不存在
```

**工作原理**（简化版）：

```python
class BloomFilter:
    def __init__(self, size, hash_count):
        self.bit_array = [0] * size
        self.hash_count = hash_count  # 哈希函数数量

    def add(self, element):
        """添加元素到过滤器"""
        for i in range(self.hash_count):
            # 用不同的哈希函数计算位置
            pos = hash(f"{i}:{element}") % len(self.bit_array)
            self.bit_array[pos] = 1

    def might_contain(self, element):
        """判断元素是否可能存在"""
        for i in range(self.hash_count):
            pos = hash(f"{i}:{element}") % len(self.bit_array)
            if self.bit_array[pos] == 0:
                return False  # 一定不存在
        return True  # 可能存在
```

**为什么用布隆过滤器解决缓存穿透？**

```python
# 1. 应用启动时，把所有合法的用户 ID 加载到布隆过滤器
bloom = BloomFilter(size=100_000_000, hash_count=7)
for user_id in db.query_all_user_ids():
    bloom.add(user_id)

# 2. 请求到来时，先用布隆过滤器判断
def get_user(user_id):
    if not bloom.might_contain(user_id):
        # 布隆过滤器说不存在 → 一定不存在
        return None  # 直接返回，不查缓存也不查数据库
    
    # 布隆过滤器说可能存在 → 继续正常流程
    user = redis.get(f"user:{user_id}")
    if user:
        return user
    
    user = db.query_user(user_id)
    if user:
        redis.setex(f"user:{user_id}", 3600, json.dumps(user))
    return user
```

**布隆过滤器的优缺点**：

| 优点 | 缺点 |
|------|------|
| 节省内存（几 GB 的数据用几百 MB 搞定） | 有误判率（只会误判"存在"，不会误判"不存在"） |
| 查询速度快（O(k)，k=哈希函数数量） | 无法删除元素（不能把位从 1 改回 0） |
| 不存储原始数据，隐私友好 | 需要预先知道数据总量以设置位数组大小 |

**缓存空值 vs 布隆过滤器，怎么选？**

| 维度 | 缓存空值 | 布隆过滤器 |
|------|---------|-----------|
| 实现复杂度 | 低（几行代码） | 中（需要引入库或实现） |
| 内存占用 | 较高（每个空 Key 都占内存） | 低（位数组，固定大小） |
| 适用场景 | 不存在的数据量不大 | 不存在的数据量极大（如爬虫攻击） |
| 对"新数据"的敏感度 | 空值过期后自动适配 | 需要重新加载过滤器 |

---

### 6.3 缓存击穿（Cache Breakdown / Hotkey Invalidation）

#### 什么是缓存击穿

**定义**：一个**热点 Key**（被高并发访问的 Key）在过期的一瞬间，大量请求同时发现缓存中没有这个 Key，瞬间全部穿透到数据库。由于并发量极高，数据库瞬间承受巨大压力，可能宕机。

**注意**：缓存击穿和缓存穿透的本质区别在于——击穿的数据在数据库中**存在**，只是缓存恰好在那一刻过期了。

```
① t = 0s: 热点 Key "article:1001" 在缓存中存在，大量请求命中缓存
② t = 10s: Key 过期（TTL 到了）
③ t = 10.001s: 请求 A 发现缓存未命中，查询数据库
④ t = 10.002s: 请求 B 也发现缓存未命中，也查询数据库
                ...
                ↑ 这里就是"击穿"——大量请求同时穿透到数据库
⑤ 数据库压力飙升
```

#### 解决方案一：互斥锁（Mutex Lock）

保证只有一个请求去数据库加载数据，其他请求等待这个请求完成后直接从缓存读取：

```python
def get_hot_article(article_id):
    key = f"hot:article:{article_id}"
    lock_key = f"lock:hot:article:{article_id}"

    # 1. 尝试从缓存获取
    article = redis.get(key)
    if article:
        return json.loads(article)

    # 2. 缓存未命中，尝试获取分布式锁
    #    SET NX = 只有键不存在时才设置（原子操作）
    if redis.setnx(lock_key, "locked"):
        # 获取到锁的线程才有权查数据库
        redis.expire(lock_key, 5)  # 防止死锁

        # 3. 双重检查：可能其他线程已经加载好了
        article = redis.get(key)
        if article:
            redis.delete(lock_key)
            return json.loads(article)

        # 4. 查询数据库
        article = db.query("SELECT * FROM articles WHERE id = ?", article_id)

        # 5. 写入缓存
        redis.setex(key, 3600, json.dumps(article))

        # 6. 释放锁
        redis.delete(lock_key)

        return article
    else:
        # 没有获取到锁，等待后重试
        time.sleep(0.01)
        return get_hot_article(article_id)
```

**为什么用 SETNX 而不是先判断键是否存在再设置？** 因为 SETNX 是原子的——"检查不存在 → 设置"两步在单线程 Redis 中是一个原子操作。如果先 GET 再 SET，两个线程可能同时发现锁不存在，都去 SET，导致两个线程都认为自己是"获锁者"。这就是典型的**竞态条件**。

**这个方案有什么问题？** 

1. **死锁风险**：线程 A 获取锁后崩溃了，锁永远不释放。其他线程永远无法加载数据。解决方案是设置锁的过期时间（如上文中的 `expire(lock_key, 5)`）。
2. **锁过期问题**：线程 A 加载数据太慢（比如数据库慢查询），5 秒后锁过期了，线程 B 获取了新的锁，也去查数据库。解决方案是用更可靠的锁实现（如下面的 RedLock）。
3. **阻塞等待**：大量线程都在 sleep 等待，响应时间增加。但对缓存场景来说，偶尔的几百毫秒等待是可以接受的。

#### 解决方案二：逻辑过期（永不过期）

不设置物理过期时间，而是把过期时间作为数据的一部分存储在 value 中：

```python
def get_hot_article(article_id):
    key = f"hot:article:{article_id}"

    # 1. 从缓存获取数据（永不过期）
    data = redis.get(key)
    if not data:
        return None  # 数据还没加载到缓存

    article = json.loads(data)

    # 2. 检查逻辑过期时间
    if article["expire_at"] > time.time():
        # 还没过期，直接返回
        return article["data"]

    # 3. 逻辑上已过期，异步刷新
    #    先返回旧数据，同时启动后台线程更新缓存
    refresh_hot_article_in_background(article_id)

    return article["data"]  # 返回"可能有点旧"但可用的数据
```

**为什么"返回旧数据"反而是一种更好的体验？** 在缓存击穿场景中，如果所有请求都等待数据库查询，响应时间会从 1ms（缓存命中）飙升到 100ms（数据库查询 + 缓存写入）。而返回过期数据虽然"旧了一点点"（比如 1 秒前的数据），但响应时间仍然是 1ms。对于大部分应用来说，返回稍微过期的数据远好于让用户等待。

#### 互斥锁 vs 逻辑过期

| 维度 | 互斥锁 | 逻辑过期 |
|------|--------|---------|
| 一致性 | 强一致（永远获取最新数据） | 最终一致（可能返回旧数据） |
| 响应时间 | 偶尔出现高峰（等待数据库查询） | 始终低延迟 |
| 实现复杂度 | 中（需要考虑锁的问题） | 低（无锁） |
| 适用场景 | 数据一致性要求高 | 高并发、可接受短暂不一致 |

---

### 6.4 缓存雪崩（Cache Avalanche）

#### 什么是缓存雪崩

**定义**：大量的缓存 Key 在同一时间失效（或 Redis 本身宕机），导致所有请求直接打到数据库，数据库在瞬间承受数倍甚至几十倍的流量冲击，最终崩溃。

**缓存雪崩和缓存击穿的区别**：

```
缓存击穿：一个热点 Key 过期 → 大量请求打到数据库
缓存雪崩：大量 Key 同时过期 → 海量请求打到数据库（和击穿比，流量再大 100 倍）
```

#### 原因一：大量 Key 同时过期

**为什么会有大量 Key 同时过期？** 最常见的原因是：
- 开发者在代码中统一设置了相同的过期时间（如所有缓存都设 3600 秒）
- 系统定时任务在同一时刻刷新所有缓存
- 缓存预热时所有 Key 的过期时间相同

**解决方案**：

**方案一：过期时间加随机偏移**

```python
# 不这样做：
redis.setex(key, 3600, value)

# 而是这样做：
import random
base_ttl = 3600
jitter = random.randint(-600, 600)  # ±10 分钟随机
redis.setex(key, base_ttl + jitter, value)
```

**为什么随机偏移有效？** 假设有 10 万个 Key，如果都是 3600 秒（1 小时）过期，那么在 1 小时后的那一秒，10 万个 Key 同时过期。加上 ±10 分钟的随机偏移后，这些 Key 的过期时间分布在 50 分钟到 70 分钟之间，大大降低了同时过期的概率。

**方案二：多级缓存**

在 Redis 前面再加一层本地缓存（如进程内缓存 Caffeine、Guava Cache）：

```
请求 → 本地缓存（Caffeine） → Redis 缓存 → 数据库
        毫秒级               微秒级       十毫秒级
```

即使 Redis 中的 Key 大量过期，本地缓存仍然能"顶住"一部分流量，减少穿透到数据库的请求量。但本地缓存的弊端是：多台服务器之间缓存不一致，且占用每台服务器的内存。

#### 原因二：Redis 宕机

如果 Redis 服务本身的不可用导致雪崩，和 Key 过期的原因不同，解决方案也不同。

**解决方案一：Redis 高可用架构**

| 方案 | 原理 | 自动切换 |
|------|------|---------|
| 主从复制 + 哨兵 | 主节点宕机，哨兵自动选主 | 是（30 秒左右） |
| Redis Cluster | 数据分片到多个节点，部分节点宕机不影响整体 | 是（秒级） |

**解决方案二：限流降级**

当检测到数据库压力过大时，主动丢弃部分请求：

```python
# 1. 在 API 网关或应用层做限流
from time import time

class RateLimiter:
    def __init__(self, max_qps=100):
        self.max_qps = max_qps
        self.window = []
    
    def allow(self):
        now = time()
        # 移除 1 秒前的记录
        self.window = [t for t in self.window if t > now - 1]
        if len(self.window) >= self.max_qps:
            return False  # 限流
        self.window.append(now)
        return True

# 2. 降级：返回默认数据或错误提示
def get_recommendations(user_id):
    if not limiter.allow():
        # 返回缓存的热门数据（即使不是为该用户量身定制）
        return get_default_recommendations()
    
    return db.query_recommendations(user_id)
```

**解决方案三：提前预热**

在业务低峰期提前将热点数据加载到缓存：

```python
def preheat_cache():
    """系统上线或定时任务：预热热点数据"""
    hot_articles = db.query("SELECT * FROM articles WHERE view_count > 10000")
    for article in hot_articles:
        ttl = 3600 + random.randint(-300, 300)
        redis.setex(f"hot:article:{article.id}", ttl, json.dumps(article))
```

---

### 6.5 三类缓存问题的对比总结

| 维度 | 缓存穿透 | 缓存击穿 | 缓存雪崩 |
|------|---------|---------|---------|
| **根因** | 查询不存在的数据 | 热点 Key 过期 | 大量 Key 同时过期 / Redis 宕机 |
| **数据是否存在** | 不存在 | 存在 | 存在 |
| **影响范围** | 单 Key | 单 Key（但热点） | 大量 Key |
| **数据库压力** | 持续的低频压力 | 瞬间的高频压力 | 瞬间的极高压力 |
| **核心解决方案** | 布隆过滤器 / 缓存空值 | 互斥锁 / 逻辑过期 | 随机 TTL / 多级缓存 / 高可用 |

---

## 七、Redis 事务

### 7.1 Redis 事务概述

Redis 的事务通过 `MULTI`、`EXEC`、`DISCARD`、`WATCH` 等命令实现：

```bash
MULTI              # 开始事务
SET key1 "value1"  # 命令入队
SET key2 "value2"  # 命令入队
EXEC               # 执行事务
```

**Redis 事务的特点**：
1. **批量执行**：事务中的命令会一次性按顺序执行
2. **无回滚**：如果中间有命令执行失败，之前的命令不会回滚
3. **不保证原子性**（传统意义）：Redis 事务中的命令如果遇到语法错误，所有命令都不执行；但如果是运行时错误（如对 String 类型执行 List 操作），已执行的成功命令不会回滚

**和关系型数据库事务的对比**：

| 维度 | MySQL 事务 | Redis 事务 |
|------|-----------|-----------|
| 原子性 | 要么全成功要么全回滚 | 不支持回滚 |
| 隔离性 | 多级隔离（RU/RC/RR/SERIALIZABLE） | 单线程+WATCH 实现条件执行 |
| 持久性 | 依赖 Redo Log | 依赖 RDB/AOF |

---

## 八、总结

Redis 的设计哲学可以概括为：**"在内存中做最擅长的事"**。

- 它选择单线程执行命令，避免了多线程的复杂性和锁开销，让操作天然原子。
- 它选择丰富的数据结构，让开发者可以用 String 做缓存、Zset 做排行榜、List 做队列——每个类型都为特定场景优化。
- 它提供过期和淘汰机制，用惰性+定期删除平衡 CPU 和内存，用 8 种淘汰策略覆盖不同的业务场景。
- 它在缓存穿透、击穿、雪崩三大问题上提供了多种解决方案，但这些方案都需要开发者根据实际场景选择和组合。

使用 Redis 的最高境界，不是背下所有命令和配置参数，而是能在设计系统时预判"这个 Key 的访问频率什么样"、"内存够不够用"、"如果 Redis 挂了怎么办"——然后在编码层面提前规避这些问题。

---

> **相关章节**：学习完 Redis 缓存层，你可以继续阅读 [第三部分：MySQL](03_mysql从零到实战.md) 了解持久化存储层的设计，以及 [第二部分：RESTful API 设计原则](02_restful_api_design.md) 了解如何设计良好的 API 接口。
