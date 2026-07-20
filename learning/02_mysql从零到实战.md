# MySQL 从零到实战

> **前置**: 会用计算机，不需要数据库基础。建议先看 Python 文档的第九章数据库连接部分，两者配合阅读。

---

## 第一章 数据库是什么——Excel 的超级加强版

### 1.1 你已经每天都在用数据库

| 场景         | 背后的数据库操作           |
| ------------ | -------------------------- |
| 刷淘宝看商品 | 从商品表查询数据           |
| 下单付款     | 插入订单记录、扣库存       |
| 查快递到哪了 | 按运单号查询物流记录       |
| 微信朋友圈   | 按时间线查帖子、按关系过滤 |

数据库就是**储存和管理大量结构化数据的软件**。没有它，你的购物车一关闭就没了。

### 1.2 为什么不用 Excel

Excel 能存数据，但：

- **并发**: 1000 人同时改一个表格 → Excel 崩了，数据库没事
- **容量**: Excel 十万行就卡，MySQL 千万行依然流畅
- **安全**: MySQL 可以精细控制"谁能看到什么"、"谁能改什么"
- **关联**: 两个表之间建立关系、跨表查询，MySQL 是强项

### 1.3 核心概念

```
服务器 (MySQL Service)
  └── 数据库 A (database / schema)
        ├── 表 users
        ├── 表 orders
        └── 表 products
  └── 数据库 B
        └── 表 logs
```

- **服务器**: MySQL 这个软件在运行，占用 3306 端口
- **数据库**: 一个项目一个数据库，互相隔离
- **表**: 真正的数据存在表里。每个表定义了"有哪些列（字段）"

> **数据库 ≈ 文件夹，表 ≈ 某个文件夹里的 Excel 文件。** 一个项目一个文件夹，一个文件夹里多个文件。

### 1.4 安装

```bash
# Ubuntu
sudo apt install mysql-server

# Mac
brew install mysql

# Windows
# 去 mysql.com 下载 MySQL Community Server 和 MySQL Workbench

# 启动服务
sudo systemctl start mysql    # Linux
brew services start mysql     # Mac
```

安装后会有一个 `root` 用户，是管理员账号。

---

## 第 1.5 章 SQL 指令四大分类——心中有数，下笔不乱

MySQL 所有的 SQL 指令按操作性质分为四大类。学之前先搞清分类，后面每学一条指令你都能把它归到对应类别里，不会越学越乱。

### 分类总览

```
MySQL 指令
├── DDL（管结构）     CREATE / ALTER / DROP / TRUNCATE / RENAME
├── DML（管数据）     SELECT / INSERT / UPDATE / DELETE
├── DCL（管权限）     GRANT / REVOKE / CREATE USER / DROP USER
└── TCL（管事务）     COMMIT / ROLLBACK / SAVEPOINT / BEGIN
```

### DDL — 数据定义语言 (Data Definition Language)

**操作对象：数据库、表、索引、视图的结构本身。** DDL 指令动的是"骨架"，不是里面的数据。

| 指令 | 作用 | 示例 |
|------|------|------|
| `CREATE` | 创建数据库、表、索引、视图 | `CREATE TABLE students (...)` |
| `ALTER` | 修改表结构（加列、改类型、加约束） | `ALTER TABLE students ADD age INT` |
| `DROP` | 删除数据库、表、索引、视图 | `DROP TABLE students` |
| `TRUNCATE` | 清空表（保留结构，删除全部数据） | `TRUNCATE TABLE students` |
| `RENAME` | 重命名表 | `RENAME TABLE old TO new` |

**特点**：DDL 执行后**自动提交**（隐式事务），不能回滚。`DROP TABLE` 执行完表就没了，没有"撤回"键。在生产环境执行 DDL 前务必确认——这是无数事故的源头。

> 第二章的 `CREATE TABLE` 就是 DDL。你建的每一张表都靠 DDL 指令定义结构。

### DML — 数据操作语言 (Data Manipulation Language)

