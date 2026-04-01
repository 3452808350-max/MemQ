#!/usr/bin/env node
/**
 * OpenClaw WebSocket Proxy
 * 部署在公网服务器 (106.53.186:90)，转发到本地 OpenClaw Gateway
 */

const WebSocket = require('ws');
const http = require('http');
const crypto = require('crypto');

// 配置
const CONFIG = {
  // 公网监听端口
  port: process.env.PROXY_PORT || 8080,
  
  // 本地 OpenClaw Gateway 地址
  upstreamUrl: process.env.UPSTREAM_URL || 'ws://127.0.0.1:18789/ws',
  
  // 可选：简单 Token 认证（留空则不验证）
  authToken: process.env.AUTH_TOKEN || '',
  
  // 日志级别: debug, info, warn, error
  logLevel: process.env.LOG_LEVEL || 'info'
};

// 日志工具
const logger = {
  debug: (...args) => CONFIG.logLevel === 'debug' && console.log('[DEBUG]', ...args),
  info: (...args) => ['debug', 'info'].includes(CONFIG.logLevel) && console.log('[INFO]', ...args),
  warn: (...args) => ['debug', 'info', 'warn'].includes(CONFIG.logLevel) && console.warn('[WARN]', ...args),
  error: (...args) => console.error('[ERROR]', ...args)
};

// 验证 Token
function verifyToken(req) {
  if (!CONFIG.authToken) return true;
  
  const url = new URL(req.url, `http://${req.headers.host}`);
  const token = url.searchParams.get('token') || req.headers['x-auth-token'];
  
  return token === CONFIG.authToken;
}

// 创建 WebSocket 服务器
const wss = new WebSocket.Server({ 
  port: CONFIG.port,
  verifyClient: (info, cb) => {
    if (!verifyToken(info.req)) {
      cb(false, 401, 'Unauthorized');
      return;
    }
    cb(true);
  }
});

logger.info(`WebSocket Proxy started on port ${CONFIG.port}`);
logger.info(`Forwarding to: ${CONFIG.upstreamUrl}`);

wss.on('connection', (client, req) => {
  const clientId = crypto.randomUUID().slice(0, 8);
  const ip = req.socket.remoteAddress;
  
  logger.info(`[${clientId}] Client connected from ${ip}`);
  
  // 连接到上游 OpenClaw Gateway
  let upstream;
  try {
    upstream = new WebSocket(CONFIG.upstreamUrl);
  } catch (err) {
    logger.error(`[${clientId}] Failed to connect upstream:`, err.message);
    client.close(1011, 'Upstream connection failed');
    return;
  }
  
  let upstreamReady = false;
  let clientBuffer = [];
  
  // 上游连接成功
  upstream.on('open', () => {
    logger.info(`[${clientId}] Upstream connected`);
    upstreamReady = true;
    
    // 发送缓冲的消息
    while (clientBuffer.length > 0) {
      const data = clientBuffer.shift();
      upstream.send(data);
    }
  });
  
  // 客户端 -> 上游
  client.on('message', (data) => {
    logger.debug(`[${clientId}] Client -> Upstream:`, data.toString().slice(0, 200));
    
    if (upstreamReady) {
      upstream.send(data);
    } else {
      clientBuffer.push(data);
    }
  });
  
  // 上游 -> 客户端
  upstream.on('message', (data) => {
    logger.debug(`[${clientId}] Upstream -> Client:`, data.toString().slice(0, 200));
    
    if (client.readyState === WebSocket.OPEN) {
      client.send(data);
    }
  });
  
  // 错误处理
  client.on('error', (err) => {
    logger.error(`[${clientId}] Client error:`, err.message);
  });
  
  upstream.on('error', (err) => {
    logger.error(`[${clientId}] Upstream error:`, err.message);
    if (client.readyState === WebSocket.OPEN) {
      client.close(1011, 'Upstream error');
    }
  });
  
  // 关闭处理
  client.on('close', (code, reason) => {
    logger.info(`[${clientId}] Client disconnected:`, code, reason.toString());
    upstream.close();
  });
  
  upstream.on('close', (code, reason) => {
    logger.info(`[${clientId}] Upstream disconnected:`, code, reason.toString());
    if (client.readyState === WebSocket.OPEN) {
      client.close(1000, 'Upstream closed');
    }
  });
});

// 健康检查 HTTP 端点
const healthServer = http.createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'ok',
      uptime: process.uptime(),
      connections: wss.clients.size,
      timestamp: new Date().toISOString()
    }));
  } else {
    res.writeHead(404);
    res.end('Not Found');
  }
});

healthServer.listen(CONFIG.port + 1, () => {
  logger.info(`Health check endpoint: http://localhost:${CONFIG.port + 1}/health`);
});

// 优雅退出
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, closing server...');
  wss.close(() => {
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  logger.info('SIGINT received, closing server...');
  wss.close(() => {
    process.exit(0);
  });
});
