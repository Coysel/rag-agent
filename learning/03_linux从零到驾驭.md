# 第十一部分：Linux 基础

> **学习目标**：这一部分的目标是让你真正理解 Linux——不再把它当作一个"黑乎乎的命令行窗口"，而是理解文件系统怎么组织数据、权限系统为什么存在、进程如何被管理、以及 Shell 为什么能成为工程师最强大的工具。学完之后，你应该能回答"为什么 Linux 一切皆文件"、"权限 755 和 644 分别代表什么"、"管道是怎么把两个程序连起来的"以及"进程被杀掉时到底发生了什么"这类深层问题。

---

## 一、Linux 概述——为什么 Linux 统治了服务器世界

### 1.1 操作系统是什么——Linux 在其中的角色

要理解 Linux，先要理解它在一个计算机系统中扮演的角色。整个计算机系统可以看作四层结构：

```
应用程序（浏览器、游戏、Python 脚本）
      ↑  系统调用（System Call）接口
操作系统内核（Linux Kernel）
      ↑  驱动程序
硬件（CPU、内存、硬盘、网卡）
```

**操作系统（Operating System）** 是位于硬件和应用程序之间的软件层。它的核心职责有两项：

1. **管理硬件资源**：CPU 时间怎么分配给各个程序、内存怎么分配和回收、硬盘怎么读写——这些都是操作系统在背后打理
2. **为应用程序提供抽象**：你的程序不需要知道硬盘的具体型号和接口规范，只需要调用 `open()`、`read()`、`write()` 这些系统调用，操作系统会跟硬件打交道

**Linux** 就是一个操作系统——更准确地说，它是一个**操作系统内核**。你平时说的"Ubuntu"、"CentOS"是**发行版**，它们 = Linux 内核 + 一堆预装的软件和应用。

### 1.2 Linux 的设计哲学——为什么它如此成功

Linux 继承了 Unix 的设计哲学，这些哲学指导了它 30 多年的发展：

**哲学一：一切皆文件**

这是 Linux 最核心的设计思想。在 Linux 里，普通文件是文件，目录是文件，硬盘是文件（`/dev/sda`），键盘是文件（`/dev/input/event0`），网络连接是文件（socket），甚至正在运行的进程信息也是文件（`/proc/1234/status`）。

为什么这样做？因为如果一切都是文件，那么操作一切都可以用同一套 API——`open()`、`read()`、`write()`、`close()`。你的程序不需要为键盘写一套读写逻辑，为硬盘写另一套，为网络又写一套。统一的接口极大简化了软件设计。

**哲学二：每个程序只做一件事，并把这件事做好**

Linux 的命令行工具都是"小工具"：`ls` 只负责列出文件，`grep` 只负责搜索文本，`sort` 只负责排序。但通过管道（`|`），你可以把这些小工具像积木一样组合起来，完成复杂的任务。这比一个大而全的"全能工具"灵活得多。

**哲学三：一切配置都是文本**

在 Linux 里，配置文件是文本文件（放在 `/etc/` 下），硬件信息是文本（`/proc/` 下的文件），日志也是文本。文本是人类可读、可编辑、可以用 `grep` 搜索的。这在 1970 年代是革命性的想法。对比之下，Windows 的注册表是二进制结构，很难直接用文本工具处理。

### 1.3 内核 vs 发行版——理清这两个概念

很多人说"我用的是 Linux"，但其实更准确的说法是"我用的是 Ubuntu（Linux 发行版）"。

| 概念 | 是什么 | 类比 |
|------|--------|------|
| **Linux 内核** | 操作系统的核心，管理 CPU、内存、设备驱动 | 汽车的发动机 |
| **发行版（Distribution）** | 内核 + 包管理器 + 桌面环境 + 应用软件 | 整个汽车（发动机 + 车身 + 内饰） |

Ubuntu、Debian、CentOS、Fedora、Arch Linux 都是发行版，它们都使用 Linux 内核，区别在于：
- 预装了什么软件（桌面环境、办公软件等）
- 用什么包管理器（apt、yum、pacman）
- 更新策略（激进更新如 Arch，保守稳定如 Debian）
- 社区和支持（Ubuntu 文档最全，CentOS 企业支持最好）

**你只需要掌握 Linux 命令和概念，换发行版就像换手机壳——本质没变。**

### 1.4 为什么服务器都用命令行而不是图形界面

当你第一次面对黑乎乎的终端时会想：为什么不能像 Windows 一样点鼠标？

```
图形界面（GUI）:  点来点去，一次只能做一件事，难以自动化
命令行（CLI）:    敲命令，一次可以做一百台服务器，全自动
```

想象一下：你的老板说"给 50 台服务器装 Python 3.12 并配置防火墙"。用图形界面的话，你需要远程桌面到每一台，点开浏览器下载安装包，点下一步、下一步……几个小时过去了。

用命令行，你写一个脚本：

```bash
for server in server{01..50}; do
    ssh "$server" "apt update && apt install -y python3.12 && ufw enable && ufw allow 22,80,443/tcp"
done
```

这一行命令（加上 SSH 密钥认证）在 5 分钟内完成所有 50 台服务器的配置。这就是命令行不可替代的原因——**可组合、可脚本化、可批量执行**。

---

## 二、文件系统——一切皆文件的哲学实践

### 2.1 什么是文件系统

**文件系统（Filesystem）** 是操作系统用来组织和管理存储在硬盘上的数据的方式。它定义了：

- 数据怎么存储在硬盘的物理扇区上
- 目录和文件怎么组织成树形结构
- 文件的元信息（创建时间、权限、所有者）存在哪里

Linux 支持多种文件系统：ext4（最常用）、XFS（适合大文件）、Btrfs（支持快照）、ZFS（企业级）。但不管底层是哪种文件系统，你看到的都是统一的树形目录结构——这就是 "一切皆文件" 设计的具体体现。

### 2.2 目录结构——从根开始的一棵树

Linux 的目录结构是一个从 `/` 开始的树：

```
/                       ← 根目录：一切从这里开始
├── home/               ← 用户目录（你的私人空间）
│   └── yourname/       ← 你的家目录，~ 的快捷方式指向这里
├── etc/                ← 配置文件（改端口、改密码都在这里操作）
├── var/                ← 变动数据（日志、数据库文件、邮件）
│   └── log/            ← 系统日志存放处
├── tmp/                ← 临时文件，系统重启时会清空
├── usr/                ← 你安装的软件（Unix System Resources）
│   ├── bin/            ← 用户可用的程序
│   └── lib/            ← 程序的库文件
├── bin/                ← 系统基础命令（ls、cp、mv 等）
├── sbin/               ← 系统管理命令（需要 root 权限）
├── dev/                ← 设备文件（硬盘、键盘、鼠标都是"文件"）
├── proc/               ← 虚拟文件系统（进程信息、内存状态，存在内存里）
└── opt/                ← 第三方大型软件（如数据库、IDE）
```

**每个目录为什么放在这里？**

- `/etc` 放配置：当一个程序需要读取配置时，它去 `/etc` 下找。这种约定让管理员知道"改配置就去 `/etc` 找"。
- `/var/log` 放日志：如果系统出了问题，你第一件事就是去 `/var/log` 翻日志。
- `/proc` 是虚拟的：它不占据任何硬盘空间，里面的文件是内核实时生成的，反映系统的当前状态。