**操作对象：表里的数据行。** DML 动的是"血肉"，表的结构不变。

| 指令 | 作用 | 示例 |
|------|------|------|
| `SELECT` | 查询数据 | `SELECT * FROM students WHERE age > 18` |
| `INSERT` | 插入新行 | `INSERT INTO students VALUES (...)` |
| `UPDATE` | 修改已有行 | `UPDATE students SET age = 20 WHERE id = 1` |
| `DELETE` | 删除行 | `DELETE FROM students WHERE id = 1` |

**特点**：在 InnoDB 引擎下，DML 操作后需要手动 `COMMIT` 才会持久化，`ROLLBACK` 可以撤销。这也是为什么误删数据后可以抢救——只要还没提交。

> **注意**：国内有些教材把 `SELECT` 单独叫 **DQL（数据查询语言）**，把 `INSERT/UPDATE/DELETE` 叫 DML。这是培训机构的习惯分法。MySQL 官方文档是把四条都算 DML。两种叫法你都可能遇到，知道它们指的是同一批指令就行。

> 第三、四章的内容全部属于 DML。你日常写的 90% 都是 DML，`SELECT` 是其中写得最多的。

### DCL — 数据控制语言 (Data Control Language)

**操作对象：用户账号和访问权限。** DCL 决定"谁能进"、"进来能干什么"。

| 指令 | 作用 | 示例 |
|------|------|------|
| `CREATE USER` | 创建用户 | `CREATE USER 'zhangsan'@'%' IDENTIFIED BY 'pwd'` |
| `DROP USER` | 删除用户 | `DROP USER 'zhangsan'@'%'` |
| `GRANT` | 授予权限 | `GRANT SELECT ON db.* TO 'zhangsan'@'%'` |
| `REVOKE` | 收回权限 | `REVOKE INSERT ON db.* FROM 'zhangsan'@'%'` |
| `SET PASSWORD` | 修改密码 | `SET PASSWORD FOR 'zhangsan' = 'newpwd'` |

**特点**：运维和 DBA 用得最多。开发环境通常用 root 一把梭，但生产环境必须按最小权限原则分配账号——API 服务只需要 `SELECT/INSERT/UPDATE/DELETE`，绝不给 `DROP`。

### TCL — 事务控制语言 (Transaction Control Language)

**操作对象：事务的边界和状态。** TCL 控制"一组操作是绑定生效还是全部撤销"。

| 指令 | 作用 |
|------|------|
| `START TRANSACTION` / `BEGIN` | 开启一个事务 |
| `COMMIT` | 提交事务，所有修改持久化 |
| `ROLLBACK` | 回滚事务，撤销全部未提交修改 |
| `SAVEPOINT 保存点名` | 在事务中设置一个保存点 |
| `ROLLBACK TO SAVEPOINT 保存点名` | 回滚到指定保存点，而非全部撤销 |
| `SET AUTOCOMMIT = 0/1` | 关闭/开启自动提交模式 |

**特点**：TCL 本身不改数据也不改结构，它只控制 DML 操作的**生效时机**。第六章会详细讲解事务。

> InnoDB 引擎默认 `AUTOCOMMIT = 1`，即每条 DML 自动提交。想手动控制事务，用 `START TRANSACTION` 开启，然后显式 `COMMIT` 或 `ROLLBACK`。

### 一条 SQL 的生命周期（按分类走一遍）

以一个实际场景串联四类指令，让你看清它们是如何协作的：

```sql
-- 1. DDL：先建好表结构
CREATE TABLE accounts (
    id      BIGINT PRIMARY KEY AUTO_INCREMENT,
    name    VARCHAR(50) NOT NULL,
    balance DECIMAL(10,2) DEFAULT 0.00
);

-- 2. DCL：给应用账号授权（只给必要的）
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'secure_pwd';
GRANT SELECT, INSERT, UPDATE ON mydb.accounts TO 'app_user'@'localhost';

-- 3. DML：日常数据操作
INSERT INTO accounts (name, balance) VALUES ('张三', 1000.00);
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
SELECT * FROM accounts WHERE balance > 0;

-- 4. TCL：关键操作绑定在一起
START TRANSACTION;
    UPDATE accounts SET balance = balance - 100 WHERE id = 1;  -- A 扣钱
    UPDATE accounts SET balance = balance + 100 WHERE id = 2;  -- B 加钱
COMMIT;  -- 两条同时生效
```

