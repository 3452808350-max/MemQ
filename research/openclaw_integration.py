#!/usr/bin/env python3
"""
MemQ OpenClaw 集成指南

将 MemQ Pro 集成到 OpenClaw 记忆系统的完整方案

⚠️  重要：OpenClaw 插件系统基于 TypeScript，Python 插件需要通过 SDK 适配
当前方案：作为 Python 工具库使用，通过 CLI 或 API 调用
"""

# ============================================================================
# 方案 1: 作为 Python 工具库使用（推荐，立即可用）
# ============================================================================

"""
在 OpenClaw 对话中直接使用：

```python
from memq.openclaw_plugin import MemQOpenClawPlugin

# 初始化
plugin = MemQOpenClawPlugin()

# 保存记忆
plugin.save_memory("user_pref", "喜欢简洁代码", category="preferences")

# 检索记忆
results = plugin.search("代码风格", top_k=3)
for r in results:
    print(f"{r['id']}: {r['content']} (相关性：{r['score']:.3f})")
```

优势:
- ✅ 立即可用，无需修改 OpenClaw 核心
- ✅ 完整功能（分层 + GPU 加速 + 缓存）
- ✅ 可与其他插件并存

劣势:
- ❌ 需要手动调用（非自动注入）
"""


# ============================================================================
# 方案 2: TypeScript 插件封装（未来方案）
# ============================================================================

"""
由于 OpenClaw 插件系统基于 TypeScript，完整的插件集成需要：

1. 创建 TypeScript 插件包装器
2. 调用 Python 后端（通过 subprocess 或 HTTP API）
3. 实现 OpenClaw 插件接口

步骤（供参考）:

```bash
# 创建插件目录
mkdir -p ~/.openclaw/plugins/memq-pro
cd ~/.openclaw/plugins/memq-pro

# 复制配置文件
cp /home/kyj/.openclaw/workspace/memq/openclaw_plugin.json .

# 创建 TypeScript 包装器
cat > index.ts << 'EOF'
import { spawn } from 'node:child_process';
import { join } from 'node:path';

const PYTHON_SCRIPT = join(__dirname, '../../workspace/memq/openclaw_plugin.py');

export function setup(pluginApi: any, config: any) {
  return {
    async saveMemory(id: string, content: string, category: string) {
      // 调用 Python 脚本
      return callPython('save_memory', [id, content, category]);
    },
    async search(query: string, topK: number, layer: string) {
      return callPython('search', [query, topK, layer]);
    }
  };
}

function callPython(method: string, args: any[]) {
  return new Promise((resolve, reject) => {
    const py = spawn('python3', [PYTHON_SCRIPT, '--method', method, '--args', JSON.stringify(args)]);
    let output = '';
    py.stdout.on('data', (data) => output += data);
    py.on('close', (code) => {
      if (code === 0) resolve(JSON.parse(output));
      else reject(new Error(`Python exited with code ${code}`));
    });
  });
}
EOF
```

注意:
- 此方案需要额外开发工作
- 当前推荐方案 1（Python 工具库）
"""


# ============================================================================
# 使用示例
# ============================================================================

def example_usage():
    """MemQ OpenClaw 插件使用示例"""
    
    from openclaw_plugin import MemQOpenClawPlugin
    
    # 初始化
    plugin = MemQOpenClawPlugin(
        data_dir="/home/kyj/.openclaw/workspace/memq",
        cache_ttl_days=7,
        max_cache_size=1000
    )
    
    # 保存记忆
    plugin.save_memory(
        "user_preference_001",
        "K 喜欢简洁的代码风格，讨厌过度工程化",
        category="user/preferences"
    )
    
    # 检索记忆（L1 层，平衡速度和内容）
    results = plugin.search("代码风格偏好", top_k=3, layer="l1")
    for r in results:
        print(f"{r['id']}: {r['content']} (相关性：{r['score']:.3f})")
    
    # 检索记忆（L0 层，最快）
    results_l0 = plugin.search("代码风格", top_k=5, layer="l0")
    
    # 检索记忆（L2 层，完整内容）
    results_l2 = plugin.search("代码风格", top_k=3, layer="l2")
    
    # 获取统计
    stats = plugin.get_stats()
    print(f"记忆总数：{stats['total_memories']}")
    print(f"Token 节省：{stats['token_savings_l0']} (L0), {stats['token_savings_l1']} (L1)")
    
    # 可视化检索轨迹
    print(plugin.visualize_trajectory())
    
    # 清理（保存缓存）
    plugin.close()


# ============================================================================
# 配置选项
# ============================================================================

"""
MemQOpenClawPlugin 配置选项:

- `data_dir`: MemQ 数据目录（默认：/home/kyj/.openclaw/workspace/memq）
- `cache_dir`: 缓存目录（默认：{data_dir}/cache）
- `cache_ttl_days`: 缓存有效期（天）（默认：7）
- `max_cache_size`: 最大缓存条目（默认：1000）
- `enable_concurrent`: 启用并发检索（默认：True）

搜索选项:

- `query`: 查询文本（必需）
- `top_k`: 返回结果数（默认：5）
- `layer`: 返回层次 "l0"/"l1"/"l2"（默认："l1"）
"""


# ============================================================================
# 性能对比
# ============================================================================

"""
MemQ vs 原有 LanceDB 插件:

| 指标 | LanceDB | MemQ Pro | 提升 |
|------|---------|----------|------|
| 检索延迟 | ~500ms | ~100ms* | 5x |
| 召回率 | ~70% | ~75%+ | +5% |
| Token 消耗 | 100% | 12-30% | -70-88% |
| GPU 加速 | ❌ | ✅ | - |
| 缓存持久化 | ❌ | ✅ | - |

*缓存命中情况下
"""


# ============================================================================
# 故障排查
# ============================================================================

"""
常见问题:

1. **Ollama 服务未运行**
   ```bash
   systemctl status ollama
   sudo systemctl start ollama
   ```

2. **模型未加载到 GPU**
   ```bash
   ollama ps
   # 应该显示 "100% GPU"
   ```

3. **缓存加载失败**
   - 检查缓存目录权限
   - 删除损坏的缓存文件重新生成

4. **检索速度慢**
   - 检查 GPU 是否启用
   - 检查缓存是否命中
   - 启用并发检索（enable_concurrent=True）
"""


if __name__ == '__main__':
    print("="*70)
    print("MemQ OpenClaw 集成指南")
    print("="*70)
    print(__doc__)
    
    print("\n" + "="*70)
    print("使用示例:")
    print("="*70)
    example_usage()
