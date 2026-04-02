# Claude Code 上下文管理机制分析 - 第二部分：Tool Output 与文件内容管理

## 目录
1. [Tool Output 处理](#1-tool-output-处理)
2. [文件内容管理](#2-文件内容管理)
3. [Lazy Loading 策略](#3-lazy-loading-策略)
4. [Compaction 与上下文保留](#4-compaction-与上下文保留)

---

## 1. Tool Output 处理

### 1.1 大小限制与截断策略

Claude Code 对 Tool Output 实施多层限制策略：

#### 核心限制常量

**文件路径**: `utils/file.ts`
```typescript
export const MAX_OUTPUT_SIZE = 0.25 * 1024 * 1024 // 0.25MB in bytes
```

**文件路径**: `tools/FileReadTool/prompt.ts`
```typescript
export const MAX_LINES_TO_READ = 2000
export const DEFAULT_MAX_OUTPUT_TOKENS = 25000
```

**文件路径**: `utils/shell/outputLimits.ts`

Shell 命令输出限制通过 `getMaxOutputLength()` 函数获取，默认值：
- 最大字符数：约 100KB
- 可通过环境变量覆盖

#### 两层限制机制

**文件路径**: `tools/FileReadTool/limits.ts`

```typescript
/**
 * Read tool output limits. Two caps apply to text reads:
 *
 *   | limit         | default | checks                    | cost          | on overflow     |
 *   |---------------|---------|---------------------------|---------------|-----------------|
 *   | maxSizeBytes  | 256 KB  | TOTAL FILE SIZE (not out) | 1 stat        | throws pre-read |
 *   | maxTokens     | 25000   | actual output tokens      | API roundtrip | throws post-read|
 */
```

关键实现细节：
```typescript
export type FileReadingLimits = {
  maxTokens: number
  maxSizeBytes: number
  includeMaxSizeInPrompt?: boolean
  targetedRangeNudge?: boolean
}

// 优先级：环境变量 > GrowthBook > 默认值
export const getDefaultFileReadingLimits = memoize((): FileReadingLimits => {
  const override = getFeatureValue_CACHED_MAY_BE_STALE('tengu_amber_wren', {})
  
  const maxSizeBytes = typeof override?.maxSizeBytes === 'number' && ...
    ? override.maxSizeBytes
    : MAX_OUTPUT_SIZE
    
  const envMaxTokens = getEnvMaxTokens()
  const maxTokens = envMaxTokens ?? ...
    ? override.maxTokens
    : DEFAULT_MAX_OUTPUT_TOKENS
    
  return { maxSizeBytes, maxTokens, ... }
})
```

### 1.2 Bash/Shell 输出处理

**文件路径**: `utils/task/TaskOutput.ts`

Bash 工具输出通过 `getMaxOutputLength()` 获取限制：

```typescript
import { getMaxOutputLength } from '../shell/outputLimits.js'

// 输出截断逻辑
export function truncateOutput(output: string, maxLength: number): string {
  if (output.length <= maxLength) return output
  return output.slice(0, maxLength) + '\n[output truncated...]'
}
```

**文件路径**: `tools/BashTool/utils.ts`

```typescript
import { getMaxOutputLength } from '../../utils/shell/outputLimits.js'

// Bash 输出处理时调用 getMaxOutputLength() 获取限制
```

### 1.3 输出截断错误类

**文件路径**: `utils/readFileInRange.ts`

```typescript
export class FileTooLargeError extends Error {
  constructor(
    public sizeInBytes: number,
    public maxSizeBytes: number,
  ) {
    super(
      `File content (${formatFileSize(sizeInBytes)}) exceeds maximum allowed size 
       (${formatFileSize(maxSizeBytes)}). Use offset and limit parameters to read 
       specific portions of the file, or search for specific content instead of 
       reading the whole file.`,
    )
    this.name = 'FileTooLargeError'
  }
}
```

**文件路径**: `tools/FileReadTool/FileReadTool.ts`

```typescript
export class MaxFileReadTokenExceededError extends Error {
  constructor(
    public tokenCount: number,
    public maxTokens: number,
  ) {
    super(
      `File content (${tokenCount} tokens) exceeds maximum allowed tokens 
       (${maxTokens}). Use offset and limit parameters to read specific 
       portions of the file...`,
    )
    this.name = 'MaxFileReadTokenExceededError'
  }
}
```

---

## 2. 文件内容管理

### 2.1 大文件读取策略

**文件路径**: `utils/readFileInRange.ts`

Claude Code 实现了双路径文件读取策略：

```typescript
const FAST_PATH_MAX_SIZE = 10 * 1024 * 1024 // 10 MB

/**
 * Returns lines [offset, offset + maxLines) from a file.
 *
 * Fast path (regular files < 10 MB):
 *   Opens the file, stats the fd, reads the whole file with readFile(),
 *   then splits lines in memory. ~2x faster for typical source files.
 *
 * Streaming path (large files, pipes, devices, etc.):
 *   Uses createReadStream with manual indexOf('\n') scanning.
 *   Content is only accumulated for lines inside the requested range.
 */
export async function readFileInRange(
  filePath: string,
  offset = 0,
  maxLines?: number,
  maxBytes?: number,
  signal?: AbortSignal,
  options?: { truncateOnByteLimit?: boolean },
): Promise<ReadFileRangeResult>
```

#### Fast Path 实现（小文件）

```typescript
function readFileInRangeFast(
  raw: string,
  mtimeMs: number,
  offset: number,
  maxLines: number | undefined,
  truncateAtBytes: number | undefined,
): ReadFileRangeResult {
  const endLine = maxLines !== undefined ? offset + maxLines : Infinity
  
  // Strip BOM
  const text = raw.charCodeAt(0) === 0xfeff ? raw.slice(1) : raw
  
  // Split lines, strip \r, select range
  const selectedLines: string[] = []
  let lineIndex = 0
  let startPos = 0
  
  while ((newlinePos = text.indexOf('\n', startPos)) !== -1) {
    if (lineIndex >= offset && lineIndex < endLine) {
      let line = text.slice(startPos, newlinePos)
      if (line.endsWith('\r')) line = line.slice(0, -1)
      selectedLines.push(line)
    }
    lineIndex++
    startPos = newlinePos + 1
  }
  
  return {
    content: selectedLines.join('\n'),
    lineCount: selectedLines.length,
    totalLines: lineIndex,
    totalBytes: Buffer.byteLength(text, 'utf8'),
    readBytes: Buffer.byteLength(content, 'utf8'),
    mtimeMs,
  }
}
```

#### Streaming Path 实现（大文件）

```typescript
function readFileInRangeStreaming(
  filePath: string,
  offset: number,
  maxLines: number | undefined,
  maxBytes: number | undefined,
  truncateOnByteLimit: boolean,
  signal?: AbortSignal,
): Promise<ReadFileRangeResult> {
  // 使用 createReadStream + 手动换行符扫描
  // 只累积请求范围内的行，其他行只计数不保存
  // 避免读取 100GB 文件时内存爆炸
  
  const state: StreamState = {
    stream: createReadStream(filePath, {
      encoding: 'utf8',
      highWaterMark: 512 * 1024,  // 512KB chunks
    }),
    offset,
    endLine: maxLines !== undefined ? offset + maxLines : Infinity,
    maxBytes,
    selectedLines: [],
    currentLineIndex: 0,
    ...
  }
}
```

### 2.2 文件内容缓存机制

**文件路径**: `utils/fileStateCache.ts`

```typescript
// 文件状态缓存 - 追踪最近读取的文件
export type FileStateEntry = {
  content: string
  timestamp: number  // 最后读取时间
}

// Cache key: 文件路径
// Cache value: { content, timestamp }
export const readFileState: Map<string, FileStateEntry> = new Map()

// 用于检测文件变化
export function cacheToObject(cache: Map<string, FileStateEntry>): Record<string, FileStateEntry>
```

**文件路径**: `services/compact/compact.ts`

Compact 后恢复最近读取的文件：

```typescript
// 存储当前文件状态
const preCompactReadFileState = cacheToObject(context.readFileState)

// 清空缓存
context.readFileState.clear()

// Compact 后恢复最近的文件（最多5个，每个最多5000 tokens）
export const POST_COMPACT_MAX_FILES_TO_RESTORE = 5
export const POST_COMPACT_TOKEN_BUDGET = 50_000
export const POST_COMPACT_MAX_TOKENS_PER_FILE = 5_000

async function createPostCompactFileAttachments(
  readFileState: Record<string, { content: string; timestamp: number }>,
  toolUseContext: ToolUseContext,
  maxFiles: number,
  preservedMessages: Message[] = [],
): Promise<AttachmentMessage[]> {
  // 按时间排序，取最近的文件
  const recentFiles = Object.entries(readFileState)
    .map(([filename, state]) => ({ filename, ...state }))
    .sort((a, b) => b.timestamp - a.timestamp)
    .slice(0, maxFiles)
  
  // Token budget 控制
  let usedTokens = 0
  return results.filter((result) => {
    const attachmentTokens = roughTokenCountEstimation(jsonStringify(result))
    if (usedTokens + attachmentTokens <= POST_COMPACT_TOKEN_BUDGET) {
      usedTokens += attachmentTokens
      return true
    }
    return false
  })
}
```

### 2.3 文件内容保留策略

**文件路径**: `utils/readFileInRange.ts`

返回结果包含完整元数据：

```typescript
export type ReadFileRangeResult = {
  content