### 2.3 绝对路径与相对路径

当你定位文件时，有两种方式指定它的位置：

```bash
# 绝对路径：从根目录 / 开始，完整描述文件位置
/home/blue/projects/mycode.py

# 相对路径：从当前目录开始描述
./mycode.py          # . 代表当前目录
../other/file.txt    # .. 代表上一级目录
~/downloads          # ~ 代表当前用户的家目录
```

**为什么需要这两种路径？** 绝对路径在任何环境下都有效——不管你的当前目录在哪里，`/home/blue/projects/mycode.py` 始终指向同一个文件。相对路径更短、更便于人阅读，但依赖于"你当前在哪个目录"，适合在脚本和日常操作中使用。

常用路径操作命令：

```bash
pwd              # Print Working Directory：显示你当前所在的目录
cd /etc/nginx    # Change Directory：进入 /etc/nginx 目录
cd ~             # 回到自己的家目录
cd -             # 回到上一个目录（很实用，在两个目录间快速切换）
```

### 2.4 文件操作命令——不是背命令，是理解模式

文件操作其实只有四类：**查看、创建、复制/移动、删除**。每个类做了什么事、有什么变体，理解了模式就自然记住了。

```bash
# 查看
ls                # 列出当前目录的内容
ls -l             # 长格式：显示权限、所有者、大小、修改时间
ls -la            # 包含隐藏文件（以 . 开头的文件）
ls -lh            # 大小以人类可读方式显示（1K、2M、3G 而非字节数）

# 创建
touch newfile.txt       # 创建空文件（若文件已存在，只更新其修改时间）
mkdir newfolder         # 创建新目录
mkdir -p a/b/c          # 创建嵌套目录：如果 a 不存在，自动创建 a，再创建 a/b，再创建 a/b/c

# 复制和移动
cp source.txt dest.txt           # 复制文件
cp -r sourcedir/ destdir/        # 递归复制目录（-r = recursive）
mv oldname.txt newname.txt       # 移动或重命名（同一个目录下 mv = 重命名）
mv file.txt /tmp/                # 移动到不同目录

# 删除（⚠️ 不可逆）
rm file.txt                      # 删除文件
rm -r dir/                       # 递归删除目录及其内容
rm -rf dir/                      # 强制递归删除（不提示，极危险！）

# 查看文件内容
cat file.txt                     # 打印整个文件到终端（适合小文件）
less file.txt                    # 分页查看（按 q 退出，按 / 搜索，按 n 跳到下一个匹配）
head -20 file.txt                # 只看前 20 行
tail -20 file.txt                # 只看后 20 行
tail -f app.log                  # 实时跟踪日志追加（调试 Web 服务时最常用的命令之一）
wc -l file.txt                   # 统计文件行数
```

**为什么 `rm -rf /` 是危险的？** 因为 `/` 是根目录，包含整个系统。`rm -rf /` 会从根目录开始递归删除所有文件——包括系统文件。一旦执行，系统将不可用。不要在任何不理解的命令中尝试这个。

### 2.5 硬链接与软链接——两个不同的"指向"

Linux 中，一个"文件名"实际上只是一个指向硬盘上数据的指针。当你创建一个文件时，实际上做了两件事：

1. 在硬盘上分配数据块（存文件内容）
2. 在目录中创建一个"文件名 → 数据块"的映射

**硬链接（Hard Link）**：创建另一个指向同一数据块的文件名

```bash
ln original.txt hardlink.txt
# 现在 original.txt 和 hardlink.txt 指向硬盘上的同一份数据
# 删除其中一个，另一个依然可以访问数据
# 只有最后一个指向该数据的链接被删除时，数据才真正被释放
```

硬链接有两个限制：
- 不能跨文件系统（不同硬盘分区的数据块不能用同一个名字空间寻址）
- 不能指向目录（避免循环引用）

**软链接（Symbolic Link / Symlink）**：创建指向另一个文件名的"快捷方式"

```bash
ln -s /path/to/original.txt symlink.txt
# symlink.txt 只记录了一个路径字符串："/path/to/original.txt"
# 如果你删除了 original.txt，symlink.txt 就变成了"断链"——指向一个不存在的文件
```

**为什么区分硬链接和软链接？** 硬链接更"底层"——它直接共享数据块，删除一个不影响另一个。软链接更像是"引用"——它只是存了一个路径，原文件没了链接就断了。在日常使用中，软链接更常见（比如把 `/etc/nginx/sites-available/myapp` 链接到 `/etc/nginx/sites-enabled/`）。

---

## 三、权限模型——多用户系统的安全基石

### 3.1 为什么需要权限

Linux 从诞生之初就是**多用户系统**——多个人可以同时登录同一台服务器。如果没有权限控制，就会出现：

- 用户 A 删除了用户 B 的文件
- 任何人可以修改系统配置文件（如 `/etc/passwd`，存着所有用户的密码）
- 任何人都可以执行危险命令

权限系统的核心目的就是回答三个问题：**谁**能对**什么文件**做**什么操作**。

### 3.2 rwx 模型——三位一体的权限设计

执行 `ls -l` 会看到每行开头有 10 个字符：

```bash
$ ls -l
-rwxr-xr-x  1 alice  staff  2048 Jun 27 10:30  script.sh
drw-r--r--  2 bob    dev    4096 Jun 27 09:15  project/
```

第一个字符表示文件类型：`-` 是普通文件，`d` 是目录，`l` 是软链接，`c` 是字符设备（如键盘），`b` 是块设备（如硬盘）。

后面 9 个字符分为三组，每组三个字符，代表三种权限：

```
-  rwx  r-x  r-x
│  ─┬─  ─┬─  ─┬─
│   │    │    └── Others（其他人）：既不是主人也不在组的用户
│   │    └───── Group（组）：与文件所属组相同的用户
│   └───────── Owner（主人）：文件的所有者
└── 文件类型
```

每组中三个字母的含义：

| 字母 | 含义 | 对文件的意义 | 对目录的意义 |
|------|------|-------------|-------------|
| `r` | read (读) | 可以查看文件内容 | 可以列出目录中有哪些文件 |
| `w` | write (写) | 可以修改文件内容 | 可以在目录中创建/删除文件 |
| `x` | execute (执行) | 可以执行文件（如果是脚本或程序） | 可以进入目录（`cd` 进入） |

**目录的 x 权限常常被误解。** 如果你没有 x 权限但有 r 权限，你可以看到目录里有哪些文件，但不能进入目录（`cd` 失败），也不能访问里面的任何文件。反之，如果你有 x 但没有 r，你可以进入目录并根据文件名访问已知的文件，但不能列出目录中的文件列表。

### 3.3 权限的数字表示——为什么 755 代表 rwxr-xr-x

每个权限位可以用一个二进制位表示：`r=4`、`w=2`、`x=1`。这三种权限值相加得到 0-7 的数字：

