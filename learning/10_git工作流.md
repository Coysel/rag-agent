# 第十部分：Git 工作流

> **前置**: 理解 Git 的基本概念——仓库(Repository)、提交(Commit)、分支(Branch)。如果还不会 `git add` / `git commit` / `git push`，建议先花 30 分钟跑一遍 Git 入门教程。

---

## 第一章 Git 的底层逻辑——先理解"快照"而非"差异"

### 1.1 Git 和其他版本控制的本质区别

大部分版本控制系统（SVN、CVS）采用**增量式存储**——每次提交只保存"这次改了哪些行"的差异补丁。要重建某个版本，你得从初始版本开始，逐个应用每个补丁。

Git 则采用**快照式存储**——每次提交都保存所有文件的一个完整快照（实际上 Git 会为内容不变的文件重用已有的对象，而不是真的存两份，但在逻辑上你应该把它当作快照）。

```
SVN 的存储方式:
  v1 ─→ v2 (diff) ─→ v3 (diff) ─→ v4 (diff)
  要读 v4: 先读 v1, 然后依次打上 diff

Git 的存储方式:
  v1 (snapshot) ─→ v2 (snapshot) ─→ v3 (snapshot) ─→ v4 (snapshot)
  要读 v4: 直接读 v4 的快照
```

这个设计决定了 Git 的几乎所有行为：分支切换极快、离线操作完全可行、合并时能精准找到共同祖先。

### 1.2 三个区域：工作区 → 暂存区 → 仓库

这是初学者最容易混淆的概念，但理解了它，你就理解了 Git 的一半。

```
Working Directory (工作区)         你写代码的地方，能看到的文件
        │
        │ git add <file>
        ▼
Staging Area (暂存区 / Index)      你准备提交的内容清单，存在 .git/index 里
        │
        │ git commit
        ▼
Repository (仓库 / .git)           所有历史版本，存在 .git/objects 里
```

为什么需要"暂存区"这一层？因为现实中你经常是这样工作的：

1. 你在 `app.py` 里修了一个 bug
2. 顺手改了 `utils.py` 里的一个打印日志格式
3. 测试时发现另一个紧急 bug，正在修复中
4. 老板说"那个 bug fix 先上线"

**没有暂存区**，你要么把未完成的代码一起提交，要么用 stash 硬拆。**有暂存区**，你只需要 `git add app.py`（只把改好的 bug fix 放进来），`git commit`，就只提交了 bug fix，`utils.py` 的改动还在工作区等你。

这就是暂存区存在的根本原因——让你可以**精细控制一次提交的内容**。

### 1.3 分支就是指针

在 Git 里，**分支就是一个指向某次提交的可移动指针**，仅此而已。

```bash
# 创建一个分支——只是生成了一个新指针
git branch feature-login

# 查看分支指向哪里——显示每个分支所指向的 commit hash
git log --oneline --graph --all --decorate
```

```
提交历史 (类似链表):
  A ← B ← C ← D       ← master (指向 D)
               ← E     ← feature-login (指向 D，因为刚创建)
```

当你切到 feature-login 后做新提交：

```bash
git switch feature-login     # 把 HEAD 指向 feature-login
# 修改代码...
git add . && git commit -m "add login form"
```

```
  A ← B ← C ← D            ← master
               ← E ← F     ← feature-login (前进到 F)
```

HEAD 是一个**特殊指针**，指向"当前在哪个分支/提交上"。`git switch` 做的就是：移动 HEAD 的指向，然后更新工作区的文件内容。

**为什么 Git 的分支这么轻量？** 因为在 SVN 里"创建分支"意味着复制整个目录（实际就是 copy 一份代码），几百 MB 的项目要等几分钟。而 Git 的分支只是创建一个 41 字节的文件（40 字节 hash + 1 字节换行），瞬间完成。

---

## 第二章 分支策略——Git Flow vs GitHub Flow

### 2.1 为什么需要分支策略

当团队只有一个人、项目只有几百行代码时，直接在 `main` 分支上开发没问题。但一旦出现以下情况：

- 5 个人同时开发不同的功能
- 有人修线上 Bug，有人开发新功能，有人做实验性重构
- 需要同时维护 v1.0（线上版本）和开发 v2.0

如果没有分支策略，结果就是**混乱**——谁在做什么、哪个分支是稳定的、上线时该合并谁，全都说不清。

不同的团队规模、发布周期、风险偏好，需要不同的分支策略。Git Flow 和 GitHub Flow 是两种最主流的模型。

### 2.2 Git Flow——功能完备的"重武器"

Git Flow 是 Vincent Driessen 在 2010 年提出的分支模型。它定义了**一套完整的分支类型和生命周期**，适合有固定发布周期的产品（如移动 App、桌面软件、企业级系统）。

#### 2.2.1 五种分支类型

```
main (主分支)
  ├── develop (开发主线)
  │     ├── feature/* (功能分支，从 develop 分出来)
  │     └── feature/* (多个功能同时开发)
  ├── release/* (发布准备分支，从 develop 分出来，合并回 main 和 develop)
  └── hotfix/* (紧急修复分支，从 main 分出来，合并回 main 和 develop)
```

