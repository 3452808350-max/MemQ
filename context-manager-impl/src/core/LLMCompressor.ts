/**
 * LLM Context Compressor
 * 
 * P1: 使用 LLM 对长对话进行语义压缩
 * - 生成对话摘要
 * - 保留关键决策和工具结果
 * - 支持增量压缩
 */

import {
  UserMessage,
  CompressionResult,
  CompressionConfig,
  DEFAULT_COMPRESSION_CONFIG,
} from "../types/index.js";

/**
 * LLM 压缩器
 * 
 * P1 简化版：使用模板生成摘要
 * P2 完整版：调用 LLM API 进行智能压缩
 */
export class LLMCompressor {
  constructor(_config?: Partial<CompressionConfig>) {
    // Config reserved for future LLM-based compression
    void _config;
  }

  /**
   * 压缩消息列表
   * 
   * P1: 基于规则的简化压缩
   * - 提取关键决策
   * - 保留工具结果
   * - 生成结构化摘要
   */
  async compress(messages: UserMessage[]): Promise<CompressionResult> {
    if (messages.length === 0) {
      return {
        originalMessages: [],
        compressedSummary: "",
        tokensBefore: 0,
        tokensAfter: 0,
        compressionRatio: 1,
        preservedMessages: [],
        compressedMessages: [],
      };
    }

    const tokensBefore = this.estimateTokens(messages);
    
    // P1: 基于规则的压缩
    const summary = this.generateRuleBasedSummary(messages);
    
    // 识别需要保留的原始消息（高优先级）
    const preservedMessages = this.identifyPreservedMessages(messages);
    
    const tokensAfter = this.estimateStringTokens(summary) + 
      this.estimateTokens(preservedMessages);
    
    return {
      originalMessages: messages,
      compressedSummary: summary,
      tokensBefore,
      tokensAfter,
      compressionRatio: tokensAfter / tokensBefore,
      preservedMessages,
      compressedMessages: messages.filter(
        m => !preservedMessages.some(p => p.id === m.id)
      ),
    };
  }

  /**
   * 增量压缩
   * 
   * 将新消息与现有摘要合并
   */
  async compressIncremental(
    existingSummary: string,
    newMessages: UserMessage[]
  ): Promise<CompressionResult> {
    const tokensBefore = this.estimateStringTokens(existingSummary) + 
      this.estimateTokens(newMessages);
    
    // P1: 简单追加摘要
    const newSummary = this.generateRuleBasedSummary(newMessages);
    const combinedSummary = existingSummary 
      ? `${existingSummary}\n\n## 新增内容\n${newSummary}`
      : newSummary;
    
    const tokensAfter = this.estimateStringTokens(combinedSummary);
    
    return {
      originalMessages: newMessages,
      compressedSummary: combinedSummary,
      tokensBefore,
      tokensAfter,
      compressionRatio: tokensAfter / tokensBefore,
      preservedMessages: this.identifyPreservedMessages(newMessages),
      compressedMessages: newMessages,
    };
  }

  /**
   * 基于规则的摘要生成
   * 
   * P1 实现：提取关键信息，不调用 LLM
   */
  private generateRuleBasedSummary(messages: UserMessage[]): string {
    const parts: string[] = [];
    
    // 提取决策
    const decisions = this.extractDecisions(messages);
    if (decisions.length > 0) {
      parts.push("## 关键决策");
      decisions.forEach((d, i) => parts.push(`${i + 1}. ${d}`));
    }
    
    // 提取工具结果
    const toolResults = this.extractToolResults(messages);
    if (toolResults.length > 0) {
      parts.push("\n## 工具结果");
      toolResults.forEach((t, i) => parts.push(`${i + 1}. ${t.tool}: ${t.result}`));
    }
    
    // 提取错误
    const errors = this.extractErrors(messages);
    if (errors.length > 0) {
      parts.push("\n## 错误与修复");
      errors.forEach((e, i) => parts.push(`${i + 1}. ${e}`));
    }
    
    // 生成流程概述
    const flow = this.generateFlowSummary(messages);
    if (flow) {
      parts.unshift(`## 对话流程\n${flow}\n`);
    }
    
    return parts.join("\n") || "[无关键内容]";
  }

