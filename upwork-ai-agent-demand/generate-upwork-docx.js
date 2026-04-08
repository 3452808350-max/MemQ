const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType, BorderStyle } = require('docx');
const fs = require('fs');

const mdContent = fs.readFileSync('upwork-ai-agent-demand-report.md', 'utf8');

function parseMarkdown(md) {
  const lines = md.split('\n');
  const sections = [];
  let currentSection = { title: '', content: [], level: 0 };
  
  for (const line of lines) {
    if (line.startsWith('# ')) {
      if (currentSection.title) sections.push(currentSection);
      currentSection = { title: line.substring(2), content: [], level: 1 };
    } else if (line.startsWith('## ')) {
      if (currentSection.title) sections.push(currentSection);
      currentSection = { title: line.substring(3), content: [], level: 2 };
    } else if (line.startsWith('### ')) {
      if (currentSection.title) sections.push(currentSection);
      currentSection = { title: line.substring(4), content: [], level: 3 };
    } else if (line.startsWith('**') && line.endsWith('**')) {
      currentSection.content.push({ type: 'bold', text: line.substring(2, line.length - 2) });
    } else if (line.startsWith('> ')) {
      currentSection.content.push({ type: 'quote', text: line.substring(2) });
    } else if (line.startsWith('| ')) {
      currentSection.content.push({ type: 'table', text: line });
    } else if (line.startsWith('- ')) {
      currentSection.content.push({ type: 'list', text: line.substring(2) });
    } else if (line.trim()) {
      currentSection.content.push({ type: 'text', text: line });
    }
  }
  if (currentSection.title) sections.push(currentSection);
  return sections;
}

const sections = parseMarkdown(mdContent);

const doc = new Document({
  sections: [{
    properties: {},
    children: [
      new Paragraph({
        children: [
          new TextRun({
            text: "2026年Q1 线上工作平台企业 AI Agent 真实需求深度调查报告",
            bold: true,
            size: 48,
            font: "SimHei"
          })
        ],
        alignment: AlignmentType.CENTER,
        spacing: { after: 400 }
      }),
      new Paragraph({
        children: [
          new TextRun({ text: "调查周期: 2026年1月-4月 | 数据来源: Hacker News (188+帖子) | 生成时间: 2026-04-08", size: 24, font: "SimSun" })
        ],
        alignment: AlignmentType.CENTER,
        spacing: { after: 600 }
      }),
      ...sections.flatMap(section => {
        const headingLevel = section.level === 1 ? HeadingLevel.HEADING_1 : 
                             section.level === 2 ? HeadingLevel.HEADING_2 : HeadingLevel.HEADING_3;
        
        const paragraphs = [
          new Paragraph({
            children: [new TextRun({ text: section.title, bold: true, size: section.level === 1 ? 36 : section.level === 2 ? 28 : 24, font: "SimHei" })],
            heading: headingLevel,
            spacing: { before: section.level === 1 ? 400 : 200, after: 200 }
          })
        ];
        
        for (const item of section.content) {
          if (item.type === 'text') {
            paragraphs.push(new Paragraph({
              children: [new TextRun({ text: item.text, size: 22, font: "SimSun" })],
              spacing: { after: 100 }
            }));
          } else if (item.type === 'bold') {
            paragraphs.push(new Paragraph({
              children: [new TextRun({ text: item.text, bold: true, size: 22, font: "SimSun" })],
              spacing: { after: 100 }
            }));
          } else if (item.type === 'quote') {
            paragraphs.push(new Paragraph({
              children: [new TextRun({ text: item.text, italics: true, size: 20, font: "SimSun", color: "666666" })],
              spacing: { after: 100 },
              indent: { left: 720 }
            }));
          } else if (item.type === 'list') {
            paragraphs.push(new Paragraph({
              children: [new TextRun({ text: "• " + item.text, size: 22, font: "SimSun" })],
              spacing: { after: 50 },
              indent: { left: 360 }
            }));
          }
        }
        
        return paragraphs;
      })
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("upwork-ai-agent-demand-report.docx", buffer);
  console.log("✅ Word 文档已生成");
});