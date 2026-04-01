#!/usr/bin/env python3
"""
自动记忆归档系统
根据时间、重要性等条件自动归档旧记忆
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict
import shutil

class MemoryArchiver:
    """记忆归档器"""
    
    def __init__(self, workspace_path: str = "/home/kyj/.openclaw/workspace"):
        self.workspace = workspace_path
        self.memory_dir = os.path.join(workspace_path, "memory")
        self.archive_dir = os.path.join(workspace_path, "archive", "memory")
        
        # 归档规则
        self.rules = {
            'age_days': 30,  # 30 天以上的记忆
            'importance_threshold': 0.3,  # 重要性低于 0.3
            'min_count': 10  # 至少保留 10 个记忆
        }
        
        # 确保归档目录存在
        os.makedirs(self.archive_dir, exist_ok=True)
    
    def get_memory_files(self) -> List[Dict]:
        """获取所有记忆文件"""
        memories = []
        
        if not os.path.exists(self.memory_dir):
            return memories
        
        for filename in os.listdir(self.memory_dir):
            if filename.endswith('.md'):
                filepath = os.path.join(self.memory_dir, filename)
                
                # 解析文件名获取日期
                try:
                    date_str = filename.replace('.md', '')
                    memory_date = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    # 读取文件获取重要性
                    importance = self._get_importance(filepath)
                    
                    memories.append({
                        'filename': filename,
                        'filepath': filepath,
                        'date': memory_date,
                        'importance': importance,
                        'age_days': (datetime.now() - memory_date).days
                    })
                except Exception as e:
                    print(f"⚠️  解析 {filename} 失败：{e}")
        
        return memories
    
    def _get_importance(self, filepath: str) -> float:
        """从文件中提取重要性"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 查找重要性标记
                if '重要性' in content:
                    import re
                    match = re.search(r'重要性 [::]\s*([0-9.]+)', content)
                    if match:
                        return float(match.group(1))
                
                # 默认重要性
                return 0.5
        except:
            return 0.5
    
    def should_archive(self, memory: Dict) -> bool:
        """判断是否应该归档"""
        # 检查年龄
        if memory['age_days'] < self.rules['age_days']:
            return False
        
        # 检查重要性
        if memory['importance'] >= self.rules['importance_threshold']:
            return False
        
        return True
    
    def archive_memory(self, memory: Dict) -> str:
        """归档单个记忆"""
        # 创建归档子目录（按月）
        month_dir = os.path.join(
            self.archive_dir,
            memory['date'].strftime('%Y-%m')
        )
        os.makedirs(month_dir, exist_ok=True)
        
        # 移动文件
        dest_path = os.path.join(month_dir, memory['filename'])
        shutil.move(memory['filepath'], dest_path)
        
        return dest_path
    
    def run_archive(self, dry_run: bool = False) -> Dict:
        """运行归档"""
        print("=" * 60)
        print("🗄️  自动记忆归档")
        print("=" * 60)
        print()
        
        # 获取所有记忆
        memories = self.get_memory_files()
        print(f"📊 找到 {len(memories)} 个记忆文件")
        
        # 筛选需要归档的
        to_archive = [m for m in memories if self.should_archive(m)]
        print(f"📦 需要归档：{len(to_archive)} 个")
        
        # 确保保留至少 min_count 个
        if len(memories) - len(to_archive) < self.rules['min_count']:
            # 保留最重要的
            to_archive = sorted(to_archive, key=lambda x: x['importance'])
            keep_count = self.rules['min_count'] - (len(memories) - len(to_archive))
            to_archive = to_archive[:-keep_count] if keep_count > 0 else []
            print(f"📦 保留 {self.rules['min_count']} 个后，实际归档：{len(to_archive)} 个")
        
        if not to_archive:
            print("✅ 无需归档")
            return {'archived': 0, 'files': []}
        
        print()
        
        # 执行归档
        archived_files = []
        for memory in to_archive:
            if dry_run:
                print(f"📦 [预览] 归档：{memory['filename']} ({memory['age_days']}天)")
            else:
                dest = self.archive_memory(memory)
                print(f"✅ 归档：{memory['filename']} → {dest}")
            archived_files.append(memory['filename'])
        
        print()
        print("=" * 60)
        print(f"✅ 归档完成！共 {len(archived_files)} 个文件")
        print("=" * 60)
        
        return {
            'archived': len(archived_files),
            'files': archived_files
        }

# 运行归档
if __name__ == "__main__":
    import sys
    
    dry_run = '--dry-run' in sys.argv
    
    archiver = MemoryArchiver()
    result = archiver.run_archive(dry_run=dry_run)
    
    print()
    print(f"📊 统计:")
    print(f"   归档文件数：{result['archived']}")
    if result['files']:
        print(f"   文件列表:")
        for f in result['files']:
            print(f"      - {f}")
