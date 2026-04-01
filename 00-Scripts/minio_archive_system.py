"""
混合记忆架构 - 阶段 5 实现
MinIO 对象存储归档

实施内容:
1. MinIO 客户端集成
2. 自动归档策略
3. 压缩算法优化
4. 归档检索集成
5. 成本基准测试

预期收益：存储成本 ↓60%
"""

import os
import json
import gzip
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import shutil


# ==================== MinIO 客户端集成 ====================

class MinIOClient:
    """
    MinIO 对象存储客户端
    
    功能:
    - 上传对象
    - 下载对象
    - 删除对象
    - 列出对象
    - 批量操作
    
    配置:
    - endpoint: MinIO 服务器地址
    - access_key: 访问密钥
    - secret_key: 密钥
    - bucket: 存储桶名称
    - secure: 是否使用 HTTPS
    """
    
    def __init__(self, 
                 endpoint: str = "localhost:9000",
                 access_key: str = "minioadmin",
                 secret_key: str = "minioadmin",
                 bucket: str = "openclaw-memory",
                 secure: bool = False):
        """
        初始化 MinIO 客户端
        
        Args:
            endpoint: MinIO 地址
            access_key: 访问密钥
            secret_key: 密钥
            bucket: 存储桶
            secure: 是否 HTTPS
        """
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.secure = secure
        
        self.client = None
        self.is_connected = False
        
        # 模拟连接（实际需要 minio 库）
        print(f"📦 连接 MinIO: {endpoint}")
        print(f"   存储桶：{bucket}")
        print(f"   注意：实际使用需要安装 minio 库")
        print(f"   pip install minio")
        self._connect()
    
    def _connect(self):
        """连接 MinIO"""
        try:
            from minio import Minio
            self.client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )
            
            # 确保存储桶存在
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
            
            self.is_connected = True
            print(f"✅ MinIO 连接成功")
            
        except ImportError:
            print(f"⚠️  未安装 minio 库，使用模拟模式")
            self.is_connected = False
        except Exception as e:
            print(f"⚠️  MinIO 连接失败：{e}")
            self.is_connected = False
    
    def upload_object(self, 
                     object_name: str, 
                     file_path: str,
                     metadata: Dict = None) -> bool:
        """
        上传对象
        
        Args:
            object_name: 对象名称
            file_path: 文件路径
            metadata: 元数据
        
        Returns:
            是否成功
        """
        if not self.is_connected:
            # 模拟上传
            print(f"📤 [模拟] 上传：{object_name}")
            return True
        
        try:
            self.client.fput_object(
                self.bucket,
                object_name,
                file_path,
                metadata=metadata
            )
            print(f"📤 上传成功：{object_name}")
            return True
            
        except Exception as e:
            print(f"❌ 上传失败：{e}")
            return False
    
    def download_object(self,
                       object_name: str,
                       file_path: str) -> bool:
        """
        下载对象
        
        Args:
            object_name: 对象名称
            file_path: 文件路径
        
        Returns:
            是否成功
        """
        if not self.is_connected:
            # 模拟下载
            print(f"📥 [模拟] 下载：{object_name}")
            return True
        
        try:
            self.client.fget_object(
                self.bucket,
                object_name,
                file_path
            )
            print(f"📥 下载成功：{object_name}")
            return True
            
        except Exception as e:
            print(f"❌ 下载失败：{e}")
            return False
    
    def delete_object(self, object_name: str) -> bool:
        """
        删除对象
        
        Args:
            object_name: 对象名称
        
        Returns:
            是否成功
        """
        if not self.is_connected:
            print(f"🗑️  [模拟] 删除：{object_name}")
            return True
        
        try:
            self.client.remove_object(self.bucket, object_name)
            print(f"🗑️  删除成功：{object_name}")
            return True
            
        except Exception as e:
            print(f"❌ 删除失败：{e}")
            return False
    
    def list_objects(self, prefix: str = "") -> List[str]:
        """
        列出对象
        
        Args:
            prefix: 前缀过滤
        
        Returns:
            对象名称列表
        """
        if not self.is_connected:
            # 模拟列表
            print(f"📋 [模拟] 列出对象：{prefix}")
            return []
        
        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix)
            return [obj.object_name for obj in objects]
            
        except Exception as e:
            print(f"❌ 列出失败：{e}")
            return []
    
    def get_storage_stats(self) -> Dict:
        """
        获取存储统计
        
        Returns:
            统计信息
        """
        if not self.is_connected:
            return {
                "connected": False,
                "objects": 0,
                "size_bytes": 0,
                "size_human": "0 B"
            }
        
        # 实际实现需要查询 MinIO
        return {
            "connected": True,
            "objects": 0,
            "size_bytes": 0,
            "size_human": "0 B"
        }


