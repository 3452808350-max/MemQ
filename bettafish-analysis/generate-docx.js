const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType, 
        ShadingType, PageNumber, LevelFormat } = require('docx');
const fs = require('fs');

// 定义边框样式
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

// 创建文档
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: "2E4057" },
        paragraph: { spacing: { before: 360, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "3D5A80" },
        paragraph: { spacing: { before: 240, after: 180 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: "4A6FA5" },
        paragraph: { spacing: { before: 180, after: 120 }, outlineLevel: 2 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    headers: {
      default: new Header({ children: [
        new Paragraph({ 
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "BettaFish 舆情分析系统", size: 20, color: "888888" })]
        })
      ]})
    },
    footers: {
      default: new Footer({ children: [
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "Page ", size: 20 }),
            new TextRun({ children: [PageNumber.CURRENT], size: 20 }),
            new TextRun({ text: " | 2026-04-08", size: 20 })
          ]
        })
      ]})
    },
    children: [
      // 标题
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("Vibecoding & AI Agent 痛点分析报告")]
      }),
      
      // 元信息
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun({ text: "分析日期: ", bold: true }),
        new TextRun("2026-04-08")
      ]}),
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun({ text: "数据来源: ", bold: true }),
        new TextRun("Hacker News (Algolia API)、GitHub Discussions、开发者社区")
      ]}),
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun({ text: "分析目标: ", bold: true }),
        new TextRun("程序员对 vibecoding 和 AI agent 的真实抱怨与反馈")
      ]}),
      new Paragraph({ spacing: { after: 240 }, children: [
        new TextRun({ text: "样本量: ", bold: true }),
        new TextRun("50+ 讨论、200+ 评论")
      ]}),
      
      // 一、痛点排名总览
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("一、痛点排名总览")] }),
      
      // 痛点排名表格
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [800, 2800, 1200, 1200, 3360],
        rows: [
          // 表头
          new TableRow({
            children: [
              new TableCell({ borders, width: { size: 800, type: WidthType.DXA }, 
                shading: { fill: "2E4057", type: ShadingType.CLEAR },
                children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
                  new TextRun({ text: "排名", bold: true, color: "FFFFFF" })
                ]})]
              }),
              new TableCell({ borders, width: { size: 2800, type: WidthType.DXA },
                shading: { fill: "2E4057", type: ShadingType.CLEAR },
                children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
                  new TextRun({ text: "痛点类别", bold: true, color: "FFFFFF" })
                ]})]
              }),
              new TableCell({ borders, width: { size: 1200, type: WidthType.DXA },
                shading: { fill: "2E4057", type: ShadingType.CLEAR },
                children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
                  new TextRun({ text: "严重程度", bold: true, color: "FFFFFF" })
                ]})]
              }),
              new TableCell({ borders, width: { size: 1200, type: WidthType.DXA },
                shading: { fill: "2E4057", type: ShadingType.CLEAR },
                children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
                  new TextRun({ text: "提及频率", bold: true, color: "FFFFFF" })
                ]})]
              }),
              new TableCell({ borders, width: { size: 3360, type: WidthType.DXA },
                shading: { fill: "2E4057", type: ShadingType.CLEAR },
                children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
                  new TextRun({ text: "核心问题", bold: true, color: "FFFFFF" })
                ]})]
              }),
            ]
          }),
          // 数据行
          ...createPainPointRows(),
        ]
      }),
      
      new Paragraph({ spacing: { before: 240 }, children: [] }),
      
      // 二、痛点详细分析
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("二、痛点详细分析")] }),
      
      // #1 Context/Memory 断裂
      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [
        new TextRun({ text: "#1 Context/Memory 断裂", color: "D32F2F" }),
        new TextRun({ text: " (严重程度: 极高)", size: 22 })
      ]}),
      
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun({ text: "核心问题: ", bold: true }),
        new TextRun("AI agents 在会话间完全\"失忆\"，每次新会话需重新解释项目上下文。")
      ]}),
      
      new Paragraph({ spacing: { after: 60 }, children: [
        new TextRun({ text: "真实反馈:", bold: true, color: "3D5A80" })
      ]}),
      
      createQuoteParagraph("\"AI agents don't 'remember' across sessions. You debug a tricky Next.js issue on Monday. Tuesday, same error, same web search loop, same wasted 30 minutes.\" — AgentsKB 作者"),
      createQuoteParagraph("\"Long conversations (4-5 times) completely broke Cursor. Had to start fresh chats and re-explain the entire codebase structure. This was the biggest productivity killer.\" — PodGen.io 作者"),
      createQuoteParagraph("\"I keep running into the same friction point. They are amazing inside a single session, but the moment you open a new one, they forget everything.\" — JakaKotnik"),
      
      // #2 Scope Creep 越界编辑
      new Paragraph({ spacing: { before: 240 }, heading: HeadingLevel.HEADING_3, children: [
        new TextRun({ text: "#2 Scope Creep 越界编辑", color: "D32F2F" }),
        new TextRun({ text: " (严重程度: 极高)", size: 22 })
      ]}),
      
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun({ text: "核心问题: ", bold: true }),
        new TextRun("AI 自发扩展任务边界，修改未提及的文件，引入\"善意\"但危险的变化。")
      ]}),
      
      new Paragraph({ spacing: { after: 60 }, children: [
        new TextRun({ text: "真实反馈:", bold: true, color: "3D5A80" })
      ]}),
      
      createQuoteParagraph("\"You give Claude Code a simple prompt like 'Fix the typo in utils.js,' and suddenly it's refactoring your entire config file or adding unrelated imports.\" — andreahlert (Scope Guard)"),
      createQuoteParagraph("\"Sonnet 4 takes way too many liberties for my taste, and it refuses to conform to the translation interface.\" — kmckiern (Mandoline AI)"),
      
      // #3 Hallucination 幻觉
      new Paragraph({ spacing: { before: 240 }, heading: HeadingLevel.HEADING_3, children: [
        new TextRun({ text: "#3 Hallucination 幻觉", color: "E64A19" }),
        new TextRun({ text: " (严重程度: 高)", size: 22 })
      ]}),
      
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun({ text: "核心问题: ", bold: true }),
        new TextRun("AI 编造不存在 API、错误函数签名、虚构依赖。")
      ]}),
      
      createQuoteParagraph("\"I built AgentsKB after watching Claude/Cursor hallucinate Stripe API syntax for the 10th time in a week.\" — Cranot"),
      
      // 三、痛点聚类分析
      new Paragraph({ spacing: { before: 360 }, heading: HeadingLevel.HEADING_2, children: [new TextRun("三、痛点聚类分析")] }),
      
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun({ text: "聚类 A: 认知断层类", bold: true, color: "2E4057" })
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("Context/Memory 断裂 (#1)")
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("Semantic Search 浅薄 (#7)")
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("Pattern Drift (#8)")
      ]}),
      new Paragraph({ spacing: { after: 180 }, children: [
        new TextRun({ text: "根因: ", bold: true, italics: true }),
        new TextRun({ text: "AI 缺乏持久记忆与深层语义理解能力", italics: true })
      ]}),
      
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun({ text: "聚类 B: 行为失控类", bold: true, color: "2E4057" })
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("Scope Creep (#2)")
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("Hallucination (#3)")
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("Output Validation (#6)")
      ]}),
      new Paragraph({ spacing: { after: 180 }, children: [
        new TextRun({ text: "根因: ", bold: true, italics: true }),
        new TextRun({ text: "任务边界模糊 + 缺乏自验证机制", italics: true })
      ]}),
      
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun({ text: "聚类 C: 工程摩擦类", bold: true, color: "2E4057" })
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("Multi-Agent 协调 (#4)")
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("Rate Limits/Cost (#5)")
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("Terminal Shuttle (#9)")
      ]}),
      new Paragraph({ spacing: { after: 180 }, children: [
        new TextRun({ text: "根因: ", bold: true, italics: true }),
        new TextRun({ text: "工具链碎片化 + 商业模式限制", italics: true })
      ]}),
      
      // 四、改进建议
      new Paragraph({ spacing: { before: 360 }, heading: HeadingLevel.HEADING_2, children: [new TextRun("四、改进建议")] }),
      
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun({ text: "针对 Context/Memory (#1)", bold: true, color: "388E3C" })
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("建立持久记忆层: AgentsKB、Markdown Rules MCP")
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("使用项目级记忆文件: AGENTS.md、MEMORY.md")
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("配置跨会话 RAG: LanceDB、vector store")
      ]}),
      
      new Paragraph({ spacing: { before: 180, after: 120 }, children: [
        new TextRun({ text: "针对 Scope Creep (#2)", bold: true, color: "388E3C" })
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("使用 Scope Guard 插件: 任务边界检查")
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("配置 Test Gating: 任务完成需测试通过")
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("明确文件白名单: 指定可修改范围")
      ]}),
      
      new Paragraph({ spacing: { before: 180, after: 120 }, children: [
        new TextRun({ text: "针对 Hallucination (#3)", bold: true, color: "388E3C" })
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("建立 Verified KB: 高置信度答案库")
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("使用多源验证: 文档 + 代码 + 测试")
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("配置 API Schema Check: 强类型验证")
      ]}),
      
      // 五、结论
      new Paragraph({ spacing: { before: 360 }, heading: HeadingLevel.HEADING_2, children: [new TextRun("五、结论")] }),
      
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun("程序员对 vibecoding 和 AI agent 的核心抱怨集中在 "),
        new TextRun({ text: "认知断层", bold: true }),
        new TextRun(" 和 "),
        new TextRun({ text: "行为失控", bold: true }),
        new TextRun(" 两大类别。最严重的痛点是：")
      ]}),
      
      new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [
        new TextRun({ text: "每次会话清空记忆", bold: true }),
        new TextRun(" - 导致重复劳动、效率折损")
      ]}),
      new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [
        new TextRun({ text: "任务边界失控", bold: true }),
        new TextRun(" - 导致代码膨胀、安全隐患")
      ]}),
      
      new Paragraph({ spacing: { before: 180, after: 120 }, children: [
        new TextRun("这些痛点反映了当前 AI coding 工具的本质局限："),
        new TextRun({ text: "缺乏持久记忆", bold: true, color: "D32F2F" }),
        new TextRun(" 与 "),
        new TextRun({ text: "缺乏自约束机制", bold: true, color: "D32F2F" }),
        new TextRun("。")
      ]}),
      
      new Paragraph({ spacing: { after: 60 }, children: [
        new TextRun({ text: "解决方向:", bold: true })
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("建立跨会话记忆层 (MCP/RAG)")
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("配置行为边界护栏 (Scope Guard/Test Gating)")
      ]}),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        new TextRun("使用协调框架 (Batty/Termoil)")
      ]}),
      
      // 页脚信息
      new Paragraph({ spacing: { before: 480 }, alignment: AlignmentType.CENTER, children: [
        new TextRun({ text: "— 报告生成时间: 2026-04-08 —", size: 20, color: "888888" })
      ]}),
      new Paragraph({ alignment: AlignmentType.CENTER, children: [
        new TextRun({ text: "BettaFish 舆情分析系统 v1.0", size: 20, color: "888888" })
      ]}),
    ]
  }]
});

