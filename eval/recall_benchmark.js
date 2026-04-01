#!/usr/bin/env node
/**
 * Synthetic PerLTQA - 召回率基准测试
 * 测试 memory-lancedb-pro 在不同数据量下的召回率表现
 * 
 * 使用 Kimi K2.5 作为评估 Agent
 * 
 * ⚠️ 安全提示：API Key 应通过环境变量配置
 * 使用方式：
 *   export DASHSCOPE_API_KEY=your_key
 *   export MINIMAX_API_KEY=your_key
 *   node recall_benchmark.js
 */

import * as lancedb from '@lancedb/lancedb';
import { OpenAI } from 'openai';
import fs from 'fs';
import path from 'path';
import dotenv from 'dotenv';

// 加载 .env 文件
dotenv.config();

// ============ 配置 ============
const config = {
  dbPath: '/home/kyj/.openclaw/workspace/lancedb',
  testScope: `perltqa-test-${Date.now()}`,
  embedding: {
    // ✅ 从环境变量读取 API Key
    apiKey: process.env.DASHSCOPE_API_KEY,
    baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    model: 'text-embedding-v3'
  },
  evaluator: {
    // ✅ 从环境变量读取 API Key
    apiKey: process.env.MINIMAX_API_KEY,
    baseURL: 'https://api.minimax.chat/v1',
    model: 'minimax2.5'
  }
};

// 验证 API Key 是否配置
if (!config.embedding.apiKey) {
  console.error('❌ 错误：缺少 DASHSCOPE_API_KEY 环境变量');
  console.error('请设置：export DASHSCOPE_API_KEY=your_key\n');
  process.exit(1);
}

if (!config.evaluator.apiKey) {
  console.error('❌ 错误：缺少 MINIMAX_API_KEY 环境变量');
  console.error('请设置：export MINIMAX_API_KEY=your_key\n');
  process.exit(1);
}

// 数据规模梯度
const SCALES = ['baseline', 'small', 'medium', 'medium-large', 'large'];

// ============ 工具函数 ============

async function getEmbedding(text, retries = 3) {
  const client = new OpenAI({
    apiKey: config.embedding.apiKey,
    baseURL: config.embedding.baseURL
  });
  
  for (let i = 0; i < retries; i++) {
    try {
      const response = await client.embeddings.create({
        model: config.embedding.model,
        input: text
      });
      return response.data[0].embedding;
    } catch (e) {
      if (e.status === 429 && i < retries - 1) {
        const waitTime = Math.pow(2, i) * 1000; // 指数退避：1s, 2s, 4s