```
权限   二进制  十进制  意义
---    000     0      没有任何权限
--x    001     1      仅执行
-w-    010     2      仅写入
-wx    011     3      写入+执行
r--    100     4      仅读取
r-x    101     5      读取+执行
rw-    110     6      读取+写入
rwx    111     7      读取+写入+执行
```

所以 `755` 是三个八进制数字的拼接：**owner=7 + group=5 + others=5** = rwxr-xr-x

常见的权限组合：

| 权限 | 数字 | 使用场景 |
|------|------|---------|
| `rwx------` | 700 | 私密脚本，只有自己能执行 |
| `rwxr-xr-x` | 755 | 可执行程序，别人可以执行但不能修改 |
| `rw-r--r--` | 644 | 普通文本文件，自己编辑，别人只能读 |
| `rw-------` | 600 | SSH 私钥、密码文件等高度敏感内容 |
| `rw-rw----` | 660 | 团队协作文件，同组可编辑，其他人不可见 |

### 3.4 chmod——修改权限

`chmod`（change mode）有两种模式：数字模式和符号模式。

```bash
# 数字模式（推荐，精确无误）
chmod 755 script.sh     # rwxr-xr-x
chmod 644 readme.md     # rw-r--r--
chmod 600 id_rsa        # rw-------（SSH 私钥必须是 600，否则 SSH 会拒绝使用）
chmod 700 private/      # drwx------（私人目录）

# 符号模式（直觉式，小改动方便）
chmod +x script.sh      # 给所有用户加上执行权限（等价于 a+x）
chmod u+w file.txt      # 给所有者（user）加上写权限
chmod g-r file.txt      # 从组（group）移除读权限
chmod o-w file.txt      # 从其他人（others）移除写权限
chmod u=rwx,g=rx,o=r    # 精确设置每组的权限（等价于 754）
```

> **为什么建议不要用 777？** `chmod 777 file` 让所有人——包括你的服务器上的其他用户、可能被黑客利用的恶意程序——都可以读写执行这个文件。这个等于打开了你家大门并贴了"随便进"的告示。最合适的权限是最小权限——只给完成任务所需的最小权限。

### 3.5 chown——改变文件的所有者

```bash
chown alice file.txt              # 把文件所有者改为 alice
chown alice:dev file.txt          # 把所有者改为 alice，组改为 dev
chown :dev file.txt               # 只改组不改所有者
chown -R alice:dev project/       # 递归修改整个目录及其所有内容
```

**什么时候需要 chown？** 当你用 `sudo` 安装软件或创建文件后，这些文件的所有者通常是 root。如果你需要用普通用户来操作这些文件，就需要 `chown` 来更改所有者。例如：你的 Web 应用需要写日志文件，而这个文件是 root 创建的，你就需要 `chown www-data:www-data /var/log/myapp/`。

### 3.6 默认权限与 umask

当你创建一个新文件或目录时，它的默认权限不是 666（文件）或 777（目录），而是减去 umask 值。

```bash
umask      # 查看当前的 umask 值（通常 022）
```

umask = 022 的含义：
- 新建文件：666 - 022 = 644（rw-r--r--）
- 新建目录：777 - 022 = 755（rwxr-xr-x）

为什么文件默认没有 x 权限？出于安全考虑——大多数文件不是可执行程序，如果自动加了执行权限，意外执行的风险会增加。如果你需要可执行文件，用 `chmod +x` 手动添加。

---

## 四、进程管理——程序是如何"活"起来的

### 4.1 从程序到进程——代码变成活着的"生命"

**程序** 是一个静态的概念——它是硬盘上的一堆二进制指令（一个文件）。**进程** 是动态的概念——是程序被加载到内存并开始执行后的"活体"。

```
程序（/usr/bin/python3）──(被加载执行)──→ 进程（PID=12345）
    硬盘上躺着                          内存中跑着
    不占 CPU                            占用 CPU 和内存
    是一个文件                           有自己的"生命"状态
```

每个进程有一个唯一的数字标识：**PID（Process ID）**。操作系统通过 PID 来追踪和管理每一个进程。

你之前在操作系统的学习中知道，每个进程拥有独立的虚拟地址空间、文件描述符表、信号处理方式等。Linux 中的进程管理就是围绕这些资源展开的。

### 4.2 查看进程——知道系统在干什么

```bash
ps aux                    # 查看当前所有进程的快照
```

这行命令的每个参数都有含义：
- `a`：显示所有用户的所有进程（不只是当前用户）
- `u`：以用户为中心的格式显示（包含 CPU 和内存使用率）
- `x`：显示没有控制终端的进程（后台守护进程）

输出示例（每列的含义）：
```
USER       PID  %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1   0.0  0.3 168496 11316 ?        Ss   Jun27   0:23 /sbin/init
alice     1234   0.1  2.1 302456 87000 ?        Sl   10:30   0:45 python server.py
```

| 列名 | 含义 |
|------|------|
| USER | 运行这个进程的用户 |
| PID | 进程的唯一 ID |
| %CPU | CPU 占用百分比 |
| %MEM | 内存占用百分比 |
| VSZ | 虚拟内存大小（KB） |
| RSS | 实际物理内存大小（KB） |
| TTY | 终端类型（`?` 表示没有终端，通常是守护进程） |
| STAT | 进程状态（R=运行，S=休眠，D=不可中断睡眠，Z=僵尸，<为高优先级） |
| START | 启动时间 |
| TIME | 占用的 CPU 总时间 |
| COMMAND | 启动命令 |

`ps` 和操作系统中讲的 PCB（进程控制块）是什么关系？**`ps aux` 的输出内容，其实就是从每个进程的 PCB 中提取关键字段展示给你看。** 你看到的每一行，对应内核中一个 PCB 结构体的数据。

```bash
# 其他常用的进程查看方式
ps aux | grep python       # 结合管道，过滤出含 python 的进程
top                        # 实时进程监视器（按 q 退出，按 P 按 CPU 排序，按 M 按内存排序）
htop                       # top 的彩色增强版（需要额外安装，交互更友好）
```

**`top` 和 `ps` 有什么区别？** `ps` 是"在某一时刻拍一张快照"——你看的是那个瞬间的状态。`top` 是"持续监控"——每隔几秒刷新一次，你可以实时看到 CPU 和内存的变动。

### 4.3 信号与 kill——进程间通信的原语

`kill` 这个名字有误导性——它字面意思是"杀死"，实际上它的作用是**给进程发送一个信号**。有些信号会终止进程，有些只是通知进程某件事发生了。

```bash
kill 1234                  # 默认发送 SIGTERM(15)：请进程"优雅地"退出
kill -9 1234               # 发送 SIGKILL(9)：强制杀死，进程无法抗拒
kill -15 1234              # 明确发送 SIGTERM（和 kill 1234 等价）
kill -2 1234               # 发送 SIGINT(2)：等于按了 Ctrl+C
kill -1 1234               # 发送 SIGHUP(1)：让进程重新加载配置文件
killall python             # 杀死所有名为 python 的进程
pkill -f "python server"   # 按命令行字符串匹配杀死进程
```

