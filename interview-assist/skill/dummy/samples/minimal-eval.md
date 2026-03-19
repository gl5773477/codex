# Minimal Eval 场景

> 最小输入：只有转录文字，无简历/代码题/手动记录。
> 用于验证 --eval 基础流程是否可跑通。

## 输入命令

```
/interview-assist --eval --job ios-engineer --candidate test-candidate-a
```

## 所需文件（执行前需写入 dummy 数据）

### job/ios-engineer/description.md
```
岗位：iOS 客户端工程师
要求：
- 3年以上 iOS 开发经验，熟悉 Swift/Objective-C
- 熟悉 UIKit/SwiftUI，有复杂列表性能优化经验
- 有良好的代码规范和工程化意识
- 加分项：有组件化/模块化架构经验
```

### common/process_template.md
```markdown
# 面试过程记录模板
## [话题/问题]
**候选人回答**：
🏷️ **考察点**：
📝 **面试官标注**：
💬 **Agent 小结**：
```

### job/ios-engineer/candidates/test-candidate-a/interview_transcription.md
```
面试官：你好，先自我介绍一下吧。
候选人：你好，我叫小明，有4年iOS开发经验，之前在某电商公司做商品详情页，主要负责性能优化，把首屏加载从1.2秒优化到了400ms。
面试官：说说你是怎么做这个优化的？
候选人：主要是三个方向，第一是图片懒加载，用了预加载策略；第二是把主线程的数据处理移到子线程；第三是做了局部刷新，不再整个 reload。
面试官：你用过 SwiftUI 吗？
候选人：用过，在业余项目里用过，公司项目主要还是 UIKit，感觉 SwiftUI 在复杂场景下状态管理比较麻烦。
```

## 期望产物结构

生成 `interview_report.md` 应包含：
- 简历摘要：无（无简历文件，标注"简历未提供"）
- 面试过程记录：3 个话题，各有打标
- 综合评价：基于转录和 JD 要求
- 决策区：留白
