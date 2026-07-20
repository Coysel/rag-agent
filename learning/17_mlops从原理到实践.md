# 第十七部分：MLOps 概念

## 一、从 DevOps 到 MLOps：为什么机器学习需要专属的运维体系？

### 1.1 什么是 DevOps？先理解软件工程中的"开发运维一体化"

在理解 MLOps 之前，我们需要先理解它的父概念——**DevOps**。

DevOps 是 Development（开发）和 Operations（运维）的合成词，它并不是一个具体的工具或技术，而是一套**文化、实践和流程**，目的是打破软件开发团队和运维团队之间的壁垒。

**传统软件开发的问题：**

在没有 DevOps 的时代，软件开发和运维是泾渭分明的两个团队：

- **开发团队**的职责是写代码、实现功能。他们追求的是"快速上线新功能"。
- **运维团队**的职责是保证系统稳定运行。他们追求的是"不要出问题，不要变更"。

这两个目标天然冲突。开发说"赶快上线"，运维说"再测试一下"。结果是：

```
开发写完代码 ──→ 扔给运维 ──→ 运维部署 ──→ 出问题 ──→ 互相推诿
                          ↑                       
                      "在我机器上能跑啊！"             
```

这被称为" throw over the wall"（扔过墙）模式——开发把代码包扔给运维，之后就不再管了。

**DevOps 的核心思想：**

DevOps 的解决思路是：**谁开发，谁运维**。开发团队不仅要写代码，还要负责代码的部署、监控和故障处理。这样，开发人员在设计系统时就会自然考虑"这个系统好不好运维"的问题。

具体来说，DevOps 落地为以下实践：

| 实践 | 说明 | 解决什么问题 |
|------|------|-------------|
| **CI/CD（持续集成/持续部署）** | 每次代码提交自动触发构建、测试、部署 | 人工部署容易出错，流程慢 |
| **基础设施即代码（IaC）** | 用代码定义服务器、网络、数据库等基础设施 | 手动配置环境不一致，难以复现 |
| **监控与告警** | 实时监控系统指标，异常时自动告警 | 出了问题没人知道 |
| **日志聚合** | 集中收集所有服务的日志，方便排查问题 | 问题排查时逐个登录服务器翻日志 |
| **不可变基础设施** | 服务器出问题时直接替换，而不是修复 | 手动修复导致配置漂移，越修越乱 |

一个典型的 CI/CD 流水线：

```
代码提交 ──→ 自动构建 ──→ 自动测试 ──→ 自动部署到预发布环境 ──→ 自动部署到生产环境
   ↑                                                                  │
   └────────────────────── 发现Bug，修复代码 ──────────────────────────┘
```

> **关键理解**：DevOps 的本质是将"运维"从开发完成后的一道工序，变成贯穿整个软件生命周期的持续活动。

### 1.2 为什么 DevOps 不够用？——ML 系统的特殊挑战

DevOps 完美解决了传统软件的问题。但当我们将 DevOps 应用到机器学习系统时，发现它远远不够。这是因为机器学习系统与传统软件有**本质的不同**。

**传统软件 vs 机器学习系统的核心差异：**

| 维度 | 传统软件 | 机器学习系统 |
|------|----------|-------------|
| **产品是什么** | 代码（确定的逻辑） | 代码 + 数据 + 模型 |
| **行为是否固定** | 是——同样的输入永远产生同样的输出 | 否——模型的行为由训练数据决定，可能无法预测 |
| **错误如何发现** | 编译错误、运行时异常、测试断言失败 | 模型在特定样本上表现差，难以提前发现 |
| **性能退化方式** | 很少退化（除非有Bug） | 必然退化——数据分布变化导致模型效果下降 |
| **出问题后怎么办** | 回滚到上一个版本即可 | 回滚不一定有用（数据已经变了），可能需要重新训练 |

用一个具体的案例来理解这个差异：

```
传统软件：
  if user.age > 18:
      allow_access()
  
  这条逻辑是确定的。只要代码没改，行为就不会变。
  即使运行十年，年龄判断的逻辑依然正确。

机器学习模型：
  一个信用评分模型，根据用户的收入、消费记录、历史还款等特征判断信用等级。
  
  问题：2020年训练好的模型，到了2024年——
  - 用户的消费模式可能已经变了（数据漂移）
  - "好信用"的定义可能变了（概念漂移）
  - 模型的效果会不知不觉地下降
  - 你甚至不知道它开始出问题了，直到用户投诉
  
  "模型在训练时准确率95%，上线六个月后准确率降到了82%，
   没有人发现，因为没有人盯着它。"
```

这就是为什么需要 **MLOps（Machine Learning Operations）**——一套专门为机器学习系统设计的运维实践。

### 1.3 MLOps 的定义与核心目标

MLOps 是 Machine Learning 和 Operations 的合成词，也被称为 **ML 工程化**。它是一套将机器学习模型从开发到生产部署、监控和维护的标准化流程和最佳实践。

MLOps 的核心目标可以概括为三个：

```
MLOps 三大目标：

1. 可重复（Reproducible）
   ─ 同样的数据 + 同样的代码 = 同样的模型
   ─ 解决"我明明得到了92%的准确率，为什么部署时只有85%？"

2. 可追溯（Traceable）
   ─ 任何时候都能回答：这个模型是用什么数据、什么代码、什么参数训练的？
   ─ 解决"生产环境的模型是哪个版本？训练数据是哪份？"

3. 持续交付（Continuous Delivery）
   ─ 模型从训练到部署的流程自动化
   ─ 新数据来了自动触发重新训练，新模型自动上线
```

**MLOps 和 DevOps 的对比总结：**

| 对比维度 | DevOps | MLOps |
|----------|--------|-------|
| **核心产物** | 代码 | 代码 + 数据 + 模型 |
| **主要挑战** | 代码Bug、部署失败、服务宕机 | 数据漂移、概念漂移、模型退化、可重复性 |
| **CI/CD 含义** | 代码集成与部署 | 代码 + 数据 + 模型 的集成与部署；增加了 CT（持续训练） |
| **测试范围** | 单元测试、集成测试 | 以上 + 数据验证、模型评估、公平性测试 |
| **版本控制** | 代码版本控制（Git） | 代码 + 数据 + 模型 三者的版本控制 |
| **监控重点** | 系统指标：CPU、内存、延迟、错误率 | 以上 + 模型指标：预测分布、特征分布、准确率 |
| **回滚方式** | 回滚代码版本 | 回滚模型版本（但可能数据已变，旧模型不一定有效） |

> **记住这个核心区别**：在 DevOps 中，代码的行为是确定的，你部署了什么就能得到什么。在 ML 中，模型的行为是由数据和代码共同决定的——你部署了同一个模型，但线上的数据分布变了，模型的行为就会变。这就是 MLOps 要解决的核心问题。

---

## 二、MLOps 六步生命周期——从数据到生产再到监控

MLOps 将机器学习项目的生命周期划分为六个阶段，每个阶段都有明确的目标和产出。这六个阶段构成了一个**闭环**，永不停歇。

```
                  ┌─────────────┐
                  │  数据管理    │
                  │ (Data Mgmt) │
                  └──────┬──────┘
                         ▼
                  ┌─────────────┐
                  │  特征工程    │
                  │ (Feat Eng)  │
                  └──────┬──────┘
                         ▼
                  ┌─────────────┐
                  │  模型训练    │
                  │ (Training)  │
                  └──────┬──────┘
                         ▼
                  ┌─────────────┐
                  │  模型评估    │
                  │ (Evaluation)│
                  └──────┬──────┘
                         ▼
                  ┌─────────────┐
                  │  模型部署    │
                  │ (Deploy)    │
                  └──────┬──────┘
                         ▼
                  ┌─────────────┐
                  │  监控与反馈  │←──── 回到数据管理（闭环）
                  │ (Monitoring)│
                  └─────────────┘
```

下面我们逐一深入每个阶段。

### 2.1 第一阶段：数据管理（Data Management）

#### 2.1.1 这个阶段在做什么？

数据管理是 MLOps 流水线的起点，也是**最重要的阶段**——"垃圾进，垃圾出"（Garbage In, Garbage Out）是机器学习的第一定律。如果数据有问题，后面的一切都是徒劳。

这个阶段包含三个核心活动：

**活动一：数据采集（Data Collection）**

从哪里获取数据？常见的数据源包括：

- **业务数据库**：用户行为日志、交易记录、订单数据等
- **外部 API**：天气预报、股票行情、地图数据等第三方服务
- **日志文件**：服务器日志、应用日志中提取的用户行为模式
- **人工标注**：对于监督学习，需要人工标注标签数据
- **数据合成**：在数据不足时，通过规则或生成模型创造数据

