#!/usr/bin/env python3
"""
导入 A 级和 B 级记忆文档到 LanceDB

平衡导入策略：
- A 级：高价值个人记忆（scope="personal"）
- B 级：项目重要文档（scope="project"）
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

MEMORY_DIR = Path('/home/kyj/.openclaw/workspace/memory')

def extract_memories_from_file(file_path, grade):
    """从文件提取记忆"""
    content = file_path.read_text(encoding='utf-8')
    filename = file_path.stem.replace(f'({grade})', '')
    
    memories = []
    
    # 按章节分段
    sections = content.split('\n## ')
    
    for i, section in enumerate(sections[1:], 1):  # 跳过标题
        lines = section.split('\n')
        section_title = lines[0].strip() if lines else 'Unknown'
        section_content = '\n'.join(lines[1:]).strip()
        
        if len(section_content) > 100:  # 太短的不是有效记忆
            # 确定 scope
            if grade == 'A':
                scope = 'personal'
            elif grade == 'B':
                scope = 'project' if any(kw in content for kw in ['DSS', '项目', '架构']) else 'personal'
            else:
                scope = 'global'
            
            memory_text = f"[{filename}] {section_title}: {section_content[:500]}"
            
            memories.append({
                'text': memory_text,
                'category': 'fact' if '事实' in section_content or '数据' in section_content else 'decision',
                'scope': scope,
                'importance': 0.9 if grade == 'A' else 0.8,
                'tags': [f'watchdog-{grade}', filename, section_title[:20]],
                'metadata': {
                    'source': str(file_path),
                    'grade': grade,
                    'section': section_title,
                    'imported_at': datetime.now().isoformat()
                }
            })
    
    return memories

def import_memories(memories):
    """导入记忆到 LanceDB"""
    if not memories:
        return 0
    
    # 准备临时文件
    temp_file = Path('/home/kyj/.openclaw/workspace/.temp_import.json')
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)
    
    # 调用导入脚本
    import_script = Path('/home/kyj/.openclaw/workspace/memory-lancedb-pro/import_supplement.js')
    
    if import_script.exists():
        result = subprocess.run(
            ['node', str(import_script)],
            capture_output=True,
            text=True,
            cwd=import_script.parent,
            timeout=120
        )
        print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
    
    # 清理
    if temp_file.exists():
        temp_file.unlink()
    
    return len(memories)

def main():
    print("=" * 70)
    print("📥 平衡导入：A 级+B 级记忆文档")
    print("=" * 70)
    print()
    
    # 扫描 A 级和 B 级文件
    grade_a_files = list(MEMORY_DIR.glob('*\(A\).md'))
    grade_b_files = list(MEMORY_DIR.glob('*\(B\).md'))
    
    print(f"📂 A 级文件：{len(grade_a_files)} 个")
    print(f"📂 B 级文件：{len(grade_b_files)} 个")
    print()
    
    total_imported = 0
    
    # 导入 A 级
    if grade_a_files:
        print("=" * 70)
        print("🌟 导入 A 级（高价值个人记忆）")
        print("=" * 70)
        
        for file in grade_a_files:
            print(f"\n📄 {file.name}")
            memories = extract_memories_from_file(file, 'A')
            print(f"   📊 提取 {len(memories)} 条记忆")
            
            imported = import_memories(memories)
            total_imported += imported
            print(f"   ✅ 导入 {imported} 条")
    
    # 导入 B 级
    if grade_b_files:
        print("\n" + "=" * 70)
        print("📊 导入 B 级（项目重要文档）")
        print("=" * 70)
        
        for file in grade_b_files:
            print(f"\n📄 {file.name}")
            memories = extract_memories_from_file(file, 'B')
            print(f"   📊 提取 {len(memories)} 条记忆")
            
            imported = import_memories(memories)
            total_imported += imported
            print(f"   ✅ 导入 {imported} 条")
    
    print("\n" + "=" * 70)
    print(f"📊 导入完成！")
    print(f"   A 级：{len(grade_a_files)} 个文件")
    print(f"   B 级：{len(grade_b_files)} 个文件")
    print(f"   总计：{total_imported} 条记忆")
    print("=" * 70)

if __name__ == "__main__":
    main()
