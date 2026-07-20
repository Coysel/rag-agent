# 第八部分：Docker

> **学习目标**：这一部分的目标是让你真正理解 Docker——不再把它当作一个"黑盒部署工具"，而是理解容器和镜像的本质区别、Docker 的隔离原理、以及如何正确地构建和编排容器化应用。学完之后，你应该能回答"容器和虚拟机到底有什么区别"、"为什么 Docker 镜像要分层"、"CMD 和 ENTRYPOINT 应该怎么选"这类深层问题。

---

## 一、Docker 概述：它解决了什么问题

### 1.1 为什么需要 Docker

在 Docker 出现之前，软件部署是一个令人头疼的问题。想象这样一个场景：

你在本地开发了一个 Python Web 应用，一切运行正常。你把代码发给同事，同事的电脑上却报错——因为同事的 Python 版本是 3.8 而不是你的 3.10。你把它部署到服务器，服务器是 CentOS 而你的开发机是 Windows，路径分隔符不同、依赖库的二进制包不同、甚至系统底层的 glibc 版本都不同。你花了一天时间调试环境问题，代码本身一行没改。

这种现象被称为 **"Works on my machine"（在我的机器上能跑）**问题。它的根源在于：**你的开发和运行环境之间存在着不可控的差异**——操作系统不同、系统库版本不同、语言运行时不同、依赖的版本不同。

Docker 的核心理念就是解决这个问题：**把你的应用和它所需要的完整环境打包在一起，在任何机器上以完全相同的方式运行**。

### 1.2 Docker 的核心架构

Docker 采用 **客户端-服务器（C/S）架构**：

```
┌─────────────┐     命令      ┌─────────────────┐     管理      ┌──────────────┐
│  Docker CLI  │ ──────────→  │  Docker Daemon   │ ──────────→  │  容器/镜像    │
│  (docker命令) │ ←──────────  │  (后台守护进程)   │ ←──────────  │              │
└─────────────┘   响应       └─────────────────┘              └──────────────┘
```

三个核心组件：

| 组件 | 角色 | 通俗理解 |
|------|------|---------|
| **Docker Daemon（dockerd）** | 后台守护进程，负责管理容器、镜像、网络、存储 | Docker 的"引擎"，真正干活的部分 |
| **Docker CLI（docker）** | 命令行工具，向 Daemon 发送指令 | 方向盘和踏板，你操作的地方 |
| **Docker Registry** | 镜像仓库，存储和分发镜像 | Docker 的"应用商店"，默认是 Docker Hub |

你执行的 `docker run`、`docker build` 等命令，本质上是 Docker CLI 通过 REST API 告诉 Docker Daemon："帮我做一件事"。Daemon 收到指令后，去拉取镜像、创建容器、管理网络——这些才是真正的工作。

> **为什么设计成 C/S 架构？** 这个设计让 Docker CLI 和 Docker Daemon 可以运行在不同的机器上。你可以在一台机器上执行 `docker` 命令，控制另一台服务器上的 Docker Daemon。这在 CI/CD 流程中非常常见：开发机上执行构建命令，远程服务器上运行容器。

### 1.3 Docker 的"三个层次"理解法

要真正理解 Docker，可以从下到上分三个层次来看：

**第一层：Linux 内核能力（底层基础）**
Docker 本身不是一种虚拟化技术（如 VMware、VirtualBox），而是一种**进程隔离技术**。它依赖 Linux 内核的两个核心能力：
- **Namespace（命名空间）**：让每个容器看到独立的进程树、网络栈、文件系统、用户 ID——容器内的进程"以为"自己是系统中的唯一进程
- **Cgroups（控制组）**：限制和监控每个容器使用的 CPU、内存、磁盘 I/O——防止一个容器吃光所有资源

**第二层：镜像和容器（基本单元）**
- **镜像（Image）**：一个只读的模板，包含了运行应用所需的一切——代码、运行时、系统库、环境变量、配置文件
- **容器（Container）**：镜像的一个可运行实例，是**镜像 + 可写层 + 进程**

**第三层：编排和调度（上层工具）**
当容器数量增多（从几个到几百个），就需要工具来管理它们：
- **Docker Compose**：单机上定义和运行多个容器
- **Kubernetes / Docker Swarm**：跨多台机器的容器编排

---

## 二、镜像（Image）与容器（Container）：最核心的两个概念

### 2.1 什么是 Docker 镜像

Docker 镜像是一个**只读的、分层构建的文件系统模板**。它包含了运行一个应用所需的一切：

```
一个典型 Python Web 应用的镜像包含：
┌─────────────────────────────────┐
│  应用代码 (app.py)               │
│  Python 依赖 (requirements.txt)  │
│  Python 解释器 (3.10)            │
│  系统库 (libssl, libcrypto 等)   │
│  操作系统基础层 (Ubuntu 22.04)   │
│  ...                            │
└─────────────────────────────────┘
```

**镜像的关键特性：**

1. **只读（Read-only）**：镜像一旦构建完成就不可修改。你无法"编辑"一个镜像——你只能基于它创建一个新镜像。
2. **分层（Layered）**：镜像由多个只读层（Layer）叠加而成，每一层代表一个 Dockerfile 指令。
3. **可分发（Distributable）**：镜像可以推送到仓库（如 Docker Hub），在其他机器上拉取运行。

### 2.2 什么是 Docker 容器

容器是**镜像的一个可运行实例**。当你执行 `docker run` 时，Docker 在镜像的只读层之上添加一个**可写层（Writable Layer / Container Layer）**，然后启动一个进程。

```
┌─────────────────────────────────┐
│  可写层 (容器层) ← 运行时修改在此 │
├─────────────────────────────────┤
│  镜像层 3 (只读)                 │
│  镜像层 2 (只读)                 │
│  镜像层 1 (只读)  ← 基础层       │
└─────────────────────────────────┘
```

**容器的关键特性：**

1. **有状态的**：容器运行期间，所有文件修改、日志写入、临时数据都保存在可写层。
2. **临时性的**：容器可以启动、停止、删除。删除容器时，如果没有通过 Volume 持久化，可写层的数据也会被删除。
3. **隔离的**：每个容器有自己的文件系统、网络、进程空间。