```python
# 数据采集示例：从多个源聚合数据
# 实际生产中，数据往往分散在不同系统中，需要整合

import pandas as pd
from sqlalchemy import create_import

# 1. 从业务数据库采集用户交易数据
def collect_transaction_data(start_date, end_date):
    engine = create_engine("postgresql://user:pass@prod-db:5432/ecommerce")
    query = f"""
        SELECT user_id, amount, category, timestamp
        FROM transactions
        WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
    """
    return pd.read_sql(query, engine)

# 2. 从日志文件采集用户行为数据
def collect_user_behavior_logs(date):
    # 日志文件存储在 S3 上，每天一个分区
    log_path = f"s3://ecommerce-logs/behavior/{date}/part-*.parquet"
    return pd.read_parquet(log_path)

# 3. 合并数据
def build_training_dataset(start_date, end_date):
    transactions = collect_transaction_data(start_date, end_date)
    behaviors = collect_user_behavior_logs(start_date)
    # 按用户ID合并两个数据源
    dataset = transactions.merge(behaviors, on="user_id", how="left")
    return dataset
```

**活动二：数据验证（Data Validation）**

数据验证的目的是在数据进入流水线之前就发现问题。典型的检查包括：

- **完整性检查**：必需的字段是否有缺失值？缺失率是否在可接受范围内？
- **范围检查**：数值特征是否在合理范围内？（比如年龄不可能为负值，温度不会低于-100°C）
- **唯一性检查**：ID 字段是否有重复？
- **分布检查**：特征分布是否与预期一致？（比如突然所有用户的年龄都变成了 0，说明数据采集出了问题）

```python
# 数据验证示例：用 Great Expectations 库做数据验证
# Great Expectations 是 MLOps 中常用的数据验证工具

import great_expectations as ge

def validate_training_data(df):
    # 将 DataFrame 包装为 Great Expectations 的 ExpectationSuite
    ge_df = ge.dataset.PandasDataset(df)
    
    # 验证1：user_id 不应该有空值
    expectations = []
    expectations.append(ge_df.expect_column_values_to_not_be_null("user_id"))
    
    # 验证2：年龄应该在 0-120 之间
    expectations.append(ge_df.expect_column_values_to_be_between("age", 0, 120))
    
    # 验证3：交易金额应该为正数
    expectations.append(ge_df.expect_column_values_to_be_between("amount", 0, 1000000))
    
    # 验证4：类别列的值应该在预期的集合中
    expected_categories = ["食品", "交通", "购物", "娱乐", "医疗"]
    expectations.append(ge_df.expect_column_values_to_be_in_set("category", expected_categories))
    
    # 统计验证失败的条数
    failures = [e for e in expectations if not e.success]
    if failures:
        print(f"数据验证失败！{len(failures)} 项检查未通过")
        for f in failures:
            print(f"  - {f.expectation_config.expectation_type}: 失败率 {f.result['unexpected_percent']:.2f}%")
        return False
    return True
```

**活动三：数据版本控制（Data Versioning）**

这可能是初学者最不理解的概念——**为什么数据需要版本控制？**

想象这个场景：你训练了一个模型，A/B 测试效果很好，于是部署到生产环境。两个月后，你发现模型效果下降了，你决定重新训练。但问题是：**你还能拿到两个月前训练模型时用的那批数据吗？**

- 原始数据可能已经被新的数据覆盖了
- 数据库中的数据可能已经更新了
- 日志文件可能已经被清理了

如果不能重现训练数据，你就无法定位"模型效果下降到底是因为数据变了，还是模型需要调整"。

这就是数据版本控制的用途。实践中常用 **DVC（Data Version Control）** 或 **LakeFS** 来管理数据版本：

```bash
# DVC 数据版本控制示例
# DVC 像 Git 管理代码一样管理数据和模型文件

# 1. 初始化 DVC
dvc init

# 2. 添加数据到 DVC 追踪（将数据集添加到版本控制）
dvc add data/training_data_v3.parquet
# 这会在 data/ 下生成一个 .dvc 文件，记录数据的哈希值和路径

# 3. 提交到 Git
git add data/training_data_v3.parquet.dvc
git commit -m "添加训练数据集 v3，包含2024年全量数据"

# 4. 推送到远程存储（S3/GCS/Azure Blob）
dvc push

# 5. 以后需要恢复到这个版本时
git checkout v3.0        # 恢复代码到 v3.0 的 commit
dvc checkout             # 同步数据到这个 commit 对应的版本
# 现在你的工作目录中的数据和训练 v3.0 模型时的数据完全一致
```

**为什么数据版本控制如此重要？**

```
没有数据版本控制的问题链：

模型效果下降 
  → 想重新训练一个更好的模型
  → 但训练数据的来源已经变了
  → 无法确定是新数据好还是老数据好
  → 浪费大量时间在"数据考古"上
  → 最终放弃，拍脑袋决定

有数据版本控制后的流程：

模型效果下降 
  → 从 Git 中找到当时训练模型所用的代码和数据版本
  → 用 git checkout + dvc checkout 精确复现训练环境
  → 确定问题出在数据漂移还是模型本身
  → 有针对性地改进
```

### 2.2 第二阶段：特征工程（Feature Engineering）

#### 2.2.1 这个阶段在做什么？

特征工程是将原始数据转化为机器学习模型可以理解的**特征（Features）** 的过程。这是 ML 开发中最具创意、也最耗时的环节。

为什么需要特征工程？因为原始数据通常不能直接喂给模型：

- **文本**：模型不认识"苹果很好吃"这个句子，它只认识数字
- **类别**："红色"、"蓝色"、"绿色"这些值不能直接输入，需要编码
- **数值分布不均匀**：有些特征的数值范围很大（收入 0~1000万），有些很小（年龄 0~100），模型会对大数值的特征更"敏感"
- **缺失值**：原始数据中很多字段是空的，模型不知道该怎么处理

特征工程的核心操作：

| 操作 | 说明 | 举例 |
|------|------|------|
| **编码（Encoding）** | 将非数值数据转为数值 | 独热编码：`"红色"→[1,0,0]`；标签编码：`"红色"→0` |
| **标准化/归一化（Scaling）** | 将不同量纲的特征缩放到同一范围 | Z-score 标准化：`(x - μ) / σ` |
| **缺失值处理（Imputation）** | 填充或删除缺失值 | 用均值填充、用中位数填充、用前向值填充 |
| **特征交叉（Crossing）** | 将两个或多个特征组合成新特征 | `年龄 × 收入`、`星期几 × 时段` |
| **特征选择（Selection）** | 筛选出最有用的特征，去掉噪音 | 过滤低方差特征、基于模型重要性选择 |

#### 2.2.2 为什么需要特征存储（Feature Store）？

在大规模 ML 系统中，特征工程面临一个很实际的问题：**训练时用的特征和推理时用的特征必须完全一致**。

听起来很简单？但实际中经常出现这样的问题：

```
问题场景：

训练阶段：
  数据科学家小张写了一段代码，从原始交易数据中提取了"用户近30天平均消费金额"这个特征。
  模型训练时，这个特征的效果很好，模型 AUC 达到 0.92。

推理阶段（模型上线后）：
  模型需要实时打分——用户来了，模型要判断这个用户是否可能违约。
  但"用户近30天平均消费金额"需要在推理时重新计算。
  小张写的特征是 pandas 代码，线上用的是 Flink 实时流处理。
  两个人对"近30天"的理解不同：
  - 训练代码：取数据中最近30天的所有记录
  - 线上代码：取当前时间往前推30天的记录
  - 结果：同一个用户在训练和推理时得到的特征值不同！
  - 模型表现从 0.92 AUC 降到 0.75

这就是"训练-推理偏差"（Training-Serving Skew）的经典案例。
```

**特征存储（Feature Store）** 就是为了解决这个问题而生的。它是一个集中管理特征的中心化平台，核心功能包括：

1. **特征定义统一**：所有特征的计算逻辑在一个地方定义，训练和推理共用同一份代码
2. **特征共享与复用**：不同团队可以复用已有的特征，不需要重复开发
3. **在线/离线一致性**：保证训练时的特征计算逻辑和线上推理时完全一致
4. **特征回溯**：可以快速生成历史上某个时间点的特征数据

```
特征存储的架构：

                    ┌─────────────────────────────────────┐
                    │           Feature Store             │
                    │                                     │
                    │  ┌──────────────┐  ┌──────────────┐ │
                    │  │ 离线特征表    │  │ 在线特征表    │ │
                    │  │ (批处理)     │  │ (实时)       │ │
                    │  └──────────────┘  └──────────────┘ │
                    │         ↑                ↑          │
                    └─────────┼────────────────┼──────────┘
                              │                │
                    ┌─────────┘                └─────────┐
                    ▼                                    ▼
            ┌──────────────┐                    ┌──────────────┐
            │ 训练流水线    │                    │ 推理服务      │
            │ (Training)   │                    │ (Serving)    │
            └──────────────┘                    └──────────────┘
```

Python 中常用的特征工程操作示例：

