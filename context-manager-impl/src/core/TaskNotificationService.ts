/**
 * TaskNotificationService - 任务通知存储与检索服务
 * 
 * P2 核心功能：
 * 1. TaskNotification 的存储和检索
 * 2. 与 memory-lancedb-pro 的集成
 * 3. 自动归档和清理
 */

import {
  TaskNotification,
  TaskNotificationConfig,
  NotificationQuery,
  NotificationQueryResult,
  NotificationStats,
  TaskStatus,
  DEFAULT_TASK_NOTIFICATION_CONFIG,
} from "../types/index.js";

/**
 * 内存存储实现（P2 简化版）
 * P3 将替换为 memory-lancedb-pro 集成
 */
export class TaskNotificationStorage {
  private notifications: Map<string, TaskNotification> = new Map();
  private config: TaskNotificationConfig;

  constructor(config: Partial<TaskNotificationConfig> = {}) {
    this.config = { ...DEFAULT_TASK_NOTIFICATION_CONFIG, ...config };
  }

  async store(notification: TaskNotification): Promise<string> {
    const id = `${notification.taskId}-${Date.now()}`;
    const enriched: TaskNotification = {
      ...notification,
      timestamp: notification.timestamp || Date.now(),
    };
    this.notifications.set(id, enriched);
    if (this.config.autoArchive) {
      await this.archiveOldNotifications();
    }
    return id;
  }

  async storeBatch(notifications: TaskNotification[]): Promise<string[]> {
    const ids: string[] = [];
    for (const n of notifications) {
      ids.push(await this.store(n));
    }
    return ids;
  }

  async retrieve(id: string): Promise<TaskNotification | null> {
    return this.notifications.get(id) || null;
  }

  async query(query: NotificationQuery): Promise<NotificationQueryResult> {
    let results = Array.from(this.notifications.values());

    if (query.status) results = results.filter(n => n.status === query.status);
    if (query.taskId) results = results.filter(n => n.taskId.includes(query.taskId!));
    if (query.scope) results = results.filter(n => n.scope === query.scope);
    if (query.agentId) results = results.filter(n => n.agentId === query.agentId);
    if (query.since) results = results.filter(n => n.timestamp >= query.since!);
    if (query.until) results = results.filter(n => n.timestamp <= query.until!);

    const sortField = query.sortBy || "timestamp";
    const sortOrder = query.sortOrder || "desc";
    results.sort((a, b) => {
      const aVal = a[sortField as keyof TaskNotification] as number;
      const bVal = b[sortField as keyof TaskNotification] as number;
      return sortOrder === "asc" ? aVal - bVal : bVal - aVal;
    });

    const total = results.length;
    const limit = query.limit || 10;
    const offset = query.offset || 0;
    results = results.slice(offset, offset + limit);

    return { notifications: results, total, hasMore: offset + limit < total };
  }

  async getTaskNotifications(taskId: string): Promise<TaskNotification[]> {
    const result = await this.query({ taskId, limit: 100 });
    return result.notifications;
  }

  async getAgentNotifications(agentId: string): Promise<TaskNotification[]> {
    const result = await this.query({ agentId, limit: 100 });
    return result.notifications;
  }

  async updateStatus(id: string, status: TaskStatus, result?: string): Promise<boolean> {
    const n = this.notifications.get(id);
    if (!n) return false;
    n.status = status;
    if (result !== undefined) n.result = result;
    this.notifications.set(id, n);
    return true;
  }

  async delete(id: string): Promise<boolean> {
    return this.notifications.delete(id);
  }

  async deleteBatch(ids: string[]): Promise<number> {
    let count = 0;
    for (const id of ids) {
      if (await this.delete(id)) count++;
    }
    return count;
  }

  private async archiveOldNotifications(): Promise<void> {
    const cutoff = Date.now() - (this.config.retentionDays * 24 * 60 * 60 * 1000);
    for (const [id, n] of this.notifications) {
      if (n.timestamp < cutoff) this.notifications.delete(id);
    }
  }

  async getStats(): Promise<NotificationStats> {
    const notifications = Array.from(this.notifications.values());
    const byStatus: Record<TaskStatus, number> = { completed: 0, failed: 0, killed: 0, running: 0 };
    const byScope: Record<string, number> = {};
    for (const n of notifications) {
      byStatus[n.status] = (byStatus[n.status] || 0) + 1;
      byScope[n.scope] = (byScope[n.scope] || 0) + 1;
    }
    return { total: notifications.length, byStatus, byScope, retentionDays: this.config.retentionDays };
  }

  async clear(): Promise<void> {
    this.notifications.clear();
  }

  getConfig(): TaskNotificationConfig {
    return { ...this.config };
  }
}

/**
 * TaskNotificationService - 主服务类
 */
export class TaskNotificationService {
  private storage: TaskNotificationStorage;

  constructor(config?: Partial<TaskNotificationConfig>) {
    this.storage = new TaskNotificationStorage(config);
  }

  async createNotification(params: {
    taskId: string;
    agentId: string;
    status: TaskStatus;
    summary: string;
    result?: string;
    scope?: string;
    usage?: { totalTokens: number; toolUses: number; durationMs: number };
  }): Promise<TaskNotification> {
    const notification: TaskNotification = {
      taskId: params.taskId,
      agentId: params.agentId,
      status: params.status,
      summary: params.summary,
      result: params.result,
      scope: params.scope || "task:notifications",
      timestamp: Date.now(),
      usage: params.usage || { totalTokens: 0, toolUses: 0, durationMs: 0 },
    };
    await this.storage.store(notification);
    return notification;
  }

  async completeNotification(taskId: string, result: string, usage: TaskNotification["usage"]): Promise<void> {
    const notifications = await this.storage.getTaskNotifications(taskId);
    const latest = notifications[notifications.length - 1];
    if (latest) {
      latest.status = "completed";
      latest.result = result;
      latest.usage = usage;
      await this.storage.store(latest);
    }
  }

  async failNotification(taskId: string, error: string, usage: TaskNotification["usage"]): Promise<void> {
    const notifications = await this.storage.getTaskNotifications(taskId);
    const latest = notifications[notifications.length - 1];
    if (latest) {
      latest.status = "failed";
      latest.result = error;
      latest.usage = usage;
      await this.storage.store(latest);
    }
  }

  formatAsXML(notification: TaskNotification): string {
    return `<task-notification>
  <task-id>${notification.taskId}</task-id>
  <status>${notification.status}</status>
  <summary>${notification.summary}</summary>
  ${notification.result ? `<result>${notification.result}</result>` : ""}
  <usage total_tokens="${notification.usage.totalTokens}" tool_uses="${notification.usage.toolUses}" duration_ms="${notification.usage.durationMs}"/>
</task-notification>`;
  }

  formatAsJSON(notification: TaskNotification): string {
    return JSON.stringify(notification, null, 2);
  }

  async queryNotifications(query: NotificationQuery): Promise<NotificationQueryResult> {
    return this.storage.query(query);
  }

  async getStats(): Promise<NotificationStats> {
    return this.storage.getStats();
  }

  async clear(): Promise<void> {
    await this.storage.clear();
  }
}

export default TaskNotificationService;