### 2.3 镜像 vs 容器：最直观的类比

理解镜像和容器关系的最佳方式是使用**面向对象编程**的类比：

| 概念 | OOP 类比 | 解释 |
|------|---------|------|
| **Dockerfile** | 类定义（Class） | 描述如何构建镜像的"蓝图" |
| **镜像（Image）** | 类本身（编译后的 Class） | 一个静态的、不可变的模板 |
| **容器（Container）** | 类的实例（Instance/Object） | 镜像的运行态实体 |

```python
class MyAWebApp:       # ← Dockerfile
    code = "app.py"    # ← FROM python 3.10
    deps = [...]       # ← RUN pip install
    ...

app1 = MyWebApp()      # ← docker run → 容器 1
app2 = MyWebApp()      # ← docker run → 容器 2
```

多个容器可以从同一个镜像创建，它们一开始的内容完全相同。运行时对文件系统的修改（写入日志、创建临时文件）只影响各自的容器层，互不干扰。

### 2.4 为什么 Docker 镜像要分层

这是 Docker 设计中最精妙的地方之一。分层带来了三个巨大的好处：

**好处一：节省磁盘空间**

假设你在一个 Ubuntu 基础镜像上运行 10 个 Python 应用。没有分层时，你需要存储 10 份完整的操作系统文件。有了分层：

```
所有容器共享同一份 Ubuntu 基础层 + Python 层
每个容器只需要存储自己独有的代码层

10 个应用的磁盘占用 = 基础层(200MB) + Python层(100MB) + 10 × 应用层(各50MB)
                      = 200 + 100 + 500 = 800MB
如果没有分层：10 × (200 + 100 + 50) = 3500MB
节省了 77% 的磁盘空间
```

**好处二：加速构建和部署**

Docker 构建镜像时，每一层都会缓存。如果你修改了应用代码，只需要重建"代码层"以上的层，基础层和依赖层可以直接使用缓存：

```dockerfile
FROM python:3.10-slim        # 层 A：基础镜像

WORKDIR /app                  # 层 B：创建工作目录

COPY requirements.txt .       # 层 C：复制依赖文件
RUN pip install -r requirements.txt  # 层 D：安装依赖

COPY . .                      # 层 E：复制应用代码
CMD ["python", "app.py"]      # 层 F：启动命令
```

如果你修改了 `app.py`（只影响层 E 和 F），Docker 会使用缓存中的层 A、B、C、D，只重新构建层 E 和 F。这比完整构建快得多。

**不过，这里有一个常见的陷阱**：如果你把 `COPY . .` 放在 `COPY requirements.txt` 之前，那么每次修改任何代码文件都会导致 `pip install` 重新执行（因为 `RUN pip install` 依赖的层变了），这将大大增加构建时间。

**好处三：便于分发**

推送和拉取镜像时，Docker 只传输本地没有的层。如果不同机器上已经有相同的底层，只需传输顶部的差异层。

### 2.5 镜像层的物理存储

每层实际上是一个**增量文件（diff）**——只记录相对于上一层的文件变化：

```
层 1 (Ubuntu 基础):         contains /bin, /usr, /lib, /etc 等系统文件
层 2 (Python 安装):         包含 Python 解释器文件
层 3 (pip 安装的依赖):      包含 site-packages 目录下的 .py 文件
层 4 (应用代码):            包含 app.py 等文件
```

这些层存储在 Docker 主机的 `/var/lib/docker/overlay2/` 目录下（假设使用 overlay2 存储驱动）。Docker 使用**写时复制（Copy-on-Write, CoW）** 策略：当容器需要修改一个文件时，Docker 不会直接修改镜像层的文件（因为是只读的），而是把文件复制到可写层，在可写层上修改。这就是"写时复制"——只在写入时才复制。

### 2.6 镜像仓库：Docker Hub 和其他 Registry

镜像是通过 Registry（镜像仓库）分发的：

```bash
# 从 Docker Hub 拉取镜像
docker pull nginx:latest

# 推送到自己的仓库
docker push yourname/myapp:1.0

# 从私有仓库拉取
docker pull registry.example.com/myapp:1.0
```

镜像的命名规则是：`[仓库地址/]镜像名[:标签]`
- `nginx:latest` → Docker Hub 上的 nginx 镜像，标签为 latest
- `yourname/myapp:1.0` → Docker Hub 上 yourname 用户下的 myapp 镜像，版本 1.0
- `registry.example.com/myapp:1.0` → 私有仓库的镜像

> **为什么需要标签（Tag）？** 标签让你可以区分镜像的不同版本。`latest` 是最新版本，`1.0` 是特定的发布版本，`alpine` 是基于 Alpine Linux 的轻量版本。生产环境中应该使用明确的版本标签而非 `latest`，因为 `latest` 是可变的——今天拉的和明天拉的可能是不同的镜像。

---

## 三、Docker vs 虚拟机（VM）：两种隔离方案

### 3.1 为什么需要对比

很多初学者容易混淆容器和虚拟机，因为它们的用户接口看起来很相似——都是"启动一个隔离的环境来运行应用"。但它们的底层实现完全不同，这导致它们在性能、启动速度、隔离强度上有本质区别。

### 3.2 架构对比

先看两者的架构：