### 一条指令属于哪类？快速判断法

| 判断方法 | 归类 |
|----------|------|
| 指令动词是 CREATE/ALTER/DROP/TRUNCATE | DDL（动结构） |
| 指令动词是 SELECT/INSERT/UPDATE/DELETE | DML（动数据） |
| 指令动词是 GRANT/REVOKE/CREATE USER | DCL（动权限） |
| 指令动词是 COMMIT/ROLLBACK/SAVEPOINT | TCL（动事务） |
| `SHOW` / `DESC` / `EXPLAIN` / `USE` | 实用工具命令（非 SQL 语句，是 MySQL 客户端命令） |

---

## 第二章 表设计——先想清楚存什么

### 2.1 表的样子

```
users 表:
┌────┬────────┬─────┬──────────────────┐
│ id │ name   │ age │ email            │
├────┼────────┼─────┼──────────────────┤
│ 1  │ 张三   │ 25  │ zh3@test.com     │
│ 2  │ 李四   │ 30  │ ls@test.com      │
│ 3  │ 王五   │ 28  │ ww@test.com      │
└────┴────────┴─────┴──────────────────┘
      ↑                    ↑
   列（字段）           一行（记录）
```

### 2.2 数据类型——每个字段的口味

| 类型             | 用法                  | 示例                                       |
| ---------------- | --------------------- | ------------------------------------------ |
| `INT`          | 整数                  | `age INT`                                |
| `BIGINT`       | 大整数                | `id BIGINT` (自增ID)                     |
| `VARCHAR(N)`   | 可变长字符串          | `name VARCHAR(50)`                       |
| `TEXT`         | 长文本                | `content TEXT`                           |
| `DATETIME`     | 日期时间              | `created_at DATETIME`                    |
| `DECIMAL(M,N)` | 精确小数              | `price DECIMAL(10,2)` (10位总长,2位小数) |
| `BOOLEAN`      | 布尔 (实际是 TINYINT) | `is_active BOOLEAN`                      |

> **钱用 DECIMAL，不用 FLOAT。** FLOAT 是近似值，`0.1 + 0.2 = 0.30000000000000004`。涉及金额你赔不起。

### 2.3 建表 CREATE TABLE

```sql
CREATE TABLE users (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(50)  NOT NULL,
    age         INT,
    email       VARCHAR(100) UNIQUE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

拆解每行：

- `PRIMARY KEY`: 主键，每条记录的唯一身份证，一张表只有一个
- `AUTO_INCREMENT`: 自增，每次插入自动 +1，不用手动填
- `NOT NULL`: 不允许为空
- `UNIQUE`: 值不能重复
- `DEFAULT`: 不填时的默认值

> **主键就像身份证号**。全国可能有同名同姓的人，但身份证号独一无二。数据库也一样，靠主键精确找到某一条记录。

### 2.4 外键 — 表与表之间的关系

```sql
CREATE TABLE orders (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id     BIGINT NOT NULL,
    product     VARCHAR(100),
    amount      DECIMAL(10, 2),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)   -- 外键约束
);
```

`FOREIGN KEY` 保证 `orders.user_id` 必须是 `users` 表里真实存在的 `id`。你想给一个不存在的用户下订单？数据库直接拒绝。这叫**引用完整性**。

---

## 第三章 CRUD——数据的一生

CRUD = Create(增) / Read(查) / Update(改) / Delete(删)，数据操作的四个基本动作。

### 3.1 INSERT — 插入数据

```sql
-- 插入一条
INSERT INTO users (name, age, email) VALUES ('张三', 25, 'zh3@test.com');

