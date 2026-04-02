/**
 * LanceDBStorageAdapter - memory-lancedb-pro 存储适配器 (P3)
 */

import {
  TaskNotificationConfig,
  DEFAULT_TASK_NOTIFICATION_CONFIG,
} from "../types/index.js";

// TaskNotification 类型（与 TaskNotificationService 一致）
export interface TaskNotification {
  taskId: string;
  agentId: string;
  status: TaskStatus;
  summary: string;
  result?: string;
  scope: string;
  timestamp: number;
  usage: {
    totalTokens: number;
    toolUses: number;
    durationMs: number;
  };
}

export type TaskStatus = "completed" | "failed" | "killed" | "running";

export interface NotificationQuery {
  taskId?: string;
  agentId?: string;
  status?: TaskStatus;
  since?: number;
  until?: number;
  limit?: number;
  offset?: number;
  sortBy?: "timestamp" | "usage";
  sortOrder?: "asc" | "desc";
}

export interface NotificationQueryResult {
  notifications: TaskNotification[];
  total: number;
  hasMore: boolean;
}

export interface NotificationStats {
  total: number;
  byStatus: Record<TaskStatus, number>;
  byScope: Record<string, number>;
  retentionDays: number;
}

interface MemoryEntry {
  id: string;
  text: string;
  vector: number[];
  category: "preference" | "fact" | "decision" | "entity" | "other";
  scope: string;
  importance: number;
  timestamp: number;
  metadata?: string;
}

interface MemorySearchResult {
  entry: MemoryEntry;
  score: number;
}

interface MemoryStore {
  store(entry: Omit<MemoryEntry, "id" | "timestamp">): Promise<MemoryEntry>;
  vectorSearch(vector: number[], limit?: number, minScore?: number, scopeFilter?: string[]): Promise<MemorySearchResult[]>;
  bm25Search(query: string, limit?: number, scopeFilter?: string[]): Promise<MemorySearchResult[]>;
  delete(id: string, scopeFilter?: string[]): Promise<boolean>;
  list(scopeFilter?: string[], category?: string, limit?: number, offset?: number): Promise<MemoryEntry[]>;
  stats(scopeFilter?: string[]): Promise<{ totalCount: number; scopeCounts: Record<string, number>; categoryCounts: Record<string, number> }>;
  update(id: string, updates: Partial<MemoryEntry>, scopeFilter?: string[]): Promise<MemoryEntry | null>;
  bulkDelete(scopeFilter: string[], beforeTimestamp?: number): Promise<number>;
}

interface Embedder {
  embed(text: string): Promise<number[]>;
}

export class LanceDBStorageAdapter {
  private store: MemoryStore;
  private embedder: Embedder;
  private config: TaskNotificationConfig;

  constructor(store: MemoryStore, embedder: Embedder, config?: Partial<TaskNotificationConfig>) {
    this.store = store;
    this.embedder = embedder;
    this.config = { ...DEFAULT_TASK_NOTIFICATION_CONFIG, ...config };
  }

  private async toMemoryEntry(notification: TaskNotification): Promise<Omit<MemoryEntry, "id" | "timestamp">> {
    const text = this.notificationToText(notification);
    const vector = await this.embedder.embed(text);

    return {
      text,
      vector,
      category: "fact" as const,
      scope: notification.scope,
      importance: notification.status === "failed" ? 0.9 : 0.7,
      metadata: JSON.stringify({
        taskId: notification.taskId,
        agentId: notification.agentId,
        status: notification.status,
        summary: notification.summary,
        result: notification.result,
        usage: notification.usage,
      }),
    };
  }

  private notificationToText(notification: TaskNotification): string {
    return `Task ${notification.taskId} by ${notification.agentId}: ${notification.summary}. Status: ${notification.status}. ${notification.result || ""}`;
  }

  private toTaskNotification(entry: MemoryEntry): TaskNotification {
    const metadata = JSON.parse(entry.metadata || "{}");
    return {
      taskId: metadata.taskId || "unknown",
      agentId: metadata.agentId || "unknown",
      status: metadata.status || "completed",
      summary: metadata.summary || entry.text,
      result: metadata.result,
      scope: entry.scope,
      timestamp: entry.timestamp,
      usage: metadata.usage || { totalTokens: 0, toolUses: 0, durationMs: 0 },
    };
  }

  async store(notification: TaskNotification): Promise<string> {
    const entry = await this.toMemoryEntry(notification);
    const stored = await this.store.store(entry);
    return stored.id;
  }

