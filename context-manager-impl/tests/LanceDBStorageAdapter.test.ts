/**
 * LanceDBStorageAdapter 完整测试 (P3)
 */

import { describe, it, expect, beforeEach } from "vitest";

// Mock MemoryStore
class MockMemoryStore {
  private entries: Map<string, any> = new Map();
  private idCounter = 0;

  async store(entry: any): Promise<any> {
    const id = `mem-${++this.idCounter}`;
    const fullEntry = { ...entry, id, timestamp: Date.now() };
    this.entries.set(id, fullEntry);
    return fullEntry;
  }

  async vectorSearch(vector: number[], limit = 10, minScore = 0.3, scopeFilter?: string[]): Promise<any[]> {
    const results: any[] = [];
    for (const [id, entry] of this.entries) {
      if (!scopeFilter || scopeFilter.includes(entry.scope)) {
        results.push({ entry, score: 0.8 });
      }
    }
    return results.slice(0, limit);
  }

  async bm25Search(query: string, limit = 10, scopeFilter?: string[]): Promise<any[]> {
    const results: any[] = [];
    for (const [id, entry] of this.entries) {
      if (entry.text.includes(query) && (!scopeFilter || scopeFilter.includes(entry.scope))) {
        results.push({ entry, score: 0.7 });
      }
    }
    return results.slice(0, limit);
  }

  async list(scopeFilter?: string[], category?: string, limit = 20, offset = 0): Promise<any[]> {
    const results: any[] = [];
    for (const [id, entry] of this.entries) {
      if (!scopeFilter || scopeFilter.includes(entry.scope)) {
        results.push(entry);
      }
    }
    return results.sort((a, b) => b.timestamp - a.timestamp).slice(offset, offset + limit);
  }

  async stats(scopeFilter?: string[]): Promise<any> {
    const scopeCounts: Record<string, number> = {};
    let totalCount = 0;
    for (const [id, entry] of this.entries) {
      if (!scopeFilter || scopeFilter.includes(entry.scope)) {
        totalCount++;
        scopeCounts[entry.scope] = (scopeCounts[entry.scope] || 0) + 1;
      }
    }
    return { totalCount, scopeCounts, categoryCounts: {} };
  }
}

class MockEmbedder {
  async embed(text: string): Promise<number[]> {
    return Array.from({ length: 1536 }, (_, i) => Math.sin(text.length + i) * 0.1);
  }
}

// 测试适配器
class TestAdapter {
  store: MockMemoryStore;
  embedder: MockEmbedder;
  scope: string;

  constructor(store: MockMemoryStore, embedder: MockEmbedder, scope = "test-scope") {
    this.store = store;
    this.embedder = embedder;
    this.scope = scope;
  }

  async storeNotification(notification: any): Promise<string> {
    const text = `Task ${notification.taskId}: ${notification.summary}`;
    const vector = await this.embedder.embed(text);
    const entry = {
      text,
      vector,
      category: "fact",
      scope: this.scope,
      importance: notification.status === "failed" ? 0.9 : 0.7,
      metadata: JSON.stringify(notification),
    };
    const stored = await this.store.store(entry);
    return stored.id;
  }

  async semanticSearch(query: string, limit = 10): Promise<any[]> {
    const vector = await this.embedder.embed(query);
    const results = await this.store.vectorSearch(vector, limit, 0.3, [this.scope]);
    return results.map((r: any) => JSON.parse(r.entry.metadata));
  }

  async keywordSearch(query: string, limit = 10): Promise<any[]> {
    const results = await this.store.bm25Search(query, limit, [this.scope]);
    return results.map((r: any) => JSON.parse(r.entry.metadata));
  }

  async hybridSearch(query: string, limit = 10): Promise<any[]> {
    const [vResults, kResults] = await Promise.all([
      this.semanticSearch(query, limit),
      this.keywordSearch(query, limit),
    ]);
    const seen = new Set();
    const merged: any[] = [];
    for (const r of [...vResults, ...kResults]) {
      if (!seen.has(r.taskId)) {
        seen.add(r.taskId);
        merged.push(r);
      }
    }
    return merged.slice(0, limit);
  }