```python
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder

def engineer_features(raw_df):
    """将原始数据转化为模型可用的特征"""
    df = raw_df.copy()
    
    # 1. 缺失值处理
    # 为什么用中位数而不是均值？因为中位数对异常值更鲁棒
    # 如果某个用户是亿万富翁，均值会被拉高，但中位数不受影响
    df['age'].fillna(df['age'].median(), inplace=True)
    df['income'].fillna(df['income'].median(), inplace=True)
    
    # 2. 创建时间特征（从时间戳中提取）
    # 将 transaction_time 从字符串转为时间对象
    df['transaction_datetime'] = pd.to_datetime(df['transaction_time'])
    df['hour_of_day'] = df['transaction_datetime'].dt.hour       # 在哪个小时交易？
    df['day_of_week'] = df['transaction_datetime'].dt.dayofweek   # 周几交易？
    # 为什么提取这些？用户的消费行为有明显的"时间模式"
    # 比如：深夜交易可能意味着异常行为，周末消费模式与工作日不同
    
    # 3. 聚合特征（从交易历史中统计）
    # 一个用户的特征不仅来自他当前这条记录，还来自他的历史行为
    user_stats = df.groupby('user_id').agg({
        'amount': ['mean', 'std', 'max', 'count'],  # 平均消费、波动、峰值、频率
        'category': lambda x: x.nunique()            # 涉及多少种消费类别？
    })
    user_stats.columns = ['avg_amount', 'std_amount', 'max_amount', 'txn_count', 'category_diversity']
    df = df.merge(user_stats, on='user_id', how='left')
    
    # 4. 类别特征编码
    # 将"食品"、"交通"等文字转为数字
    encoder = LabelEncoder()
    df['category_encoded'] = encoder.fit_transform(df['category'])
    
    # 5. 数值特征标准化
    # 为什么需要标准化？许多模型（如 SVM、KNN、神经网络）对特征量纲敏感
    # "收入"的范围是 0~1000万，"年龄"的范围是 0~100
    # 如果不标准化，模型会认为"收入"比"年龄"重要 10 万倍
    numerical_cols = ['age', 'income', 'avg_amount', 'txn_count']
    scaler = StandardScaler()
    df[numerical_cols] = scaler.fit_transform(df[numerical_cols])
    
    return df
```

### 2.3 第三阶段：模型训练（Model Training）

#### 2.3.1 这个阶段在做什么？

模型训练是 ML 项目中最"性感"的阶段——数据科学家在这里尝试各种算法、调参、提升指标。但从 MLOps 的角度看，训练阶段的核心挑战不是"如何提升准确率"，而是**如何让训练过程可复现、可管理、可审计**。

一个 MLOps 化的训练流程应该包含：

**实验追踪（Experiment Tracking）**

数据科学家每天跑几十个实验：换一个模型、调一个参数、换一组特征。如果没有实验追踪，很快就会陷入混乱：

```
没有实验追踪的噩梦：

Day 1: "跑了一个 XGBoost，AUC 0.88，保存为 model_v1.pkl"
Day 2: "跑了一个 LightGBM，AUC 0.91，保存为 model_v2.pkl"
Day 3: "调整了特征，AUC 0.89，保存为 model_v3.pkl"
...
Day 14: "回到 XGBoost 再试试，AUC 0.90，保存为 model_v8.pkl"
         → 等等，这个 v8 比 v2 的 0.91 低
         → 但 v2 用了哪些特征来着？记不清了
         → v2 的代码还在吗？
         → v2 的配置文件是什么样的？
         → 完了，全都忘了，只能重新跑
```

实验追踪工具（如 MLflow、Weights & Biases、Neptune）自动记录每次实验的：

| 记录项 | 说明 | 为什么重要 |
|--------|------|-----------|
| **代码版本** | 训练时 Git commit 的 hash | 可以精确复现 |
| **超参数** | learning_rate、max_depth、n_estimators 等 | 知道什么参数组合最好 |
| **数据版本** | 训练数据集的文件 hash 或版本号 | 知道模型是用什么数据训练的 |
| **评估指标** | AUC、准确率、召回率、F1 等 | 比较不同模型的效果 |
| **模型产物** | 训练好的模型文件 | 可以直接部署 |
| **环境信息** | Python 版本、库版本 | 避免"环境不一致"导致的复现问题 |

```python
# 使用 MLflow 进行实验追踪
# MLflow 是最流行的开源 MLOps 平台之一

import mlflow
import mlflow.sklearn
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score

def train_and_log_model(X_train, X_test, y_train, y_test, params):
    """训练模型并自动记录所有实验信息"""
    
    # 启动 MLflow 实验追踪
    # 从此刻开始，MLflow 会自动记录代码版本、运行时间等
    with mlflow.start_run(run_name="gbm_experiment_1"):
        
        # 1. 记录超参数
        # 为什么记录？才能知道"哪个参数组合最优"
        mlflow.log_params({
            "learning_rate": params["learning_rate"],
            "max_depth": params["max_depth"],
            "n_estimators": params["n_estimators"],
            "subsample": params["subsample"]
        })
        
        # 2. 训练模型
        model = GradientBoostingClassifier(**params)
        model.fit(X_train, y_train)
        
        # 3. 评估并记录指标
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        auc_score = roc_auc_score(y_test, y_pred_proba)
        mlflow.log_metric("test_auc", auc_score)
        
        # 4. 记录特征重要性（知道哪些特征对模型贡献最大）
        for i, importance in enumerate(model.feature_importances_):
            mlflow.log_metric(f"feature_importance_{i}", importance)
        
        # 5. 保存模型文件（记录模型产物）
        mlflow.sklearn.log_model(model, "model")
        
        # 6. 记录数据源信息（关键！知道这份数据是谁、什么时候生成的）
        mlflow.log_param("dataset_version", "v3.2")
        mlflow.log_param("training_rows", len(X_train))
        mlflow.log_param("test_rows", len(X_test))
        
        print(f"实验完成！AUC = {auc_score:.4f}")
        print(f"MLflow run ID: {mlflow.active_run().info.run_id}")
        
        return model

# 使用示例
params = {
    "learning_rate": 0.05,
    "max_depth": 5,
    "n_estimators": 200,
    "subsample": 0.8
}
model = train_and_log_model(X_train, X_test, y_train, y_test, params)

# 实验完成后，可以在 MLflow UI 中查看所有实验
# 通过网页界面比较不同实验的 AUC、参数等
# 命令：mlflow ui
```

**模型版本控制**

模型文件（.pkl、.pt、.h5 等）通常是二进制文件，不能直接用 Git 追踪（Git 适合文本文件，对大二进制文件效率很低）。MLOps 中通常用**模型注册表（Model Registry）** 来管理模型版本。

模型注册表的核心概念：

```
模型注册表的结构：

模型名称：credit_scoring_model_v2
├── 版本 1 (2024-01-15)
│   ├── 模型文件：s3://models/credit_scoring/v1/model.pkl
│   ├── 训练数据：data_v2.1
│   ├── 评估指标：AUC 0.89, F1 0.72
│   └── 状态：已归档（旧版本）
├── 版本 2 (2024-03-20)
│   ├── 模型文件：s3://models/credit_scoring/v2/model.pkl
│   ├── 训练数据：data_v2.2
│   ├── 评估指标：AUC 0.92, F1 0.76
│   └── 状态：Staging（预发布，正在A/B测试）
├── 版本 3 (2024-05-10)
│   ├── 模型文件：s3://models/credit_scoring/v3/model.pkl
│   ├── 训练数据：data_v3.0
│   ├── 评估指标：AUC 0.94, F1 0.79
│   └── 状态：Production（生产环境）

状态流转：Staging → Production → Archived
         （先验证）  （正式上线）  （淘汰归档）
```

### 2.4 第四阶段：模型评估（Model Evaluation）

#### 2.4.1 这个阶段在做什么？

模型评估不仅仅是看一个"准确率"数字就完事了。在生产环境中，模型评估需要从多个维度考察模型的表现：

**维度一：常规评估指标**

根据任务类型选择合适指标：

| 任务类型 | 常用指标 | 说明 |
|----------|---------|------|
| **二分类** | AUC-ROC、精确率、召回率、F1-score | 需要关注正负样本不平衡问题 |
| **多分类** | Top-1/Top-5 准确率、混淆矩阵 | 需要看模型在哪些类别上容易混淆 |
| **回归** | MSE、MAE、R² | 需要看预测值 vs 真实值的分布 |
| **推荐系统** | NDCG、MRR、Recall@K | 关注排序质量而非绝对精确 |
| **时序预测** | MAPE、sMAPE | 关注预测误差的百分比 |

**维度二：切片评估（Slice Evaluation）**

这是生产环境中极重要但常被忽视的一环。**整体指标好，不代表所有用户群都表现好**。

```python
# 切片评估示例：检查模型在不同群体上的表现差异

def evaluate_by_slices(model, X_test, y_test, df_original):
    """按照不同维度切片评估模型，发现公平性问题"""
    
    results = []
    
    # 整体评估
    y_pred = model.predict(X_test)
    overall_accuracy = (y_pred == y_test).mean()
    results.append(("整体", "全部用户", overall_accuracy))
    
    # 按年龄段切片
    for age_group in ["18-25", "26-35", "36-50", "50+"]:
        mask = df_original.loc[X_test.index, 'age_group'] == age_group
        if mask.sum() > 0:
            acc = (y_pred[mask] == y_test[mask]).mean()
            results.append(("年龄段", age_group, acc))
    
    # 按收入水平切片
    for income_level in ["低收入", "中收入", "高收入"]:
        mask = df_original.loc[X_test.index, 'income_level'] == income_level
        if mask.sum() > 0:
            acc = (y_pred[mask] == y_test[mask]).mean()
            results.append(("收入水平", income_level, acc))
    
    # 打印结果，找出表现差的切片
    for dim, group, acc in results:
        print(f"{dim} - {group}: 准确率 {acc:.3f}")
        if acc < overall_accuracy - 0.1:  # 比整体低10%以上，需要关注
            print(f"  ⚠️ 警告：{group} 的准确率显著低于整体！")
```