  async storeBatch(notifications: TaskNotification[]): Promise<string[]> {
    const ids: string[] = [];
    for (const notification of notifications) {
      ids.push(await this.store(notification));
    }
    return ids;
  }

  async retrieve(id: string): Promise<TaskNotification | null> {
    const results = await this.store.list(undefined, undefined, 1000);
    const entry = results.find(e => e.id === id);
    return entry ? this.toTaskNotification(entry) : null;
  }

  async semanticSearch(query: string, limit = 10): Promise<TaskNotification[]> {
    const vector = await this.embedder.embed(query);
    const results = await this.store.vectorSearch(vector, limit, 0.3, [this.config.scope]);
    return results.map(r => this.toTaskNotification(r.entry));
  }

  async keywordSearch(query: string, limit = 10): Promise<TaskNotification[]> {
    const results = await this.store.bm25Search(query, limit, [this.config.scope]);
    return results.map(r => this.toTaskNotification(r.entry));
  }

  async hybridSearch(query: string, limit = 10): Promise<TaskNotification[]> {
    const [vectorResults, keywordResults] = await Promise.all([
      this.semanticSearch(query, limit),
      this.keywordSearch(query, limit),
    ]);

    const seen = new Set<string>();
    const merged: TaskNotification[] = [];

    for (const result of [...vectorResults, ...keywordResults]) {
      const key = `${result.taskId}-${result.timestamp}`;
      if (!seen.has(key)) {
        seen.add(key);
        merged.push(result);
      }
    }

    return merged.slice(0, limit);
  }

  async query(query: NotificationQuery): Promise<NotificationQueryResult> {
    let searchQuery = "";
    if (query.taskId) searchQuery += query.taskId + " ";
    if (query.agentId) searchQuery += query.agentId + " ";
    if (query.status) searchQuery += query.status + " ";

    let notifications: TaskNotification[];

    if (searchQuery.trim()) {
      notifications = await this.hybridSearch(searchQuery.trim(), query.limit || 10);
    } else {
      const entries = await this.store.list([this.config.scope], undefined, query.limit || 10, query.offset || 0);
      notifications = entries.map(e => this.toTaskNotification(e));
    }

    if (query.since) notifications = notifications.filter(n => n.timestamp >= query.since!);
    if (query.until) notifications = notifications.filter(n => n.timestamp <= query.until!);

    const sortField = query.sortBy || "timestamp";
    const sortOrder = query.sortOrder || "desc";
    notifications.sort((a, b) => {
      const aVal = a[sortField as keyof TaskNotification] as number;
      const bVal = b[sortField as keyof TaskNotification] as number;
      return sortOrder === "asc" ? aVal - bVal : bVal - aVal;
    });

    const stats = await this.store.stats([this.config.scope]);

    return {
      notifications,
      total: stats.totalCount,
      hasMore: notifications.length >= (query.limit || 10),
    };
  }

  async getTaskNotifications(taskId: string): Promise<TaskNotification[]> {
    return this.keywordSearch(taskId, 100);
  }

  async getAgentNotifications(agentId: string): Promise<TaskNotification[]> {
    return this.keywordSearch(agentId, 100);
  }

  async updateStatus(id: string, status: TaskStatus, result?: string): Promise<boolean> {
    const entry = await this.store.update(id, { metadata: JSON.stringify({ status, result }) }, [this.config.scope]);
    return entry !== null;
  }

  async delete(id: string): Promise<boolean> {
    return this.store.delete(id, [this.config.scope]);
  }

  async deleteBatch(ids: string[]): Promise<number> {
    let count = 0;
    for (const id of ids) {
      if (await this.delete(id)) count++;
    }
    return count;
  }

  async getStats(): Promise<NotificationStats> {
    const stats = await this.store.stats([this.config.scope]);

    const byStatus: Record<TaskStatus, number> = { completed: 0, failed: 0, killed: 0, running: 0 };
    const byScope: Record<string, number> = stats.scopeCounts;

    const entries = await this.store.list([this.config.scope], undefined, 1000);
    for (const entry of entries) {
      const metadata = JSON.parse(entry.metadata || "{}");
      const status = metadata.status as TaskStatus;
      if (status) byStatus[status] = (byStatus[status] || 0) + 1;
    }

    return {
      total: stats.totalCount,
      byStatus,
      byScope,
      retentionDays: this.config.retentionDays,
    };
  }

  async cleanup(): Promise<number> {
    const cutoff = Date.now() - this.config.retentionDays * 24 * 60 * 60 * 1000;
    return this.store.bulkDelete([this.config.scope], cutoff);
  }
}
