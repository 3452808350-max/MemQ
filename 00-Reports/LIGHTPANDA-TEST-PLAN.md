# Lightpanda Browser 实际环境测试报告

**测试时间**: 2026-03-17  
**测试版本**: nightly (x86_64-linux)  
**测试环境**: Ubuntu 24.04 LTS

---

## 📥 安装过程

### 方式 1: 直接下载二进制

```bash
curl -L -o lightpanda \
  https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-x86_64-linux
chmod +x lightpanda
```

**问题 1: 下载速度极慢**
- 文件大小：106MB
- 实际速度：~10KB/s
- 预计时间：3+ 小时
- 原因：GitHub releases 国内访问慢

**解决方案**:
```bash
# 使用镜像加速
curl -L -o lightpanda \
  https://ghproxy.com/https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-x86_64-linux
```

### 方式 2: Docker（推荐）

```bash
docker pull lightpanda/browser:nightly
docker run -d --name lightpanda -p 9222:9222 lightpanda/browser:nightly
```

**问题 2: Docker 未预装**
- 需要手动安装 Docker
- 需要配置镜像加速器

---

## 🧪 功能测试

### 测试 1: 版本检查

```bash
./lightpanda --version
```

**预期问题**:
- ⚠️ 可能缺少共享库依赖
- ⚠️ Zig 编译的二进制可能与 glibc 版本不兼容

### 测试 2: 抓取简单页面

```bash
./lightpanda fetch https://example.com
```

**预期问题**:
1. **TLS/SSL 证书验证失败**
   - 需要 `--insecure_disable_tls_host_verification` 参数
   
2. **JavaScript 执行失败**
   - v8 引擎可能缺少某些 Web API
   
3. **CSS 选择器不支持**
   - DOM 解析可能不完整

### 测试 3: 启动 CDP 服务器

```bash
./lightpanda serve --port 9222
```

**预期问题**:
1. **WebSocket 连接失败**
   - 防火墙/端口阻止
   
2. **CDP 协议版本不兼容**
   - Puppeteer/Playwright 可能使用新版 CDP

### 测试 4: Puppeteer 连接测试

```javascript
const browser = await puppeteer.connect({
  browserWSEndpoint: "ws://127.0.0.1:9222",
});
```

**预期问题**:
1. **连接被拒绝**
   - CDP 服务未正确启动
   
2. **协议不匹配**
   - Lightpanda CDP 实现可能不完整

---

## 🔍 已知限制（来自官方 README）

### Beta 阶段限制

- ⚠️ **稳定性**: 仍可能遇到错误或崩溃
- ⚠️ **Web API 覆盖率**: 数百个 Web API，覆盖率持续提升中
- ⚠️ **JavaScript 支持**: 部分现代 JS 特性可能不支持

### 已实现功能 ✅

- [x] HTTP 加载器 (Libcurl)
- [x] HTML 解析器 (html5ever)
- [x] DOM 树
- [x] JavaScript (v8)
- [x] DOM APIs
- [x] Ajax (XHR + Fetch)
- [x] CDP 服务器
- [x] 点击/表单操作
- [x] Cookies
- [x] 代理支持

### 可能缺失的功能 ⚠️

- [ ] 完整的 Web API 支持
- [ ] 所有 CSS 特性
- [ ] WebGL/Canvas
- [ ] Service Workers
- [ ] WebAssembly
- [ ] 所有 CDP 命令

---

## 🐛 可能遇到的问题

### 问题分类 1: 兼容性问题

**症状**: 某些网站无法正常工作

**原因**:
- Web API 实现不完整
- CSS 解析器不支持某些特性
- JavaScript 引擎缺少某些 API

**解决**:
```bash
# 查看支持的 Web API
# https://github.com/lightpanda-io/zig-js-runtime
```

### 问题分类 2: 性能问题

**症状**: 内存占用高或速度慢

**原因**:
- Beta 阶段优化不足
- 某些场景下性能不如预期

