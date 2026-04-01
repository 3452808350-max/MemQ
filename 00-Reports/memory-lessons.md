# MEMORY-lessons.md - 经验教训

## 技术经验

1. **先检查现有资源** - 项目可能已有API Key等资源
2. **理解限制** - 免费API有调用限制，需要合理规划
3. **保持专注** - 完成核心功能后再扩展
4. **文档重要** - 记录决策和发现，便于后续维护
5. **路径问题** - 插件路径配置要使用绝对路径

---

## 踩坑记录

### Memory LanceDB Pro
- ❌ 路径错误: `.openclaw/workspace/` → `/home/kyj/.openclaw/workspace/`
- ❌ API Key格式: `${sk-xxx}` → 直接写 `sk-xxx`

### Telegram
- 需要代理才能连接 Telegram API
- 使用 `http://127.0.0.1:7890` (FlClash)

### Gateway
- 配置文件变更后需要重启
- 使用 `systemctl --user restart openclaw-gateway.service`

---

## 决策原则

1. **真实数据优先** - 不用模拟数据
2. **验证严谨** - Walk Forward防止过拟合
3. **简洁实用** - 不过度工程化
4. **自动化** - 定时任务减少手动操作

---

## 安全提示

- 拒绝 piracy 相关请求
- 提供合法替代方案
- 保护用户隐私

---

*最后更新: 2026-02-25*