```
输出示例：
整体 - 全部用户: 准确率 0.941
年龄段 - 18-25: 准确率 0.952
年龄段 - 26-35: 准确率 0.948
年龄段 - 36-50: 准确率 0.935
年龄段 - 50+: 准确率 0.812
  ⚠️ 警告：50+ 的准确率显著低于整体！

→ 这说明模型对老年用户群体的预测效果不好
→ 可能的原因：训练数据中老年用户样本不足
→ 需要补充老年用户数据重新训练
```

**维度三：对抗验证（Adversarial Validation）**

这是判断"训练数据和线上数据分布是否一致"的巧妙方法：

1. 将训练数据和线上数据合并，打上标签（训练数据=0，线上数据=1）
2. 训练一个分类器，看能否区分两条数据
3. 如果分类器能轻松区分（AUC > 0.8），说明训练数据和线上数据分布差异很大
4. 这意味着模型在线上环境中可能表现很差

```python
# 对抗验证示例

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

def adversarial_validation(train_data, online_data):
    """用对抗验证检测训练数据和线上数据的分布差异"""
    
    # 1. 合并数据并打标签
    train_data['source'] = 0  # 训练数据标记为0
    online_data['source'] = 1  # 线上数据标记为1
    
    combined = pd.concat([train_data, online_data], axis=0)
    X = combined.drop('source', axis=1)
    y = combined['source']
    
    # 2. 训练分类器
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.3)
    clf = RandomForestClassifier(n_estimators=100)
    clf.fit(X_train, y_train)
    
    # 3. 评估分类能力
    y_pred = clf.predict_proba(X_val)[:, 1]
    auc = roc_auc_score(y_val, y_pred)
    
    if auc > 0.8:
        print(f"⚠️ 警告：对抗验证 AUC = {auc:.3f}")
        print("训练数据和线上数据分布差异很大！模型上线后效果可能会下降。")
        print("建议重新采集训练数据，使其更接近线上数据分布。")
    else:
        print(f"✅ 对抗验证 AUC = {auc:.3f}，数据分布基本一致。")
    
    return auc
```

### 2.5 第五阶段：模型部署（Model Deployment）

#### 2.5.1 这个阶段在做什么？

模型部署是将训练好的模型"发布"到生产环境，使其能够处理真实用户请求的过程。但 ML 模型的部署方式有多种选择，每种方式适合不同的场景：

**部署方式一：批处理（Batch Inference）**

定期对一批数据运行模型，产出预测结果存入数据库。

```
适用场景：
  - 推荐系统：每天凌晨计算所有用户的推荐列表，白天直接读取
  - 风控系统：每天批量评估所有用户的信用等级
  - 报表系统：每月生成销售预测报告

工作流程：
  定时任务触发 → 读取最新数据 → 模型推理 → 结果存入数据库/缓存
  
优点：
  - 实现简单，不需要实时服务
  - 可以处理大量数据（批量处理效率高）
  - 可以充分利用计算资源（Spark/分布式计算）

缺点：
  - 预测结果不是实时的（可能有数小时延迟）
  - 不适合需要即时响应的场景
```

```python
# 批处理推理示例：每天凌晨计算用户推荐
# 使用 Apache Spark 处理海量用户数据

from pyspark.sql import SparkSession
import mlflow.pyfunc

def batch_recommendation_job():
    """批处理推荐任务：每天凌晨运行"""
    
    # 1. 加载当天最新数据
    spark = SparkSession.builder.appName("daily_recommendation").getOrCreate()
    user_data = spark.read.parquet("s3://data/user_features/{today}/")
    
    # 2. 从 MLflow Model Registry 加载最新生产模型
    model = mlflow.pyfunc.load_model(
        model_uri="models:/recommendation_model/Production"
    )
    
    # 3. 批量推理（使用 Spark UDF）
    # 将模型包装为 Spark UDF，可以分布式地处理百万级用户
    predict_udf = mlflow.pyfunc.spark_udf(spark, model_uri="models:/recommendation_model/Production")
    predictions = user_data.withColumn("recommendation", predict_udf(*user_data.columns))
    
    # 4. 结果写入推荐表，白天服务直接从数据库读取
    predictions.write.mode("overwrite").parquet("s3://results/recommendations/{today}/")
    print(f"已完成 {predictions.count()} 个用户的推荐计算")
```

**部署方式二：在线推理（Online Inference）**

将模型封装为 REST API，用户请求时实时返回预测结果。

```
适用场景：
  - 欺诈检测：用户下单时需要立即判断是否欺诈
  - 实时翻译：用户输入文本后立即返回翻译结果
  - 个性化搜索：用户搜索时需要实时调整排序

工作流程：
  用户请求 → API Gateway → 模型服务 → 返回预测结果（毫秒级）

优点：
  - 实时响应，用户体验好
  - 可以处理动态变化的情况

缺点：
  - 需要保证低延迟（通常 <100ms）
  - 需要处理高并发请求
  - 对基础设施要求高
```

```python
# 在线推理示例：使用 FastAPI 部署模型为 REST API
# FastAPI 是目前 Python 最流行的异步 Web 框架之一

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mlflow.pyfunc
import numpy as np

app = FastAPI(title="信用评分模型 API")

# 应用启动时加载模型（一次加载，避免每次请求都重新加载）
# 这是性能优化的重要原则：模型加载到内存后常驻
model = mlflow.pyfunc.load_model("models:/credit_scoring_model/Production")

# 定义请求体的数据结构（Pydantic 自动验证输入）
class CreditScoreRequest(BaseModel):
    age: float
    income: float
    transaction_count: int
    avg_transaction_amount: float
    has_overdue: bool

class CreditScoreResponse(BaseModel):
    credit_score: float  # 0~1，越高信用越好
    risk_level: str      # low / medium / high

@app.post("/predict", response_model=CreditScoreResponse)
async def predict(request: CreditScoreRequest):
    """实时信用评分接口"""
    try:
        # 1. 将请求数据转为模型输入的格式
        #     将 Pydantic 模型转为 numpy 数组
        input_data = np.array([[
            request.age,
            request.income,
            request.transaction_count,
            request.avg_transaction_amount,
            int(request.has_overdue)
        ]])
        
        # 2. 模型推理（通常 < 10ms）
        prediction = model.predict(input_data)[0]
        
        # 3. 根据预测分数确定风险等级
        if prediction > 0.8:
            risk_level = "low"
        elif prediction > 0.5:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        return CreditScoreResponse(
            credit_score=float(prediction),
            risk_level=risk_level
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 健康检查接口（用于负载均衡器和服务发现）
@app.get("/health")
async def health():
    return {"status": "ok"}

# 启动命令：
# uvicorn app:app --host 0.0.0.0 --port 8080 --workers 4
```

**部署方式三：边缘推理（Edge Inference）**

模型部署在设备端（手机、IoT 设备、嵌入式系统），在本地完成推理，不需要联网。

```
适用场景：
  - 手机相机的人脸识别
  - 智能音箱的语音唤醒词检测
  - IoT 设备的异常检测

工作流程：
  传感器采集数据 → 设备端推理 → 本地执行决策（不上传云端）

优点：
  - 无延迟（不需要网络请求）
  - 保护用户隐私（数据不出设备）
  - 离线可用

挑战：
  - 设备算力有限（CPU/内存/电池）
  - 需要模型压缩（量化、剪枝、蒸馏）
  - 模型更新困难（需要 OTA 推送）
```

**部署策略：蓝绿部署与金丝雀发布**

模型上线不像"关掉旧的、开启新的"那么简单。如果新模型有问题，可能会影响所有用户。因此 MLOps 中常用以下策略：

| 策略 | 做法 | 风险 | 适用场景 |
|------|------|------|---------|
| **蓝绿部署** | 同时运行两套环境（蓝=旧模型、绿=新模型），切换流量 | 低——切回去很容易 | 大版本更新 |
| **金丝雀发布** | 新模型先接收 1% 的流量，没有问题逐步增加到 100% | 极低——影响面小 | 新模型上线初期 |
| **A/B 测试** | 两个模型同时服务不同用户，比较业务指标 | 低——有对照组 | 验证模型业务效果 |
| **滚动更新** | 逐步替换旧模型实例 | 中——新旧共存 | 小版本迭代 |