-- 插入多条
INSERT INTO users (name, age, email) VALUES
    ('李四', 30, 'ls@test.com'),
    ('王五', 28, 'ww@test.com');

-- 插完想看刚插进去的 id
INSERT INTO users (name, age) VALUES ('赵六', 22);
SELECT LAST_INSERT_ID();  -- 返回刚才自动生成的 id
```

### 3.2 SELECT — 查询数据（核心中的核心）

```sql
-- 查所有
SELECT * FROM users;

-- 查指定列
SELECT name, email FROM users;

-- 条件查询
SELECT * FROM users WHERE age > 25;

-- 多条件
SELECT * FROM users WHERE age > 20 AND email IS NOT NULL;
SELECT * FROM users WHERE age < 20 OR age > 60;

-- 模糊搜索
SELECT * FROM users WHERE name LIKE '张%';   -- 张开头
SELECT * FROM users WHERE name LIKE '%三';   -- 三结尾
SELECT * FROM users WHERE name LIKE '%小%';  -- 包含小
-- % 匹配任意个字符，_ 匹配单个字符

-- 排序
SELECT * FROM users ORDER BY age DESC;        -- 降序
SELECT * FROM users ORDER BY age ASC;         -- 升序（默认）

-- 分页
SELECT * FROM users LIMIT 10 OFFSET 20;       -- 跳过20条，取10条

-- 去重
SELECT DISTINCT age FROM users;                -- 年龄有哪些值

-- 聚合
SELECT COUNT(*) FROM users;                   -- 共多少行
SELECT AVG(age) FROM users;                   -- 平均年龄
SELECT MAX(age), MIN(age) FROM users;         -- 最大最小
SELECT SUM(amount) FROM orders;               -- 总金额
```

### 3.3 UPDATE — 修改数据

```sql
-- 改单条（必须用 WHERE，不然全表遭殃）
UPDATE users SET age = 26 WHERE id = 1;

-- 改多条
UPDATE users SET age = age + 1 WHERE age < 60;

-- 危险：忘写 WHERE → 所有人的 age 都改了
-- 安全设置: SET SQL_SAFE_UPDATES = 1; (MySQL Workbench 默认开启)
```

### 3.4 DELETE — 删除数据

```sql
-- 删单条
DELETE FROM users WHERE id = 5;

-- 清空整张表（保留表结构）
DELETE FROM users;         -- 逐行删，慢，可回滚
TRUNCATE TABLE users;      -- 直接干掉重建，快，不可回滚
```

> **DELETE 和 UPDATE 永远先写 WHERE，确定条件正确再执行。** 无数次事故的教训。

---

## 第四章 查询进阶——这才是你的利器

### 4.1 GROUP BY — 分组统计

```sql
-- 每个年龄有多少人
SELECT age, COUNT(*) AS cnt
FROM users
GROUP BY age
HAVING cnt > 1;           -- HAVING 过滤分组后的结果

-- 每天订单总额
SELECT DATE(created_at) AS day, SUM(amount) AS total
FROM orders
GROUP BY DATE(created_at)
ORDER BY day DESC;
```

> **WHERE 在分组前过滤，HAVING 在分组后过滤。** WHERE 管原始行，HAVING 管分组结果。

### 4.2 JOIN — 多表联合查询

这是关系型数据库的看家本领，也是最难的部分。

假设 `users` 和 `orders` 两张表：

```sql
-- INNER JOIN: 两边都有的才出来
SELECT u.name, o.product, o.amount
FROM users u
INNER JOIN orders o ON u.id = o.user_id;
-- 结果: 只包含下过单的用户。没下过单的用户不出现

-- LEFT JOIN: 左边全保留
SELECT u.name, o.product, o.amount
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;
-- 结果: 所有用户都出现，没下过单的 product 和 amount 显示 NULL