| 信号 | 编号 | 发送方式 | 进程能否处理 | 含义 |
|------|------|---------|------------|------|
| SIGHUP | 1 | 终端断开 | 可以 | 通知进程终端挂了，通常是让进程重新加载配置 |
| SIGINT | 2 | Ctrl+C | 可以 | 中断进程——用户主动中断 |
| SIGKILL | 9 | `kill -9` | **不能** | 强制杀死——内核直接终止进程，不给它清理资源的机会 |
| SIGTERM | 15 | `kill` | 可以 | 请求终止——程序收到后可以保存数据、释放资源再退出 |

**为什么需要不同的信号？** SIGTERM（15）是"礼貌请求"——程序收到后可以执行清理代码（关闭文件、释放内存、保存状态），然后优雅退出。但如果程序卡死了（死循环），它无法响应 SIGTERM，这时候 SIGKILL（9）是最后的手段——内核直接将其移除，但进程没有机会做任何清理。

**进程被 SIGKILL 时到底发生了什么？** 操作系统直接将进程从进程表中移除，回收它占用的所有资源（文件描述符、内存页、信号处理程序等）。因为这个过程是内核完成的，不需要进程的配合。

### 4.4 前台与后台——终端下的多任务

当你直接在终端运行程序时，它默认是**前台**进程——终端被"占住"，直到程序结束才能输入下一条命令。

```bash
# 前台运行
python server.py
# 终端被占住了，没法做其他操作，按 Ctrl+C 终止

# 后台运行（加 &）
python server.py &
# 终端立即返回，可以继续敲其他命令

# 查看后台任务
jobs
# 输出: [1]+  Running                 python server.py &

# 把后台任务拉到前台
fg %1                    # 将编号为 1 的后台任务移到前台

# 挂起前台任务
# 按 Ctrl + Z   → 暂停当前前台任务

# 把挂起的任务放后台继续跑
bg                       # 将刚刚挂起的任务放到后台继续执行
```

**`&` vs `nohup` —— 有什么区别？**

```bash
python server.py &              # 后台运行，但关掉终端进程会被杀
nohup python server.py &        # 后台运行，关掉终端后进程继续运行
```

为什么关掉终端后台进程也会被杀？当你通过 SSH 连接到服务器时，你启动的进程是当前终端的"子进程"。当 SSH 连接断开（终端关闭）时，系统会给这个终端下的所有进程发送 SIGHUP 信号，默认行为是终止进程。

`nohup`（no hangup）的作用就是让进程**忽略 SIGHUP 信号**——即使关掉终端，进程依然运行。

### 4.5 环境变量——进程的"全局配置"

每个进程启动时都会继承一个环境变量表——一组键值对，影响着进程的行为：

```bash
env               # 查看当前 Shell 的所有环境变量
echo $HOME        # 查看 HOME 变量的值（/home/alice）
echo $PATH        # 查看 PATH 的值——可执行文件的搜索路径
echo $SHELL       # 查看当前使用的 Shell（/bin/bash）

# 临时设置环境变量（仅当前会话有效）
export MY_VAR="hello world"

# 临时设置只在单条命令生效
DB_HOST=localhost python app.py   # DB_HOST 这个变量只在这条命令的环境中存在
```

**PATH 是什么，为什么它如此重要？** 当你输入 `python` 并按回车，Shell 会在 PATH 变量列出的目录中逐个搜索名为 `python` 的可执行文件。PATH 通常包含 `/usr/local/bin:/usr/bin:/bin` 等目录。

```
输入 python
   ↓
Shell 检查 /usr/local/bin 中是否有 python
   ↓
Shell 检查 /usr/bin 中是否有 python
   ↓
Shell 检查 /bin 中是否有 python
   ↓
如果都没有 → "command not found"
```

这就是为什么有时安装了一个程序但运行提示"找不到"——通常是因为它安装在 PATH 没有包含的目录中。

**如何让环境变量永久生效？** `export` 命令只在当前会话有效。要让变量每次登录都自动设置，需要把它写入 Shell 的配置文件中：

```bash
echo 'export MY_VAR="hello"' >> ~/.bashrc   # 追加到 .bashrc
source ~/.bashrc                             # 让修改立即生效
```

---

## 五、Shell——命令行真正的力量

### 5.1 Shell 到底是什么

Shell 本质上是一个**命令解释器**——它读取你输入的文本，解析成命令，交给操作系统执行，然后把结果返回给你。

```
你输入 "ls -l /home"
      ↓
Shell 解析：命令 = "ls"，参数 = ["-l", "/home"]
      ↓
Shell 调用 fork() 创建子进程，通过 execve() 加载 /bin/ls 程序
      ↓
/bin/ls 执行，返回结果
      ↓
Shell 把结果打印到终端
```

最常见的 Shell 是 **Bash（Bourne Again SHell）**，它是大多数 Linux 发行版的默认 Shell。其他 Shell 还有 Zsh（macOS 默认、支持更好的自动补全）、Fish（开箱即用，对新手友好）等。

### 5.2 管道——把小工具串成流水线

管道（`|`）是 Shell 中最强大的功能之一。它的作用很简单：**把左边命令的输出作为右边命令的输入**。

```bash
# 没有管道：先保存结果到文件，再处理文件
ps aux > /tmp/processes.txt
grep python /tmp/processes.txt
rm /tmp/processes.txt

# 有管道：一步到位
ps aux | grep python
```

**管道的底层原理是什么？** 在操作系统层面，管道是这样工作的：

1. Shell 在内存中创建一个**内核缓冲区**（可以理解为一块临时内存）
2. Shell 把左边的命令（`ps aux`）的标准输出指向这个缓冲区——`ps aux` 的输出不再到终端，而是进入这个缓冲区
3. Shell 把右边的命令（`grep python`）的标准输入指向同一个缓冲区——`grep python` 从这个缓冲区读取数据
4. `ps aux` 开始执行，把数据写入缓冲区；`grep python` 从缓冲区读取数据逐行处理
5. 如果缓冲区满了，写入者（`ps aux`）会阻塞；如果缓冲区空了，读取者（`grep python`）也会阻塞

```
ps aux 的输出 → [内核缓冲区] → grep python 的输入
```

这就是 5.1 节中提到的"进程间通信（IPC）"中**管道**的实际应用。`|` 这个符号背后，是操作系统的 pipe 系统调用。

**为什么管道如此重要？** 它体现了 Linux 的设计哲学：每个命令只做一件事，但通过管道组合，你可以完成无限复杂的任务——而不需要任何编程。

```bash
# 管道组合实战：找出日志中最常出现的 10 个 IP 地址
cat access.log | awk '{print $1}' | sort | uniq -c | sort -rn | head -10

# 一步步拆解：
cat access.log      # 1. 读取日志文件，输出每一行
| awk '{print $1}'  # 2. 提取每一行的第一个字段（IP 地址）
| sort              # 3. 把所有 IP 地址排序（相同的 IP 排在一起）
| uniq -c           # 4. 统计每个唯一值出现的次数（-c = count）
| sort -rn          # 5. 按数字逆序排序（出现最多的排最上面）
| head -10          # 6. 只取前 10 行
```

### 5.3 重定向——控制数据的流向

**重定向（Redirection）** 让你控制"程序的输出去哪"和"程序的输入从哪来"。

Linux 中每个进程启动时默认有三个**文件描述符**：

