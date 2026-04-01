# DSS 快速开始指南

## 🚀 一键命令

```bash
# 验证配置
python3 /home/kyj/.openclaw/workspace/dss_config.py

# 运行所有测试
python3 -m unittest discover /home/kyj/.openclaw/workspace/tests -v

# 性能基准测试
python3 /home/kyj/.openclaw/workspace/benchmark_dss.py

# 每日选股分析
python3 /home/kyj/.openclaw/workspace/dss_daily_optimized.py
```

## 📁 关键文件

| 文件 | 用途 |
|------|------|
| `dss_config.py` | 统一配置 |
| `DSS_README.md` | 完整文档 |
| `tests/` | 测试目录 |
| `benchmark_dss.py` | 性能测试 |

## ✅ 优化完成状态

- [x] 配置统一
- [x] 测试覆盖 (27/27 通过)
- [x] 文档完善
- [x] 性能优化 (200x 提升)

## 📊 性能指标

- 单股票分析：~10ms
- 20 股票批量：~0.2s
- 测试通过率：100%