| 分支类型 | 命名示例 | 从谁分出 | 合并回谁 | 生命周期 |
|---------|---------|---------|---------|---------|
| `main` | `main` / `master` | — | — | 永久存在，只存已发布的代码 |
| `develop` | `develop` | `main` | `main` (通过 release) | 永久存在，日常开发的集结点 |
| `feature/*` | `feature/user-auth` | `develop` | `develop` | 功能开发完就删 |
| `release/*` | `release/v2.1.0` | `develop` | `main` + `develop` | 发布准备阶段结束后删 |
| `hotfix/*` | `hotfix/critical-crash` | `main` | `main` + `develop` | 紧急修复完成后删 |

#### 2.2.2 标准工作流程

**日常开发流程：**

```bash
# 1. 从 develop 分支一个新功能
git switch develop
git pull origin develop
git switch -c feature/user-login

# 2. 在 feature 分支上开发，多次提交
echo "login code" > login.py
git add login.py && git commit -m "feat: add login page"
echo "login logic" >> login.py
git add login.py && git commit -m "feat: implement login validation"

# 3. 开发完成，合并回 develop
git switch develop
git pull origin develop                     # 拉取队友的最新代码
git merge --no-ff feature/user-login        # --no-ff 强制创建 merge commit
git push origin develop
git branch -d feature/user-login            # 删除本地分支
git push origin --delete feature/user-login # 删除远程分支
```

**发布流程：**

```bash
# 1. 功能开发完了，从 develop 拉出 release 分支
git switch develop
git pull origin develop
git switch -c release/v2.1.0

# 2. 在 release 分支上只做 bug 修复，不添加新功能
# 修改版本号、更新文档、修复发现的 bug
echo "version=2.1.0" > VERSION
git add VERSION && git commit -m "chore: bump version to 2.1.0"

# 3. release 准备好后，合并到 main 并打 tag
git switch main
git merge --no-ff release/v2.1.0
git tag -a v2.1.0 -m "Release version 2.1.0"  # 打标签，标记这个版本

# 4. 同时也合并回 develop（因为 release 上可能修了 bug）
git switch develop
git merge --no-ff release/v2.1.0

# 5. 删除 release 分支
git branch -d release/v2.1.0
```

**紧急 hotfix 流程：**

```bash
# 1. 线上出了严重 bug，从 main 直接拉 hotfix 分支
git switch main
git switch -c hotfix/critical-crash

# 2. 修复代码
echo "fixed" > crash.py
git add crash.py && git commit -m "fix: resolve null pointer crash"

# 3. 合并回 main 并打 tag
git switch main
git merge --no-ff hotfix/critical-crash
git tag -a v2.1.1 -m "Hotfix: null pointer crash"

# 4. 也要合并回 develop，确保下次发布包含这个修复
git switch develop
git merge --no-ff hotfix/critical-crash

# 5. 删除 hotfix 分支
git branch -d hotfix/critical-crash
```

#### 2.2.3 Git Flow 的优点

- **严格的分工**——每个分支都有明确的职责，不会出现"开发了一半的代码被意外上线"
- **同时维护多个版本**——hotfix 直接基于 main，和正在开发的 develop 互不干扰
- **发布准备空间**——release 分支给了团队"冻结功能、只修 bug"的隔离环境

#### 2.2.4 Git Flow 的缺点

- **复杂**——5 种分支、需要频繁合并、大量的 merge commit 让历史看起来很乱
- **不适合持续部署**——每次发布都要走 release 分支流程，对于一天上线多次的团队来说太重了
- **初学者理解成本高**——很多人搞不清什么时候该从谁合并到谁

**为什么 Git Flow 对某些项目还是好选择？** 如果你在做一款 iOS App，它的发布周期是"每两周一个版本"，需要同时维护线上版和开发版，hotfix 必须快速且安全。Git Flow 的严格隔离正适合这种场景——你绝不会因为"develop 上有个提交了一半的功能"而挡住 hotfix 上线。

### 2.3 GitHub Flow——轻量级的"快刀"

GitHub Flow 是 GitHub 在 2011 年左右推广的极简模型。GitHub 自身使用这种流程，每天部署几十次到上百次。

#### 2.3.1 核心原则

GitHub Flow 只有**一个长期分支**（`main`），所有开发都在临时分支上进行，通过 Pull Request 审核后合并。

```
main ──A──B──C──D──E──F──G──  (唯一的长期分支)
         \        /
          X──────Y              (功能分支，PR 审核后合并)
                \
                 Z────W         (另一个功能分支，基于最新的 main)
```

#### 2.3.2 标准工作流程

```bash
# 1. 从 main 创建功能分支
git switch main
git pull origin main
git switch -c feature/checkout-flow

# 2. 正常开发，多次提交
git add . && git commit -m "add checkout page"
git add . && git commit -m "implement payment integration"

# 3. 推送到远程，创建 Pull Request
git push origin feature/checkout-flow
# → 在 GitHub/Bitbucket/GitLab 上创建 PR

# 4. 团队 Review 代码，讨论修改
#    Review 通过后，点击 PR 上的"Merge"按钮

# 5. 合并后删除远程分支，本地也清理
git switch main
git pull origin main
git branch -d feature/checkout-flow
```

#### 2.3.3 关键实践：持续集成 + 自动化测试

GitHub Flow 能工作的前提是：

1. **每次 push 都自动跑测试**——CI（Continuous Integration）确保你的分支不会引入回归 bug
2. **PR 必须通过 CI 才能合并**——防止坏代码进入 main
3. **main 永远是可部署的**——任何时刻 main 的代码都可以直接上线