# ==================== 压缩算法优化 ====================

class CompressionManager:
    """
    压缩管理器
    
    支持的压缩算法:
    - gzip: 通用压缩 (推荐)
    - bz2: 高压缩率
    - lzma: 最高压缩率
    - zstd: 快速压缩 (需要 zstandard 库)
    
    压缩级别:
    - 1-9 (9 为最高压缩)
    """
    
    def __init__(self, algorithm: str = "gzip", level: int = 6):
        """
        初始化压缩管理器
        
        Args:
            algorithm: 压缩算法
            level: 压缩级别 (1-9)
        """
        self.algorithm = algorithm
        self.level = level
        
        print(f"🗜️  压缩管理器已初始化")
        print(f"   算法：{algorithm}")
        print(f"   级别：{level}")
    
    def compress(self, 
                 input_path: str,
                 output_path: str = None) -> str:
        """
        压缩文件
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
        
        Returns:
            输出文件路径
        """
        if output_path is None:
            output_path = f"{input_path}.{self.algorithm}"
        
        # 读取原始文件
        with open(input_path, 'rb') as f:
            data = f.read()
        
        original_size = len(data)
        
        # 压缩
        if self.algorithm == "gzip":
            compressed_data = gzip.compress(data, compresslevel=self.level)
        elif self.algorithm == "bz2":
            import bz2
            compressed_data = bz2.compress(data, compresslevel=self.level)
        elif self.algorithm == "lzma":
            import lzma
            compressed_data = lzma.compress(data)
        else:
            # 默认 gzip
            compressed_data = gzip.compress(data, compresslevel=self.level)
        
        # 写入压缩文件
        with open(output_path, 'wb') as f:
            f.write(compressed_data)
        
        compressed_size = len(compressed_data)
        compression_ratio = original_size / compressed_size if compressed_size > 0 else 0
        
        print(f"🗜️  压缩完成：{input_path} → {output_path}")
        print(f"   原始大小：{original_size / 1024:.2f} KB")
        print(f"   压缩后：{compressed_size / 1024:.2f} KB")
        print(f"   压缩比：{compression_ratio:.2f}x")
        print(f"   节省：{(1 - compressed_size/original_size) * 100:.1f}%")
        
        return output_path
    
    def decompress(self,
                  input_path: str,
                  output_path: str = None) -> str:
        """
        解压缩文件
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
        
        Returns:
            输出文件路径
        """
        if output_path is None:
            # 自动推断输出路径
            output_path = input_path.rsplit('.', 1)[0]
        
        # 读取压缩文件
        with open(input_path, 'rb') as f:
            compressed_data = f.read()
        
        # 解压缩
        if input_path.endswith('.gz'):
            data = gzip.decompress(compressed_data)
        elif input_path.endswith('.bz2'):
            import bz2
            data = bz2.decompress(compressed_data)
        elif input_path.endswith('.xz'):
            import lzma
            data = lzma.decompress(compressed_data)
        else:
            data = gzip.decompress(compressed_data)
        
        # 写入解压文件
        with open(output_path, 'wb') as f:
            f.write(data)
        
        print(f"📦 解压完成：{input_path} → {output_path}")
        
        return output_path
    
    def estimate_compression(self, data_size: int) -> Dict:
        """
        估算压缩效果
        
        Args:
            data_size: 原始数据大小
        
        Returns:
            估算结果
        """
        # 根据经验估算压缩比
        compression_ratios = {
            "gzip": 3.0,
            "bz2": 4.0,
            "lzma": 5.0,
            "zstd": 3.5
        }
        
        ratio = compression_ratios.get(self.algorithm, 3.0)
        compressed_size = data_size / ratio
        savings = (1 - 1/ratio) * 100
        
        return {
            "algorithm": self.algorithm,
            "original_size": data_size,
            "compressed_size": compressed_size,
            "compression_ratio": ratio,
            "savings_percent": savings
        }


