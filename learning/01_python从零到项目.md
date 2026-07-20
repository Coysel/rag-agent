# Python 从零到项目实战

> **前置**: 会开关电脑即可，不需要任何编程基础。

---

## 第一章 程序是什么——和计算机说话

### 1.1 你已经在用"程序"了

打开微信、浏览器搜东西、用 Excel 算账——这些都是程序。程序就是**给计算机下的一串指令**，告诉它"先做什么、再做什么"。

Python 是一种**写指令的语言**。选它不是因为它最强，而是因为它**最接近人话**。你看：

```python
print("你好")
```

这就是一个完整的 Python 程序。运行它，屏幕上出现"你好"。你已经让计算机听你话了。

### 1.2 为什么叫 Python

跟蛇没关系。创始人是英国喜剧团体 Monty Python 的粉丝。所以 Python 社区的人喜欢把"巨蟒"的梗到处用——仅此而已。

### 1.3 安装和第一次运行

```bash
# Linux/Mac 一般已经装了
python3 --version

# 没装的话:
# Ubuntu: sudo apt install python3
# Mac: brew install python3
# Windows: 去 python.org 下载安装包，勾选"Add Python to PATH"
```

装好之后，打开终端输入 `python3`，你会看到一个 `>>>` 提示符。这就是 Python 的**交互模式**（也叫 REPL：Read → Evaluate → Print → Loop）：

```python
>>> 1 + 1
2
>>> print("Hello World")
Hello World
```

你输一行，Python 立刻执行一行。学习阶段最好的玩法。

> **REPL 就是 Read-Eval-Print Loop**，读你的指令、执行、打印结果、等你下一行——这就是 Python 的最简形态。

---

## 第二章 数据和变量——程序的记忆

### 2.1 变量：给数据贴标签

```python
name = "小明"      # 把"小明"这个数据存到 name 里
age = 25           # 把 25 存到 age 里
pi = 3.14159       # 把圆周率存到 pi 里
is_student = True  # 存一个"是/否"
```

把变量想象成**贴了标签的盒子**。`name = "小明"` 就是拿个盒子，贴上 `name` 标签，把 `"小明"` 放进去。以后用 `name` 就等于用 `"小明"`。

### 2.2 四种基本数据类型

| 类型    | 写法             | 含义 | 例子               |
| ------- | ---------------- | ---- | ------------------ |
| `int`   | `42`             | 整数 | 年龄、数量、编号   |
| `float` | `3.14`           | 小数 | 价格、温度、比率   |
| `str`   | `"hello"`        | 文本 | 名字、消息、路径   |
| `bool`  | `True` / `False` | 真假 | 是否开启、是否通过 |

### 2.3 字符串那些事

```python
name = "Alice"
greeting = "你好，" + name        # 拼接: "你好，Alice"
repeated = "哈" * 3              # 重复: "哈哈哈"
length = len(name)               # 长度: 5
upper = name.upper()             # 转大写: "ALICE"
contains = "li" in name          # 包含: True

# f-string —— 最常用的格式化方式
age = 25
info = f"{name} 今年 {age} 岁"   # "Alice 今年 25 岁"
```

### 2.4 类型转换

```python
int("42")    # 字符串变整数: 42
str(42)      # 整数变字符串: "42"
float("3.14") # 字符串变小数: 3.14
bool(0)      # 0 变布尔: False
bool("hi")   # 非空字符串: True
```

---

## 第三章 流程控制——让程序"思考"

### 3.1 条件判断 if

```python
score = 85

if score >= 90:
    print("优秀")
elif score >= 80:
    print("良好")
elif score >= 60:
    print("及格")
else:
    print("不及格")
```

**缩进是 Python 的命。** 同一个缩进级别 = 同一个代码块。Python 用缩进代替了其他语言的 `{}` 括号。

```python
if True:
    print("我在 if 里面")   # 缩进了，属于 if
print("我在外面")           # 没缩进，不属于 if
```

### 3.2 循环 for

```python
# 遍历列表
names = ["张三", "李四", "王五"]
for name in names:
    print(f"你好，{name}")

# range() 生成数字序列
for i in range(5):        # 0, 1, 2, 3, 4
    print(i)

for i in range(1, 10, 2): # 1, 3, 5, 7, 9 (从1到10，步长2)
    print(i)
```

### 3.3 循环 while

```python
count = 0
while count < 5:
    print(count)
    count += 1     # 每次加1，不加就会死循环
```