```yaml
# .github/workflows/ci.yml (GitHub Actions 示例)
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm install
      - run: npm test
      - run: npm run build
```

这行配置的意思是：每次有人 push 代码或创建 PR，自动执行 `npm test` 和 `npm run build`。测试通过才能合并。

#### 2.3.4 为什么 GitHub Flow 更适合现代 Web 项目

**对比一下两种场景：**

**场景 A：传统企业软件（版本 2.1.0，固定发布周期）**
- 需要同时维护 v2.0.1 (线上)、v2.1.0 (开发中)、v2.2.0 (实验性)
- hotfix 需要被合入所有活跃版本
- Release 需要 QA 团队的完整回归测试
- → Git Flow 更适合

**场景 B：SaaS Web 应用（每天上线 5 次）**
- 没有"版本号"的概念，线上永远是最新版
- 功能开发完就上线，不需要等待"发版日"
- 紧急 bug 修完直接合并到 main，自动部署
- → GitHub Flow 更适合

**为什么 GitHub Flow 不需要 release 分支？** 在持续部署模式下，功能开发完成并通过 Review 后，它就直接上线了。"发布"不是一个独立阶段——它就是合并到 main 的那一刻。如果某个功能还没准备好，加一个 feature flag（功能开关）来控制它在前端隐藏，而不是用一个分支来隔离它。

### 2.4 如何选择

| 考量维度 | 适合 Git Flow | 适合 GitHub Flow |
|---------|-------------|----------------|
| 发布周期 | 固定周期（每周/每两周一版） | 持续部署（随时发） |
| 版本管理 | 需要语义化版本号（v1.2.3） | 不需要版本号，或由 CI 自动生成 |
| 团队规模 | 10-50 人 | 2-20 人 |
| 发布流程 | 需要 QA 团队完整测试 | 自动化测试取代人工 QA |
| 产品形态 | 移动 App、桌面软件、嵌入式 | Web 应用、SaaS、微服务 |

**一个实用的建议：** 大多数中小团队从 GitHub Flow 开始就够了。当项目复杂到明显感到 GitHub Flow 不够用时（比如发布周期和开发周期严重不同步），再引入 Git Flow 不迟。**不要为可能永远不会出现的场景提前增加复杂度。**

---

## 第三章 Merge 与 Rebase——两种"合代码"的方式

### 3.1 问题是什么

想象你和队友同时在 `feature/cart` 分支上开发，期间 `main` 分支被别人更新了两次。现在你想把 `main` 的新代码合到你的分支上。Git 给了你两种方式：

```bash
# 方式一：Merge
git merge main          # 创建一个 merge commit 把两个分支的历史连起来

# 方式二：Rebase
git rebase main         # 把你在 feature/cart 上的提交"搬到"main 的最新位置
```

两种方式的结果不同，理解它们的区别是 Git 进阶的核心。

### 3.2 Merge——"记录事实"

Merge 会创建一个**新的 merge commit**，这个 commit 有两个父提交（parent），分别指向两个分支的末端。

```
Merge 之前:
  main:     A ← B ← C
                      \
  feature:             D ← E

Merge 之后 (git switch feature && git merge main):
  main:     A ← B ← C
                      \
  feature:             D ← E ← F (Merge commit, 耦合了 C 和 E 的历史)
```

Merge commit 的 `git log` 看起来：

```
commit f1234567 (HEAD -> feature)
Merge: e89abc2 c7654321
Author: Alice <alice@example.com>
Date:   Mon Jul 13 2026

    Merge branch 'main' into feature/cart
```

"Merge: e89abc2 c7654321" 这一行表示这个 commit 有两个父 commit，分别来自 feature 分支和 main 分支。

**Merge 的特点：**
- **保留真实历史**——合并前的所有 commit 原封不动，谁在什么时候做了什么，一目了然
- **不会重写历史**——已有的 commit hash 不会改变
- **会产生额外的 merge commit**——频繁合并的话，历史会变得错综复杂

```bash
git log --graph --oneline --all

*   f123456 (feature) Merge branch 'main' into feature/cart
|\
| * c765432 (main) fix: validate email format
| * b234567 (main) feat: add pagination
* | e89abc2 feat: implement cart checkout
* | d345678 feat: add cart persistence
|/
* a123456 (tag: v1.0) initial commit
```

这个 `--graph` 参数告诉 Git 用 ASCII 字符画出分支拓扑，`--oneline` 简化每条记录为一行。你看到的 `|\` 和 `|/` 就是两个分支合并的视觉表示。

### 3.3 Rebase——"重写历史"

Rebase 不会创建 merge commit。它把当前分支上的 commit **取下来**，然后**在目标分支的最新位置重新应用**。

```
Rebase 之前:
  main:     A ← B ← C
                      \
  feature:             D ← E

Rebase 之后 (git switch feature && git rebase main):
  main:     A ← B ← C
                     \
                      D' ← E'  (注意：D' 和 E' 是新的 commit，和原来的 D、E 不同)
```

D' 和 D 的内容**一样**，但 hash 不同。因为 commit 的 hash 是由它的内容、父 commit 的 hash、时间戳等一起计算的——父 commit 变了，hash 必然变。

```bash
git rebase main  # 实际发生的事情