```
虚拟机架构：
┌─────────────────────────────────────────────────────┐
│  物理服务器 / 宿主机操作系统                          │
│  ┌─────────────────────────────────────────────────┐│
│  │ Hypervisor (VMware / KVM / Hyper-V)              ││
│  │  ┌─────────────────┐  ┌─────────────────┐       ││
│  │  │ VM 1: Ubuntu     │  │ VM 2: CentOS     │       ││
│  │  │  ┌───────────┐   │  │  ┌───────────┐   │       ││
│  │  │  │ 应用 A     │   │  │  │ 应用 B     │   │       ││
│  │  │  │ 系统库     │   │  │  │ 系统库     │   │       ││
│  │  │  │ 完整 OS    │   │  │  │ 完整 OS    │   │       ││
│  │  │  └───────────┘   │  │  └───────────┘   │       ││
│  │  └─────────────────┘  └─────────────────┘       ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘

Docker 容器架构：
┌─────────────────────────────────────────────────────┐
│  物理服务器 / 宿主机操作系统                          │
│  ┌─────────────────────────────────────────────────┐│
│  │ Docker Daemon                                   ││
│  │  ┌─────────────────┐  ┌─────────────────┐       ││
│  │  │ 容器 1           │  │ 容器 2           │       ││
│  │  │  ┌───────────┐   │  │  ┌───────────┐   │       ││
│  │  │  │ 应用 A     │   │  │  │ 应用 B     │   │       ││
│  │  │  │ 系统库     │   │  │  │ 系统库     │   │       ││
│  │  │  └───────────┘   │  │  └───────────┘   │       ││
│  │  └─────────────────┘  └─────────────────┘       ││
│  │  共享宿主机的 Linux 内核                          ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

**两者的本质区别：**

| 维度 | 虚拟机 | Docker 容器 |
|------|--------|------------|
| **内核** | 每个 VM 有**独立的内核**（Guest OS） | 所有容器**共享宿主机内核** |
| **虚拟化层** | Hypervisor 虚拟化硬件（CPU、内存、磁盘） | Docker 利用 Namespace 和 Cgroups 实现进程隔离 |
| **启动时间** | 分钟级（需要启动完整的操作系统） | 秒级（只是一个进程） |
| **镜像大小** | GB ~ 几十 GB（包含完整 OS） | MB ~ 几百 MB |
| **隔离程度** | 强（完全独立的 OS） | 弱（共享宿主机内核） |
| **性能损耗** | 较高（硬件虚拟化开销） | 极小（原生进程性能） |

### 3.3 为什么容器比虚拟机快

**启动速度：秒级 vs 分钟级**

当你启动一个虚拟机时，Hypervisor 需要：
1. 分配虚拟 CPU 和内存资源
2. 加载 Guest OS 的内核（从磁盘读取内核文件）
3. 初始化内核（驱动加载、设备检测、启动初始化进程 systemd）
4. 启动系统服务（网络、SSH、日志等）
5. 最后才启动你的应用

而启动一个容器时，Docker 只需要：
1. 创建 Namespace 隔离环境
2. 挂载镜像层文件系统
3. 把你的应用作为进程启动（PID 1）

因为容器不需要加载和初始化一个完整的操作系统内核——它直接使用宿主机的内核。

**性能损耗：几乎无 vs 明显**

虚拟机有性能损耗的原因：
- CPU 指令需要经过 Hypervisor 的**二进制翻译**或**硬件辅助虚拟化**（VT-x/AMD-V）
- 内存访问需要经过**影子页表**或**EPT（扩展页表）**——虚拟机认为自己在访问物理内存，实际上访问的是 Hypervisor 映射的物理内存
- 磁盘 I/O 经过虚拟化层（模拟的磁盘控制器）

容器中的进程就是宿主机上的一个普通进程（只是被隔离了），它的 CPU 指令直接被 CPU 执行，没有中间层。它的系统调用直接进入宿主机内核，不需要虚拟化。

### 3.4 为什么需要虚拟机而不是只用容器

既然容器这么好，为什么虚拟机还没有消失？因为容器的隔离是**"软隔离"**——依赖 Linux 内核提供的 Namespace 和 Cgroups。

**容器的安全边界问题**：所有容器共享宿主机内核。如果一个容器中的进程利用内核漏洞获取了宿主机的 root 权限，它可以影响到宿主机上的所有其他容器。在虚拟机中，即使 Guest OS 被完全攻破，攻击者也难以突破 Hypervisor 到达宿主机——因为中间隔着硬件虚拟化层。

所以：
- **容器**更适用于：微服务、DevOps、CI/CD、开发测试环境
- **虚拟机**更适用于：需要强隔离的场景（多租户云平台）、运行不同操作系统的场景（在 Linux 上跑 Windows 应用）

在实践中，两者的结合很常见：**在虚拟机上运行 Docker**。比如云服务器（ECS）本身就是一台虚拟机，你在这台 VM 上安装 Docker 来部署你的微服务。

### 3.5 Docker 在 macOS 和 Windows 上的特殊实现

这里有一个重要的细节：**Docker 依赖 Linux 内核的 Namespace 和 Cgroups 功能**。macOS 和 Windows 本身没有这些机制，那 Docker 在这些平台上如何运行？

答案是：Docker Desktop 在 macOS 和 Windows 上会创建一个轻量级的 Linux 虚拟机（使用 HyperKit 或 Hyper-V），Docker Daemon 和所有容器都运行在这个 Linux 虚拟机中。

```
macOS:
┌─────────────────────────────────────┐
│  macOS 应用层                       │
│  Docker CLI ─→ API 代理             │
│                                     │
│  ┌── Linux VM (通过 HyperKit) ──┐  │
│  │  Docker Daemon                │  │
│  │  ┌── 容器1 ──┐ ┌── 容器2 ──┐ │  │
│  │  │ 应用A     │ │ 应用B     │ │  │
│  │  └───────────┘ └───────────┘ │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

这意味着在 macOS/Windows 上，Docker 容器实际上运行在一个虚拟机里——但在 Linux 服务器上，它是原生运行的。

---

## 四、Dockerfile：如何构建镜像

### 4.1 什么是 Dockerfile

Dockerfile 是一个文本文件，包含了一系列构建镜像的指令。它就像一份"菜谱"——告诉 Docker 如何一步步地制作一个镜像。

来看一个最简单的 Dockerfile：

```dockerfile
# 使用 Python 3.10 作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件到容器
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 声明容器运行时监听的端口
EXPOSE 8000

# 指定容器启动时运行的命令
CMD ["python", "app.py"]
```

### 4.2 每条指令的详细解释

#### FROM — 一切的基础

```dockerfile
FROM python:3.10-slim
```

**作用**：指定基础镜像。每条 Dockerfile 必须以 `FROM` 开头。

**为什么需要基础镜像？** 你的应用不可能在"空"中运行。Python 应用需要 Python 解释器，而 Python 解释器又依赖 glibc（GNU C 库）、openssl 等系统库。基础镜像提供了这些底层依赖。