> **死循环** = 条件永远为 True 的 while 循环。按 Ctrl+C 可以强制中断。

### 3.4 break 和 continue

```python
# break: 跳出整个循环
for i in range(10):
    if i == 5:
        break          # 到 5 就停
    print(i)           # 输出 0,1,2,3,4

# continue: 跳过本次循环
for i in range(5):
    if i == 2:
        continue       # 跳过 2
    print(i)           # 输出 0,1,3,4
```

---

## 第四章 容器——储存多个数据

### 4.1 列表 list — 最常用的容器

```python
fruits = ["苹果", "香蕉", "橘子"]

# 增
fruits.append("葡萄")       # 末尾加: ["苹果","香蕉","橘子","葡萄"]
fruits.insert(1, "梨")      # 在位置1插入

# 删
fruits.remove("香蕉")        # 按值删除
last = fruits.pop()          # 弹出最后一个
del fruits[0]                # 按位置删除

# 查
first = fruits[0]            # 取第一个
last = fruits[-1]            # 取最后一个
subset = fruits[0:2]         # 切片: 取前两个

# 改
fruits[0] = "西瓜"           # 直接赋值修改

# 排序
numbers = [3, 1, 4, 1, 5]
numbers.sort()               # 原地排序: [1, 1, 3, 4, 5]
sorted_nums = sorted(numbers) # 返回新列表，原列表不变
```

**索引从 0 开始** — 这几乎是所有编程语言的约定。`fruits[0]` 是第一个，`fruits[1]` 是第二个。

### 4.2 字典 dict — 键值对

```python
person = {
    "name": "小明",
    "age": 25,
    "city": "北京"
}

name = person["name"]        # 取值
name = person.get("name")    # 更安全的方式（键不存在返回 None）
person["job"] = "工程师"     # 添加
del person["city"]           # 删除

# 遍历
for key, value in person.items():
    print(f"{key}: {value}")

# 检查键是否存在
if "age" in person:
    print("有年龄信息")
```

把字典想象成现实中的字典——你想查"apple"的意思，就翻到 A 开头的部分，顺着"apple"找到"苹果"。**键是索引，值是内容**。

### 4.3 元组 tuple — 不可变列表

```python
coordinates = (3, 4)
color = (255, 128, 0)   # RGB

x = coordinates[0]       # 可以读
# coordinates[0] = 5      # 会报错！元组不可修改
```

元组的存在理由：**有些数据不应该被修改**。函数的多个返回值自动打包成元组。

### 4.4 集合 set — 无重复的集合

```python
tags = {"python", "编程", "入门"}
tags.add("教程")           # 添加
tags.add("python")         # 重复的不生效

a = {1, 2, 3}
b = {2, 3, 4}
a | b   # 并集: {1, 2, 3, 4}
a & b   # 交集: {2, 3}
a - b   # 差集: {1}
```

> **去重神器**: `list(set([1,1,2,2,3]))` → `[1, 2, 3]`

### 4.5 列表推导式 — Python 的标志性写法

```python
# 普通写法
squares = []
for i in range(10):
    squares.append(i ** 2)

# 推导式 — 一行搞定
squares = [i ** 2 for i in range(10)]      # [0, 1, 4, 9, ..., 81]

# 带条件
evens = [i for i in range(20) if i % 2 == 0]  # 所有偶数

# 字典推导
word_lengths = {w: len(w) for w in ["a", "ab", "abc"]}
```

---

## 第五章 函数——让代码可复用

### 5.1 为什么需要函数

```python
# 没有函数 — 重复三遍
len_a = len([1,2,3])
print(len_a)
len_b = len([4,5,6,7])
print(len_b)
len_c = len([8,9])
print(len_c)

# 有函数
def print_length(lst):
    print(len(lst))

print_length([1,2,3])
print_length([4,5,6,7])
print_length([8,9])
```

函数是把**一段逻辑打包**，起个名字，以后随时调用。

### 5.2 参数和返回值

```python
def greet(name, greeting="你好"):      # name 必填，greeting 有默认值
    return f"{greeting}，{name}！"     # return 把结果传回去

msg = greet("小明")                    # "你好，小明！"
msg = greet("小红", "早上好")          # "早上好，小红！"
msg = greet(greeting="晚上好", name="小刚")  # 关键字参数，顺序无所谓
```

### 5.3 作用域 — 变量能活在哪