-- RIGHT JOIN: 右边全保留（较少用）
-- 所有订单都出现，即使是孤儿订单
```

```
INNER JOIN:         LEFT JOIN:
┌───┬───┐          ┌───┬───┐
│ A │ 1 │          │ A │ 1 │
│ B │ 2 │          │ B │ 2 │
└───┴───┘          │ C │ ∅ │   ← C 没订单也保留
  只出配对的        └───┴───┘
```

> **INNER JOIN = 取交集，LEFT JOIN = 左表全保留右边有就有没有就 NULL。** 工作中 LEFT JOIN 用得最多。

### 4.3 子查询 — 查询里套查询

```sql
-- 查出下过单的所有用户
SELECT * FROM users
WHERE id IN (SELECT DISTINCT user_id FROM orders);

-- 查出消费总额超过 500 的用户
SELECT name, (
    SELECT SUM(amount) FROM orders WHERE user_id = users.id
) AS total_spent
FROM users
HAVING total_spent > 500;
```

---

## 第五章 索引——从"翻箱倒柜"到"直达目标"

### 5.1 没有索引有多慢

想象一本 1000 页的书没有目录。你要找"数据库的连接方式"，只能一页页翻。这就是**全表扫描**。

```sql
-- 1000 万行表，name 没有索引
SELECT * FROM users WHERE name = '张三';
-- 耗时: 5 秒 (逐行比对 name)

-- 加上索引后
-- 耗时: 0.01 秒
```

### 5.2 索引的原理

索引就像书的目录——不存全部内容，只存"关键词 → 页码"的映射。MySQL 的默认索引结构是 **B+Tree**：

```
         [50]
        /    \
    [20,30]  [70,80]
    /  |  \   /  |  \
   1  25  40 55  75  90
   
每个节点存多个值，叶子节点存全部数据。
查找 40: 50>40→往左，在[20,30]的右边→找到。
3 次定位，而不是逐条对比 1000 万次。
```

> **B+Tree = 多叉、自平衡的排序树。** 不深究算法细节，只需知道：按索引查是 O(log n)，全表扫是 O(n)。

### 5.3 创建索引

```sql
-- 单列索引
CREATE INDEX idx_users_name ON users(name);

-- 联合索引（多列组合）
CREATE INDEX idx_users_age_city ON users(age, city);

-- 唯一索引（值不能重复）
CREATE UNIQUE INDEX idx_users_email ON users(email);
```

### 5.4 索引使用的铁律

| 规则                 | 解释                                                       |
| -------------------- | ---------------------------------------------------------- |
| 主键自动有索引       | 不用再手动建                                               |
| WHERE 的条件列建索引 | 查得最多的列优先                                           |
| JOIN 的关联列建索引  | `ON u.id = o.user_id` 两边都要                           |
| 联合索引有"最左前缀" | `(a,b)` 索引对 `WHERE a=?` 有效，对 `WHERE b=?` 无效 |
| 不要每列都建         | 索引也占空间，`INSERT/UPDATE` 时要更新索引               |
| 避免在索引列上套函数 | `WHERE YEAR(created_at) = 2024` 不走索引，改成范围查询   |

### 5.5 EXPLAIN — 看查询走不走索引

```sql
EXPLAIN SELECT * FROM users WHERE name = '张三';
-- type=ALL: 全表扫，缺索引
-- type=ref: 走了索引，没问题
-- type=range: 范围查询，正常
-- key: 用的是哪个索引
-- rows: 预计扫描行数
```

---

## 第六章 事务——要么全做，要么全不做

### 6.1 经典场景：银行转账

```
A 转账 100 元给 B:
  1. A 账户 -100
  2. B 账户 +100