**常用的基础镜像**：
- `alpine:latest` — 只有 5MB 的超精简 Linux，但需要手动安装各种依赖
- `ubuntu:22.04` — 完整的 Ubuntu 系统，约 80MB
- `python:3.10-slim` — Debian 精简版 + Python，约 120MB
- `node:18-alpine` — Alpine + Node.js，约 50MB

> **为什么不用 `ubuntu` 全量镜像？** 全量 Ubuntu 镜像包含了大量在容器中可能永远不会用到的工具（如 systemd、网络管理工具、编辑器等）。镜像越大，构建越慢、传输越慢。生产环境倾向于使用 **Slim**（精简）或 **Alpine**（极简）版本的基础镜像，减少攻击面也减少资源占用。

#### WORKDIR — 设置工作目录

```dockerfile
WORKDIR /app
```

**作用**：设置当前的工作目录。后续的 `COPY`、`RUN`、`CMD` 等指令都会在这个目录下执行。

**为什么需要 `WORKDIR` 而不是直接用 `cd`？** 在 Docker 中，每个 `RUN` 指令都会在新的临时容器中执行。如果你写 `RUN cd /app`，这条命令只在当前 `RUN` 指令中生效，下一条指令又回到根目录了。`WORKDIR` 创建的是一个持久化的目录状态。

这也解释了 Dockerfile 的一个常见问题：**不要用 `cd` 切换目录，用 `WORKDIR`**。

#### COPY — 复制文件

```dockerfile
COPY requirements.txt .
COPY . .
```

**作用**：把本地（构建上下文）的文件复制到镜像中。

第一个参数是本地路径（相对于构建上下文），第二个参数是容器内的路径。`.` 表示当前工作目录（由 `WORKDIR` 设置的目录）。

**注意**：`COPY . .` 会把整个构建上下文复制到镜像中。如果你有 `.git` 目录、`node_modules` 目录等不需要的文件，应该用 `.dockerignore` 排除：

```
# .dockerignore
.git/
node_modules/
__pycache__/
*.pyc
.env
```

这类似于 `.gitignore`——告诉 Docker 哪些文件不应该进入镜像。

#### RUN — 执行命令

```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```

**作用**：在镜像构建过程中执行命令。每条 `RUN` 指令创建一个新的镜像层。

`--no-cache-dir` 参数告诉 pip 不要缓存下载的包，这样可以减少镜像大小。

#### EXPOSE — 声明端口

```dockerfile
EXPOSE 8000
```

**作用**：声明容器在运行时监听的端口。**注意**：`EXPOSE` 本身**不会**让端口对外可访问。它只是一个文档声明，告诉使用者"这个容器会监听 8000 端口"。真正让端口可访问的是在 `docker run` 时加 `-p` 参数：

```bash
docker run -p 8000:8000 my-app
```

#### CMD — 默认启动命令

```dockerfile
CMD ["python", "app.py"]
```

**作用**：指定容器启动时要执行的命令。我们会在下一节详细讨论 CMD 和 ENTRYPOINT 的区别。

### 4.3 指令的执行时机

理解 Dockerfile 中指令的执行时机非常重要：

| 指令 | 执行时机 | 特点 |
|------|---------|------|
| `FROM` | `docker build` | 拉取或使用本地缓存的基础镜像 |
| `RUN` | `docker build` | 在构建过程中执行，结果持久化到镜像层 |
| `COPY` / `ADD` | `docker build` | 在构建过程中复制文件到镜像 |
| `CMD` | `docker run` | 容器启动时执行，不持久化到镜像 |
| `ENTRYPOINT` | `docker run` | 同 CMD，容器启动时执行 |
| `ENV` | `docker build` + `docker run` | 设置环境变量，构建和运行时都可用 |

**关键区别**：`RUN` 是在**构建镜像时**执行的，它的结果是镜像的一部分。而 `CMD`/`ENTRYPOINT` 是在**启动容器时**执行的，它们定义了容器启动后要运行什么命令。

---

## 五、CMD vs ENTRYPOINT：容器的启动入口

### 5.1 为什么需要区分这两个指令

容器本质上是一个**隔离的进程**。当容器启动时，它需要知道要运行什么进程。`CMD` 和 `ENTRYPOINT` 都是用来指定这个进程的，但它们在可覆盖性和灵活性上有区别。

### 5.2 CMD — 提供默认值

`CMD` 指定容器的默认启动命令，但这个命令是**可被覆盖**的。

```dockerfile
CMD ["python", "app.py"]
```

当你运行容器时，如果不加额外参数，会执行 `python app.py`：

```bash
docker run my-app
# 等价于执行: python app.py
```

但如果用户在 `docker run` 末尾指定了命令，`CMD` 会被完全替换：

```bash
docker run my-app python test.py
# 等价于执行: python test.py（CMD 被覆盖了）
```

### 5.3 ENTRYPOINT — 固定入口点

`ENTRYPOINT` 指定容器的主程序，这个主程序**不会被 `docker run` 末尾的参数覆盖**。

```dockerfile
ENTRYPOINT ["python"]
CMD ["app.py"]
```

当你运行容器时：

```bash
docker run my-app
# 等价于执行: python app.py（CMD 的内容作为 ENTRYPOINT 的参数）

docker run my-app test.py
# 等价于执行: python test.py（CMD 被覆盖为 test.py，但仍是 python）
```

### 5.4 两者的结合使用

**最重要的规则**：`CMD` 和 `ENTRYPOINT` 一起使用时，`CMD` 的内容会作为默认参数传给 `ENTRYPOINT`。这是它们的标准用法。

来看一个实际场景：你构建了一个 Docker 镜像，功能是对一个文件进行处理。你可以用 ENTRYPOINT 固定"这个容器是跑处理程序的"，用 CMD 提供默认的输入文件：

```dockerfile
FROM ubuntu:22.04
COPY process.sh /usr/local/bin/process.sh
ENTRYPOINT ["/usr/local/bin/process.sh"]
CMD ["--input", "default.txt"]
```

使用方式：

```bash
# 处理默认文件
docker run my-processor
# 等价于: /usr/local/bin/process.sh --input default.txt

# 处理自定义文件
docker run my-processor --input mydata.csv
# 等价于: /usr/local/bin/process.sh --input mydata.csv

# 查看帮助（如果 process.sh 支持 --help）
docker run my-processor --help
# 等价于: /usr/local/bin/process.sh --help
```