```python
x = 10          # 全局变量

def foo():
    y = 20      # 局部变量，只在 foo 里有效
    print(x)    # 能读到 x
    print(y)

foo()
# print(y)      # 报错！y 不存在
```

> 简单记：**函数内部创建的变量，函数外看不到。** 这防止了不同函数之间互相干扰。

### 5.4 把函数当参数传

```python
def apply_to_list(func, lst):
    return [func(item) for item in lst]

numbers = [1, 2, 3]
doubled = apply_to_list(lambda x: x * 2, numbers)   # [2, 4, 6]

# lambda 就是一行匿名函数
add = lambda a, b: a + b     # 等价于 def add(a,b): return a+b
```

---

## 第六章 类和对象——设计你自己的数据

### 6.1 什么是类

你已经用过很多"类型"了——`int`、`str`、`list`，每个都是类。`42` 是 `int` 类的一个实例，`"hello"` 是 `str` 类的一个实例。

**类 = 蓝图，对象 = 按蓝图造出来的具体东西。**

```python
class Dog:
    def __init__(self, name, age):     # 构造函数，创建对象时自动调用
        self.name = name
        self.age = age

    def bark(self):                     # 方法
        print(f"{self.name}: 汪汪！")

    def get_old(self, years):
        self.age += years
        print(f"{self.name} 现在 {self.age} 岁了")

# 用类造对象
my_dog = Dog("旺财", 3)      # 调用 __init__
my_dog.bark()                # "旺财: 汪汪！"
my_dog.get_old(2)            # "旺财 现在 5 岁了"
```

### 6.2 self 是什么

```python
my_dog.bark()
# Python 在背后做了: Dog.bark(my_dog)
# self 就是"当前这个对象自己"
```

`self` 不是关键字，写成 `this`、`me` 都行——但全 Python 世界都用 `self`，你不要反着来。

### 6.3 继承 — 复用父类的代码

```python
class Animal:
    def __init__(self, name):
        self.name = name

    def eat(self):
        print(f"{self.name} 在吃东西")

class Cat(Animal):              # Cat 继承 Animal
    def meow(self):
        print(f"{self.name}: 喵～")

cat = Cat("小白")
cat.eat()    # 来自 Animal — "小白 在吃东西"
cat.meow()   # Cat 自己的 —  "小白: 喵～"
```

继承的核心思想：**共性放父类，个性放子类。**

### 6.4 魔术方法 — 让类用起来更自然

```python
class BankAccount:
    def __init__(self, owner, balance=0):
        self.owner = owner
        self.balance = balance

    def __str__(self):                      # print() 时调用
        return f"{self.owner} 的账户，余额 {self.balance} 元"

    def __add__(self, other):               # + 运算符
        return BankAccount("Joint", self.balance + other.balance)

    def __len__(self):                      # len() 时调用
        return self.balance  # 返回余额的"长度"（只是一个例子）

a = BankAccount("小明", 100)
b = BankAccount("小红", 200)
print(a)          # "小明 的账户，余额 100 元" — 调了 __str__
joint = a + b     # 调了 __add__
```

---

## 第七章 模块和包 — 组织代码

### 7.1 import 就是引入别人的代码

```python
import math            # 整个模块引入
math.sqrt(16)          # 4.0

from math import sqrt  # 只引入一个函数
sqrt(16)               # 4.0

import numpy as np     # 起别名
np.array([1, 2, 3])

from pathlib import Path  # 面向对象的文件路径
```

### 7.2 自己写模块

```python
# utils.py
def greet(name):
    return f"你好，{name}"

PI = 3.14159

# main.py
from utils import greet, PI
```

**模块就是 .py 文件，包就是装了 .py 文件的文件夹。** 文件夹下放个 `__init__.py`（可以是空的），Python 就把它当包。

```
my_project/
├── main.py
└── my_package/
    ├── __init__.py     # 空文件，标识这是一个包
    ├── utils.py
    └── models.py
```

---

## 第八章 异常处理 — 程序不出错才怪

### 8.1 try/except

```python
try:
    num = int(input("输入数字: "))
    result = 100 / num
    print(f"100 / {num} = {result}")
except ValueError:
    print("你输入的不是数字！")
except ZeroDivisionError:
    print("不能除以 0！")
except Exception as e:
    print(f"未知错误: {e}")
finally:
    print("无论有没有错，我都会执行")
```

