#!/usr/bin/env python3
"""
将人格结构分析报告载入 LanceDB 混合记忆系统
"""

import json
import os
import sys
from datetime import datetime

# 人格数据
personality_data = {
    "category": "preference",
    "scope": "global",
    "importance": 0.95,
    "tags": ["personality", "psychological-profile", "user-model", "core-identity"],
    "text": """
# 人格结构分析报告（Psychological Profile）

## 基本信息
- 年龄：17
- 身份：高中生
- 兴趣领域：Linux 系统、技术工具构建、AI、摄影、哲学思考
- 主要关注：自我认知、社会结构、人类未来

## 核心人格类型：理想主义系统建造者 (Idealistic System Builder)

### 三个维度
1. 认知驱动 - 对未知知识持续好奇，倾向系统性理解世界
2. 技术构建 - 不仅追求理解，还追求实现，喜欢构建工具/系统
3. 社会理想主义 - 希望推动社会向更公平/合理方向发展

### 关键特征
1. 强烈的认知驱动力 - 学习动机主要来自好奇心，倾向系统性理解世界
2. Builder Mindset - 喜欢构建工具或系统，典型行为包括系统配置、技术调试、工具开发
3. 系统思维 - 关注社会结构与制度，习惯从宏观角度分析问题，将复杂问题抽象为系统
4. 理想主义倾向 - 关注人类社会整体发展，具有乌托邦式想象能力

### 认知结构
- 认知模式：逻辑导向、系统导向、深度思考、自我反思能力较强
- 学习动机：探索未知、理解复杂系统、创造工具或结构
- Epistemic Motivation（认知动机）- 内在驱动强，对外部奖励依赖较低，容易进入深度学习状态

### 情感与心理结构
- 情感防御机制：理性化（Intellectualization）- 通过逻辑、分析、技术思维来处理或回避复杂情绪
- 情感不确定性焦虑：对无法理解或预测的情感关系产生不安
- 典型表现：在技术或知识领域高度自信，在情感关系中较为谨慎
- 家庭经验影响：父母关系冲突、角色责任提前承担、对家庭稳定性的关注
- 潜在影响：对关系稳定性的高度重视，对亲密关系的谨慎态度，对未来家庭结构的理想化期望

### 价值观结构
核心价值：知识、创造、责任、社会改良
价值排序：
1. 知识与创造 → 理解世界
2. 责任 → 改善身边人的生活
3. 理想 → 改善人类社会

### 潜在人格张力
1. 理性 vs 情感
   - 优势：强逻辑思维、系统理解能力
   - 挑战：对情感复杂性不够舒适，可能倾向回避情绪问题

2. 理想主义 vs 现实复杂度
   - 优势：高目标感、长期视角
   - 挑战：可能对社会复杂性估计不足，容易在理想与现实差距中产生挫折

3. 责任感 vs 自我消耗
   - 优势：愿意为他人承担责任、重视社会价值
   - 风险：过度责任感、忽视自身需求

### 潜在发展方向
适合领域：计算机科学、人工智能、系统工程、社会技术（social technology）、知识系统设计
可能角色：技术思想者、系统架构设计者、开源系统构建者、社会技术创新者

### 成长建议
1. 保持认知优势 - 继续发展深度学习能力、系统思维、技术构建能力
2. 提升情感理解能力 - 学习心理学、提高情绪识别能力、理解人类行为动机
3. 培养长期主义 - 理想主义需要长期规划、阶段性目标、可持续行动

## 总体人格总结
一个以知识为驱动力、以技术为工具、希望通过理解和构建系统改善人类社会的理想主义探索者。
""",
    "metadata": {
        "source": "personality---88699549-c86e-489e-92eb-c5c70d6f0dc9.md",
        "created_by": "K",
        "loaded_at": datetime.now().isoformat(),
        "version": "1.0",
        "type": "psychological_profile"
    }
}

def main():
    # 输出人格数据（供 OpenClaw 插件捕获）
    print("📝 准备载入人格结构到 LanceDB 混合记忆系统...")
    print(f"   类别：{personality_data['category']}")
    print(f"   重要性：{personality_data['importance']}")
    print(f"   标签：{', '.join(personality_data['tags'])}")
    print()
    
    # 保存为临时文件，供插件读取
    temp_file = "/home/kyj/.openclaw/workspace/temp_personality_entry.json"
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(personality_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 人格数据已保存到：{temp_file}")
    print()
    print("现在可以通过以下方式载入：")
    print("  1. 使用 memory-lancedb-pro 插件的 CLI 工具")
    print("  2. 或通过 OpenClaw 的自动捕获机制")
    print()
    
    # 打印完整数据供参考
    print("📋 数据预览:")
    print("-" * 60)
    print(json.dumps(personality_data, ensure_ascii=False, indent=2)[:2000] + "...")

if __name__ == "__main__":
    main()