| 文件描述符 | 名称 | 默认指向 | 缩写 |
|-----------|------|---------|------|
| 0 | 标准输入（stdin） | 键盘 | 程序读数据的地方 |
| 1 | 标准输出（stdout） | 终端屏幕 | 程序正常输出 |
| 2 | 标准错误（stderr） | 终端屏幕 | 程序错误输出 |

> 文件描述符是操作系统分配给每个打开的文件或 I/O 通道的一个整数编号。你在操作系统的学习中应该记得，这就是进程 PCB 中"打开的文件列表"的一部分。

```bash
# 标准输出重定向
echo "hello" > file.txt          # 把 stdout 写到 file.txt（覆盖）
echo "world" >> file.txt         # 把 stdout 追加到 file.txt

# 标准错误重定向
python bad_code.py 2> error.log  # 把 stderr 写到 error.log（正常的输出仍到屏幕）
python bad_code.py 2>> error.log # 追加形式

# 合并 stdout 和 stderr
python app.py > output.log 2>&1  # 把 stderr(2) 重定向到 stdout(1) 当前的目标
                                 # 从右往左读：2>&1 = "fd 2 去 fd 1 去的地方"
                                 # 等价于更现代的写法: python app.py &> output.log

# 从文件读取输入
sort < unsorted.txt              # 把 unsorted.txt 的内容作为 sort 的输入
                                 # 相当于 cat unsorted.txt | sort

# 黑洞 /dev/null
python app.py > /dev/null 2>&1  # 所有输出全部丢弃，静默运行
                                 # /dev/null 是一个特殊的设备文件，写入的数据直接消失
```

**为什么需要区分 stdout 和 stderr？** 想象你执行一个复杂的命令，正常的输出你需要保留到文件，但错误信息你需要看到（或在不同的地方处理）。区分两者允许你：

```bash
# 正常输出到日志文件，错误输出到屏幕
python process.py > process.log

# 正常输出到日志，错误输出到另一个日志
python process.py > process.log 2> error.log

# 两者到不同的地方
python process.py > result.txt 2> /dev/null  # 只看正常结果，忽略错误
```

### 5.4 grep——文本搜索的瑞士军刀

`grep`（Global Regular Expression Print）是一个在文件或输入流中搜索文本模式的工具。它的名字源自 ed 编辑器中的一条命令 `g/re/p`——"全局搜索正则表达式并打印匹配行"。

```bash
# 基本用法
grep "error" app.log               # 在 app.log 中找包含 "error" 的行
grep -r "def main" src/            # 递归搜索 src/ 目录下的所有文件
grep -i "error" app.log            # 忽略大小写（匹配 ERROR、Error、error）
grep -v "debug" app.log            # 反向匹配：找不包含 "debug" 的行
grep -n "TODO" *.py                # 显示匹配行的行号
grep -c "failed" app.log           # 只统计匹配的行数
grep -A 3 "exception" app.log      # 匹配后额外显示后面 3 行（After）
grep -B 3 "exception" app.log      # 匹配前额外显示前面 3 行（Before）
grep -C 3 "exception" app.log      # 匹配前后各显示 3 行（Context）
```

**grep 使用正则表达式进行匹配**，这意味着它可以匹配复杂的模式：

```bash
grep "^2024-06" app.log            # 找以 "2024-06" 开头的行（^ 表示行首）
grep "error$" app.log              # 找以 "error" 结尾的行（$ 表示行尾）
grep "error\|fatal\|crash" app.log # 找包含 error、fatal 或 crash 的行（\| 表示"或"）
grep "^[0-9]\{3\}\." app.log       # 找以三位数字加句点开头的行
```

### 5.5 sed 与 awk——编辑与格式化

`sed`（Stream Editor）是一个流式文本编辑器，它读取数据流，对每一行执行指定操作（替换、删除、插入），然后输出。

```bash
# sed 基本用法：'s/旧/新/标志'  模式
sed 's/foo/bar/g' file.txt        # 把每一行中所有 foo 替换为 bar
                                   # s = substitute（替换）
                                   # g = global（全局，一行中所有匹配都替换）
                                   # 不加 g 只替换每行的第一个匹配

sed 's/foo/bar/' file.txt         # 只替换每行第一个 foo
sed -i 's/foo/bar/g' file.txt     # -i = in-place（直接修改文件，不输出到终端）
sed -i '' 's/foo/bar/g' file.txt  # macOS 的 sed 需要加空备份后缀
sed '/^#/d' config.txt            # 删除所有以 # 开头的行（d = delete）
sed '3,10d' file.txt              # 删除第 3 到第 10 行
```

`awk` 是一个更强大的处理工具，它专为处理结构化文本（如表格、CSV、日志）而设计：

```bash
# awk 基本模式: awk 'pattern {action}' file
# 它把每行按分隔符拆分，$1、$2 等代表第几列

awk '{print $1}' access.log                    # 打印每行的第一个字段（默认按空格拆分）
awk -F',' '{print $2}' data.csv                # 以逗号分隔（-F','），打印第二列
awk '$3 > 100 {print $1, $3}' data.txt         # 如果第三列 > 100，打印第一和第三列
awk '{sum += $3} END {print "Total:", sum}'    # 统计第三列的总和
```

`awk` 实际上是一种迷你编程语言——它有变量、循环、条件、数组和内置函数。当你需要做比简单的替换（sed）更复杂的处理时，awk 是最佳选择。

### 5.6 三剑客实战——grep、sed、awk 如何协作

这三个工具——grep、sed、awk——被称为 Linux 文本处理"三剑客"。它们的分工非常清晰：

```
grep: 搜索（从数据中找出你关心的行）
sed:  编辑（对文本进行替换、删除、插入）
awk:  分析（拆分结构化字段、统计计算）
```

**实战：分析 Nginx 访问日志中的异常请求**

```bash
# 日志格式假设：IP 时间 方法 路径 状态码 大小
# 192.168.1.1 [27/Jun/2024:10:30:15] "GET /api/data" 200 1234

# 1. 找出所有返回 500 错误的请求
grep ' 500 ' access.log

# 2. 统计每个 IP 的 500 错误次数，按次数降序排列
grep ' 500 ' access.log | awk '{print $1}' | sort | uniq -c | sort -rn

# 3. 把这些 IP 加入防火墙黑名单
grep ' 500 ' access.log | awk '{print $1}' | sort -u | while read ip; do
    ufw deny from "$ip"
done

# 4. 把日志中的 IP 地址替换为匿名化形式（最后一段置零）
sed -r 's/([0-9]+\.[0-9]+\.[0-9]+\.)[0-9]+/\10/g' access.log > anonymized.log
```

---

## 六、软件包管理——安装和卸载软件的标准化方式

### 6.1 为什么需要包管理器

在 Linux 出现之前，安装软件通常是这样的：
1. 去网站下载源代码压缩包
2. 解压
3. 运行 `./configure` 检查系统依赖
4. 运行 `make` 编译
5. 运行 `make install` 复制文件到系统目录
6. 如果想卸载——你得手动找到所有被复制到各处的文件并删除

**包管理器（Package Manager）** 解决了这个问题：它自动处理依赖关系、下载、安装、配置、卸载和升级。你只需要一个命令：