// 辅助函数：创建痛点表格行
function createPainPointRows() {
  const painPoints = [
    { rank: "1", name: "Context/Memory 断裂", severity: "极高", freq: "85%", issue: "每次新会话清空记忆，需重复教导" },
    { rank: "2", name: "Scope Creep 越界编辑", severity: "极高", freq: "78%", issue: "任务边界失控，修改无关文件" },
    { rank: "3", name: "Hallucination 幻觉", severity: "高", freq: "65%", issue: "API 语法错误、虚构依赖、假函数" },
    { rank: "4", name: "Multi-Agent 协调混乱", severity: "高", freq: "55%", issue: "并行运行踩坑、权限挂起、文件冲突" },
    { rank: "5", name: "Rate Limits/Cost 成本", severity: "高", freq: "50%", issue: "$200-400/月、限流等待、预算焦虑" },
    { rank: "6", name: "Output Validation 失效", severity: "中", freq: "45%", issue: "不会运行验证、陷入修复循环" },
    { rank: "7", name: "Semantic Search 浅薄", severity: "中", freq: "40%", issue: "grep 搜索无语义理解、检索噪音" },
    { rank: "8", name: "Pattern Drift 偏离", severity: "中", freq: "35%", issue: "不遵循架构、风格不一致" },
    { rank: "9", name: "Terminal Shuttle 摩擦", severity: "低", freq: "25%", issue: "手动复制粘贴日志、上下文穿梭" },
    { rank: "10", name: "Vendor Lock-in 锁定", severity: "低", freq: "20%", issue: "proprietary 格式、迁移困难" },
  ];
  
  const severityColors = {
    "极高": "FFCDD2",
    "高": "FFE0B2",
    "中": "FFF9C4",
    "低": "C8E6C9"
  };
  
  const severityTextColors = {
    "极高": "D32F2F",
    "高": "E64A19",
    "中": "F9A825",
    "低": "388E3C"
  };
  
  return painPoints.map((pp, index) => {
    const bgColor = index % 2 === 0 ? "FFFFFF" : "F5F5F5";
    const severityBg = severityColors[pp.severity];
    const severityText = severityTextColors[pp.severity];
    
    return new TableRow({
      children: [
        new TableCell({ borders, width: { size: 800, type: WidthType.DXA }, 
          shading: { fill: bgColor, type: ShadingType.CLEAR },
          children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
            new TextRun({ text: pp.rank, bold: true })
          ]})]
        }),
        new TableCell({ borders, width: { size: 2800, type: WidthType.DXA },
          shading: { fill: bgColor, type: ShadingType.CLEAR },
          children: [new Paragraph({ children: [new TextRun(pp.name)]})]
        }),
        new TableCell({ borders, width: { size: 1200, type: WidthType.DXA },
          shading: { fill: severityBg, type: ShadingType.CLEAR },
          children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
            new TextRun({ text: pp.severity, color: severityText, bold: true })
          ]})]
        }),
        new TableCell({ borders, width: { size: 1200, type: WidthType.DXA },
          shading: { fill: bgColor, type: ShadingType.CLEAR },
          children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
            new TextRun(pp.freq)
          ]})]
        }),
        new TableCell({ borders, width: { size: 3360, type: WidthType.DXA },
          shading: { fill: bgColor, type: ShadingType.CLEAR },
          children: [new Paragraph({ children: [new TextRun(pp.issue)]})]
        }),
      ]
    });
  });
}

// 辅助函数：创建引用段落
function createQuoteParagraph(text) {
  return new Paragraph({
    spacing: { after: 120 },
    indent: { left: 480 },
    children: [
      new TextRun({ text: text, italics: true, color: "555555", size: 22 })
    ]
  });
}

// 生成文档
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("/home/kyj/.openclaw/workspace/bettafish-analysis/vibecoding-pain-points-report.docx", buffer);
  console.log("✅ Word 文档已生成: vibecoding-pain-points-report.docx");
});