### 5.5 三种配置模式的完整对比

| 模式 | Dockerfile | `docker run` 不带参数 | `docker run` 带参数 | 适用场景 |
|------|-----------|---------------------|-------------------|---------|
| 仅 CMD | `CMD ["python", "app.py"]` | `python app.py` | 参数替换 CMD，如 `docker run img bash` → 执行 `bash` | 快速启动，用户可以完全替换命令 |
| 仅 ENTRYPOINT | `ENTRYPOINT ["python"]` | 报错（缺少参数） | `docker run img app.py` → `python app.py` | 不常用，因为没有默认参数 |
| ENTRYPOINT + CMD | `ENTRYPOINT ["python"]` `CMD ["app.py"]` | `python app.py` | `docker run img test.py` → `python test.py` | **最常用**，固定主程序，用户可换参数 |

### 5.6 Shell 格式 vs Exec 格式

CMD 和 ENTRYPOINT 都支持两种书写格式：

**Exec 格式（推荐）**：
```dockerfile
CMD ["python", "app.py"]
ENTRYPOINT ["python", "app.py"]
```

**Shell 格式**：
```dockerfile
CMD python app.py
ENTRYPOINT python app.py
```

**两者的关键区别**：

```bash
# Exec 格式（推荐）：
# 容器中的 PID 1 就是 python 进程
# 收到 SIGTERM 信号时直接发给 python 进程
PID 1 → python app.py

# Shell 格式：
# PID 1 是 /bin/sh -c，python 是子进程
# SIGTERM 发给 sh，sh 可能不会转发给 python
PID 1 → /bin/sh -c "python app.py"
       └── python app.py (PID 2)
```

**为什么 Exec 格式是推荐的？** 因为容器的 PID 1 进程负责接收和处理系统信号。Shell 格式下，PID 1 是 shell 而不是你的应用。当 Docker 试图优雅地停止容器时（`docker stop`），它会向 PID 1 发送 SIGTERM。如果 PID 1 是 shell，shell 可能不会把信号转发给子进程——导致应用被 SIGKILL 强制杀掉，可能丢失数据或无法完成清理工作。

使用 Exec 格式，你的应用直接作为 PID 1 运行，可以正确处理信号。

---

## 六、多阶段构建（Multi-stage Builds）

### 6.1 为什么需要多阶段构建

在构建应用时，我们通常需要**构建工具**和**运行环境**。但构建工具（编译器、依赖管理器、头文件）只在构建时需要，运行时并不需要。如果把它们留在镜像中，会导致镜像体积巨大。

来看一个编译型语言（Go）的例子：

**单阶段构建的问题**：

```dockerfile
# 单阶段构建：把所有东西塞进一个镜像
FROM golang:1.20

# 安装编译工具（已经包含在 golang 镜像中）
WORKDIR /app
COPY . .

# 编译
RUN go build -o myapp

# 运行时需要的只有编译好的二进制文件
# 但 Go 编译器、头文件、源码…… 都还在镜像里
CMD ["./myapp"]
```

这个镜像的大小是多少？`golang:1.20` 基础镜像约 800MB。加上源代码和依赖，最终镜像可能在 1GB 左右。但真正运行时需要的只是一个 10MB 的 Go 二进制文件。

### 6.2 多阶段构建的工作原理

多阶段构建允许你在一个 Dockerfile 中使用多个 `FROM` 语句。每个 `FROM` 开始一个新的构建阶段，你可以从之前的阶段复制文件到最终的阶段。

```dockerfile
# 第一阶段：构建环境
FROM golang:1.20 AS builder    # ← AS 给这个阶段起个名字

WORKDIR /app
COPY . .
RUN go build -o myapp           # 编译出二进制文件

# 第二阶段：运行环境
FROM alpine:latest              # ← 全新的轻量基础镜像

WORKDIR /app
COPY --from=builder /app/myapp .  # ← 只从 builder 阶段复制编译结果

CMD ["./myapp"]
```

最终镜像大小：`alpine:latest`（约 5MB）+ `myapp`（约 10MB）= **约 15MB**。相比单阶段的 1GB，减少了 98% 以上。

### 6.3 多阶段构建的典型模式

**Python 应用的多阶段构建**（用于需要编译 C 扩展的场景）：

```dockerfile
# 第一阶段：构建 C 扩展
FROM python:3.10-slim AS builder

WORKDIR /app
COPY requirements.txt .
# 安装编译依赖并构建 wheel
RUN apt-get update && \
    apt-get install -y gcc libffi-dev && \
    pip install --user --no-warn-script-location -r requirements.txt

# 第二阶段：运行
FROM python:3.10-slim

WORKDIR /app
# 只复制编译好的 wheel，不需要 gcc 等编译工具
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
CMD ["python", "app.py"]
```

**Node.js 应用的多阶段构建**：

```dockerfile
# 第一阶段：安装依赖并构建
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production    # 只安装生产依赖

# 第二阶段：运行
FROM node:18-alpine

WORKDIR /app
# 只复制 node_modules，不复制 package.json 的完整依赖树历史
COPY --from=builder /app/node_modules ./node_modules
COPY . .

CMD ["node", "server.js"]
```

### 6.4 多阶段构建和单阶段构建的对比

| 维度 | 单阶段构建 | 多阶段构建 |
|------|-----------|-----------|
| 镜像大小 | 大（包含构建工具） | 小（只包含运行时） |
| 构建速度 | 相同 | 相同（构建本身所需时间一样）|
| 安全性 | 低（攻击面大，包含额外工具） | 高（最小化运行环境） |
| Dockerfile 复杂度 | 低 | 中（需要组织多个阶段） |
| 调试便利性 | 可以直接进入容器调试 | 运行容器只有最终产物 |

**最佳实践**：生产环境总是使用多阶段构建。即使对于 Python 或 Node.js 这样的解释型语言，多阶段构建也能帮你保持镜像的精简（比如只保留 `node_modules` 的 production 依赖）。

---

## 七、Docker 存储：数据持久化的三种方式