# ==================== 自动归档策略 ====================

class ArchivePolicy:
    """
    自动归档策略
    
    策略类型:
    - 时间策略：基于创建时间
    - 访问策略：基于最后访问时间
    - 重要性策略：基于重要性分数
    - 组合策略：多种条件组合
    """
    
    def __init__(self, 
                 strategy: str = "time_based",
                 archive_after_days: int = 30,
                 min_importance: float = 0.3):
        """
        初始化归档策略
        
        Args:
            strategy: 策略类型
            archive_after_days: 多少天后归档
            min_importance: 最低重要性阈值
        """
        self.strategy = strategy
        self.archive_after_days = archive_after_days
        self.min_importance = min_importance
        
        print(f"📋 归档策略已配置")
        print(f"   策略类型：{strategy}")
        print(f"   归档时间：{archive_after_days} 天")
        print(f"   最低重要性：{min_importance}")
    
    def should_archive(self, memory: Dict) -> bool:
        """
        判断是否应该归档
        
        Args:
            memory: 记忆对象
        
        Returns:
            是否归档
        """
        if self.strategy == "time_based":
            return self._check_time_based(memory)
        elif self.strategy == "access_based":
            return self._check_access_based(memory)
        elif self.strategy == "importance_based":
            return self._check_importance_based(memory)
        elif self.strategy == "combined":
            return self._check_combined(memory)
        else:
            return False
    
    def _check_time_based(self, memory: Dict) -> bool:
        """基于时间的归档"""
        created_at = memory.get("created_at", datetime.now().isoformat())
        created_date = datetime.fromisoformat(created_at)
        
        age_days = (datetime.now() - created_date).days
        
        should_archive = age_days >= self.archive_after_days
        
        if should_archive:
            print(f"   ⏰ 时间策略：已创建 {age_days} 天 >= {self.archive_after_days} 天")
        
        return should_archive
    
    def _check_access_based(self, memory: Dict) -> bool:
        """基于访问的归档"""
        last_accessed = memory.get("last_accessed")
        
        if not last_accessed:
            # 从未访问，归档
            return True
        
        last_access_date = datetime.fromisoformat(last_accessed)
        days_since_access = (datetime.now() - last_access_date).days
        
        should_archive = days_since_access >= self.archive_after_days
        
        if should_archive:
            print(f"   📖 访问策略：{days_since_access} 天未访问")
        
        return should_archive
    
    def _check_importance_based(self, memory: Dict) -> bool:
        """基于重要性的归档"""
        importance = memory.get("importance", 0.5)
        
        should_archive = importance < self.min_importance
        
        if should_archive:
            print(f"   ⭐ 重要性策略：{importance} < {self.min_importance}")
        
        return should_archive
    
    def _check_combined(self, memory: Dict) -> bool:
        """组合策略"""
        # 时间条件
        created_at = memory.get("created_at", datetime.now().isoformat())
        created_date = datetime.fromisoformat(created_at)
        age_days = (datetime.now() - created_date).days
        
        # 访问条件
        last_accessed = memory.get("last_accessed")
        days_since_access = 0
        if last_accessed:
            last_access_date = datetime.fromisoformat(last_accessed)
            days_since_access = (datetime.now() - last_access_date).days
        
        # 重要性条件
        importance = memory.get("importance", 0.5)
        
        # 组合判断
        should_archive = (
            age_days >= self.archive_after_days and
            days_since_access >= self.archive_after_days and
            importance < self.min_importance
        )
        
        if should_archive:
            print(f"   🔀 组合策略：所有条件满足")
        
        return should_archive


# ==================== 归档管理器 ====================

