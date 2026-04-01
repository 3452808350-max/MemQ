#!/usr/bin/env node
/**
 * Synthetic PerLTQA - 召回率基准测试
 * 测试 memory-lancedb-pro 在不同数据量下的召回率表现
 * 
 * 使用 Kimi K2.5 作为评估 Agent
 */

import * as lancedb from '@lancedb/lancedb';
import { OpenAI } from 'openai';
import fs from 'fs';
import path from 'path';

// ============ 配置 ============
const config = {
  dbPath: '/home/kyj/.openclaw/workspace/lancedb',
  testScope: 'perltqa-benchmark',
  embedding: {
    apiKey: 'sk-e8b53592ebe841f28a03d4d54024761c',
    baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    model: 'text-embedding-v3'
  },
  kimi: {
    apiKey: 'sk-e8b53592ebe841f28a03d4d54024761c',
    baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    model: 'kimi-k2.5'
  }
};

// 数据规模梯度
const SCALES = ['baseline', 'small', 'medium', 'medium-large', 'large'];

// ============ 工具函数 ============

async function getEmbedding(text) {
  const client = new OpenAI({
    apiKey: config.embedding.apiKey,
    baseURL: config.embedding.baseURL
  });
  
  const response = await client.embeddings.create({
    model: config.embedding.model,
    input: text
  });
  
  return response.data[0].embedding;
}

async function queryKimi(prompt) {
  const client = new OpenAI({
    apiKey: config.kimi.apiKey,
    baseURL: config.kimi.baseURL
  });
  
  const response = await client.chat.completions.create({
    model: config.kimi.model,
    messages: [
      {
        role: "system",
        content: "你是一个记忆召回率评估助手。请严格判断检索到的记忆是否包含问题所需的关键信息。"
      },
      {
        role: "user",
        content: prompt
      }
    ],
    temperature: 0.1,
    max_tokens: 300
  });
  
  return response.choices[0].message.content;
}

// ============ 核心测试逻辑 ============

class RecallMetrics {
  constructor() {
    this.results = [];
  }

  record(query, targetId, retrieved, evalResult) {
    const hit = retrieved.slice(0, 5).some(r => r.id === targetId);
    const rank = retrieved.findIndex(r => r.id === targetId) + 1;
    
    this.results.push({
      query_id: query.id,
      query: query.query,
      target_id: targetId,
      hit_at_5: hit,
      rank: rank > 0 ? rank : -1,
      eval: evalResult
    });
  }

  getRecallAtK(k = 5) {
    const hits = this.results.filter(r => r.hit_at_5).length;
    return hits / this.results.length;
  }

  getMRR() {
    let sum = 0;
    for (const r of this.results) {
      if (r.rank > 0) {
        sum += 1 / r.rank;
      }
    }
    return sum / this.results.length;
  }

  getSummary() {
    return {
      total_queries: this.results.length,
      recall_at_5: this.getRecallAtK(5).toFixed(3),
      recall_at_10: this.getRecallAtK(10).toFixed(3),
      mrr: this.getMRR().toFixed(3)
    };
  }
}

async function insertMemories(db, memories, scope) {
  console.log(`  📥 插入 ${memories.length} 条记忆到 scope: ${scope}...`);
  
  let table;
  try {
    table = await db.openTable(scope);
  } catch (e) {
    // 创建新表
    const sampleEmbedding = await getEmbedding(memories[0].content);
    table = await db.createTable(scope, [{
      id: '',
      text: '',
      embedding: sampleEmbedding,
      metadata: {},
      scope: scope,
      category: '',
      importance: 0.7,
      timestamp: new Date().toISOString()
    }]);
    await table.delete('id != ""'); // 清空示例数据
  }
  
  // 批量插入
  const batchSize = 100;
  for (let i = 0; i < memories.length; i += batchSize) {
    const batch = memories.slice(i, i + batchSize);
    const records = await Promise.all(batch.map(async m => ({
      id: m.id,
      text: m.content,
      embedding: await getEmbedding(m.content),
      metadata: m.metadata,
      scope: scope,
      category: m.type,
      importance: 0.7,
      timestamp: m.timestamp
    })));
    await table.add(records);
  }
  
  console.log(`  ✅ 插入完成`);
}