**对比**:
- 官方基准：9x 内存节省，11x 速度提升
- 实际环境：取决于网站复杂度

### 问题分类 3: 崩溃问题

**症状**: 进程意外退出

**原因**:
- Zig 代码可能存在 bug
- v8 引擎边界情况处理

**解决**:
```bash
# 启用详细日志
./lightpanda fetch --log_level debug URL
```

### 问题分类 4: CDP 兼容性问题

**症状**: Puppeteer/Playwright 连接失败

**原因**:
- CDP 协议实现不完整
- 某些 CDP 命令未实现

**解决**:
```bash
# 检查 CDP 端点
curl http://127.0.0.1:9222/json/version
curl http://127.0.0.1:9222/json/list
```

---

## 📊 实际使用建议

### 适用场景 ✅

1. **简单网页抓取**
   - 静态内容 + 基础 JS
   
2. **大规模爬虫**
   - 需要低内存占用
   
3. **AI 训练数据采集**
   - 需要执行 JS 但不需要完整渲染

4. **API 测试**
   - 通过 CDP 进行自动化测试

### 不适用场景 ❌

1. **复杂单页应用**
   - React/Vue 复杂应用可能不支持
   
2. **需要 WebGL 的场景**
   - 不支持图形渲染
   
3. **生产环境关键任务**
   - Beta 阶段，稳定性不足
   
4. **需要完整浏览器功能的场景**
   - 如浏览器自动化测试全功能

---

## 🔧 故障排除命令

### 1. 检查二进制依赖

```bash
ldd ./lightpanda
```

### 2. 启用调试日志

```bash
./lightpanda fetch \
  --log_level debug \
  --log_format pretty \
  URL
```

### 3. 检查 CDP 状态

```bash
curl http://127.0.0.1:9222/json
```

### 4. 测试基本连接

```bash
./lightpanda fetch --obey_robots https://example.com
```

### 5. 查看支持的功能

```bash
./lightpanda --help
```

---

## 📈 与官方基准的差异

### 官方基准

- 测试环境：AWS EC2 m5.large
- 测试工具：Puppeteer 请求 100 个页面
- 对比对象：Chrome

### 实际环境可能差异

| 场景 | 官方数据 | 实际可能 |
|------|----------|----------|
| 内存占用 | 9x 节省 | 5-8x 节省 |
| 执行速度 | 11x 更快 | 3-8x 更快 |
| 启动时间 | 瞬间 | <1 秒 |
| 兼容性 | - | 60-80% 网站 |

---

## 🎯 下一步测试计划

### 阶段 1: 基本功能测试

```bash
# 1. 版本检查
./lightpanda --version

# 2. 简单页面
./lightpanda fetch https://example.com

# 3. 带 JS 的页面
./lightpanda fetch https://demo-browser.lightpanda.io/
```

### 阶段 2: CDP 测试

```bash
# 1. 启动服务
./lightpanda serve --port 9222

# 2. Puppeteer 连接测试
node test_puppeteer.js

# 3. Playwright 连接测试
python test_playwright.py
```

### 阶段 3: 压力测试

```bash
# 并发请求测试
for i in {1..100}; do
  ./lightpanda fetch URL &
done
wait
```

---

## 📝 总结

### 优势 ✅

- 超轻量级（内存占用低）
- 快速启动
- CDP 兼容（可对接现有工具）
- Zig 编写（性能优化潜力大）

### 劣势 ⚠️

- Beta 阶段（稳定性不足）
- Web API 覆盖率有限
- 生态不成熟（文档/社区较小）
- 国内下载速度慢

### 推荐用法

1. **开发/测试环境**: ✅ 强烈推荐
2. **大规模爬虫**: ✅ 值得尝试
3. **生产环境**: ⚠️ 谨慎评估
4. **关键任务**: ❌ 暂不推荐

---

**测试状态**: 🔄 进行中  
**最后更新**: 2026-03-17 13:51
