# 话题切换自动记忆系统

**最后更新**: 2026-03-17 10:46

---

## 🎯 功能

当检测到用户开始新话题时：
1. 自动保存当前对话摘要到记忆文件
2. 清空 context 标记
3. 准备新话题的记忆载入

---

## 📁 文件结构

```
/home/kyj/.openclaw/workspace/
├── topic_memory.py          # 话题检测脚本
├── .current_topic.json      # 当前话题状态
└── memory/
    ├── topic-memq-integration.md  # 已保存的话题
    └── ...
```

---

## 🔧 使用方式

### 手动保存话题

```bash
# 保存当前话题
python3 /home/kyj/.openclaw/workspace/topic_memory.py \
  save "MemQ 集成" "完成质量评分系统集成" "关键点 1" "关键点 2"
```

### 查看当前话题

```bash
python3 /home/kyj/.openclaw/workspace/topic_memory.py load
```

### 设置新话题

```bash
python3 /home/kyj/.openclaw/workspace/topic_memory.py \
  set "新话题名称"
```

---

## 🤖 自动检测

**触发词** (检测到这些词时保存当前话题):
- 新的话题 / 换个话题 / 聊点别的
- 准备 / 开始 / 结束 / 完成 / 告一段落
- ok / 好的 / 明白了 / 懂了
- 下一个 / 继续 / 然后

**检测逻辑**:
1. 监听用户消息
2. 匹配触发词
3. 调用 LLM 生成摘要
4. 保存到记忆文件
5. 清空 context

---

## 📝 记忆文件格式

```markdown
# 💾 记忆载入：[话题名称]

**时间**: YYYY-MM-DD HH:mm

## 📋 摘要

[对话摘要]

## 🔑 关键点

1. [关键点 1]
2. [关键点 2]
...

---
**状态**: ✅ 已保存
```

---

## 🧪 测试

```bash
# 1. 设置当前话题
python3 topic_memory.py set "测试话题"

# 2. 保存话题
python3 topic_memory.py save "测试" "这是测试" "关键点 1"

# 3. 查看状态
python3 topic_memory.py load
```

---

## 🔗 与 OpenClaw 集成

在 `HEARTBEAT.md` 中添加：

```markdown
# 话题切换检测
- 检测用户消息中的话题切换触发词
- 触发时调用 topic_memory.py save
- 清空 .current_topic.json
```

或在插件中注册 `message_received` 钩子：

```typescript
api.on("message_received", async (event, ctx) => {
  if (detectTopicSwitch(event.content)) {
    await saveCurrentTopic();
  }
});
```

---

**状态**: 🚧 基础功能完成，待集成到 Gateway
