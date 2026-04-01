#!/usr/bin/env python3
"""
自动导入 watchdog 生成的记忆文档到 LanceDB

功能：
1. 扫描 ~/.openclaw/workspace/memory/*.md
2. 提取关键信息
3. 导入到 LanceDB
4. 记录导入状态，避免重复
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime

try:
    import subprocess
    HAS_NODE = True
except:
    HAS_NODE = False

MEMORY_DIR = Path('/home/kyj/.openclaw/workspace/memory')
STATE_FILE = Path('/home/kyj/.openclaw/workspace/.watchdog_import_state.json')

def load_state():
    """加载导入状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'imported_files': [], 'last_import': None}

def save_state(state):
    """保存导入状态"""
    state['last_import'] = datetime.now().isoformat()
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_file_hash(file_path):
    """计算文件哈希"""
    content = file_path.read_text(encoding='utf-8')
    return hashlib.md5(content.encode()).hexdigest()

def extract_memories_from_md(file_path):
    """从 Markdown 文件提取记忆"""
    content = file_path.read_text(encoding='utf-8')
    
    memories = []
    
    # 提取标题
    title = file_path.stem
    
    # 简单分段
    sections = content.split('\n## ')
    
    for section in sections[1:]:  # 跳过第一个（标题）
        lines = section.split('\n')
        section_title = lines[0].strip() if lines else 'Unknown'
        
        # 提取内容（跳过标题行）
        section_content = '\n'.join(lines[1:])
        
        if len(section_content.strip()) > 100:  # 太短的不是有效记忆
            memory_text = f"[{title}] {section_title}: {section_content.strip()[:500]}"
            
            memories.append({
                'text': memory_text,
                'category': 'fact',
                'scope': 'global',
                'importance': 0.7,
                'tags': ['watchdog', '日志', title],
                'metadata': {
                    'source': str(file_path),
                    'section': section_title,
                    'imported_at': datetime.now().isoformat()
                }
            })
    
    return memories

def import_to_lancedb(memories):
    """导入记忆到 LanceDB"""
    if not memories:
        return 0
    
    # 准备 JSON 文件
    temp_file = Path('/home/kyj/.openclaw/workspace/.temp_watchdog_memories.json')
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)
    
    # 调用 Node.js 脚本导入（复用现有的 import_supplement.js）
    import_script = Path('/home/kyj/.openclaw/workspace/memory-lancedb-pro/import_supplement.js')
    
    if import_script.exists() and HAS_NODE:
        result = subprocess.run(
            ['node', str(import_script)],
            capture_output=True,
            text=True,
            cwd=import_script.parent
        )
        print(result.stdout)
        if result.stderr:
            print(f"错误：{result.stderr}")
    
    # 清理
    if temp_file.exists():
        temp_file.unlink()
    
    return len(memories)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='导入 watchdog 记忆文档到 LanceDB')
    parser.add_argument('--force', action='store_true', help='强制导入所有文件')
    parser.add_argument('--dry-run', action='store_true', help='只显示，不导入')
    args = parser.parse_args()
    
    print("=" * 70)
    print("📥 导入 watchdog 记忆文档到 LanceDB")
    print("=" * 70)
    print()
    
    state = load_state()
    
    # 扫描记忆文档
    md_files = list(MEMORY_DIR.glob('*.md'))
    
    print(f"📂 发现 {len(md_files)} 个记忆文档\n")
    
    total_imported = 0
    
    for file in md_files:
        current_hash = get_file_hash(file)
        
        # 检查是否已导入
        if not args.force:
            imported_info = next(
                (item for item in state['imported_files'] if item['file'] == str(file)),
                None
            )
            
            if imported_info and imported_info.get('hash') == current_hash:
                print(f"⏭️  跳过：{file.name} (已导入)")
                continue
        
        print(f"📝 导入：{file.name}")
        
        # 提取记忆
        memories = extract_memories_from_md(file)
        
        if not memories:
            print(f"   ⚠️  无有效记忆")
            continue
        
        print(f"   📊 提取 {len(memories)} 条记忆")
        
        if not args.dry_run:
            # 导入到 LanceDB
            imported = import_to_lancedb(memories)
            total_imported += imported
            print(f"   ✅ 导入 {imported} 条")
            
            # 更新状态
            state['imported_files'].append({
                'file': str(file),
                'hash': current_hash,
                'memories': len(memories),
                'imported_at': datetime.now().isoformat()
            })
            save_state(state)
        else:
            total_imported += len(memories)
            print(f"   ⏭️  预览模式，未导入")
    
    print()
    print("=" * 70)
    if args.dry_run:
        print(f"📊 预览：共 {total_imported} 条记忆待导入")
    else:
        print(f"📊 导入完成！共导入 {total_imported} 条记忆")
    print("=" * 70)

if __name__ == "__main__":
    main()
