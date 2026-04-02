/**
 * TaskNotificationService 模块测试 (P2)
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  TaskNotificationService,
  TaskNotificationStorage,
} from "../src/core/TaskNotificationService";
import type { TaskNotification, TaskStatus } from "../src/types";

describe("TaskNotificationService", () => {
  let service: TaskNotificationService;

  beforeEach(() => {
    service = new TaskNotificationService();
  });

  describe("基本功能", () => {
    it("应该创建通知", async () => {
      const notification = await service.createNotification({
        taskId: "task-1",
        agentId: "agent-1",
        status: "running" as TaskStatus,
        summary: "Task started",
      });

      expect(notification.taskId).toBe("task-1");
      expect(notification.agentId).toBe("agent-1");
      expect(notification.status).toBe("running");
    });

    it("应该完成通知", async () => {
      await service.createNotification({
        taskId: "task-1",
        agentId: "agent-1",
        status: "running" as TaskStatus,
        summary: "Task started",
      });

      await service.completeNotification("task-1", "Task completed successfully", {
        totalTokens: 1000,
        toolUses: 5,
        durationMs: 5000,
      });

      const result = await service.queryNotifications({ taskId: "task-1" });
      const completed = result.notifications.find(n => n.status === "completed");
      expect(completed).toBeDefined();
    });

    it("应该失败通知", async () => {
      await service.createNotification({
        taskId: "task-1",
        agentId: "agent-1",
        status: "running" as TaskStatus,
        summary: "Task started",
      });

      await service.failNotification("task-1", "Task failed with error", {
        totalTokens: 500,
        toolUses: 2,
        durationMs: 2000,
      });

      const result = await service.queryNotifications({ taskId: "task-1" });
      const failed = result.notifications.find(n => n.status === "failed");
      expect(failed).toBeDefined();
    });
  });

  describe("格式化", () => {
    it("应该格式化为 XML", async () => {
      const notification = await service.createNotification({
        taskId: "task-1",
        agentId: "agent-1",
        status: "completed" as TaskStatus,
        summary: "Task completed",
        result: "Success",
      });

      const xml = service.formatAsXML(notification);

      expect(xml).toContain("<task-notification>");
      expect(xml).toContain("<task-id>task-1</task-id>");
      expect(xml).toContain("<status>completed</status>");
      expect(xml).toContain("<result>Success</result>");
    });

    it("应该格式化为 JSON", async () => {
      const notification = await service.createNotification({
        taskId: "task-1",
        agentId: "agent-1",
        status: "completed" as TaskStatus,
        summary: "Task completed",
      });

      const json = service.formatAsJSON(notification);
      const parsed = JSON.parse(json);

      expect(parsed.taskId).toBe("task-1");
      expect(parsed.status).toBe("completed");
    });
  });

  describe("查询", () => {
    beforeEach(async () => {
      await service.createNotification({
        taskId: "task-1",
        agentId: "agent-1",
        status: "completed" as TaskStatus,
        summary: "Task 1",
      });
      await service.createNotification({
        taskId: "task-2",
        agentId: "agent-2",
        status: "failed" as TaskStatus,
        summary: "Task 2",
      });
    });

    it("应该按状态查询", async () => {
      const result = await service.queryNotifications({ status: "completed" });
      expect(result.notifications).toHaveLength(1);
      expect(result.notifications[0].taskId).toBe("task-1");
    });

    it("应该按 Agent ID 查询", async () => {
      const result = await service.queryNotifications({ agentId: "agent-2" });
      expect(result.notifications).toHaveLength(1);
      expect(result.notifications[0].taskId).toBe("task-2");
    });

    it("应该支持分页", async () => {
      const result = await service.queryNotifications({ limit: 1 });
      expect(result.notifications).toHaveLength(1);
      expect(result.total).toBe(2);
      expect(result.hasMore).toBe(true);
    });
  });

  describe("统计", () => {
    it("应该获取统计信息", async () => {
      await service.createNotification({
        taskId: "task-1",
        agentId: "agent-1",
        status: "completed" as TaskStatus,
        summary: "Task 1",
      });

      const stats = await service.getStats();

      expect(stats.total).toBeGreaterThan(0);
      expect(stats.byStatus.completed).toBeGreaterThan(0);
    });
  });
});

describe("TaskNotificationStorage", () => {
  let storage: TaskNotificationStorage;

  beforeEach(() => {
    storage = new TaskNotificationStorage();
  });

  describe("存储操作", () => {
    it("应该存储通知", async () => {
      const notification: TaskNotification = {
        taskId: "task-1",
        agentId: "agent-1",
        status: "completed",
        summary: "Test",
        timestamp: Date.now(),
        scope: "test",
        usage: { totalTokens: 0, toolUses: 0, durationMs: 0 },
      };

      const id = await storage.store(notification);
      expect(id).toContain("task-1");
    });

    it("应该检索通知", async () => {
      const notification: TaskNotification = {
        taskId: "task-1",
        agentId: "agent-1",
        status: "completed",
        summary: "Test",
        timestamp: Date.now(),
        scope: "test",
        usage: { totalTokens: 0, toolUses: 0, durationMs: 0 },
      };

      const id = await storage.store(notification);
      const retrieved = await storage.retrieve(id);

      expect(retrieved).not.toBeNull();
      expect(retrieved?.taskId).toBe("task-1");
    });

    it("应该更新状态", async () => {
      const notification: TaskNotification = {
        taskId: "task-1",
        agentId: "agent-1",
        status: "running",
        summary: "Test",
        timestamp: Date.now(),
        scope: "test",
        usage: { totalTokens: 0, toolUses: 0, durationMs: 0 },
      };

      const id = await storage.store(notification);
      const updated = await storage.updateStatus(id, "completed", "Done");

      expect(updated).toBe(true);

      const retrieved = await storage.retrieve(id);
      expect(retrieved?.status).toBe("completed");
      expect(retrieved?.result).toBe("Done");
    });

    it("应该删除通知", async () => {
      const notification: TaskNotification = {
        taskId: "task-1",
        agentId: "agent-1",
        status: "completed",
        summary: "Test",
        timestamp: Date.now(),
        scope: "test",
        usage: { totalTokens: 0, toolUses: 0, durationMs: 0 },
      };

      const id = await storage.store(notification);
      const deleted = await storage.delete(id);

      expect(deleted).toBe(true);
      expect(await storage.retrieve(id)).toBeNull();
    });
  });
});