```bash
apt install nginx        # 安装 nginx（自动下载、解决依赖、安装配置）
apt remove nginx         # 卸载 nginx（清理文件）
apt upgrade              # 升级所有已安装的软件包到最新版本
```

不同发行版使用不同的包管理器：

| 发行版 | 包管理器 | 包格式 |
|--------|---------|--------|
| Debian / Ubuntu | `apt` | `.deb` |
| CentOS / RHEL / Fedora | `dnf` 或 `yum` | `.rpm` |
| Arch Linux | `pacman` | `.pkg.tar.zst` |
| openSUSE | `zypper` | `.rpm` |

### 6.2 apt 使用详解

```bash
sudo apt update                  # 从软件源获取最新的软件包列表
                                 # update 不会升级软件，只是更新"有哪些版本可用"的信息
sudo apt upgrade                 # 升级所有已安装的软件到最新版本
sudo apt full-upgrade            # 升级同时处理依赖变化（可能卸载旧包）

sudo apt install python3         # 安装 python3
sudo apt install nginx mysql-server -y  # -y 自动回答"是"，跳过确认

sudo apt remove nginx            # 卸载（保留配置文件）
sudo apt purge nginx             # 卸载 + 删除配置文件
sudo apt autoremove              # 自动删除不再需要的依赖包

apt search "web server"          # 搜索软件包
apt show nginx                   # 查看包详情（版本、依赖、描述等）
apt list --installed             # 列出已安装的所有包
```

**为什么需要 `sudo apt update` 之后再 `install`？** `apt` 维护一个本地的软件包索引文件，记录了仓库中有什么包、什么版本。这个索引不会自动更新——你需要运行 `apt update` 来让本地索引与远程仓库同步。如果不 update，你可能安装的是几天前甚至几周前的版本。

`/etc/apt/sources.list` 这个文件定义了"从哪里下载软件包"。你可以修改它来使用国内镜像源（如清华源、阿里云源）来加速下载。

### 6.3 从源码安装——当包管理器不够用时

虽然包管理器解决了大多数需求，但有些情况下你需要从源码编译：

- 包管理器里的版本太旧，你需要最新版本
- 你需要自定义编译参数
- 你需要的软件包管理器里没有

```bash
# 经典的五步编译安装流程
tar -xzf redis-7.2.0.tar.gz      # 1. 解压源码包（tar -xzf: x=解压, z=gzip解压, f=文件名）
cd redis-7.2.0/                   # 2. 进入源码目录
./configure                       # 3. 检查系统环境，生成 Makefile
make                              # 4. 编译源代码（调用 gcc/cc 编译器）
sudo make install                 # 5. 将编译好的可执行文件复制到系统目录（如 /usr/local/bin/）
```

> `make` 和 `Makefile` 是 C/C++ 项目的标准构建系统。`Makefile` 定义了编译规则——哪些文件需要编译、用什么参数、按什么顺序。`make` 按照 Makefile 中的规则执行编译。如果你用的是 Python 或 Node.js，你不需要 `make`——因为它们是解释型语言，没有"编译"这一步。这就是为什么我们安装 Web 服务时用 `apt` + `pip`。

### 6.4 systemd——现代 Linux 的服务管理

当你安装了一个服务（如 Nginx、MySQL），你需要知道怎么启动它、停止它、让它开机自启。这是 **systemd** 的工作。它是目前几乎所有主流 Linux 发行版使用的**服务管理器（init 系统）**。

```bash
# systemctl 是管理 systemd 服务的主要命令
sudo systemctl start nginx         # 启动 Nginx
sudo systemctl stop nginx          # 停止 Nginx
sudo systemctl restart nginx       # 重启 Nginx
sudo systemctl reload nginx        # 热重载配置（不中断现有连接）
sudo systemctl enable nginx        # 设置 Nginx 开机自启
sudo systemctl disable nginx       # 取消开机自启
sudo systemctl status nginx        # 查看服务运行状态
sudo systemctl is-enabled nginx    # 检查服务是否已设为开机自启

# 查看服务日志
journalctl -u nginx                # 查看 Nginx 的日志
journalctl -u nginx -f             # 实时追踪（-f = follow）
```

**`reload` 和 `restart` 有什么区别？** `restart` 是"先停止再启动"——存在短暂的断连。`reload` 是让正在运行的服务重新读取配置文件——服务主进程收到 SIGHUP 信号，然后在不中断服务的情况下应用新配置。对于 Web 服务器，`reload` 意味着客户端的连接不会断开。

**systemd 与进程管理的关系**：systemd 是 PID 为 1 的进程——它是系统启动后第一个被内核启动的进程，是所有其他进程的"祖父"。你之前学的"init 进程"在现代 Linux 中就是 systemd。

有关守护进程（daemon）的概念——很多服务和进程管理方式与 systemd 紧密相关。例如 `gunicorn`（Python Web 服务器）通常会配置为一个 systemd 服务，以便自动管理和监控。

---

## 七、网络基础——每一台电脑都是海洋里的鱼

### 7.1 网络命令——诊断网络问题的工具箱

当你需要排查"我的服务器为什么连不上"时，这些命令是你的第一道防线：

```bash
# ping：测试网络连通性
ping google.com                  # 持续 ping（Ctrl+C 停止）
ping -c 4 google.com             # 只发 4 个包后自动停止
```

ping 发送 ICMP 协议的回显请求包，如果目标可达，它会返回响应包，并显示往返时间。如果 ping 不通，可能的原因有：目标主机宕机、网络连接断开、防火墙阻止了 ICMP 请求。

```bash
# curl：发送 HTTP 请求（测试 Web 服务最常用的工具）
curl https://api.example.com          # GET 请求
curl -X POST -d '{"key":"val"}' url   # POST 请求 + JSON 数据
curl -I https://example.com           # 只看响应头（-I = head 请求）
curl -v https://example.com           # 显示完整的请求和响应过程（调试用）
curl -o output.html https://example.com  # 将响应内容保存到文件
```

`curl -v` 的详细输出会显示 SSL/TLS 握手过程、请求头、响应头、重定向等——这是调试 API 接口的利器。

```bash
# 查看端口监听情况——你的服务器在等谁来连接？
netstat -tlnp                  # 显示所有 TCP 监听端口
                               # -t = TCP，-l = listening，-n = 数字格式，-p = 进程信息
ss -tlnp                      # netstat 的现代替代，更快（推荐使用）
```

输出示例：
```
Proto Recv-Q Send-Q Local Address   Foreign Address  State    PID/Program name
tcp   0      0      0.0.0.0:80      0.0.0.0:*        LISTEN   1234/nginx
tcp   0      0      0.0.0.0:22      0.0.0.0:*        LISTEN   567/sshd
tcp   0      0      127.0.0.1:3306  0.0.0.0:*        LISTEN   890/mysqld
```

解读这个输出：
- `0.0.0.0:80`：Nginx 在**所有网络接口**的 80 端口上监听（可以从任何 IP 访问）
- `127.0.0.1:3306`：MySQL 只在**本地回环地址**监听（只能从本机访问，外部无法连接——这是安全最佳实践）