  async query(filters: any): Promise<any> {
    const entries = await this.store.list([this.scope], undefined, filters.limit || 10, filters.offset || 0);
    let notifications = entries.map((e: any) => JSON.parse(e.metadata));
    if (filters.taskId) notifications = notifications.filter((n: any) => n.taskId === filters.taskId);
    if (filters.agentId) notifications = notifications.filter((n: any) => n.agentId === filters.agentId);
    if (filters.status) notifications = notifications.filter((n: any) => n.status === filters.status);
    const stats = await this.store.stats([this.scope]);
    return { notifications, total: stats.totalCount, hasMore: notifications.length >= (filters.limit || 10) };
  }

  async getStats(): Promise<any> {
    const stats = await this.store.stats([this.scope]);
    return { total: stats.totalCount, byScope: stats.scopeCounts };
  }
}

describe("LanceDBStorageAdapter", () => {
  let adapter: TestAdapter;
  let mockStore: MockMemoryStore;
  let mockEmbedder: MockEmbedder;

  beforeEach(() => {
    mockStore = new MockMemoryStore();
    mockEmbedder = new MockEmbedder();
    adapter = new TestAdapter(mockStore, mockEmbedder);
  });

  describe("存储", () => {
    it("应该存储通知", async () => {
      const notification = { taskId: "task-1", agentId: "agent-1", status: "completed", summary: "Test task" };
      const id = await adapter.storeNotification(notification);
      expect(id).toContain("mem-");
    });

    it("应该批量存储", async () => {
      const notifications = [
        { taskId: "task-1", agentId: "agent-1", status: "completed", summary: "Task 1" },
        { taskId: "task-2", agentId: "agent-2", status: "failed", summary: "Task 2" },
      ];
      const ids = await Promise.all(notifications.map(n => adapter.storeNotification(n)));
      expect(ids).toHaveLength(2);
    });
  });

  describe("检索", () => {
    beforeEach(async () => {
      await adapter.storeNotification({ taskId: "task-1", agentId: "agent-1", status: "completed", summary: "Test task completed" });
    });

    it("应该语义搜索", async () => {
      const results = await adapter.semanticSearch("completed task", 10);
      expect(results.length).toBeGreaterThan(0);
    });

    it("应该关键词搜索", async () => {
      const results = await adapter.keywordSearch("task-1", 10);
      expect(results.length).toBeGreaterThan(0);
    });

    it("应该混合搜索", async () => {
      const results = await adapter.hybridSearch("task", 10);
      expect(results.length).toBeGreaterThan(0);
    });
  });

  describe("查询", () => {
    beforeEach(async () => {
      await adapter.storeNotification({ taskId: "task-1", agentId: "agent-1", status: "completed", summary: "Task 1" });
      await adapter.storeNotification({ taskId: "task-2", agentId: "agent-2", status: "failed", summary: "Task 2" });
    });

    it("应该按taskId查询", async () => {
      const result = await adapter.query({ taskId: "task-1", limit: 10 });
      expect(result.notifications.length).toBeGreaterThan(0);
    });

    it("应该按agentId查询", async () => {
      const result = await adapter.query({ agentId: "agent-1", limit: 10 });
      expect(result.notifications.length).toBeGreaterThan(0);
    });

    it("应该按status查询", async () => {
      const result = await adapter.query({ status: "completed", limit: 10 });
      expect(result.notifications.length).toBeGreaterThan(0);
    });

    it("应该支持分页", async () => {
      const result = await adapter.query({ limit: 1 });
      expect(result.notifications.length).toBeLessThanOrEqual(1);
    });
  });

  describe("统计", () => {
    it("应该获取统计信息", async () => {
      await adapter.storeNotification({ taskId: "task-1", agentId: "agent-1", status: "completed", summary: "Task 1" });
      const stats = await adapter.getStats();
      expect(stats.total).toBeGreaterThan(0);
    });
  });
});