```
金丝雀发布的流量控制过程：

Step 1: 新模型接收 1% 流量（观察 30 分钟，没有异常报警）
         ┌─────────────────────────────┐
         │ 旧模型 99%   │ 新模型 1%     │
         └─────────────────────────────┘

Step 2: 增加到 10%（再观察 1 小时）
         ┌─────────────────────────────┐
         │ 旧模型 90%   │ 新模型 10%    │
         └─────────────────────────────┘

Step 3: 增加到 50%（再观察 1 小时）
         ┌─────────────────────────────┐
         │ 旧模型 50%   │ 新模型 50%    │
         └─────────────────────────────┘

Step 4: 新模型 100%（旧模型保留，随时可以切回）
         ┌─────────────────────────────┐
         │ 新模型 100%                 │
         └─────────────────────────────┘
```

### 2.6 第六阶段：监控与反馈（Monitoring & Feedback）

#### 2.6.1 这个阶段在做什么？

监控是整个 MLOps 生命周期中最**重要**也最容易被忽视的阶段。传统软件监控的是"系统是否活着"，MLOps 监控的是"模型是否还聪明"。

MLOps 监控分为三个层次：

```
监控层次金字塔：

         ╱  ╲
        ╱ 业务 ╲         ← 最上层：模型对业务指标的影响
       ╱ 指标  ╲           （转化率、营收、用户满意度）
      ╱─────────╲
     ╱  模型   ╲        ← 中间层：模型本身的预测质量
    ╱  指标    ╲          （准确率、AUC、预测分布）
   ╱─────────────╲
  ╱   数据和    ╲      ← 基础层：输入数据的质量
 ╱   特征指标    ╲        （特征分布、缺失率、异常值）
╱─────────────────╲
```

**基础层监控：数据和特征**

这是最重要的监控层，因为"数据出问题"通常比"模型出问题"更早被发现。如果在数据层面就发现问题，可以在模型出问题之前采取措施。

```python
# 特征分布监控示例：检测输入数据是否发生漂移

def monitor_feature_distribution(batch_data, reference_stats):
    """
    监控线上特征分布是否与训练时的分布一致。
    
    参数：
        batch_data: 最近一小时线上数据的特征
        reference_stats: 训练数据时的特征统计信息（均值、标准差等）
    """
    warnings = []
    
    for feature in batch_data.columns:
        # 计算线上数据的均值和标准差
        online_mean = batch_data[feature].mean()
        online_std = batch_data[feature].std()
        
        # 获取训练时的参考值
        ref_mean = reference_stats[feature]['mean']
        ref_std = reference_stats[feature]['std']
        
        # 计算偏移量（用 Z-score 衡量）
        # Z-score = (当前均值 - 参考均值) / 参考标准差
        # 如果 Z-score 的绝对值大于 3，说明分布发生了显著偏移
        z_score = abs(online_mean - ref_mean) / ref_std
        
        if z_score > 3:
            warnings.append(f"⚠️ 特征 {feature}: 均值从 {ref_mean:.2f} 变为 {online_mean:.2f} (Z-score={z_score:.1f})")
        elif z_score > 2:
            warnings.append(f"⚡ 特征 {feature}: 轻微偏移 {z_score:.1f} 个标准差")
    
    return warnings
```

**中间层监控：模型指标**

监控模型的预测结果是否正常。但这里有一个关键挑战：**很多情况下我们不知道真实标签**。

- 在训练时，我们有 X 和 y，可以计算准确率
- 在生产中，模型预测完了，但我们不知道"正确答案"是什么（否则就不需要模型了！）

解决方案是用**替代指标**来间接监控模型效果：

| 指标 | 含义 | 如何监控 |
|------|------|---------|
| **预测分布** | 模型输出的分数分布 | 监控预测值的均值、方差、分位数。如果分布突然变了，说明模型行为变了 |
| **预测稳定性** | 相似样本的预测是否相似 | 监控预测值的方差。如果方差突然变大，模型可能变得不稳定 |
| **空值率** | 特征缺失的比例 | 如果某个特征的缺失率突然上升，说明上游数据有问题 |
| **延迟** | 推理耗时 | 如果延迟突然增加，可能模型加载出问题或资源不足 |

```python
# 预测分布监控示例

def monitor_prediction_distribution(predictions):
    """
    监控模型输出的分布是否异常。
    即使不知道真实标签，也可以从预测分数分布中发现问题。
    """
    mean_pred = np.mean(predictions)
    std_pred = np.std(predictions)
    p95 = np.percentile(predictions, 95)
    positive_rate = np.mean(predictions > 0.5)
    
    alerts = []
    
    # 1. 平均分是否在预期范围内？
    # 如果训练时平均分是 0.3，线上突然变成 0.7，说明模型行为变了
    if abs(mean_pred - 0.3) > 0.2:
        alerts.append(f"⚠️ 预测均值异常: {mean_pred:.3f} (预期 ~0.3)")
    
    # 2. 正样本率是否合理？
    if positive_rate < 0.05 or positive_rate > 0.95:
        alerts.append(f"⚠️ 正样本率异常: {positive_rate:.3f} (模型几乎只预测一个类别)")
    
    # 3. 预测值分布是否过于集中或分散？
    if std_pred < 0.05:
        alerts.append(f"⚠️ 预测值过于集中: 标准差 {std_pred:.3f} (模型区分度太低)")
    
    return alerts
```

**最上层监控：业务指标**

最终，模型的价值体现在业务指标上。如果模型上线后转化率没有提升，或者用户投诉增加了，那么模型的准确率再高也没有意义。

| 业务指标 | 说明 | 模型影响方式 |
|----------|------|-------------|
| **转化率** | 用户下单的比例 | 推荐模型让用户看到更喜欢的商品 |
| **留存率** | 用户持续使用服务的比例 | 个性化体验让用户更愿意回来 |
| **客单价** | 用户平均消费金额 | 推荐合适价位的商品 |
| **投诉率** | 用户投诉的比例 | 推荐准确，用户不会因为"给我推荐了已经买过的东西"而投诉 |
| **人工介入率** | 需要人工处理的订单比例 | 自动化决策的准确度越高，需要人工处理的越少 |

**MLOps 监控的闭环反馈**

监控不是终点，监控的结果需要反馈到流水线的起点，形成**持续改进的闭环**：

```
监控发现异常
  → 自动告警通知团队
  → 分析问题原因（数据漂移？模型退化？）
  → 重新采集/标注数据
  → 触发自动重新训练
  → 新模型上线
  → 监控新模型效果
  → （回到起点，持续循环）
```

---

## 三、数据漂移 vs 概念漂移——模型退化的两大元凶

### 3.1 为什么模型会"变老"？

一个常见的误解是：模型训练好了，部署上线，就一劳永逸了。

事实是：**任何部署到生产环境的机器学习模型，它的效果都会随时间逐渐下降**。这不是因为模型"坏了"，而是因为模型面对的世界变了。

世界是动态的：

- 用户的消费习惯在变
- 市场的经济环境在变
- 竞争对手的策略在变
- 法律法规在变
- 季节在变

而模型在训练时"看到"的世界只是某个时间点的快照。当世界变化后，模型基于旧数据学到的规律可能不再适用。

模型退化的两大原因——**数据漂移**和**概念漂移**——需要分别理解。

### 3.2 数据漂移（Data Drift）

#### 3.2.1 什么是数据漂移？

**数据漂移**指的是模型输入数据的**特征分布**随时间发生了变化。简单说就是：模型的"输入"变了。

具体定义：模型在训练时看到的特征分布（P(X)）和生产环境中实际的特征分布（P'(X)）不一致。

```
数据漂移的直观理解：

训练数据中的用户年龄分布：      生产环境中的用户年龄分布：
  ▲                              ▲
  │    ██                        │         ██
  │    ██     ██                 │    ██   ██
  │ ██ ██ ██  ██ ██              │ ██ ██ ██ ██ ██ ██
  └───────────────▶ 年龄         └────────────────▶ 年龄
   20 30 40 50 60                  20 30 40 50 60

  训练时用户集中在 30-40 岁        线上时用户年龄分布更广，60+ 用户增加
  模型在这个群体上学到的规律        模型没见过的 60+ 用户来了，预测可能不准
  对 60+ 用户可能不适用
```

#### 3.2.2 数据漂移的常见原因

| 原因 | 场景举例 |
|------|---------|
| **季节性变化** | 夏季训练的商品推荐模型，到了圣诞节，用户的搜索和购买行为完全不同 |
| **用户群体变化** | 产品上线初期用户主要是年轻人，随着产品普及，中老年用户增多 |
| **数据采集方式变更** | 更换了分析工具、升级了 SDK，新老版本采集的数据格式或精度不同 |
| **外部环境变化** | 疫情期间，用户线上购物行为激增，2020年前训练的模型完全失效 |
| **平台政策变化** | 社交平台修改了推荐算法，用户行为数据中的"推荐来源"特征发生了变化 |

#### 3.2.3 如何检测数据漂移？

**方法一：统计检验法**

使用统计检验来比较训练数据和线上数据的分布是否一致：

| 检验方法 | 适用范围 | 说明 |
|----------|---------|------|
| **KS 检验** | 连续数值特征 | 比较两个分布的差异是否显著 |
| **卡方检验** | 类别特征 | 比较类别分布的差异 |
| **JS 散度/PSI** | 任何分布 | 衡量两个分布的"距离" |