# 1. Git 找到 feature 和 main 的共同祖先（假设是 A）
# 2. 把 D 和 E 临时存到一个"草稿区"(patch)
# 3. 把 feature 分支移动到 main 的末端 (C)
# 4. 在 C 的基础上，依次应用 D 的改动(D')、E 的改动(E')
```

**为什么 Rebase 后的历史更清晰？**

```bash
git log --oneline

# Merge 版本:
f123456 Merge branch 'main' into feature/cart
e89abc2 feat: implement cart checkout
d345678 feat: add cart persistence
c765432 fix: validate email format
b234567 feat: add pagination
a123456 initial commit

# Rebase 版本:
e89abc2' feat: implement cart checkout    # hash 变了
d345678' feat: add cart persistence       # hash 变了
c765432 fix: validate email format        # 你的提交都在 main 的后面
b234567 feat: add pagination
a123456 initial commit
```

Rebase 后的历史是一条**直线**，像所有工作都是在 main 的最新版本上按顺序完成的。没有分叉，没有 merge commit，看起来干净整洁。

### 3.3.1 Rebase 的交互模式

Rebase 最有威力的用法是交互模式，它可以**整理你自己的 commit 历史**，在推送到远程之前。

```bash
# 交互式 rebase，修改最近 3 个 commit
git rebase -i HEAD~3

# 这会打开一个编辑器，让你决定对每个 commit 做什么：
pick d345678 feat: add cart persistence
pick e89abc2 feat: implement cart checkout
pick a1b2c3d fix: typo in cart

# 你可以改成:
pick d345678 feat: add cart persistence       # 保留这个
squash e89abc2 feat: implement cart checkout   # 合并到前一个 commit
fixup a1b2c3d fix: typo in cart               # 合并但不保留 commit message
```

| 命令 | 效果 |
|------|------|
| `pick` | 保留这个 commit 不变 |
| `reword` | 保留内容，但修改 commit message |
| `squash` | 把当前 commmit 合并到上一个，保留两个 message |
| `fixup` | 和 squash 一样，但丢弃当前 commit 的 message |
| `drop` | 删除这个 commit |

**交互式 Rebase 的实际场景：** 你开发了一个功能，过程中提交了 8 次，commit message 分别是 "wip"、"fix"、"fix again"、"actually fix"、"add test"、"oops"、"ok this works"、"refactor"。等开发完，你用 `git rebase -i main` 把这些合并成 2 个整洁的 commit："feat: implement cart functionality" 和 "test: add unit tests for cart"。这样队友 Review 的时候读的是清晰的逻辑步骤，而不是你的真实工作记录。

### 3.4 为什么叫"黄金法则"——永远不要 Rebase 已推送的提交

这是 Git 世界里最重要的一条规则，**没有之一**。

```bash
# ❌ 绝对不要做
git push origin feature/cart
# 队友 pull 了你的代码
git rebase main
git push origin feature/cart --force   # force push 覆盖了远程的 commit

# 队友再次 git pull 时：
# fatal: 当前分支的提交落后于远程，但本地有远程没有的提交...
# 队友: "???"
```

**为什么这么严重？**

Rebase 重写了 commit hash。如果你 rebase 了已经推送到远程的 commit，又 force push 上去：

1. 远程仓库的 commit 被替换成了新的（不同 hash 的） commit
2. 队友之前 `git pull` 得到的 commit 和远程的不一致了
3. 队友下次 `git pull` 会收到**冲突警告**，因为他们本地的历史分支和远程对不上了
4. 队友**唯一**的"修复"方式是 `git pull --rebase` 或者 `git reset --hard origin/feature/cart`——前者可能造成重复提交，后者会丢失本地的改动

**黄金法则：你只能 rebase 还没有离开你本机的 commit。一旦你用 `git push` 把 commit 分享出去了，它就不再只属于你了——其他人可能已经基于它做了工作。rebase 并 force push 会拉走他们脚下的地毯。**

```bash
# ✅ 安全的做法：rebase 只用于本地未推送的 commit
git switch feature/cart
# 做了一些提交，还没 push
git rebase main          # 安全，还没人看到这些 commit
git push origin feature/cart

# ✅ 另一种安全的做法：利用 pull --rebase
git pull --rebase origin main  # 等价于 fetch + rebase
# 原因：你先 fetch，然后 rebase — 但此时你正在 rebase 的是本地与远程同步后的内容，
# 且你还没有把自己的 commit push 出去
```

### 3.5 Merge 和 Rebase 的选择策略

```bash
# 合并主分支到功能分支时——看团队约定
# 选项 A（Merge）:
git switch feature/cart
git merge main
# 结果：多一个 merge commit，保留真实合并时间点

# 选项 B（Rebase）:
git switch feature/cart
git rebase main
# 结果：历史是直线，但需要 force push — 仅在你独占的分支上可行