async function runScaleTest(db, scaleName) {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`📊 测试规模：${scaleName}`);
  console.log('='.repeat(70));
  
  // 加载数据
  const dataDir = '/home/kyj/.openclaw/workspace/synthetic_perltqa';
  const memories = JSON.parse(fs.readFileSync(path.join(dataDir, `memories_${scaleName}.json`), 'utf-8'));
  const queries = JSON.parse(fs.readFileSync(path.join(dataDir, `queries_${scaleName}.json`), 'utf-8'));
  
  console.log(`  📚 记忆数：${memories.length}`);
  console.log(`  ❓ 查询数：${queries.length}`);
  
  // 清空并插入数据
  try {
    await db.dropTable(config.testScope);
  } catch (e) {
    // 表不存在，忽略
  }
  
  await insertMemories(db, memories, config.testScope);
  
  // 打开表进行检索
  const table = await db.openTable(config.testScope);
  
  // 运行测试
  const metrics = new RecallMetrics();
  
  for (let i = 0; i < queries.length; i++) {
    const query = queries[i];
    const targetId = query.target_memory_id;
    
    if (i % 10 === 0) {
      console.log(`  进度：${i + 1}/${queries.length}`);
    }
    
    // 向量检索
    const embedding = await getEmbedding(query.query);
    const retrieved = await table.search(embedding).limit(10).toArray();
    
    // 使用 Kimi 评估
    const evalPrompt = `
问题：${query.query}
目标记忆内容：${query.target_memory_content}
检索到的前 5 条记忆：
${retrieved.slice(0, 5).map((r, j) => `${j + 1}. ${r.text}`).join('\n')}

请判断：检索结果是否包含目标记忆的核心信息？
回答格式：是/否（只需回答一个字）
`;
    
    let evalResult;
    try {
      evalResult = await queryKimi(evalPrompt);
    } catch (e) {
      evalResult = 'Kimi 评估失败';
    }
    
    metrics.record(query, targetId, retrieved, evalResult);
  }
  
  // 清理测试数据
  await db.dropTable(config.testScope);
  
  return metrics;
}

// ============ 主函数 ============

async function main() {
  console.log('🧪 Synthetic PerLTQA 召回率基准测试');
  console.log('🤖 评估模型：Kimi K2.5');
  console.log(`📍 测试 Scope: ${config.testScope}`);
  console.log('='.repeat(70));
  
  const db = await lancedb.connect(config.dbPath);
  
  const allResults = {};
  
  for (const scale of SCALES) {
    const metrics = await runScaleTest(db, scale);
    allResults[scale] = metrics.getSummary();
    
    console.log(`\n📈 ${scale} 结果:`);
    console.log(`   Recall@5: ${allResults[scale].recall_at_5}`);
    console.log(`   Recall@10: ${allResults[scale].recall_at_10}`);
    console.log(`   MRR: ${allResults[scale].mrr}`);
  }
  
  // 保存结果
  const report = {
    timestamp: new Date().toISOString(),
    model: 'kimi-k2.5',
    scope: config.testScope,
    scales: allResults,
    data_points: SCALES.map(s => {
      const stats = JSON.parse(fs.readFileSync(`/home/kyj/.openclaw/workspace/synthetic_perltqa/stats_${s}.json`, 'utf-8'));
      return stats.num_memories;
    })
  };
  
  const outputPath = '/home/kyj/.openclaw/workspace/synthetic_perltqa/benchmark_result.json';
  fs.writeFileSync(outputPath, JSON.stringify(report, null, 2));
  
  console.log('\n' + '='.repeat(70));
  console.log('✅ 测试完成！');
  console.log(`📄 报告已保存：${outputPath}`);
  
  // 生成绘图数据
  console.log('\n📊 绘图数据:');
  console.log('数据量,Recall@5,Recall@10,MRR');
  for (const scale of SCALES) {
    const num = report.data_points[SCALES.indexOf(scale)];
    console.log(`${num},${allResults[scale].recall_at_5},${allResults[scale].recall_at_10},${allResults[scale].mrr}`);
  }
}

// 运行
main().catch(console.error);
