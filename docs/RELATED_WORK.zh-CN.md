# 相关方向与区别

本项目接触多个已有方向，但不等同于其中任何一个。

## Text-entry 研究

Text-entry 研究关注人如何通过设备和界面产生文本。常见指标包括 WPM、错误率、纠错成本和每字符击键数。Orthographic BlockCode 属于这个大方向，因为最终问题是码表能否减少真实输入努力。

## 键盘布局优化

键盘布局优化改变字符在物理键上的位置。Orthographic BlockCode 主要不是移动字母键位，而是把 `tion`、`ee`、`ing` 等正字法单位映射到输入码。

## 自动补全和预测

自动补全根据上下文预测后续内容。Orthographic BlockCode 使用确定性映射和固定候选顺序，不依赖语言模型也可以评估。

## Text expansion

Text expansion 把记忆缩写映射为长字符串。Orthographic BlockCode 在词内部工作，压缩重复正字法块。

## 速记

Stenography 和 Plover 使用和弦输入。Orthographic BlockCode 使用普通顺序按键事件。

## 压缩和编码理论

本项目与编码理论相关，因为高频单位应获得短码。但它不同于普通压缩，因为码表必须由人输入，并通过候选 rank、delimiter 和 fallback 路径解码。

## 形码输入法

中文形码输入法说明结构码表可以支持盲打。Orthographic BlockCode 探索的是不同文字系统和不同单位结构：拉丁正字法块，而不是汉字部件。