```python
# PSI（Population Stability Index）计算
# PSI 是金融行业最常用的分布稳定性指标

def calculate_psi(expected, actual, bins=10):
    """
    计算 Population Stability Index（群体稳定性指标）。
    
    这个指标衡量"预期分布"和"实际分布"之间的差异。
    
    PSI 判断标准：
    - PSI < 0.1: 分布无显著变化 ✓
    - 0.1 ≤ PSI < 0.2: 分布有轻微变化，需要关注 ⚡
    - PSI ≥ 0.2: 分布发生显著变化，需要立即采取行动 ⚠️
    """
    
    # 1. 将数据分成 bins 个区间（离散化）
    # 为什么分箱？连续数值无法直接比较分布，需要先分箱
    min_val = min(expected.min(), actual.min())
    max_val = max(expected.max(), actual.max())
    bins = np.linspace(min_val, max_val, bins + 1)
    
    # 2. 统计每个区间中的样本比例
    expected_percents = np.histogram(expected, bins=bins)[0] / len(expected)
    actual_percents = np.histogram(actual, bins=bins)[0] / len(actual)
    
    # 3. 防止除以 0（如果某个区间没有样本，给一个很小的值）
    expected_percents = np.clip(expected_percents, 0.001, 1)
    actual_percents = np.clip(actual_percents, 0.001, 1)
    
    # 4. 计算 PSI: Σ (实际_i - 预期_i) * ln(实际_i / 预期_i)
    psi = np.sum((actual_percents - expected_percents) * np.log(actual_percents / expected_percents))
    
    return psi

# 使用示例
train_age = train_data['age']      # 训练数据中的年龄分布
online_age = online_batch['age']   # 线上数据中的年龄分布

psi_value = calculate_psi(train_age, online_age)
print(f"年龄特征的 PSI = {psi_value:.3f}")

if psi_value < 0.1:
    print("✅ 年龄分布稳定")
elif psi_value < 0.2:
    print("⚡ 年龄分布轻微漂移，建议继续监控")
else:
    print("⚠️ 年龄分布显著漂移！需要检查原因并考虑重新训练")
```

**方法二：对抗验证法**

我们已经在模型评估阶段介绍过对抗验证。这种方法也可以用于检测数据漂移——定期对"训练数据"和"最近的线上数据"做对抗验证，如果分类器能区分出两者，说明存在数据漂移。

### 3.3 概念漂移（Concept Drift）

#### 3.3.1 什么是概念漂移？

**概念漂移**指的是模型的输入和输出之间的**映射关系**发生了变化。简单说就是：**特征和标签之间的关系变了**。

具体定义：训练时学到的条件分布 P(Y|X) 和当前环境的条件分布 P'(Y|X) 不一致了。

```
概念漂移的直观理解：

假设你训练了一个模型，根据"是否打伞"（X）来预测"是否下雨"（Y）：
- 训练数据：打伞 → 大概率下雨（正确率 95%）
- 模型学到了：打伞 → 下雨

模型上线后，情况变了：
- 夏天到了，很多人打伞遮阳（打伞但没下雨）
- 特征没变（还是"是否打伞"）
- 但特征和标签的关系变了（打伞不再意味着下雨）
- 模型的预测准确率下降

这就是概念漂移：
- 数据（P(X)）没有变——打伞的人依然很多
- 但条件分布 P(Y|X) 变了——打伞和下雨的关系变了
```

#### 3.3.2 数据漂移 vs 概念漂移的区别

通过一个对比表格来清晰区分这两个概念：

| 对比维度 | 数据漂移 | 概念漂移 |
|----------|---------|---------|
| **变化的对象** | 特征的分布 P(X) 变了 | 特征和标签的关系 P(Y\|X) 变了 |
| **通俗理解** | "输入变了" | "规则变了" |
| **检测方法** | 比较特征分布（KS检验、PSI） | 需要知道真实标签对比模型预测 |
| **修复方式** | 重新采样，让训练数据覆盖新分布 | 重新标注，更新模型学习新关系 |
| **困难程度** | 相对容易检测和修复 | 较难检测（因为不知道真实标签） |
| **经典例子** | 用户年龄分布变了 → 数据漂移 | "高收入=好信用"这个关系变了 → 概念漂移 |

用一个具体场景来帮助区分：

```
风控模型场景：

模型判断逻辑：输入用户的"月收入"、"历史还款记录"、"负债率" → 输出"违约概率"

场景一：数据漂移
  2020年：模型训练时，用户的月收入集中在 5,000-15,000 元
  2023年：由于业务下沉到三四线城市，新用户的月收入集中在 3,000-8,000 元
  - 特征分布（月收入）变了
  - 但"月收入低 → 违约概率高"这条规律本身没变
  - 解决方案：补充三四线城市用户的数据重新训练
  
场景二：概念漂移
  2020年：经济繁荣，"负债率高"的用户的违约率确实更高（规律成立）
  2023年：疫情冲击，政府出台纾困政策，高负债用户获得了贷款延期
  - "负债率高 → 违约概率高"这条规律不再成立
  - 特征分布可能没变，但特征和标签的关系变了
  - 解决方案：需要新的标注数据，让模型学习新的规律
```

#### 3.3.3 概念漂移的类型

概念漂移并不是"一下子全部改变"，它有几种不同的模式：

```
突发型漂移（Sudden Drift）：
  P(Y|X) 在某个时间点突然发生变化
  
  准确率 │
        │ ████████████████
        │                 ████████████████
        │                 ← 疫情爆发，市场规则突变
        └─────────────────────────▶ 时间

渐进型漂移（Gradual Drift）：
  P(Y|X) 缓慢地逐渐变化
  
  准确率 │
        │ ████████████████████
        │                  ██████████████████
        │                   ← 用户习惯慢慢改变
        └─────────────────────────▶ 时间

周期性漂移（Seasonal Drift）：
  P(Y|X) 按照周期规律变化

  准确率 │
        │ ████████████      ████████████
        │      ████████████      ████████████
        │  元旦  ██  春节       清明   ██  五一
        └─────────────────────────▶ 时间
```

#### 3.3.4 如何检测概念漂移？

检测概念漂移比检测数据漂移更困难，因为我们需要知道真实标签。常用的方法：

**方法一：延迟标签监控**

有些场景下，真实标签会延迟到达。比如：

- 信用模型：用户违约需要几个月后才能知道
- 推荐系统：用户是否点击推荐内容，几秒钟后就能知道
- 广告点击率：用户是否点击广告，实时就能知道

对于有延迟标签的场景，可以：

```python
# 延迟标签监控示例

def concept_drift_monitoring(model, X_batch, y_batch_delayed, threshold=0.05):
    """
    对比模型预测和真实标签，检测概念漂移。
    
    假设：推理时没有真实标签，但一段时间后标签会到达
    （例如：推荐系统用户点击行为、广告系统用户是否转化）
    """
    # 1. 记录模型当时的预测
    y_pred = model.predict(X_batch)
    y_pred_proba = model.predict_proba(X_batch)[:, 1]
    
    # 2. 等待真实标签到达（通常在 MLOps 系统中会有"标签延迟到达"的机制）
    #    这里假设 y_batch_delayed 是最终到达的真实标签
    
    # 3. 对比预测和实际
    accuracy = (y_pred == y_batch_delayed).mean()
    
    # 4. 计算滑动窗口准确率
    # 如果准确率持续下降，说明可能存在概念漂移
    recent_accuracy = accuracy
    
    if recent_accuracy < threshold:
        print(f"⚠️ 预警：模型准确率降至 {recent_accuracy:.3f}")
        print("可能发生了概念漂移，建议重新训练！")
    else:
        print(f"✅ 模型准确率 {recent_accuracy:.3f}，表现正常")
    
    return recent_accuracy
```

**方法二：无标签场景的间接检测**

当没有真实标签时（大多数线上场景），可以通过以下间接信号推测概念漂移：

- **预测置信度下降**：模型对预测结果越来越"不确定"（预测概率接近 0.5）
- **模型与业务指标背离**：模型预测的分布没变，但业务数据（如营收、用户满意度）发生变化
- **人工审查率上升**：需要人工处理的异常案例增多

### 3.4 应对策略

无论是数据漂移还是概念漂移，核心应对策略都是**持续重新训练**。

| 策略 | 做法 | 适用场景 | 成本 |
|------|------|---------|------|
| **定期重新训练** | 每隔固定时间（如每周、每月）重新训练 | 漂移速度可预测 | 低 |
| **触发式重新训练** | 监控到漂移超过阈值时自动触发训练 | 漂移速度不可预测 | 中 |
| **在线学习** | 新数据到达时实时更新模型 | 概念漂移快、数据量大 | 高 |
| **集成多模型** | 使用多个不同时期的模型加权投票 | 环境变化难以建模 | 高 |

---

## 四、MLOps 成熟度模型——从 L0 到 L3 的演进之路

### 4.1 为什么需要成熟度模型？

MLOps 不是"全有或全无"的。大多数团队从零开始，逐步建立 ML 工程化能力。**MLOps 成熟度模型**提供了一条清晰的演进路径，帮助团队定位当前阶段、明确下一步改进方向。