# 实际工作中最常见的做法：
git pull --rebase origin main
# 这等于 git fetch origin main + git rebase origin/main
# 让你的本地提交"浮"到最新 main 之后
```

| 场景 | 推荐方式 | 原因 |
|------|---------|------|
| 你独自使用功能分支，且未推送 | Rebase | 保持历史清洁，不产生多余的 merge commit |
| 功能分支已推送，队友也在用 | Merge | 不重写已共享的历史，不破坏队友的开发环境 |
| 合并功能到主分支 | Merge (PR) | 保留合并上下文，方便回溯"这个功能什么时候合进来的" |
| 同步主分支的最新代码 | Merge 或 Rebase 看团队约定 | 两种方式都常见，团队统一即可 |
| 想整理自己杂乱的提交 | Rebase -i (未推送前) | 交互式 rebase 可以合并、编辑、删除 commit |

**一个实用的工作流：** 在功能分支开发期间，频繁 `git pull --rebase origin main` 保持同步（历史干净）。功能开发完，`git push` 后通过 PR 合并回 main（用 merge commit 记录"这个功能被接受了"）。

---

## 第四章 --no-ff——强制保留合并痕迹

### 4.1 什么是 Fast-Forward Merge

当你要把一个分支合并到另一个分支时，如果目标分支没有新的提交（即两个分支在一条直线上），Git 默认会执行 **fast-forward（快进）合并**——它只是把指针向前移动，不创建任何新 commit。

```bash
# 情况：feature 从 main 分出来，main 在此期间没有新提交
main:     A ← B
                \
feature:        C ← D

# git switch main && git merge feature
# 结果（fast-forward）:
main:     A ← B ← C ← D
```

**什么也没有发生**——没有 merge commit，没有合并记录。main 的指针直接跳到 feature 的位置。

### 4.2 Fast-Forward 的问题

快速合并完后，你无法从历史中看出"这里曾经是一个功能分支被合并进来"。历史看起来就像所有工作都在 main 上依次完成的。

```bash
# 没有 --no-ff 的历史:
git log --oneline --graph
* d345678 feat: complete cart feature
* b234567 feat: add cart persistence
* a123456 feat: user login