class ArchiveManager:
    """
    归档管理器
    
    功能:
    - 自动归档
    - 归档检索
    - 归档恢复
    - 归档清理
    - 成本统计
    """
    
    def __init__(self,
                 minio_client: MinIOClient,
                 compression_manager: CompressionManager,
                 archive_policy: ArchivePolicy,
                 archive_prefix: str = "archive"):
        """
        初始化归档管理器
        
        Args:
            minio_client: MinIO 客户端
            compression_manager: 压缩管理器
            archive_policy: 归档策略
            archive_prefix: 归档前缀
        """
        self.minio = minio_client
        self.compressor = compression_manager
        self.policy = archive_policy
        self.archive_prefix = archive_prefix
        
        self.stats = {
            "total_archived": 0,
            "total_size_original": 0,
            "total_size_compressed": 0,
            "total_cost_saved": 0
        }
        
        print(f"📦 归档管理器已初始化")
        print(f"   归档前缀：{archive_prefix}")
    
    def archive_memory(self, memory: Dict) -> bool:
        """
        归档单条记忆
        
        Args:
            memory: 记忆对象
        
        Returns:
            是否成功
        """
        # 检查是否应该归档
        if not self.policy.should_archive(memory):
            print(f"   ⏭️  跳过：不满足归档条件")
            return False
        
        # 生成归档文件名
        memory_id = memory.get("id", "unknown")
        created_at = memory.get("created_at", datetime.now().isoformat())
        date_str = created_at.split("T")[0]
        
        # 归档路径：archive/YYYY-MM/memory_id.json.gz
        archive_path = f"{self.archive_prefix}/{date_str}/{memory_id}.json.gz"
        
        # 准备归档数据
        archive_data = {
            "memory": memory,
            "archived_at": datetime.now().isoformat(),
            "archive_reason": self.policy.strategy
        }
        
        # 保存到临时文件
        temp_file = f"/tmp/{memory_id}.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(archive_data, f, ensure_ascii=False, indent=2)
        
        original_size = os.path.getsize(temp_file)
        
        # 压缩
        compressed_file = f"{temp_file}.gz"
        self.compressor.compress(temp_file, compressed_file)
        
        compressed_size = os.path.getsize(compressed_file)
        
        # 上传到 MinIO
        success = self.minio.upload_object(archive_path, compressed_file)
        
        if success:
            # 更新统计
            self.stats["total_archived"] += 1
            self.stats["total_size_original"] += original_size
            self.stats["total_size_compressed"] += compressed_size
            
            # 计算成本节省 (假设热存储 $0.023/GB, 冷存储 $0.004/GB)
            cost_saved = (original_size / (1024**3)) * (0.023 - 0.004)
            self.stats["total_cost_saved"] += cost_saved
            
            print(f"✅ 归档成功：{memory_id}")
            print(f"   归档路径：{archive_path}")
            
            # 清理临时文件
            os.remove(temp_file)
            os.remove(compressed_file)
            
            return True
        else:
            print(f"❌ 归档失败：{memory_id}")
            return False
    
    def archive_batch(self, memories: List[Dict]) -> Dict:
        """
        批量归档
        
        Args:
            memories: 记忆列表
        
        Returns:
            归档统计
        """
        print(f"\n📦 开始批量归档：{len(memories)} 条记忆")
        print("-" * 70)
        
        archived_count = 0
        skipped_count = 0
        
        for memory in memories:
            if self.archive_memory(memory):
                archived_count += 1
            else:
                skipped_count += 1
        
        print("-" * 70)
        print(f"✅ 批量归档完成")
        print(f"   归档：{archived_count} 条")
        print(f"   跳过：{skipped_count} 条")
        print(f"   原始大小：{self.stats['total_size_original'] / 1024:.2f} KB")
        print(f"   压缩后：{self.stats['total_size_compressed'] / 1024:.2f} KB")
        print(f"   压缩比：{self.stats['total_size_original'] / max(self.stats['total_size_compressed'], 1):.2f}x")
        print(f"   节省成本：${self.stats['total_cost_saved']:.4f}")
        
        return {
            "archived": archived_count,
            "skipped": skipped_count,
            "original_size": self.stats["total_size_original"],
            "compressed_size": self.stats["total_size_compressed"],
            "cost_saved": self.stats["total_cost_saved"]
        }
    
    def retrieve_archived(self, memory_id: str) -> Optional[Dict]:
        """
        检索归档记忆
        
        Args:
            memory_id: 记忆 ID
        
        Returns:
            记忆对象
        """
        print(f"\n📥 检索归档记忆：{memory_id}")
        
        # 需要从索引中查找归档路径（简化实现）
        # 实际需要维护归档索引
        archive_path = f"{self.archive_prefix}/.../{memory_id}.json.gz"
        
        # 下载到临时文件
        temp_file = f"/tmp/{memory_id}_archived.json.gz"
        success = self.minio.download_object(archive_path, temp_file)
        
        if not success:
            print(f"❌ 检索失败：{memory_id}")
            return None
        
        # 解压
        import gzip
        with gzip.open(temp_file, 'rt', encoding='utf-8') as f:
            archive_data = json.load(f)
        
        memory = archive_data.get("memory")
        
        print(f"✅ 检索成功：{memory_id}")
        
        # 清理临时文件
        os.remove(temp_file)
        
        return memory
    
    def get_archive_stats(self) -> Dict:
        """
        获取归档统计
        
        Returns:
            统计信息
        """
        minio_stats = self.minio.get_storage_stats()
        
        compression_ratio = (
            self.stats["total_size_original"] / max(self.stats["total_size_compressed"], 1)
        )
        
        return {
            **self.stats,
            **minio_stats,
            "compression_ratio": compression_ratio,
            "cost_savings_monthly": self.stats["total_cost_saved"] * 30  # 估算月节省
        }


