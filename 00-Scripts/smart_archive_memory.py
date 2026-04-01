#!/usr/bin/env python3
"""
灵活的记忆归档系统
支持按时间、大小、类型等多种条件归档
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict
import shutil
import re

class SmartMemoryArchiver:
    """智能记忆归档器"""
    
    def __init__(self, workspace_path: str = "/home/kyj/.openclaw/workspace"):
        self.workspace = workspace_path
        self.memory_dir = os.path.join(workspace_path, "memory")
        self.archive_dir = os.path.join(workspace_path, "archive", "memory")
        
        # 确保归档目录存在
        os.makedirs(self.archive_dir, exist_ok=True)
    
    def get_all_files(self) -> List[Dict]:
        """获取所有文件并分析"""
        files = []
        
        if not os.path.exists(self.memory_dir):
            return files
        
        for filename in os.listdir(self.memory_dir):
            if filename.startswith('.'):
                continue
            
            filepath = os.path.join(self.memory_dir, filename)
            
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                
                # 尝试提取日期
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
                if date_match:
                    file_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                else:
                    file_date = datetime.fromtimestamp(stat.st_mtime)
                
                files.append({
                    'filename': filename,
                    'filepath': filepath,
                    'size': stat.st_size,
                    'date': file_date,
                    'age_days': (datetime.now() - file_date).days,
                    'type': self._get_file_type(filename)
                })
        
        return files
    
    def _get_file_type(self, filename: str) -> str:
        """获取文件类型"""
        if 'ielts' in filename.lower():
            return 'ielts'
        elif 'dss' in filename.lower():
            return 'dss'
        elif 'paper' in filename.lower():
            return 'paper'
        elif '人民币' in filename:
            return 'finance'
        else:
            return 'other'
    
    def archive_by_age(self, days: int = 30, dry_run: bool = False) -> Dict:
        """按年龄归档"""
        print(f"📦 按年龄归档 (> {days} 天)")
        print()
        
        files = self.get_all_files()
        to_archive = [f for f in files if f['age_days'] > days]
        
        return self._do_archive(to_archive, f"age_{days}d", dry_run)
    
    def archive_by_type(self, file_type: str, dry_run: bool = False) -> Dict:
        """按类型归档"""
        print(f"📦 按类型归档 ({file_type})")
        print()
        
        files = self.get_all_files()
        to_archive = [f for f in files if f['type'] == file_type]
        
        return self._do_archive(to_archive, f"type_{file_type}", dry_run)
    
    def archive_old_projects(self, dry_run: bool = False) -> Dict:
        """归档旧项目文件"""
        print("📦 归档旧项目文件")
        print()
        
        files = self.get_all_files()
        
        # 归档非当前项目的文件
        to_archive = [
            f for f in files 
            if f['type'] in ['dss', 'paper', 'finance'] 
            and f['age_days'] > 7  # 7 天前的项目文件
        ]
        
        return self._do_archive(to_archive, "old_projects", dry_run)
    
    def _do_archive(self, files: List[Dict], category: str, dry_run: bool = False) -> Dict:
        """执行归档"""
        if not files:
            print("✅ 无需归档")
            return {'archived': 0, 'files': [], 'saved_space': 0}
        
        # 创建归档子目录
        archive_subdir = os.path.join(self.archive_dir, category)
        os.makedirs(archive_subdir, exist_ok=True)
        
        archived_files = []
        total_size = 0
        
        for file in files:
            if dry_run:
                print(f"📦 [预览] 归档：{file['filename']} ({file['size']/1024:.1f}KB)")
            else:
                dest = os.path.join(archive_subdir, file['filename'])
                shutil.move(file['filepath'], dest)
                print(f"✅ 归档：{file['filename']} ({file['size']/1024:.1f}KB)")
            
            archived_files.append(file['filename'])
            total_size += file['size']
        
        print()
        print("=" * 60)
        print(f"✅ 归档完成！")
        print(f"   文件数：{len(archived_files)}")
        print(f"   节省空间：{total_size/1024/1024:.2f}MB")
        print("=" * 60)
        
        return {
            'archived': len(archived_files),
            'files': archived_files,
            'saved_space': total_size
        }
    
    def cleanup_empty_dirs(self):
        """清理空目录"""
        print("🧹 清理空目录...")
        
        for root, dirs, files in os.walk(self.memory_dir, topdown=False):
            for dir in dirs:
                dirpath = os.path.join(root, dir)
                if not os.listdir(dirpath):
                    os.rmdir(dirpath)
                    print(f"🗑️  删除空目录：{dirpath}")
        
        print("✅ 清理完成")
    
    def generate_report(self) -> str:
        """生成归档报告"""
        files = self.get_all_files()
        
        report = []
        report.append("=" * 60)
        report.append("📊 记忆文件统计报告")
        report.append("=" * 60)
        report.append("")
        report.append(f"总文件数：{len(files)}")
        report.append(f"总大小：{sum(f['size'] for f in files)/1024/1024:.2f}MB")
        report.append("")
        
        # 按类型统计
        by_type = {}
        for f in files:
            by_type[f['type']] = by_type.get(f['type'], 0) + 1
        
        report.append("按类型统计:")
        for t, count in sorted(by_type.items()):
            report.append(f"   {t}: {count} 个文件")
        
        report.append("")
        
        # 按时间统计
        by_age = {
            '最近 7 天': 0,
            '7-30 天': 0,
            '30 天以上': 0
        }
        
        for f in files:
            if f['age_days'] <= 7:
                by_age['最近 7 天'] += 1
            elif f['age_days'] <= 30:
                by_age['7-30 天'] += 1
            else:
                by_age['30 天以上'] += 1
        
        report.append("按时间统计:")
        for age, count in by_age.items():
            report.append(f"   {age}: {count} 个文件")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)

# 主程序
if __name__ == "__main__":
    import sys
    
    archiver = SmartMemoryArchiver()
    
    if '--report' in sys.argv:
        # 生成报告
        print(archiver.generate_report())
    elif '--cleanup' in sys.argv:
        # 清理空目录
        archiver.cleanup_empty_dirs()
    elif '--archive-old' in sys.argv:
        # 归档旧项目
        dry_run = '--dry-run' in sys.argv
        archiver.archive_old_projects(dry_run=dry_run)
    else:
        # 默认：显示报告
        print("使用方法:")
        print("  python3 smart_archive.py --report      # 显示报告")
        print("  python3 smart_archive.py --archive-old # 归档旧项目")
        print("  python3 smart_archive.py --cleanup     # 清理空目录")
        print("  python3 smart_archive.py --dry-run     # 预览模式")
        print()
        print(archiver.generate_report())