### 7.1 理解容器的文件系统

回忆一下我们之前讲的：容器在镜像的只读层之上有一个可写层。但这个可写层有几个重要限制：

1. **容器删除后，可写层的数据随之消失**——没有持久化
2. **可写层和其他容器不共享**——容器 A 写入的文件，容器 B 看不到
3. **可写层的性能**受限于存储驱动（overlay2 等），在某些场景下不如直接写宿主机磁盘

因此，当我们需要**持久化数据**（数据库文件、日志）或**共享数据**（多个容器读写同一份文件）时，就需要使用 Docker 的存储机制。

Docker 提供了三种存储方式：

```
Docker 存储方式
├── Volume（卷）—— 由 Docker 管理，存储在 /var/lib/docker/volumes/
├── Bind Mount（绑定挂载）—— 挂载宿主机任意路径
└── tmpfs（临时文件系统）—— 存储在内存中
```

### 7.2 Volume（卷）— Docker 推荐的方式

**Volume 是什么**

Volume 是 Docker 完全管理的一种存储方式。数据存储在 Docker 主机上的特定目录（`/var/lib/docker/volumes/`），但对用户透明——你不需要关心具体存储在哪里，只需要知道 Volume 的名字。

```bash
# 创建一个 Volume
docker volume create my-data

# 查看 Volume 信息
docker volume inspect my-data
# → {
#     "Name": "my-data",
#     "Mountpoint": "/var/lib/docker/volumes/my-data/_data",
#     ...
#   }

# 使用 Volume 启动容器
docker run -v my-data:/app/data my-app
```

**Volume 的工作原理**：

```
宿主机文件系统                   容器
┌──────────────────┐          ┌──────────────────┐
│ /var/lib/         │          │                  │
│  docker/volumes/  │          │  容器的文件系统    │
│   my-data/_data/  │◄───────►│  /app/data/       │
│    └── file.txt   │  挂载   │   └── file.txt    │
└──────────────────┘          └──────────────────┘
```

**Key 特性**：

- Volume 由 Docker 管理，删除容器时 Volume 默认保留
- 多个容器可以挂载同一个 Volume
- Volume 支持驱动扩展（如 NFS Volume、云存储 Volume）
- 在 macOS/Windows 上性能更好（因为运行在 Linux VM 中）

**典型使用场景：数据库持久化**

```bash
# 启动 PostgreSQL，数据存储在 Volume 中
docker volume create pgdata
docker run -d \
  --name postgres \
  -v pgdata:/var/lib/postgresql/data \
  -e POSTGRES_PASSWORD=secret \
  postgres:15

# 即使容器被删除和重建，数据依然保留
docker rm -f postgres
docker run -d \
  --name postgres-new \
  -v pgdata:/var/lib/postgresql/data \  # ← 使用同一个 Volume
  postgres:15
# 所有数据都在！
```

### 7.3 Bind Mount（绑定挂载）— 直接挂载宿主机路径

**Bind Mount 是什么**

Bind Mount 直接将宿主机上的一个路径挂载到容器内的路径。你完全控制这个路径——你知道它在哪里，你可以直接在宿主机上修改它。

```bash
# 把宿主机的 /home/user/project 挂载到容器的 /app
docker run -v /home/user/project:/app my-app

# Docker 17.06+ 推荐的语法：
docker run --mount type=bind,source=/home/user/project,target=/app my-app
```

**Bind Mount 的工作原理**：

```
宿主机                          容器
┌──────────────────┐          ┌──────────────────┐
│ /home/user/       │          │                  │
│   project/        │◄───────►│  /app/            │
│    └── app.py     │  挂载   │   └── app.py     │
│    └── data/      │          │   └── data/      │
└──────────────────┘          └──────────────────┘
宿主机和容器共享同一个文件系统位置
```

**关键特性**：

- 路径由用户指定，不是 Docker 管理
- 宿主机的文件和容器内的文件是**同一份**——任何一方的修改都即时反映到另一方
- 适用于开发环境（热重载）和需要传递宿主机特定文件的场景

**典型使用场景：开发环境的热重载**

```python
# app.py — 一个简单的 Flask 应用
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello, Docker!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

```bash
# 把本地代码目录挂载到容器中
# 这样修改本地代码后，容器中的应用会自动重载（因为 debug=True）
docker run -d \
  -p 5000:5000 \
  -v $(pwd):/app \
  my-flask-app
```

你可以在宿主机上用编辑器修改 `app.py`，容器中的 Flask 开发服务器检测到文件变化后会自动重启。这比每次修改代码都重新构建镜像要高效得多。

### 7.4 Volume vs Bind Mount 的选择

| 维度 | Volume | Bind Mount |
|------|--------|-----------|
| 管理方式 | Docker 管理 | 用户管理 |
| 存储位置 | `/var/lib/docker/volumes/` | 用户指定的任意路径 |
| 备份/迁移 | 容易（`docker volume` 命令） | 需要手动操作 |
| 多容器共享 | 原生支持 | 也支持（同路径） |
| 开发热加载 | 不直接支持 | 原生支持 |
| 生产环境 | **推荐** | 仅限特定场景 |

**核心选择原则**：
- **生产环境**用 Volume——Docker 管理和备份更方便
- **开发环境**用 Bind Mount——热重载调试更方便
- **需要访问宿主机特定路径**（如 `/var/run/docker.sock`）用 Bind Mount

### 7.5 tmpfs — 内存中的临时存储

**tmpfs 是什么**

tmpfs 将数据存储在宿主机的内存中（而非磁盘），容器停止后数据自动清除。

```bash
docker run --tmpfs /app/temp my-app

# 推荐的语法：
docker run --mount type=tmpfs,destination=/app/temp my-app
```

**关键特性**：

- **速度快**：内存的读写速度比磁盘快几个数量级
- **临时性**：容器停止后数据消失
- **不持久化**：不能用于需要长期存储的数据
- **受内存限制**：受 Docker 的内存限制影响（`--memory` 参数）

**典型场景**：

1. **敏感信息**：密码文件、密钥等，只在容器运行期间存在，停止后自动清除——比写入磁盘更安全
2. **高性能临时文件**：应用的缓存、日志（如果不需要持久化日志）
3. **大量小文件的临时处理**：图片处理、数据转换的中间结果

```bash
# 使用 tmpfs 存储临时缓存
docker run -d \
  --name nginx \
  --mount type=tmpfs,destination=/var/cache/nginx \
  nginx:latest