Google、Microsoft、AWS 等公司都提出了自己的 MLOps 成熟度模型，虽然细节不同，但核心思想一致：

```
MLOps 成熟度演进：

L0（无 MLOps） ──→ L1（DevOps 但无 ML）──→ L2（自动化训练）──→ L3（全自动化 MLOps）
   手动流程          CI/CD 仅覆盖代码       自动训练+模型注册      全自动闭环
   只有代码有版本    数据手动管理            实验追踪+模型版本      自动重训+自动部署
   无实验追踪        CI/CD                 数据版本控制           监控驱动自动闭环
```

### 4.2 L0 阶段：手动流程（No MLOps）

#### 4.2.1 这是什么阶段？

L0 是 ML 团队的"原始社会"阶段。大部分刚起步的 ML 项目都在这个阶段。

**典型特征：**

- 数据科学家在自己的笔记本电脑上训练模型
- 训练过程是手动的：打开 Jupyter Notebook，运行单元格
- 模型文件通过邮件或共享网盘传递
- 部署是手动的：将模型文件复制到服务器上，手动启动服务
- 没有版本控制（或者说只有代码有版本控制，数据和模型没有）
- 没有实验追踪——跑过的实验靠记忆力
- 没有监控——模型上线后没人盯着

**工作流程：**

```
数据科学家                         运维工程师
┌──────────────┐                 ┌──────────────┐
│ Jupyter Lab  │                 │  生产服务器   │
│ 训练模型     │── 模型.pkl ──▶│  手动部署     │
│ 手动调参     │  （U盘传输）   │  （手动执行）  │
└──────────────┘                 └──────┬───────┘
                                        │
                                没有监控！不知道模型
                                在线上的表现如何
```

#### 4.2.2 L0 的痛点

```
典型场景：
  1. 小张在 Jupyter 里训练了一个模型，AUC 0.92
  2. 小张把 model.pkl 发给运维小王
  3. 小王部署到线上
  4. 两周后，业务反馈模型效果不好
  5. 小张想重新训练，但发现：
     - 记不清当时用了哪些训练数据
     - 记不清用了哪些超参数
     - 那批数据已经被清理了
     - 只能重新开始

这就是 L0 的日常：每次重复做同样的事，每次都从头开始。
```

**L0 的主要问题总结：**
- **不可复现**：无法精确复现之前的实验结果
- **人工依赖**：部署、监控完全依赖个人，人员流动=知识流失
- **频繁出错**：手动操作容易出错（文件传错、版本搞混、参数配错）
- **难以协作**：多人协作时，代码、数据、模型的"最新版本"一团乱麻
- **无监控**：模型出问题时没人知道，直到业务方投诉

### 4.3 L1 阶段：DevOps 但无 ML 自动化

#### 4.3.1 这是什么阶段？

L1 阶段引入了 DevOps 的实践，但仅限于**代码层面**。数据管线和模型管线仍然是手动的。

**典型特征：**

- 代码有版本控制（Git），有 CI/CD 流水线
- Python 包依赖有管理（requirements.txt、conda env）
- 有自动化测试（代码层面的单元测试）
- 部署流程有自动化脚本（不再手动 SSH 到服务器）
- 但是：**数据仍然是手动管理，训练仍然是手动触发**

**工作流程：**

```
代码流水线（CI/CD）：
  Git commit ──→ 自动构建 ──→ 自动测试 ──→ 自动部署
  
数据/模型流水线（手动）：
  手动准备数据 ──→ 手动训练 ──→ 手动评估 ──→ 手动发布
```

#### 4.3.2 L1 的改进与不足

**相比 L0 的改进：**
- 代码部署自动化了，不再需要手动复制文件
- 有版本控制，代码变更可追溯
- 有自动化测试，减少代码级别的 Bug
- 环境管理规范化，减少"在我机器上能跑"的问题

**L1 仍然存在的问题：**
- 训练仍然手动，每次训练需要人工运行脚本
- 没有实验追踪，"哪个模型效果最好"依赖记忆
- 没有模型版本管理，生产环境用的哪个版本模糊不清
- 数据没有版本控制，"复现训练数据"仍然困难
- 模型部署后缺乏监控

**L1 阶段的构建脚本示例：**

```python
# L1 阶段的"自动化构建"（仅代码层面）
# 这是一个 CI 配置文件片段（.gitlab-ci.yml / Jenkinsfile）

stages:
  - test
  - build
  - deploy

test:
  stage: test
  script:
    - pip install -r requirements.txt
    - pytest tests/  # 运行单元测试

build:
  stage: build
  script:
    - docker build -t ml-service:${CI_COMMIT_SHORT_SHA} .
    - docker push registry.example.com/ml-service:${CI_COMMIT_SHORT_SHA}

deploy:
  stage: deploy
  script:
    - kubectl set image deployment/ml-service \
        ml-service=registry.example.com/ml-service:${CI_COMMIT_SHORT_SHA}
  # 注意：这里只部署代码（API 服务），模型文件是另外挂载的
  # 模型更新仍然需要手动操作
```

### 4.4 L2 阶段：自动化训练与模型管理

#### 4.4.1 这是什么阶段？

L2 阶段开始解决 ML 特有的问题：**自动化训练、实验追踪、模型版本管理、数据版本管理**。

**典型特征：**

- 引入实验追踪工具（MLflow、W&B、Neptune）
- 引入模型注册表（管理模型版本）
- 引入数据版本控制（DVC、LakeFS）
- 训练流水线自动化（数据准备好后自动触发训练）
- 模型评估标准化（每次训练自动生成评估报告）
- 有基础的模型监控（预测分布、特征分布）

**工作流程：**

```
自动训练流水线：

数据更新 ──→ 自动数据验证 ──→ 自动特征工程 ──→ 自动训练
                                                    │
                                                    ▼
                                             自动评估报告
                                                    │
                                           ┌────────┴────────┐
                                           ▼                 ▼
                                    评估通过→模型注册表  评估未通过→告警
                                           │
                                           ▼
                                    手动确认是否部署
```

#### 4.4.2 L2 的核心能力

**能力一：自动实验追踪**

每次训练自动记录所有信息，可以通过 Web UI 方便地比较：

```python
# L2 阶段的实验对比——在 MLflow UI 中可以轻松做到

# 实验记录（自动）
mlflow.log_param("model_type", "XGBoost")
mlflow.log_param("max_depth", 7)
mlflow.log_param("learning_rate", 0.01)
mlflow.log_metric("train_auc", 0.95)
mlflow.log_metric("test_auc", 0.88)

# MLflow UI 中可以看到：
#
# 实验名称  | model_type | max_depth | learning_rate | test_auc | train_auc
# ----------|------------|-----------|---------------|----------|----------
# exp_001   | XGBoost    | 5         | 0.01          | 0.85     | 0.91
# exp_002   | XGBoost    | 7         | 0.01          | 0.88     | 0.95
# exp_003   | LightGBM   | 7         | 0.01          | 0.87     | 0.93
# exp_004   | XGBoost    | 7         | 0.05          | 0.86     | 0.97
#
# → 一眼就能看出 exp_002（XGBoost, depth=7, lr=0.01）的泛化能力最好
# → 选择 exp_002 的模型部署到生产环境
```

**能力三：模型注册表**

```python
# MLflow Model Registry 操作示例
# 注册表管理模型的"状态"——从开发到上线的标准化流程

import mlflow
from mlflow.tracking.client import MlflowClient

client = MlflowClient()

# 1. 注册新模型（在实验追踪完成后）
mlflow.register_model(
    model_uri="runs:/<run_id>/model",  # 哪个实验产出的模型
    name="credit_scoring_model"          # 模型名称
)

# 2. 将版本 3 从 None → Staging（预发布）
client.transition_model_version_stage(
    name="credit_scoring_model",
    version=3,
    stage="Staging"
)

# 3. 在 Staging 环境中验证（A/B 测试、集成测试）
# ... 验证通过后 ...

# 4. 将版本 3 从 Staging → Production（正式上线）
client.transition_model_version_stage(
    name="credit_scoring_model",
    version=3,
    stage="Production"
)

# 5. 查看模型状态变化历史
history = client.get_model_version_stages(
    name="credit_scoring_model",
    version=3
)
for h in history:
    print(f"{h.timestamp}: {h.stage}")

# 输出：
# 2024-05-10 14:30: None → Staging   (提交预发布)
# 2024-05-12 09:00: Staging → Production (上线)
# 2024-07-01 10:00: Production → Archived (下架归档)
```

#### 4.4.3 L2 的不足

L2 阶段已经很不错了，但仍有改进空间：

- **模型部署仍然需要手动批准**：评估通过的模型不会自动上线
- **监控告警后不会自动触发重训**：发现漂移了，告警通知人，人再手动触发训练
- **重训和部署之间仍有时间差**：发现漂移到模型更新之间有"空白期"

### 4.5 L3 阶段：全自动化 MLOps（Full Automation）

#### 4.5.1 这是什么阶段？

