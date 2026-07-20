# PyTorch Conv2d 完全指南

## 概述

`torch.nn.Conv2d` 是 PyTorch 中最常用的二维卷积层，广泛应用于计算机视觉任务。

## 参数详解

```python
torch.nn.Conv2d(
    in_channels,      # 输入通道数
    out_channels,     # 输出通道数（卷积核数量）
    kernel_size,      # 卷积核大小，int 或 tuple
    stride=1,         # 步幅，默认值为 1
    padding=0,        # 填充，默认值为 0
    dilation=1,       # 空洞卷积率，默认值为 1
    groups=1,         # 分组卷积，默认值为 1
    bias=True,        # 是否使用偏置项，默认值为 True
    padding_mode='zeros',  # 填充模式，默认为 'zeros'
    device=None,
    dtype=None
)
```

### 各参数详细说明

- **in_channels**: 输入的特征图通道数。例如 RGB 图像为 3。
- **out_channels**: 输出的特征图通道数，即卷积核的数量。每个卷积核产生一个输出通道。
- **kernel_size**: 卷积核的空间尺寸。可以是单个 int（正方形）或 (h, w) tuple。
- **stride**: 卷积核滑动的步长。默认为 1，设为 2 可以减半特征图尺寸。
- **padding**: 在输入四周填充的行列数。默认为 0 表示不填充。
- **dilation**: 控制卷积核点之间的间距，用于空洞卷积（dilated convolution）。
- **groups**: 分组卷积参数。groups=in_channels 时退化为深度可分离卷积。
- **bias**: 是否添加可学习的偏置项。默认 True。
- **padding_mode**: 填充模式，支持 'zeros'、'reflect'、'replicate'、'circular'。

## 输出尺寸计算

输出特征图的尺寸计算公式：

```
H_out = floor((H_in + 2*padding - dilation*(kernel_size-1) - 1) / stride + 1)
W_out = floor((W_in + 2*padding - dilation*(kernel_size-1) - 1) / stride + 1)
```

## 使用示例

```python
import torch
import torch.nn as nn

# 创建一个卷积层：输入3通道，输出64通道，3x3卷积核
conv = nn.Conv2d(in_channels=3, out_channels=64, kernel_size=3, stride=1, padding=1)

# 输入: batch_size=1, channels=3, height=224, width=224
x = torch.randn(1, 3, 224, 224)
output = conv(x)
print(output.shape)  # torch.Size([1, 64, 224, 224])
```