  /**
   * 提取决策
   */
  private extractDecisions(messages: UserMessage[]): string[] {
    const decisions: string[] = [];
    const decisionPatterns = [
      /决定[用采用]*\s*([^.。]+)/i,
      /改用\s*([^.。]+)/i,
      /换成\s*([^.。]+)/i,
      /decided?\s+(?:to\s+)?(?:use|adopt)\s+([^.]+)/i,
      /will\s+use\s+([^.]+)/i,
    ];
    
    for (const msg of messages) {
      if (msg.role !== "user") continue;
      const content = typeof msg.content === "string" ? msg.content : "";
      
      for (const pattern of decisionPatterns) {
        const match = content.match(pattern);
        if (match) {
          decisions.push(match[1].trim());
        }
      }
    }
    
    return decisions;
  }

  /**
   * 提取工具结果
   */
  private extractToolResults(messages: UserMessage[]): Array<{ tool: string; result: string }> {
    const results: Array<{ tool: string; result: string }> = [];
    
    for (const msg of messages) {
      if (msg.role !== "assistant") continue;
      const content = typeof msg.content === "string" ? msg.content : "";
      
      // 匹配工具调用结果
      const toolMatches = content.matchAll(
        /(?:工具|tool)[：:]\s*(\w+).*?(?:结果|result)[：:]\s*([^.。]+)/gi
      );
      
      for (const match of toolMatches) {
        results.push({ tool: match[1], result: match[2] });
      }
    }
    
    return results;
  }

  /**
   * 提取错误信息
   */
  private extractErrors(messages: UserMessage[]): string[] {
    const errors: string[] = [];
    const errorPatterns = [
      /error[:：]\s*([^.]+)/i,
      /failed?[:：]\s*([^.]+)/i,
      /错误[:：]\s*([^.]+)/i,
      /失败[:：]\s*([^.]+)/i,
    ];
    
    for (const msg of messages) {
      const content = typeof msg.content === "string" ? msg.content : "";
      
      for (const pattern of errorPatterns) {
        const match = content.match(pattern);
        if (match) {
          errors.push(match[1].trim());
        }
      }
    }
    
    return errors;
  }

  /**
   * 生成流程概述
   */
  private generateFlowSummary(messages: UserMessage[]): string {
    const userMsgs = messages.filter(m => m.role === "user");
    const assistantMsgs = messages.filter(m => m.role === "assistant");
    
    const topics = this.extractTopics(messages);
    
    return `共 ${messages.length} 条消息（用户 ${userMsgs.length} 条，助手 ${assistantMsgs.length} 条）` +
      (topics.length > 0 ? `，涉及主题：${topics.join("、")}` : "");
  }

  /**
   * 提取主题
   */
  private extractTopics(messages: UserMessage[]): string[] {
    const topics = new Set<string>();
    const topicKeywords: Record<string, string[]> = {
      "代码": ["function", "class", "import", "export", "const", "let"],
      "配置": ["config", "setting", "json", "yaml"],
      "测试": ["test", "spec", "assert", "expect"],
      "部署": ["deploy", "build", "release", "publish"],
      "调试": ["debug", "error", "bug", "fix"],
    };
    
    for (const msg of messages) {
      const content = typeof msg.content === "string" ? msg.content : "";
      
      for (const [topic, keywords] of Object.entries(topicKeywords)) {
        for (const keyword of keywords) {
          if (content.toLowerCase().includes(keyword.toLowerCase())) {
            topics.add(topic);
            break;
          }
        }
      }
    }
    
    return Array.from(topics);
  }

  /**
   * 识别需要保留的消息
   */
  private identifyPreservedMessages(messages: UserMessage[]): UserMessage[] {
    // 保留系统消息和最近的决策
    return messages.filter(m => {
      if (m.role === "system") return true;
      if (m.role === "user") {
        const content = typeof m.content === "string" ? m.content : "";
        return /决定|decided|改用|换成/i.test(content);
      }
      return false;
    });
  }

  /**
   * 估算消息 token 数
   */
  private estimateTokens(messages: UserMessage[]): number {
    return messages.reduce((sum, m) => {
      const content = typeof m.content === "string" ? m.content : JSON.stringify(m.content);
      // 简单估算：每 4 个字符约 1 个 token
      return sum + Math.ceil(content.length / 4);
    }, 0);
  }

  /**
   * 估算字符串 token 数
   */
  private estimateStringTokens(text: string): number {
    return Math.ceil(text.length / 4);
  }
}