L3 是 MLOps 的终极目标——**全自动闭环**。从数据准备到模型训练到部署到监控，全部自动化，不需要人工干预。

**典型特征：**

- **自动重训**：监控到数据漂移或概念漂移后，自动触发重新训练
- **自动部署**：新模型评估通过后，自动进入金丝雀发布流程
- **自动回滚**：新模型上线后如果指标下降，自动回滚到旧版本
- **A/B 测试自动化**：自动在多个候选模型中进行 A/B 测试，选择表现最好的
- **持续学习**：新数据到达后，模型自动增量更新

**工作流程：**

```
全自动 MLOps 闭环：

                  ┌─────────────────────────────────────┐
                  │             数据流水线               │
                  │  数据采集 → 验证 → 特征工程 → 存储  │
                  └──────────────────────┬──────────────┘
                                         ▼
                  ┌─────────────────────────────────────┐
                  │             训练流水线               │
                  │  自动触发训练 → 评估 → 注册模型     │
                  └──────────────────────┬──────────────┘
                                         ▼
                  ┌─────────────────────────────────────┐
                  │             部署流水线               │
                  │  金丝雀发布 → 指标监控 → 全量上线   │
                  └──────────────────────┬──────────────┘
                                         ▼
                  ┌─────────────────────────────────────┐
                  │             监控流水线               │
                  │  实时监控 → 漂移检测 → 自动告警     │
                  │                    │                 │
                  └────────────────────┼─────────────────┘
                                       │
                  ┌────────────────────┘
                  ▼
          （自动触发重新训练，回到训练流水线）
```

#### 4.5.2 L3 的核心能力

**能力一：自动重训流水线**

```python
# L3 阶段的自动重训触发逻辑（伪代码）
# 监控系统检测到漂移 → 自动触发训练流水线

def monitor_and_auto_retrain():
    """
    监控流水线：定期检查数据漂移和模型效果。
    如果检测到异常，自动触发重新训练。
    """
    
    # 1. 每小时检查一次特征分布
    online_batch = load_last_hour_data()
    drift_score = check_data_drift(online_batch, reference_data)
    
    if drift_score > DRIFT_THRESHOLD:
        # 2. 检测到漂移 → 自动触发重新训练
        print(f"⚠️ 检测到数据漂移 (PSI={drift_score:.3f})，自动触发重训")
        
        # 3. 调用训练流水线 API（自动）
        training_run_id = trigger_training_pipeline(
            training_data=load_updated_training_data(),
            model_config=get_best_previous_config()
        )
        
        # 4. 等待训练完成并自动评估
        new_model_metrics = wait_for_training(training_run_id)
        
        # 5. 如果新模型效果优于当前生产模型 → 自动部署
        current_model_metrics = get_production_model_metrics()
        if new_model_metrics['auc'] > current_model_metrics['auc']:
            print(f"✅ 新模型 AUC {new_model_metrics['auc']:.3f} > 当前 {current_model_metrics['auc']:.3f}")
            auto_deploy_to_production(training_run_id, strategy="canary")
        else:
            print(f"新模型未超越当前模型，不部署")
```

**能力二：自动金丝雀发布**

```python
# L3 阶段的自动金丝雀发布（伪代码）

def auto_deploy_to_production(model_run_id, strategy="canary"):
    """自动部署新模型到生产环境"""
    
    if strategy == "canary":
        # 金丝雀发布：逐步增加新模型流量
        
        # Stage 1: 新模型接收 1% 流量
        set_route_weight(new_model_id=model_run_id, weight=0.01)
        wait_and_monitor(duration=30 * 60)  # 监控 30 分钟
        
        # Stage 2: 检查指标是否正常
        if check_model_health(model_run_id) == "healthy":
            set_route_weight(new_model_id=model_run_id, weight=0.10)
            wait_and_monitor(duration=60 * 60)  # 监控 1 小时
        else:
            auto_rollback(model_run_id)  # 自动回滚！
            return False
        
        # Stage 3: 继续增加到 50%
        if check_model_health(model_run_id) == "healthy":
            set_route_weight(new_model_id=model_run_id, weight=0.50)
            wait_and_monitor(duration=60 * 60)
        else:
            auto_rollback(model_run_id)
            return False
        
        # Stage 4: 全量上线
        if check_model_health(model_run_id) == "healthy":
            set_route_weight(new_model_id=model_run_id, weight=1.0)
            print("✅ 新模型全量上线成功！")
            return True
        else:
            auto_rollback(model_run_id)
            return False
```

#### 4.5.3 L0—L3 成熟度总结

```
                     L0              L1              L2              L3
                    ┌─────────────────────────────────────────────────────┐
  代码版本控制      │   ✅/❌         ✅              ✅              ✅   │
  数据版本控制      │   ❌             ❌              ✅              ✅   │
  模型版本控制      │   ❌             ❌              ✅              ✅   │
  实验追踪          │   ❌             ❌              ✅              ✅   │
  自动化测试        │   ❌             ✅              ✅              ✅   │
  CI/CD（代码级）   │   ❌             ✅              ✅              ✅   │
  自动化训练        │   ❌             ❌              ✅              ✅   │
  模型监控          │   ❌             ❌/✅           ✅              ✅   │
  自动重训          │   ❌             ❌              ❌              ✅   │
  自动部署          │   ❌             ❌（代码）       ❌（模型）      ✅   │
  自动回滚          │   ❌             ❌              ❌              ✅   │
                    └─────────────────────────────────────────────────────┘
```

> **重要理解**：L3 是理想目标，但大多数团队不需要追求 L3。对于很多业务场景，L2 已经完全够用。L3 带来的复杂性（全自动闭环的调试和维护成本）不一定值得。从 L0 到 L1 带来的收益通常最大，然后边际收益递减。

---

## 五、MLOps 技术栈概览

### 5.1 主流工具生态

MLOps 生态中有大量的工具，初学者容易感到困惑。这里按功能分类列出最常见的工具：

| 功能领域 | 推荐工具 | 说明 |
|----------|---------|------|
| **实验追踪** | MLflow、Weights & Biases、Neptune | 记录每次实验的参数和指标 |
| **模型注册表** | MLflow Model Registry、DVC | 管理模型版本和状态 |
| **数据版本控制** | DVC、LakeFS | 像管理代码一样管理数据 |
| **特征存储** | Feast、Tecton、Feast+Redis | 在线/离线统一特征管理 |
| **流水线编排** | Airflow、Kubeflow、Prefect、Argo | 调度和管理 ML 流水线 |
| **模型监控** | Evidently、WhyLogs、Seldon Alibi | 检测数据漂移和模型退化 |
| **模型部署** | MLflow Serving、Seldon Core、BentoML、Triton | 将模型封装为 API |
| **超参调优** | Optuna、Hyperopt、Ray Tune | 自动搜索最优超参数 |
| **容器化** | Docker + Kubernetes | 标准化部署环境 |

### 5.2 如何选择工具？

选择工具时的原则：**从简单开始，按需升级**。

```
推荐路径：

阶段 L0 → L1：
  1. Git（必然有）
  2. Docker（标准化环境）
  3. CI/CD（GitLab CI / GitHub Actions）
  
阶段 L1 → L2：
  4. MLflow（实验追踪 + 模型注册表）
  5. DVC（数据版本控制）
  6. Airflow / Prefect（流水线编排）
  
阶段 L2 → L3：
  7. Evidently（自动漂移检测）
  8. Seldon / BentoML（高级部署）
  9. Kubernetes（弹性伸缩）
```

> **关键建议**：不要一开始就上 Kubeflow（太多人犯这个错误了！）。Kubeflow 是一个功能强大但极其复杂的平台，对于刚开始 MLOps 的团队来说，它带来的学习成本远超收益。先从简单的工具开始（MLflow + DVC 就是一个很好的起点），等真正遇到了规模瓶颈再考虑升级。

---

## 六、总结——MLOps 的核心思想

用一句话概括 MLOps：

> **"DevOps 告诉你怎么管代码，MLOps 告诉你怎么管代码 + 数据 + 模型的组合体。"**

几个贯穿全文的核心思想值得记住：

1. **ML 系统不是"写完就完"的**。它和传统软件最大的区别是：上线后才刚刚开始——你需要持续监控、持续维护、持续更新。

2. **数据和模型需要像代码一样被管理**。没有版本控制的数据和模型是"不可复现"的，不可复现的东西在网上出了问题就没人能修。

3. **漂移是常态，不是异常**。数据会变、概念会变，模型效果下降是必然的。MLOps 的核心不是阻止漂移（这不可能），而是**尽早发现漂移并快速响应**。

4. **成熟度是逐步演进的**。不要追求一步到位到 L3。L0 → L1 带来 80% 的收益，剩下的 20% 需要 80% 的投入——根据团队的实际需要选择合适的目标。

5. **监控的三个层次都不能少**。数据层、模型层、业务层，缺少任何一层你都无法真正了解系统状态。

---

*以上是 MLOps 的核心概念。当你开始构建 ML 系统时，记住：不是所有团队都需要全自动的 MLOps 平台，但每个团队都应该做好"数据版本化、实验可追溯、模型可监控"这三件最基本的事。*