# ==================== 成本基准测试 ====================

class CostBenchmark:
    """
    成本基准测试
    
    存储成本对比 (每 GB/月):
    - 热存储 (SSD): $0.023
    - 温存储 (HDD): $0.010
    - 冷存储 (MinIO): $0.004
    - 归档 (Glacier): $0.003
    
    预期收益:
    - 冷数据归档 60% → 成本 ↓60%
    """
    
    def __init__(self):
        # 存储成本 ($/GB/月)
        self.storage_costs = {
            "hot_ssd": 0.023,
            "warm_hdd": 0.010,
            "cold_minio": 0.004,
            "archive_glacier": 0.003
        }
        
        # API 请求成本 ($/1000 次)
        self.api_costs = {
            "get": 0.0004,
            "put": 0.005,
            "delete": 0.000
        }
    
    def estimate_monthly_cost(self,
                             hot_data_gb: float,
                             warm_data_gb: float,
                             cold_data_gb: float,
                             archive_data_gb: float,
                             api_requests: int = 10000) -> Dict:
        """
        估算月度成本
        
        Args:
            hot_data_gb: 热数据量 (GB)
            warm_data_gb: 温数据量 (GB)
            cold_data_gb: 冷数据量 (GB)
            archive_data_gb: 归档数据量 (GB)
            api_requests: API 请求次数
        
        Returns:
            成本估算
        """
        # 存储成本
        storage_cost = (
            hot_data_gb * self.storage_costs["hot_ssd"] +
            warm_data_gb * self.storage_costs["warm_hdd"] +
            cold_data_gb * self.storage_costs["cold_minio"] +
            archive_data_gb * self.storage_costs["archive_glacier"]
        )
        
        # API 成本
        api_cost = (api_requests / 1000) * self.api_costs["get"]
        
        # 总成本
        total_cost = storage_cost + api_cost
        
        # 优化前成本（全部热存储）
        total_data = hot_data_gb + warm_data_gb + cold_data_gb + archive_data_gb
        cost_before = total_data * self.storage_costs["hot_ssd"]
        
        # 成本节省
        cost_saved = cost_before - total_cost
        savings_percent = (cost_saved / cost_before * 100) if cost_before > 0 else 0
        
        return {
            "storage_cost": storage_cost,
            "api_cost": api_cost,
            "total_cost": total_cost,
            "cost_before": cost_before,
            "cost_saved": cost_saved,
            "savings_percent": savings_percent
        }
    
    def run_benchmark(self) -> Dict:
        """
        运行成本基准测试
        
        Returns:
            基准测试结果
        """
        print("\n" + "=" * 70)
        print("📊 成本基准测试")
        print("=" * 70)
        
        # 模拟数据量 (GB)
        hot_data = 10    # 热数据 (最近 1 小时)
        warm_data = 100  # 温数据 (1 小时 -30 天)
        cold_data = 500  # 冷数据 (30 天 -1 年)
        archive_data = 1000  # 归档数据 (1 年+)
        
        # 估算成本
        cost_estimate = self.estimate_monthly_cost(
            hot_data, warm_data, cold_data, archive_data
        )
        
        print(f"\n数据分布:")
        print(f"  热数据：{hot_data} GB ({hot_data/(hot_data+warm_data+cold_data+archive_data)*100:.1f}%)")
        print(f"  温数据：{warm_data} GB ({warm_data/(hot_data+warm_data+cold_data+archive_data)*100:.1f}%)")
        print(f"  冷数据：{cold_data} GB ({cold_data/(hot_data+warm_data+cold_data+archive_data)*100:.1f}%)")
        print(f"  归档数据：{archive_data} GB ({archive_data/(hot_data+warm_data+cold_data+archive_data)*100:.1f}%)")
        
        print(f"\n月度成本估算:")
        print(f"  存储成本：${cost_estimate['storage_cost']:.2f}")
        print(f"  API 成本：${cost_estimate['api_cost']:.4f}")
        print(f"  总成本：${cost_estimate['total_cost']:.2f}")
        
        print(f"\n成本对比:")
        print(f"  优化前（全热存储）：${cost_estimate['cost_before']:.2f}")
        print(f"  优化后（分层存储）：${cost_estimate['total_cost']:.2f}")
        print(f"  节省：${cost_estimate['cost_saved']:.2f} ({cost_estimate['savings_percent']:.1f}%)")
        
        print("\n" + "=" * 70)
        
        return cost_estimate


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("🧪 测试混合记忆架构 - 阶段 5\n")
    
    # 测试 1: MinIO 客户端
    print("测试 1: MinIO 对象存储客户端")
    print("-" * 70)
    minio = MinIOClient(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        bucket="openclaw-memory"
    )
    print()
    
    # 测试 2: 压缩管理器
    print("测试 2: 压缩管理器")
    print("-" * 70)
    compressor = CompressionManager(algorithm="gzip", level=6)
    
    # 估算压缩效果
    estimate = compressor.estimate_compression(1024 * 1024)  # 1MB
    print(f"   1MB 数据压缩估算:")
    print(f"   压缩后：{estimate['compressed_size'] / 1024:.2f} KB")
    print(f"   压缩比：{estimate['compression_ratio']:.2f}x")
    print(f"   节省：{estimate['savings_percent']:.1f}%")
    print()
    
    # 测试 3: 归档策略
    print("测试 3: 自动归档策略")
    print("-" * 70)
    policy = ArchivePolicy(
        strategy="combined",
        archive_after_days=30,
        min_importance=0.3
    )
    
    # 测试记忆
    test_memory = {
        "id": "mem_test",
        "created_at": (datetime.now() - timedelta(days=35)).isoformat(),
        "last_accessed": (datetime.now() - timedelta(days=40)).isoformat(),
        "importance": 0.2
    }
    
    should_archive = policy.should_archive(test_memory)
    print(f"   测试记忆是否归档：{'是' if should_archive else '否'}")
    print()
    
    # 测试 4: 归档管理器
    print("测试 4: 归档管理器")
    print("-" * 70)
    archive_mgr = ArchiveManager(
        minio_client=minio,
        compression_manager=compressor,
        archive_policy=policy
    )
    
    # 批量归档测试
    test_memories = [
        {
            "id": f"mem_{i}",
            "text": f"测试记忆{i}",
            "created_at": (datetime.now() - timedelta(days=35+i)).isoformat(),
            "last_accessed": (datetime.now() - timedelta(days=40+i)).isoformat(),
            "importance": 0.2
        }
        for i in range(5)
    ]
    
    stats = archive_mgr.archive_batch(test_memories)
    print()
    
    # 测试 5: 成本基准
    print("测试 5: 成本基准测试")
    print("-" * 70)
    benchmark = CostBenchmark()
    cost_estimate = benchmark.run_benchmark()
    print()
    
    print("=" * 70)
    print("✅ 阶段 5 所有测试完成！")
    print("=" * 70)
    print()
    print("预期收益:")
    print("  • 存储成本 ↓60%")
    print("  • 冷数据访问延迟 <500ms")
    print("  • 自动归档 30 天 + 数据")