# 你问我"c345678 到 d345678 之间发生了啥"？
# 我要说"哦这里是一个功能分支合并"，但从历史根本看不出来。
```

### 4.3 --no-ff 做了什么

`--no-ff` 告诉 Git：**即使可以 fast-forward，也强制创建一个 merge commit。**

```bash
git switch main
git merge --no-ff feature/cart
```

```
# 有 --no-ff 的历史:
git log --oneline --graph
*   e89abc2 Merge branch 'feature/cart'   ← 这个 merge commit 记录了合并事件
|\
| * d345678 feat: complete cart feature
| * b234567 feat: add cart persistence
|/
* a123456 feat: user login
```

**这个 merge commit 包含了什么信息？**
- 合并的时间点
- 合并的是哪个功能分支
- 合并前后的代码版本
- 如果有冲突，合并时解决冲突的记录

### 4.4 什么时候应该用 --no-ff

| 场景 | 是否使用 --no-ff | 原因 |
|------|-----------------|------|
| 功能分支合并到 main | ✅ 是 | 让"这个功能是什么时候合入的"一目了然 |
| hotfix 合并到 main | ✅ 是 | 紧急修复的可追溯性很重要 |
| 开发中的小分支合并到 develop | ❌ 不一定 | 过于频繁的 merge commit 会让历史杂乱 |
| 一个单体功能的提交 | ❌ 可以不用 | 如果只有 1-2 个 commit，fast-forward 也 ok |

**Git Flow 通常强制 --no-ff。** 因为 Git Flow 本身就有多条长期分支，merge commit 是追踪"什么从哪到哪"的唯一线索。

**GitHub Flow 则不强制。** GitHub 的 PR 合并有 3 种模式：
1. **Create a merge commit**（等于 --no-ff）
2. **Squash and merge**（把所有 commit 压缩成一个再合并）
3. **Rebase and merge**（在 main 上重放你的 commit，保持线性历史）

这三种选择各有适用场景，GitHub 让你自行选择，而不是强制某一种。

---

## 第五章 Fetch 与 Pull——怎么理解"远程"

### 5.1 远程仓库不是"同步副本"

初学者的常见误解：认为远程仓库（GitHub/GitLab）是本地的同步副本——你在本地改了文件，远程就自动更新了。

**事实是：远程和本地是两个独立的 Git 仓库，各有各的 commit 历史。它们通过 push / fetch 来交换数据。**

```
你的电脑                           GitHub / GitLab
┌──────────────┐                ┌────────────────────┐
│ 本地仓库      │  ← push/fetch →│ 远程仓库(origin)    │
│ .git/objects  │                │ .git/objects       │
│ main @ abc123 │                │ main @ def456      │
│ refs/heads/*  │                │ refs/heads/*       │
└──────────────┘                └────────────────────┘
```

### 5.2 git fetch——只拿来，不合并

```bash
git fetch origin
```

这行命令做了两件事：

1. **从远程下载所有本地没有的 commit 和对象**——把远程的更新拉到本地的 `.git` 里
2. **更新远程跟踪分支**——把 `origin/main`、`origin/develop` 这些本地保存的"远程分支镜像"更新到最新

**fetch 不会改变你的工作区，不会改变你的本地分支，不会改变你正在修改的文件。**

```bash
# fetch 之后的状态:
git log --oneline main        # 还是你本地的 main，没有变
git log --oneline origin/main # 这是远程 main 的最新状态，可能比本地 main 多了几个 commit

# 查看本地分支和远程分支的差异:
git log --oneline main..origin/main
# 这显示"在 origin/main 上但不在 main 上的 commit"——你落后了多少
```

**什么情况下只用 fetch 不够？** Fetch 只拉数据，不改工作区。你拉完还需要手动 `git merge origin/main` 或 `git rebase origin/main` 才能让你的本地分支追上远程。

```bash
# fetch + manual merge 等价于 pull (merge 模式)
git fetch origin
git log --oneline main..origin/main   # 先看清楚远程多了什么
git merge origin/main                 # 确认没问题再合并

# 为什么这样做更好？
# 你可以先看差异，再决定要不要合并
# 如果远程有你不想要的提交（比如同事不小心 push 了实验性代码），你可以不 merge
```

### 5.3 git pull——fetch + merge 的快捷方式

```bash
git pull origin main
# 等价于:
git fetch origin main    # 拉取远程 main 的最新 commit
git merge origin/main    # 自动合并到当前分支

git pull --rebase origin main
# 等价于:
git fetch origin main    # 拉取远程 main 的最新 commit
git rebase origin/main   # 用 rebase 方式合并（而不是 merge）
```

**为什么你感觉不到 fetch？** 因为 `git pull` 把 fetch 和 merge 绑定在了一起，一步完成。大部分时候这没问题，但当你遇到以下情况时，理解 fetch 和 pull 的区别就很重要了：

**场景：git pull 提示冲突了**
```bash
$ git pull origin main
Auto-merging app.py
CONFLICT (content): Merge conflict in app.py
Automatic merge failed; fix conflicts and then commit the result.
```

如果你用的是 `git fetch` + `git merge` 分开做，你可以：
1. `git fetch`——先看看远程有哪些新 commit
2. `git log --oneline main..origin/main`——评估冲突的风险
3. 确定不会出大问题，再 `git merge origin/main`

而 `git pull` 直接把 fetch 和 merge 绑在一起，想"先看看再决定"都来不及。

### 5.4 三种方式的对比

```bash
# 1. git fetch + git merge（最安全）
git fetch origin
git log --oneline main..origin/main    # 看看远程多了什么
git merge origin/main                  # 没问题再合并

# 2. git pull（最常用）
git pull origin main                   # 一步到位

# 3. git pull --rebase（最干净）
git pull --rebase origin main          # 保持线性历史
```

| 命令 | 做了什么 | 适合场景 |
|------|---------|---------|
| `git fetch` | 只下载远程数据，不改变本地分支 | 想先看看远程有什么变化，再决定怎么处理 |
| `git pull` | fetch + merge | 想要一步更新，接受默认的 merge 行为 |
| `git pull --rebase` | fetch + rebase | 想保持历史线性，且当前分支只有你自己在用 |

**一个实用建议：** 对于大多数日常开发，用 `git pull --rebase` 而不是 `git pull`。因为 `git pull` 的 merge 会产生多余的 "Merge remote-tracking branch 'origin/main'" commit，多人多次 pull 后，历史会非常乱。`git pull --rebase` 让你的提交始终在远程最新代码之后，历史是一条干净的直线。

### 5.5 什么时候不能用 --rebase 的 pull

还记得黄金法则吗？如果你的分支上的 commit 已经 push 到远程了，**且**其他队友正基于它工作，那你 `git pull --rebase` 就等于是把已共享的 commit rebase 了——这就会破坏队友的本地历史。

**解决方案：** 在共享分支上，用 `git pull`（merge 模式），不用 `--rebase`。

---

## 第六章 冲突解决——当 Git 无法自动决定时

### 6.1 冲突为什么会发生

Git 的合并和 rebase 大多数情况下能自动完成。做法是：对比两个分支的共同祖先和你分别做的修改，如果改的是**不同文件的不同位置**，Git 直接把两个改动都保留下来。

但当**两人改了同一个文件的同一块代码**时，Git 就不知道谁对谁错了——这就是冲突。

```bash
# 小张在 main 上改了 app.py 的第 10 行:
print("Version 2.0")

# 小李在 feature 分支上也改了 app.py 的第 10 行:
print("Version 2.1")

# 当合并时:
git merge feature
# CONFLICT (content): Merge conflict in app.py
# Automatic merge failed; fix conflicts and then commit the result.
```

**冲突的本质**：不是 Git 的技术问题，是**人的协作问题**。两人同时改了一段代码，并且没有事先沟通——Git 无法替你们做这个决定。

### 6.2 冲突标记的含义

当冲突发生时，Git 会在冲突文件中插入**冲突标记**：

```python
def greet():
<<<<<<< HEAD                    # HEAD = 当前分支（你正在合并到的分支）
    print("Hello, World!")       # 你的版本
=======                          # 分隔线
    print("Hello, Everyone!")    # 被合并的版本（feature 分支）
>>>>>>> feature                  # feature = 被合并进来的分支
```

冲突标记的含义：

| 标记 | 含义 |
|------|------|
| `<<<<<<< HEAD` | 从这里开始是当前分支的代码 |
| `=======` | 分隔当前分支和被合并分支的代码 |
| `>>>>>>> feature` | 从这里开始是被合并的 feature 分支的代码 |

**解决冲突就是：你把冲突标记删掉，保留（或重写）你想要的代码。**

```python
# 解决后的 app.py:
def greet():
    print("Hello, World and Everyone!")  # 结合了两边的内容
```

### 6.3 三种基本冲突解决方式

```bash
# 1. 保留自己的版本
# 删掉 <<<<<<<, =======, >>>>>>> 和 feature 的代码

# 2. 保留对方的版本
# 删掉 <<<<<<<, =======, HEAD 的代码 和 >>>>>>>

# 3. 手动合并
# 把两边的代码结合起来，或者重写一个新的实现
```

### 6.4 解决冲突的完整流程

```bash
# 假设你在 feature 分支上，正在合并 main:
git merge main
# 输出: CONFLICT (content): Merge conflict in src/app.py

# 第一步：查看哪些文件有冲突
git status
# 你会看到：
# both modified:   src/app.py
# both modified:   src/utils.py

# 第二步：查看具体冲突
git diff
# 对比工作区和暂存区的差异，显示冲突内容

# 或者用更直观的方式打开文件
# VS Code 会高亮冲突区块，提供 "Accept Current / Accept Incoming / Accept Both" 按钮

# 第三步：逐块解决冲突
# 打开 src/app.py，找到 <<<<<<< HEAD 标记，决定保留哪段代码

# 第四步：标记为已解决
git add src/app.py
git add src/utils.py

# 第五步：完成合并
git commit
# 这会打开一个编辑器，里面是默认的 merge commit message
# 你可以保留它，也可以修改
```

### 6.5 使用可视化工具解决冲突

对于复杂的冲突，命令行方式不够直观。可以配置并使用 merge tool：

```bash
# 配置 VS Code 作为 merge tool
git config --global merge.tool vscode
git config --global mergetool.vscode.cmd 'code --wait $MERGED'

# 或者用内置的 vimdiff
git config merge.tool vimdiff

# 解决冲突时：
git mergetool
# 这会打开可视化工具，显示三个面板：
# - LOCAL (你的本地版本)
# - BASE (共同祖先版本)
# - REMOTE (被合并分支版本)
# 中间面板显示合并结果，你可以手动编辑
```

### 6.6 如何尽量减少冲突

**冲突不是技术问题，是沟通问题。** 以下做法可以显著减少冲突：

**1. 频繁同步主分支**

```bash
# 每天至少同步一次
git fetch origin
git rebase origin/main   # 或者 git merge origin/main
# 你落后得越少，冲突的概率就越低
```

**2. 代码解耦——减少同时改同一文件的可能性**

如果两个团队成员经常在同一个文件上产生冲突，说明这个文件**承担了太多职责**。考虑拆分它：

```bash
# 一个 1000 行的 app.py → 拆成:
models.py       # 数据模型
views.py        # 视图逻辑
services.py     # 业务逻辑
utils.py        # 工具函数
```

**3. 小提交 + 原子性**

```bash
# ❌ 不好：一周后提交一个大改动
git add . && git commit -m "lots of changes"
# 冲突时很难定位具体改了什么地方

# ✅ 好：每次只做一件事
git commit -m "feat: add user login form"
git commit -m "feat: implement authentication logic"
git commit -m "refactor: extract password validation"
# 冲突时更容易理解冲突的上下文
```

**4. 清楚的职责划分**

最好的避免冲突的方式：两个人不同时改同一段代码。这需要在任务拆解阶段就想清楚模块边界。

### 6.7 冲突的进阶理解——为什么有时不会冲突

Git 的智能体现在：**同一文件的不同位置被修改，不会冲突。**

```bash
# 小张改了 app.py 的 1-10 行
# 小李改了 app.py 的 50-60 行
# 合并时：Git 自动保留两者，没有冲突
```

**Git 的合并算法（三路合并）：**

```
    共同祖先 (Base)
    /          \
   A           B  (两个分支)
    \          /
     合并结果 (Merge Result)

算法:
- 对比 Base 和 A 的差异 → diff(A)
- 对比 Base 和 B 的差异 → diff(B)
- 如果 diff(A) 和 diff(B) 修改了不同的行 → 自动应用两者
- 如果 diff(A) 和 diff(B) 修改了同一行 → 冲突，等人决定
```

这就是为什么 Git 的自动合并比许多旧版本控制系统（如 SVN）更强大——SVN 的合并基于文件级别的差异追踪，而 Git 的"三路合并"基于内容级别的差异追踪，能更精确地判断什么变了、什么没变。

**「三路合并」的「三路」指哪三路？** 就是三个版本：共同祖先(Base)、当前分支(HEAD)、被合并分支(MERGE_HEAD)。有了共同祖先作为参考点，Git 才能判断每个分支上"哪些行是新增的"、"哪些行是删除的"、"哪些行是被修改的"。

---

## 第七章 工作流实战演练

### 7.1 单人开发：最简单的 GitHub Flow

```bash
# 初始化项目
git init
git add .
git commit -m "init: project setup"
git remote add origin https://github.com/yourname/project.git
git push -u origin main

# 开发新功能
git switch -c feature/login-page
# ...写代码...
git add . && git commit -m "feat: add login page layout"
# ...继续开发...
git add . && git commit -m "feat: implement login validation"
# 推送到远程，创建 PR
git push origin feature/login-page
# → GitHub 上 Create Pull Request → Review → Merge
```

### 7.2 多人协作：标准的 Git Flow 场景

```bash
# 场景：线上版本 v1.0，你在开发 v1.1，突然线上 bug
# 当前你在 develop 分支，正在开发 v1.1 的功能

# Step 1: 遇到线上 bug，需要修 v1.0
git stash                                    # 保存当前未提交的改动，清理工作区
git switch main                             # 切回 main
git pull origin main                        # 确保本地 main 和远程一致
git switch -c hotfix/crash-bug              # 从 main 创建 hotfix 分支
# ...修复 bug...
git add . && git commit -m "fix: resolve crash in payment flow"

# Step 2: 部署 hotfix
git switch main
git merge --no-ff hotfix/crash-bug          # 合并到 main，保留合并记录
git tag -a v1.0.1 -m "hotfix: payment crash"  # 打 tag
git push origin main --tags                 # 推送到远程，触发部署

# Step 3: 把 hotfix 也合入 develop
git switch develop
git merge --no-ff hotfix/crash-bug          # 确保 v1.1 也包含这个修复
git branch -d hotfix/crash-bug              # 删除本地 hotfix 分支

# Step 4: 恢复 v1.1 的开发
git stash pop                               # 恢复之前 stash 的未完成代码
# 继续开发...
```

### 7.3 使用 Rebase 的分支同步

```bash
# 场景：feature 分支开发了 2 天，main 已经前进了很多

# Step 1: 看看 main 相比你开始开发时多了什么
git fetch origin
git log --oneline feature/login..origin/main
# 输出：显示了 main 上新增的 5 个 commit

# Step 2: 用 rebase 让 feature 分支保持干净
git switch feature/login
git rebase origin/main

# Step 3: 如果有冲突，解决
# 1. 打开冲突文件，解决冲突
# 2. git add <resolved-files>
# 3. git rebase --continue
# 重复直到所有冲突解决完毕

# Step 4: force push（因为 rebase 重写了历史）
git push --force-with-lease origin feature/login
# --force-with-lease 比 --force 安全：
# 如果远程分支有新提交（队友的），--force-with-lease 会拒绝推送
# 防止你意外覆盖别人的工作
```

**为什么 `--force-with-lease` 比 `--force` 安全？** 假设你和队友都在 feature/login 上工作，你 rebase 后 force push。如果队友在这期间也 push 了新 commit，你的 force push 会**覆盖**队友的提交。`--force-with-lease` 会检查远程分支的最新状态是否还是你 fetch 时的那个版本——如果不是，它就拒绝推送，给你一个"有人在你之前提交了"的警告。

---

## 专题知识：常用 Git 命令速查

### 分支操作

```bash
git branch -a                             # 查看所有分支（包括远程）
git branch -vv                            # 查看本地分支和远程分支的跟踪关系
git switch -c feature/xxx                 # 创建并切换到新分支（推荐，替代 checkout -b）
git branch -d feature/xxx                 # 删除已合并的分支
git branch -D feature/xxx                 # 强制删除未合并的分支（慎用）

# 重命名分支
git branch -m old-name new-name           # 在当前分支上重命名
git branch -m feature/xxx feature/yyy     # 重命名（安全版）
```

### 查看历史

```bash
git log --oneline --graph --all           # 最常用的历史视图
git log --oneline -10                     # 只看最近 10 条
git log --author="Alice" --after="2026-01-01"  # 按作者和时间筛选
git log --grep="fix"                      # 搜索 commit message 包含 fix 的提交

# 查看某个文件的历史
git log -p -- src/app.py                  # 查看 app.py 每次提交的具体改动
git blame src/app.py                      # 每行代码是谁在什么时候改的
```

### 暂存与回退

```bash
git stash                                 # 暂存所有未提交的修改
git stash list                            # 查看暂存列表
git stash pop                             # 恢复最近一次 stash 并删除
git stash apply stash@{2}                 # 恢复指定的 stash 但不删除

git reset HEAD file.txt                   # 从暂存区移出，保留工作区修改
git checkout -- file.txt                  # 撤销工作区的修改（危险！会丢失改动）
git restore file.txt                      # 新式语法，同上
git restore --staged file.txt             # 新式语法，从暂存区移出

git reset --soft HEAD~1                   # 撤销上次 commit，保留工作区和暂存区
git reset --mixed HEAD~1                  # 撤销上次 commit，保留工作区，清空暂存区
git reset --hard HEAD~1                   # 撤销上次 commit，彻底丢弃所有修改（危险！）
```

**一个重要的安全建议：** 不确定自己在做什么的时候，用 `git restore` 而不是 `git reset --hard`。后者会**永久丢失未提交的修改**。

---

## 总结：核心知识点脉络图

```
Git 整体流程
│
├── 底层概念
│   ├── 快照 vs 差异存储
│   ├── 三个区域 (工作区→暂存区→仓库)
│   └── 分支 = 指针
│
├── 分支策略
│   ├── Git Flow (5 种分支，适合固定发布周期)
│   │   ├── main → 已发布代码
│   │   ├── develop → 日常开发主线
│   │   ├── feature/* → 单个功能开发
│   │   ├── release/* → 发布准备
│   │   └── hotfix/* → 紧急修复
│   └── GitHub Flow (1 个长期分支，适合持续部署)
│       └── main + 功能分支 + PR
│
├── 代码合并
│   ├── Merge → 保留真实历史，创建 merge commit
│   ├── Rebase → 重写历史，保持线性
│   ├── --no-ff → 强制创建 merge commit
│   └── 黄金法则 → 永不 rebase 已推送的 commit
│
├── 远程操作
│   ├── fetch → 只下载，不改本地
│   ├── pull → fetch + merge / rebase
│   └── pull --rebase → 保持历史干净
│
└── 冲突解决
    ├── 冲突标记含义 (<<<<< / ===== / >>>>>)
    ├── 解决流程 (识别→解决→标记→提交)
    ├── 三路合并算法 (Base / HEAD / MERGE_HEAD)
    └── 减少冲突的策略
```

---