```bash
# 查看本机 IP 地址
ip addr                      # 完整的网络接口信息
hostname -I                  # 简洁显示 IP 地址（多个 IP 用空格分隔）
```

`ip addr` 的输出中，`inet` 行后面的就是你网卡的 IPv4 地址。例如 `inet 192.168.1.100/24` 表示本机 IP 为 192.168.1.100，子网掩码为 24 位（255.255.255.0）。

### 7.2 SSH——远程控制的基础协议

SSH（Secure Shell）是目前远程登录 Linux 服务器的标准方式。它使用**加密传输**，所有数据（包括密码）在传输过程中都是加密的。

```bash
# 基本登录
ssh user@192.168.1.100              # 密码登录（输入 user 的密码）
ssh user@server.example.com         # 也可以用域名

# 指定端口（默认是 22）
ssh -p 2222 user@host

# 密钥登录（更安全、更方便，无需每次输入密码）
ssh -i ~/.ssh/id_rsa user@host      # 指定私钥文件
```

**为什么密钥登录比密码更安全？** 密码登录时，密码通过网络传输——即使加密了，如果服务器被攻破，密码可能泄露。密钥登录使用**非对称加密**：你在本地保存私钥（`id_rsa`，必须保密），把公钥（`id_rsa.pub`）上传到服务器的 `~/.ssh/authorized_keys` 文件中。登录时，服务器用你的公钥加密一个随机数，只有你的私钥才能解密——网络传输的始终是加密后的随机数，不是你的私钥。即使服务器被攻破，攻击者也无法从公钥反推私钥。

**设置密钥登录的完整流程：**

```bash
# 1. 在本地生成密钥对
ssh-keygen -t ed25519 -C "your_email@example.com"
# 生成 id_ed25519（私钥）和 id_ed25519.pub（公钥）
# -t ed25519 使用比 RSA 更高效且同样安全的算法

# 2. 把公钥复制到服务器
ssh-copy-id user@server-ip
# 或者手动操作：ssh user@server-ip "mkdir -p ~/.ssh && chmod 700 ~/.ssh"
# 然后在本地：scp ~/.ssh/id_ed25519.pub user@server-ip:~/.ssh/authorized_keys

# 3. 测试——应该不需要密码就能登录了
ssh user@server-ip
```

**文件传输：**

```bash
# scp：基于 SSH 的简单文件复制
scp localfile.txt user@host:/home/user/          # 本地上传到服务器
scp user@host:/home/user/remotefile.txt ./        # 从服务器下载到本地
scp -r localdir/ user@host:/remote/dir/           # 递归复制目录

# rsync：增量同步，比 scp 更聪明
rsync -avz localdir/ user@host:/remote/dir/       # 只传输变化的部分
# -a = archive（保留权限、时间等元信息）
# -v = verbose（显示详情）
# -z = compress（传输时压缩）
# 如果第二次运行，只传有差异的文件，极大节省时间
```

### 7.3 防火墙——服务器的第一道门

**防火墙（Firewall）** 控制哪些网络流量可以进入或离开你的服务器。它根据 IP 地址、端口、协议类型来过滤数据包。

Ubuntu 上最常用的防火墙工具是 **UFW（Uncomplicated Firewall）**：

```bash
sudo ufw status                  # 查看当前防火墙规则
sudo ufw enable                  # 开启防火墙（默认拒绝所有入站连接）
sudo ufw disable                 # 关闭防火墙

# 放行特定端口
sudo ufw allow 22/tcp            # 放行 SSH（22 端口）
sudo ufw allow 80/tcp            # 放行 HTTP（80 端口）
sudo ufw allow 443               # 放行 HTTPS（443 端口）

# 拒绝特定端口
sudo ufw deny 3306               # 拒绝外部对 MySQL 端口的访问

# 限制来源 IP
sudo ufw allow from 192.168.1.0/24 to any port 22  # 只允许内网 IP 访问 SSH
sudo ufw deny from 10.0.0.1                        # 封杀特定 IP

# 删除规则
sudo ufw delete deny 3306
```

**默认策略（Default Policy）**：UFW 的默认策略是"拒绝所有入站连接，允许所有出站连接"。这意味着除非你明确 `allow` 了一个端口，否则外部无法连接服务器的任何端口。

**为什么数据库端口（3306、5432、6379、27017）不应该对外开放？**

如果你的 MySQL 端口（3306）暴露在公网，服务器流浪扫描器会在一小时内发现它。攻击者会尝试暴力破解密码、利用已知漏洞。即使你的密码很强，也防不住零日漏洞。

正确的做法是：让数据库只监听 `127.0.0.1`（仅限本机访问），应用服务（Nginx + 你的后端）通过本机连接数据库。如果确实需要远程管理数据库，使用 SSH 隧道或者 VPN，而不是直接暴露端口。

---

## 八、终端效率——让你事半功倍的习惯

### 8.1 快捷键——每次按键都是时间

```text
Ctrl + C     终止当前命令（发送 SIGINT 信号）
Ctrl + D     退出终端 / 发送 EOF（输入结束标记）
Ctrl + Z     挂起当前程序（发送 SIGTSTP 信号）
Ctrl + L     清屏（等于清空屏幕，比 clear 更快）
Ctrl + A     跳到行首（手指不用离开主键盘区）
Ctrl + E     跳到行尾
Ctrl + U     删除光标前的所有字符
Ctrl + K     删除光标后的所有字符
Ctrl + W     删除光标前的一个单词
Ctrl + R     搜索历史命令——按一下输入关键字，历史命令就出来了
↑ / ↓        翻看历史命令
Ctrl + P / N 同上（P=Previous，N=Next，手可以不动）
Tab          自动补全命令和路径——敲一半按 Tab
!!           重复上一条命令（sudo !! ——用 sudo 执行上一条命令）
!$           上一条命令的最后一个参数
```

**最值得记住的三个快捷键：**
1. **Ctrl + R**：搜索历史命令。比 `history | grep xxx` 快得多，而且是交互式的
2. **Tab**：自动补全。如果按 Tab 没反应，说明有多个匹配——双击 Tab 列出所有匹配
3. **Ctrl + A / Ctrl + E**：在长命令中跳转，比按方向键快得多

### 8.2 常用系统命令

```bash
# 磁盘空间
df -h                         # 查看所有挂载点的磁盘使用情况
                              # -h = human-readable（显示为 G、M 而非字节数）
du -sh project/               # 查看特定目录的总大小（-s = summary）
du -sh * | sort -hr           # 当前目录下每个子目录按大小排序（找大文件利器）

# 内存和系统
free -h                       # 查看内存使用情况
uptime                        # 服务器运行了多久
uname -a                      # 查看系统信息（内核版本、架构等）
who                           # 谁登录了服务器
last                          # 最近的登录记录

# 其他实用命令
watch -n 1 "ls -l"            # 每隔 1 秒执行一次命令（观察变化）
diff file1 file2              # 对比两个文件的差异
history                       # 查看命令历史
history | grep pip            # 在历史中搜索
```

### 8.3 快速创建大文件

有时你需要测试磁盘性能或验证文件上传功能：