```

### 7.6 Docker 存储的完整对比

| 特性 | Volume | Bind Mount | tmpfs |
|------|--------|-----------|-------|
| 数据存储位置 | Docker 管理区域 | 宿主机任意路径 | 内存 |
| 容器删除后数据 | **保留** | 保留 | **消失** |
| 共享到宿主机 | 难直接访问 | 直接访问 | 不可访问 |
| 共享到其他容器 | 容易 | 容易 | 不能 |
| 持久化 | 是 | 是 | 否 |
| 性能 | 磁盘级 | 磁盘级 | 内存级 |
| 适用场景 | 数据库文件、持久化数据 | 开发调试、配置文件注入 | 敏感信息、临时缓存 |

### 7.7 如何选择存储方式——一个决策流程

```
数据需要持久化？
├── 是 → 容器停止后数据还要保留？
│   ├── 是 → 生产环境？
│   │   ├── 是 → Volume
│   │   └── 否 → Bind Mount（开发方便）
│   └── 否 → 数据需要共享到宿主机？
│       ├── 是 → Bind Mount
│       └── 否 → Volume
└── 否 → 数据是敏感信息？
    ├── 是 → tmpfs
    └── 否 → 直接写在容器层（简单场景）
```

---

## 八、Docker Compose：多容器应用的定义和编排

### 8.1 为什么需要 Docker Compose

一个典型的现代应用很少只有一个容器：

- **Web 应用容器**：跑你的应用代码
- **数据库容器**：PostgreSQL 或 MySQL
- **缓存容器**：Redis
- **消息队列容器**：RabbitMQ 或 Kafka
- **反向代理容器**：Nginx

如果只用 `docker run`，你需要手动管理每个容器的启动命令、网络连接、Volume 挂载、环境变量。一个包含 5 个服务的应用可能需要执行 15-20 条 `docker run` 命令，每条命令长达几行，而且**你必须按正确的顺序启动**（先启动数据库，再启动依赖数据库的应用）。

Docker Compose 就是为了解决这个问题而生的：**用声明式的方式定义整个应用的多容器架构，一条命令启动所有服务**。

### 8.2 Docker Compose 的核心文件：docker-compose.yml

看一个典型的例子——一个带 Redis 缓存的 Web 应用：

```yaml
version: '3.8'                  # Compose 文件格式版本

services:                        # 定义所有服务（容器）
  web:                           # 服务名：web
    build: .                     # 从当前目录的 Dockerfile 构建
    ports:
      - "8000:8000"              # 端口映射：宿主机:容器
    depends_on:
      - redis                    # 先启动 redis，再启动 web
    environment:
      - REDIS_HOST=redis         # 环境变量（服务名就是主机名）
      - REDIS_PORT=6379

  redis:                         # 服务名：redis
    image: redis:7-alpine        # 从镜像启动（非构建）
    volumes:
      - redis_data:/data         # 使用 Volume 持久化数据
    restart: always              # 自动重启

volumes:                         # 声明 Volume
  redis_data:
```

启动这个应用只需要一条命令：

```bash
# 启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f web

# 停止所有服务
docker compose down

# 停止并删除 Volume
docker compose down -v
```

### 8.3 docker-compose.yml 的核心配置项详解

#### services — 服务的定义

每个服务对应一个容器。服务名既是服务的标识，也充当了**DNS 主机名**——在一个 Compose 项目中，服务可以通过服务名互相访问。

```yaml
services:
  web:
    # 构建相关
    build:
      context: .                # 构建上下文目录
      dockerfile: Dockerfile    # Dockerfile 路径
      args:                     # 构建参数
        NODE_ENV: production

    # 镜像相关
    image: myapp:latest         # 使用现有镜像（不构建）

    # 网络相关
    ports:
      - "80:80"                 # 宿主机端口:容器端口
      - "443:443"

    # 环境变量
    environment:
      - DB_HOST=mysql
      - DB_PASSWORD=secret123
    env_file:
      - ./config/db.env         # 从文件加载环境变量

    # 存储相关
    volumes:
      - web_data:/var/www/html  # 使用 Volume
      - ./config:/etc/app/config:ro  # Bind Mount（只读，加 :ro）

    # 依赖关系
    depends_on:
      - db
      - cache

    # 健康检查
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

    # 资源限制
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

#### networks — 网络配置

默认情况下，Compose 会为你创建项目专属的网络。所有在同一个 Compose 文件中的服务通过服务名互相通信。你也可以自定义网络：

```yaml
services:
  web:
    networks:
      - frontend
      - backend

  api:
    networks:
      - backend

  db:
    networks:
      - backend

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
```

**为什么需要多个网络？** 这是**网络隔离**的最佳实践。上例中：
- `frontend` 网络：Web 服务可以访问
- `backend` 网络：API + 数据库服务可以访问

如果 Web 服务被入侵，它在 `frontend` 网络上无法直接访问数据库（因为数据库不在 `frontend` 网络上）。这就像一个三层架构——外部层、应用层、数据层。

#### volumes — 持久化存储声明

```yaml
services:
  mysql:
    image: mysql:8
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:              # 声明 Volume（Docker 自动管理）
  backup_data:
    driver: local
    driver_opts:
      type: none
      device: /mnt/backup
      o: bind
```

#### 其他常用配置

```yaml
services:
  web:
    restart: always              # 崩溃后自动重启
                                # 可选: no, always, on-failure, unless-stopped

    command: python app.py      # 覆盖 Dockerfile 中的 CMD

    entrypoint: /entrypoint.sh  # 覆盖 Dockerfile 中的 ENTRYPOINT

    logging:
      driver: "json-file"       # 日志驱动
      options:
        max-size: "10m"         # 每个日志文件最大 10MB
        max-file: "3"           # 最多保留 3 个日志文件
```

### 8.4 Docker Compose 的常用命令