如果第 1 步成功，第 2 步失败（服务器宕机）→ 100 元凭空消失！
```

事务的解决方案：这两步**绑在一起**，要么全做，要么全不做。

### 6.2 ACID 四个特性

| 特性                         | 含义                       | 类比                          |
| ---------------------------- | -------------------------- | ----------------------------- |
| **A**tomicity 原子性   | 不可分割，全做或全不做     | 签合同，不签完等于没签        |
| **C**onsistency 一致性 | 数据从一种合法状态到另一种 | 转账前后总额不变              |
| **I**solation 隔离性   | 并发事务互不干扰           | 你在 ATM 取钱时别人不能同时取 |
| **D**urability 持久性  | 一旦提交，永久保存         | 写进档案室，断电也不丢        |

### 6.3 事务操作

```sql
START TRANSACTION;
    UPDATE accounts SET balance = balance - 100 WHERE id = 1;  -- A 扣钱
    UPDATE accounts SET balance = balance + 100 WHERE id = 2;  -- B 加钱
COMMIT;    -- 确认，全部生效
-- 或者
ROLLBACK;  -- 回滚，全部撤销
```

### 6.4 脏读 / 不可重复读 / 幻读

```
脏读: 读到别人还没提交的数据（别人可能回滚）
不可重复读: 同一事务内两次读同一行，结果不同（别人中间改了）
幻读: 同一事务内两次范围查询，行数不同（别人插入/删除了）
```

MySQL 默认隔离级别 **REPEATABLE READ** 解决了脏读和不可重复读。

---

## 第七章 备份和还原

```bash
# 备份整个数据库
mysqldump -u root -p mydb > backup.sql

# 备份单个表
mysqldump -u root -p mydb users > users_backup.sql

# 只备份表结构（不含数据）
mysqldump -u root -p --no-data mydb > schema.sql

# 还原
mysql -u root -p mydb < backup.sql

# 导入时指定编码
mysql -u root -p --default-character-set=utf8mb4 mydb < backup.sql
```

---

## 第八章 查询优化实战

### 8.1 慢查询定位

```sql
-- 开启慢查询日志
SET GLOBAL slow_query_log = 1;
SET GLOBAL long_query_time = 2;  -- 超过 2 秒就记录

-- 查看慢查询日志位置
SHOW VARIABLES LIKE 'slow_query_log_file';
```

### 8.2 常见优化方法

| 问题                  | 解决                       |
| --------------------- | -------------------------- |
| 全表扫                | 在 WHERE 条件列上建索引    |
| SELECT *              | 只查需要的列，减少传输     |
| 模糊搜索`%keyword%` | 用全文索引或 Elasticsearch |
| JOIN 慢               | 确保 ON 条件列有索引       |
| 大批量写入慢          | 批量 INSERT，事务包裹      |

---

## 附录 需要记住的内容

| 知识点                          | 内容                                                                   |
| ------------------------------- | ---------------------------------------------------------------------- |
| SQL 执行顺序                    | `FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT` |
| `WHERE` vs `HAVING`         | WHERE 过滤原始行，HAVING 过滤分组结果                                  |
| JOIN 类型                       | INNER(交集)、LEFT(左全)、RIGHT(右全)、CROSS(笛卡尔积)                  |
| 索引类型                        | PRIMARY、UNIQUE、INDEX(普通)、FULLTEXT(全文)                           |
| 事务隔离级别                    | READ UNCOMMITTED → READ COMMITTED → REPEATABLE READ → SERIALIZABLE  |
| `CHAR(10)` vs `VARCHAR(10)` | CHAR 定长（空格补齐），VARCHAR 变长（按实际存储）                      |
| `utf8` vs `utf8mb4`         | utf8 只有 3 字节（不支持 emoji），utf8mb4 是真正的 UTF-8               |
| `COUNT(*)` vs `COUNT(col)`  | COUNT(*) 计数所有行含 NULL，COUNT(col) 不计 NULL                       |
| `TRUNCATE` vs `DELETE`      | TRUNCATE 快但不可回滚，DELETE 慢但可回滚                               |
| `datetime` vs `timestamp`   | timestamp 自动转时区（存 UTC），datetime 原样存储                      |
| 范式                            | 1NF(原子值) → 2NF(消除部分依赖) → 3NF(消除传递依赖)                  |
| 备份                            | `mysqldump -u root -p dbname > file.sql`                             |