`finally` 用于**清理资源**（关闭文件、断开数据库连接），不管有没有异常都执行。

### 8.2 抛异常

```python
def withdraw(balance, amount):
    if amount > balance:
        raise ValueError("余额不足")
    return balance - amount
```

---

## 第九章 实战必备技能

### 9.1 文件读写

```python
# 读文件
with open("data.txt", "r", encoding="utf-8") as f:
    content = f.read()          # 全读
    # lines = f.readlines()     # 按行读

# 写文件
with open("output.txt", "w", encoding="utf-8") as f:
    f.write("Hello\n")
    f.write("World\n")

# 追加
with open("log.txt", "a", encoding="utf-8") as f:
    f.write("新的一行\n")
```

> `with` 自动关闭文件，不用自己调 `f.close()`。**文件操作永远用 with。**

### 9.2 虚拟环境 — 项目依赖隔离

```bash
# 创建虚拟环境
python3 -m venv myproject_env

# 激活 (Linux/Mac)
source myproject_env/bin/activate

# 激活 (Windows)
myproject_env\Scripts\activate

# 安装依赖
pip install requests numpy

# 导出依赖列表
pip freeze > requirements.txt

# 在新环境安装
pip install -r requirements.txt
```

为什么需要虚拟环境？项目 A 用 requests 2.0，项目 B 用 requests 3.0，装到全局会冲突。虚拟环境让每个项目有独立的依赖副本。

### 9.3 pip 常用命令

```bash
pip install package_name         # 安装
pip uninstall package_name       # 卸载
pip list                         # 查看已安装
pip show package_name            # 查看包信息
pip install --upgrade package    # 升级
```

### 9.4 数据库连接（pymysql）

```python
import pymysql

conn = pymysql.connect(
    host="localhost",
    user="root",
    password="your_pw",
    database="mydb",
    charset="utf8mb4",
)

try:
    with conn.cursor() as cursor:
        # 查询
        cursor.execute("SELECT name, age FROM users WHERE age > %s", (18,))
        rows = cursor.fetchall()
        for row in rows:
            print(row)

        # 插入
        cursor.execute(
            "INSERT INTO users (name, age) VALUES (%s, %s)",
            ("小明", 25)
        )
    conn.commit()   # 修改数据后必须 commit
finally:
    conn.close()
```

> **占位符用 `%s` 不要用 f-string 拼 SQL**，后者会导致 SQL 注入漏洞。

### 9.5 HTTP 请求（requests）

```python
import requests

# GET
resp = requests.get("https://api.example.com/users")
data = resp.json()           # 解析 JSON

# POST
resp = requests.post(
    "https://api.example.com/login",
    json={"username": "admin", "password": "123"},
    timeout=10,               # 必须设置超时
)

if resp.status_code == 200:
    print("成功")
else:
    print(f"失败: {resp.status_code}")
```

### 9.6 JSON 处理

```python
import json

# Python → JSON 字符串
data = {"name": "小明", "age": 25}
json_str = json.dumps(data, ensure_ascii=False)  # ensure_ascii=False 保留中文

# JSON 字符串 → Python
parsed = json.loads('{"name": "小明", "age": 25}')
print(parsed["name"])  # "小明"
```

---

## 附录 需要记住的内容

| 知识点             | 内容                                                      |
| ------------------ | --------------------------------------------------------- |
| Python 数据类型    | `int float str bool list tuple dict set None`             |
| 可变 vs 不可变     | 可变:`list dict set` / 不可变: `int float str tuple bool` |
| 索引               | 从 0 开始，`[-1]` 取最后一个                              |
| 切片               | `[start:end:step]`，含头不含尾                            |
| `is` vs `==`       | `==` 比值的相等，`is` 比内存地址相同                      |
| `None` 判断        | 用`x is None` 而不是 `x == None`                          |
| 字符串方法         | `split join strip replace upper lower startswith`         |
| 列表方法           | `append pop insert remove sort reverse index count`       |
| 字典方法           | `get items keys values pop update`                        |
| 文件操作           | 永远用`with open()`                                       |
| Python 之禅        | `import this` — 20 条设计原则                             |
| `*args` `**kwargs` | 接收任意数量的位置/关键字参数                             |
| 装饰器             | `@decorator` — 在不改原函数的情况下包装它                 |
| 生成器             | `yield` — 惰性计算，逐个产出值                            |
| 上下文管理器       | `__enter__` `__exit__` — `with` 语句背后的机制            |