```bash
fallocate -l 1G bigfile.img          # 瞬间创建 1GB 文件（推荐，不实际写入数据）
dd if=/dev/zero of=bigfile bs=1M count=1024  # 创建 1GB 全零文件（会实际写入）
# if=/dev/zero：从零设备读取（无限输出零字节）
# of=bigfile：输出文件名
# bs=1M：每次读写 1MB
# count=1024：重复 1024 次 → 总大小 1GB
```

---

## 九、实战：从零搭建一个 Web 服务

把前面学的所有知识串联起来。目标是：在一台新购买的云服务器上部署一个 Python Flask Web 应用。

```bash
# 1. SSH 连接服务器
ssh root@your-server-ip
# 第一次连接会提示确认主机指纹（"Are you sure you want to continue connecting?"）
# 这是为了防止中间人攻击——确认指纹后，后续连接不再提示

# 2. 创建一个普通用户（安全规范：不使用 root 日常操作）
adduser alice
usermod -aG sudo alice          # 给 alice sudo 权限
su - alice                       # 切换到 alice 用户

# 3. 更新软件源并安装必要软件
sudo apt update                  # 更新包索引
sudo apt upgrade -y             # 升级已安装的包
sudo apt install -y python3 python3-pip python3-venv nginx git

# 4. 创建项目目录
mkdir -p ~/myapp && cd ~/myapp

# 5. 创建 Python 虚拟环境并安装依赖
python3 -m venv venv            # 创建虚拟环境（隔离项目的 Python 包）
source venv/bin/activate        # 激活虚拟环境（PATH 指向 venv 内的 python）
pip install flask gunicorn      # 安装 Flask（Web 框架）和 Gunicorn（WSGI 服务器）

# 6. 创建应用
cat > app.py << 'EOF'
from flask import Flask
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World! 服务器部署成功！"

if __name__ == "__main__":
    app.run()
EOF

# 7. 测试运行
python app.py &                 # 后台启动 Flask 开发服务器
curl http://127.0.0.1:5000      # 本地测试——应该返回 "Hello World!"
kill %1                         # 杀掉测试进程

# 8. 用 Gunicorn 正式启动（生产环境用 Gunicorn 而非 Flask 自带的开发服务器）
# gunicorn -w 4：启动 4 个工作进程（Worker）
# -b 0.0.0.0:8000：绑定到所有网络接口的 8000 端口
# app:app：模块名:Flask 实例名
# > app.log 2>&1：把 stdout 和 stderr 都重定向到日志文件
nohup venv/bin/gunicorn -w 4 -b 0.0.0.0:8000 app:app > app.log 2>&1 &

# 验证
curl http://127.0.0.1:8000       # 应返回 Hello World!

# 9. 配置 Nginx 反向代理
# 反向代理的作用：用户访问 80 端口（HTTP 默认端口）→ Nginx → 转发到 Gunicorn(8000)
# 这样可以由 Nginx 处理静态文件、HTTPS、负载均衡等
sudo tee /etc/nginx/sites-available/myapp << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # 换成你的域名或服务器 IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

# 启用站点配置
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/
# 软链接：sites-available（配置仓库）→ sites-enabled（生效配置）
# 这样禁用一个站点时只需删除软链接，保留原始配置

# 测试 Nginx 配置语法是否正确
sudo nginx -t

# 重新加载 Nginx 使配置生效（不中断现有连接）
sudo systemctl reload nginx

# 10. 配置防火墙
sudo ufw allow 22/tcp               # SSH
sudo ufw allow 80/tcp               # HTTP
sudo ufw --force enable             # 开启防火墙（--force 跳过确认）

# 11. 大功告成！用浏览器访问你的服务器 IP
```

**这个实战项目串联了哪些知识点？**

| 步骤 | 用到的知识 |
|------|-----------|
| SSH 连接 | SSH 协议、远程登录 |
| 用户管理 | 用户和组的概念、sudo 权限 |
| apt 安装 | 包管理、软件源 |
| 目录操作 | mkdir、cd、路径概念 |
| 虚拟环境 | 环境隔离、PATH 变量 |
| 文件创建 | 重定向（cat > EOF）、文本处理 |
| 后台运行 | &、nohup、进程管理 |
| 管道和重定向 | >、2>&1 |
| 进程查看 | ps、kill、jobs |
| 服务管理 | systemctl、systemd |
| 软链接 | ln -s |
| 防火墙 | ufw、端口管理 |
| 权限 | sudo 提权 |

---

## 十、总结与核心记忆点

### 文件系统

- **一切皆文件**：普通文件、设备、进程信息、网络连接都被抽象为文件接口
- **目录树**：从 `/` 根目录开始，`/etc` 是配置，`/var/log` 是日志，`/proc` 是虚拟文件系统
- **路径**：绝对路径从 `/` 开始，相对路径从 `.` 开始，`~` 是家目录
- **文件操作**：`ls` 查看、`cp`/`mv` 复制/移动、`rm -rf` 极其危险
- **链接**：软链接是路径引用（原文件删除则失效），硬链接是数据块共享

### 权限系统

- **权限三位组**：Owner（主人）、Group（组）、Others（其他人）
- **权限三位码**：r（读=4）、w（写=2）、x（执行=1）— 组合成 0-7 的数字
- **常用组合**：755（可执行文件）、644（普通文件）、600（私密文件）
- **chmod**：数字模式（`chmod 755 file`）或符号模式（`chmod +x file`）
- **chown**：改变文件的所有者和所属组

### 进程管理

- **PID**：每个进程的唯一标识
- **ps aux**：查看所有进程的快照
- **信号**：SIGTERM(15) 请求终止，SIGKILL(9) 强制杀死
- **前台/后台**：`&` 后台运行，`nohup` 脱离终端，`Ctrl+Z` 挂起，`bg` 继续
- **环境变量**：`PATH` 是命令搜索路径，`export` 临时设置，`~/.bashrc` 永久设置

### Shell 与文本处理

- **管道 `|`**：左侧输出作为右侧输入，底层是内核管道缓冲区
- **重定向**：`>` 覆盖，`>>` 追加，`2>&1` 合并 stderr 到 stdout
- **grep**：搜索文本，支持正则表达式
- **sed**：替换/编辑文本流，`sed 's/旧/新/g'`
- **awk**：结构化文本处理，按列拆分，支持统计计算

### 包管理与服务

- **apt**：`update` 更新索引 → `install` 安装 → `remove`/`purge` 卸载
- **systemd**：`systemctl start/stop/restart/reload/enable/status`
- **systemctl reload** vs **restart**：前者热重载不中断连接

### SSH 与网络

- **SSH 密钥**：公钥放在服务器 `~/.ssh/authorized_keys`，私钥本地保管
- **防火墙**：只放行必要端口（22、80、443），数据库端口绝不对外暴露
- **网络诊断**：`ping` 测连通，`curl` 测 HTTP，`ss -tlnp` 看端口监听

### 安全底线

- **不要用 root 日常操作**——用普通用户 + sudo
- **不要给 777 权限**——最小权限原则
- **不要对外暴露数据库端口**——3306、5432、6379 等只监听 127.0.0.1
- **不要运行看不懂的命令**——尤其是有 `rm -rf` 或管道到 `bash` 的
- **SSH 不要用密码**——用密钥登录，更安全更方便

---