```bash
# 启动所有服务（前台，日志实时显示）
docker compose up

# 后台启动
docker compose up -d

# 停止所有服务
docker compose down

# 只重新构建并启动某个服务
docker compose up -d --build web

# 查看服务日志
docker compose logs
docker compose logs -f web      # -f 实时跟踪

# 在运行中的容器内执行命令
docker compose exec web bash

# 查看服务状态
docker compose ps

# 拉取所有镜像
docker compose pull

# 停止但不删除容器
docker compose stop

# 重启所有服务
docker compose restart

# 查看服务依赖图
docker compose images
```

### 8.5 Docker Compose 的开发/生产环境配置

Compose 支持多配置文件合并，让你可以为开发和生产环境使用不同的配置：

```yaml
# docker-compose.yml — 公共配置
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=production
```

```yaml
# docker-compose.override.yml — 开发环境覆盖（自动加载）
services:
  web:
    volumes:
      - .:/app         # 开发环境：挂载源码实现热重载
    environment:
      - APP_ENV=development
      - DEBUG=true
    ports:
      - "8000:8000"
      - "5678:5678"    # 调试器端口
```

```bash
# 开发环境（自动加载 override 文件）
docker compose up -d

# 生产环境（显式指定配置文件）
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 8.6 完整的应用示例：一个博客系统

让我们用一个完整的例子来串联学到的知识：

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - static_files:/static
    depends_on:
      - web
    networks:
      - frontend

  # Django Web 应用
  web:
    build: ./app
    expose:
      - "8000"                 # 只在内部网络暴露，不对外
    volumes:
      - static_files:/app/static
      - ./app:/app             # 开发用 Bind Mount
    environment:
      - DB_HOST=postgres
      - REDIS_HOST=redis
      - DJANGO_SETTINGS_MODULE=config.settings
    depends_on:
      - postgres
      - redis
    networks:
      - frontend
      - backend

  # 数据库
  postgres:
    image: postgres:15-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=blog
      - POSTGRES_USER=bloguser
      - POSTGRES_PASSWORD=${DB_PASSWORD:-changeme}  # 从 .env 文件读取
    networks:
      - backend
    restart: always

  # 缓存
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - backend

volumes:
  pgdata:
  redis_data:
  static_files:

networks:
  frontend:
  backend:
```

对应的 `.env` 文件：

```
DB_PASSWORD=my_secure_password_2026
```

**这个部署方案的架构图**：

```
用户请求
    │
    ▼
┌─────────┐    port 80    ┌──────────────────────┐
│  用户    │────────────→  │  Nginx（反向代理）    │
└─────────┘              │  ▪ 静态文件服务        │
                         │  ▪ 请求转发到 Web     │
                         └──────┬───────────────┘
                                │  frontend 网络
                                ▼
                         ┌──────────────────────┐
                         │  Django Web 服务      │
                         │  ▪ 处理业务逻辑       │
                         │  ▪ 渲染模板            │
                         └──┬──────────────┬────┘
                            │              │
                    backend │ 网络         │
                            ▼              ▼
                   ┌──────────────┐  ┌──────────┐
                   │  PostgreSQL   │  │   Redis  │
                   │  (持久化存储)  │  │  (缓存)  │
                   └──────────────┘  └──────────┘
```

### 8.7 Docker Compose vs Docker run —— 什么时候用什么

| 场景 | 使用方式 | 原因 |
|------|---------|------|
| 单个简单容器测试 | `docker run` | 不需要写配置文件 |
| 多个容器的应用 | Docker Compose | 声明式管理，一条命令启动全部 |
| 生产环境单机部署 | Docker Compose | 简单可靠，自带健康检查和重启 |
| 生产环境多机集群 | Kubernetes / Docker Swarm | Compose 不跨节点 |
| CI/CD 测试环境 | Docker Compose | 快速拉起测试环境，用完即毁 |

---

## 九、Docker 核心概念速查

| 概念 | 一句话理解 | 关键特性 |
|------|-----------|---------|
| **镜像（Image）** | 应用的只读模板 + 完整运行环境 | 分层构建、不可变、可分发 |
| **容器（Container）** | 镜像的运行实例 | 隔离的进程、有可写层、临时性 |
| **Volume** | Docker 管理的持久化数据 | 独立于容器生命周期、可备份 |
| **Bind Mount** | 挂载宿主机目录到容器 | 实时同步、开发调试利器 |
| **tmpfs** | 内存中的临时文件 | 高速、临时、安全 |
| **Dockerfile** | 镜像构建说明书 | 声明式构建指令 |
| **Docker Compose** | 多容器应用编排工具 | 声明式定义、一键部署 |

---

## 十、Docker 设计哲学总结

Docker 的设计可以用三个关键词概括：

**1. 一次构建，到处运行**

这是 Docker 最核心的价值主张。通过将应用和环境打包成镜像，Docker 消除了"在我的机器上能跑"的问题。开发环境、测试环境、生产环境使用同一份镜像，部署不再依赖特定的操作系统版本或系统库。

**2. 单一职责，进程隔离**

每个容器只运行一个进程（或一组紧密耦合的进程）。这符合微服务的设计理念——每个服务独立部署、独立扩展、独立升级。当一个服务出问题时，不会影响其他服务。

**3. 不可变基础设施**

Docker 镜像一旦构建，就不应该被修改。如果代码需要更新，你应该**重新构建镜像**而不是"进入容器修改"。这听起来更麻烦，但实际上更可靠——因为每次部署都基于新的镜像，不会出现"那台服务器上有人手动改过配置文件"这种无法复现的问题。

在实际操作中，这意味着：
- 不要手动进入容器修改文件（`docker exec -it container bash`）
- 配置文件通过环境变量或 Config Volume 注入
- 每次代码变更都通过 CI/CD 构建新镜像
- 日志输出到 stdout/stdout（而非文件），由 Docker 收集

---

## 相关章节

学习完 Docker，你可以继续阅读：
- [第三部分：Linux 从零到驾驭](03_linux从零到驾驭.md) — 理解 Namespace、Cgroups 的底层实现
- [第四部分：Redis 从零到实战](04_redis从零到实战.md) — 容器化部署 Redis 的最佳实践

---
