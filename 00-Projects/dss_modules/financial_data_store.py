"""
DSS金融数据架构 - 简化版

核心原则：
1. 不可变性 - 追加更正而非覆盖
2. 时态性 - 版本快照，时间旅行查询
3. 血缘追踪 - 完整加工链记录
4. 合规元数据 - 数据来源、处理参数

架构：
├── DataVersion    - 版本控制
├── DataLineage    - 血缘追踪
├── CorrectionLog  - 更正日志
└── AuditTrail     - 审计追踪
"""

import os
import json
import hashlib
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import pandas as pd


@dataclass
class DataVersion:
    """数据版本"""
    version_id: str
    timestamp: str
    trade_date: str
    data_hash: str
    file_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CorrectionEntry:
    """更正记录"""
    correction_id: str
    timestamp: str
    original_version: str
    field: str
    symbol: str
    old_value: Any
    new_value: Any
    reason: str
    auditor: str = "system"
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class LineageNode:
    """血缘节点"""
    node_id: str
    node_type: str  # 'source', 'transform', 'output'
    name: str
    input_nodes: List[str] = field(default_factory=list)
    output_nodes: List[str] = field(default_factory=list)
    transform_params: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    hash: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


class FinancialDataStore:
    """
    金融数据存储管理器
    
    特性：
    - 不可变存储
    - 版本控制
    - 血缘追踪
    - 追加更正
    """
    
    def __init__(self, base_path: str = "/home/kyj/.openclaw/workspace/dss_data"):
        self.base_path = base_path
        self.versions_path = os.path.join(base_path, "_versions")
        self.corrections_path = os.path.join(base_path, "_corrections")
        self.lineage_path = os.path.join(base_path, "_lineage")
        self.data_path = os.path.join(base_path, "data")
        
        # 创建目录
        for path in [self.versions_path, self.corrections_path, 
                     self.lineage_path, self.data_path]:
            os.makedirs(path, exist_ok=True)
        
        # 当前版本
        self.current_version: Optional[DataVersion] = None
        self._load_current_version()
    
    def _compute_hash(self, file_path: str) -> str:
        """计算文件SHA256哈希"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _compute_dataframe_hash(self, df: pd.DataFrame) -> str:
        """计算DataFrame哈希"""
        content = df.to_csv(index=False).encode('utf-8')
        return hashlib.sha256(content).hexdigest()
    
    def _load_current_version(self):
        """加载当前版本"""
        versions_file = os.path.join(self.versions_path, "versions.json")
        if os.path.exists(versions_file):
            with open(versions_file, 'r') as f:
                versions = json.load(f)
                if versions:
                    latest = versions[-1]
                    self.current_version = DataVersion(**latest)
    
    def _save_versions(self, versions: List[Dict]):
        """保存版本列表"""
        versions_file = os.path.join(self.versions_path, "versions.json")
        with open(versions_file, 'w') as f:
            json.dump(versions, f, indent=2)
    
    def create_version(
        self,
        trade_date: str,
        description: str = "",
        metadata: Dict = None
    ) -> DataVersion:
        """
        创建数据版本快照
        
        Args:
            trade_date: 交易日期 (YYYY-MM-DD)
            description: 版本描述
            metadata: 额外元数据
            
        Returns:
            DataVersion对象
        """
        timestamp = datetime.now().isoformat()
        version_id = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 计算所有数据文件的哈希
        data_hashes = []
        file_count = 0
        
        for root, dirs, files in os.walk(self.data_path):
            for f in files:
                if f.endswith(('.parquet', '.csv', '.json')):
                    file_path = os.path.join(root, f)
                    file_hash = self._compute_hash(file_path)
                    data_hashes.append({
                        'file': os.path.relpath(file_path, self.data_path),
                        'hash': file_hash
                    })
                    file_count += 1
        
        # 计算整体哈希
        combined = json.dumps(data_hashes, sort_keys=True)
        overall_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        # 创建版本记录
        version = DataVersion(
            version_id=version_id,
            timestamp=timestamp,
            trade_date=trade_date,
            data_hash=overall_hash,
            file_count=file_count,
            metadata={
                'description': description,
                'file_hashes': data_hashes,
                **(metadata or {})
            }
        )
        
        # 保存版本
        versions_file = os.path.join(self.versions_path, "versions.json")
        versions = []
        if os.path.exists(versions_file):
            with open(versions_file, 'r') as f:
                versions = json.load(f)
        
        versions.append(version.to_dict())
        self._save_versions(versions)
        
        # 创建版本快照目录
        version_dir = os.path.join(self.versions_path, version_id)
        os.makedirs(version_dir, exist_ok=True)
        
        # 复制元数据
        with open(os.path.join(version_dir, "metadata.json"), 'w') as f:
            json.dump(version.to_dict(), f, indent=2)
        
        self.current_version = version
        return version
    
    def list_versions(self) -> List[DataVersion]:
        """列出所有版本"""
        versions_file = os.path.join(self.versions_path, "versions.json")
        if not os.path.exists(versions_file):
            return []
        
        with open(versions_file, 'r') as f:
            versions = json.load(f)
        
        return [DataVersion(**v) for v in versions]
    
    def get_version(self, version_id: str) -> Optional[DataVersion]:
        """获取指定版本"""
        versions = self.list_versions()
        for v in versions:
            if v.version_id == version_id:
                return v
        return None
    
    def save_data(
        self,
        symbol: str,
        df: pd.DataFrame,
        trade_date: str,
        data_type: str = "price"
    ) -> Dict[str, Any]:
        """
        保存数据（追加模式）
        
        Args:
            symbol: 股票代码
            df: 数据DataFrame
            trade_date: 交易日期
            data_type: 数据类型
            
        Returns:
            保存信息（包含哈希）
        """
        # 按交易日期分区
        date_dir = os.path.join(self.data_path, f"trade_date={trade_date}")
        os.makedirs(date_dir, exist_ok=True)
        
        symbol_dir = os.path.join(date_dir, f"symbol={symbol}")
        os.makedirs(symbol_dir, exist_ok=True)
        
        # 计算哈希
        data_hash = self._compute_dataframe_hash(df)
        
        # 文件名包含哈希（内容寻址）
        file_name = f"{data_type}_{data_hash[:8]}.parquet"
        file_path = os.path.join(symbol_dir, file_name)
        
        # 如果文件已存在，跳过（幂等）
        if os.path.exists(file_path):
            return {
                'status': 'exists',
                'file_path': file_path,
                'hash': data_hash
            }
        
        # 保存为Parquet
        df.to_parquet(file_path, compression='zstd')
        
        # 保存元数据
        meta_path = os.path.join(symbol_dir, f"{data_type}_metadata.json")
        metadata = {
            'symbol': symbol,
            'trade_date': trade_date,
            'data_type': data_type,
            'hash': data_hash,
            'rows': len(df),
            'columns': list(df.columns),
            'timestamp': datetime.now().isoformat()
        }
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return {
            'status': 'created',
            'file_path': file_path,
            'hash': data_hash,
            'rows': len(df)
        }
    
    def add_correction(
        self,
        symbol: str,
        field: str,
        old_value: Any,
        new_value: Any,
        reason: str,
        trade_date: str = None
    ) -> CorrectionEntry:
        """
        添加更正记录
        
        Args:
            symbol: 股票代码
            field: 更正字段
            old_value: 原值
            new_value: 新值
            reason: 更正原因
            trade_date: 交易日期
            
        Returns:
            CorrectionEntry对象
        """
        correction_id = f"corr_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        correction = CorrectionEntry(
            correction_id=correction_id,
            timestamp=datetime.now().isoformat(),
            original_version=self.current_version.version_id if self.current_version else "unknown",
            field=field,
            symbol=symbol,
            old_value=old_value,
            new_value=new_value,
            reason=reason
        )
        
        # 保存更正记录
        corrections_file = os.path.join(self.corrections_path, "corrections.json")
        corrections = []
        if os.path.exists(corrections_file):
            with open(corrections_file, 'r') as f:
                corrections = json.load(f)
        
        corrections.append(correction.to_dict())
        
        with open(corrections_file, 'w') as f:
            json.dump(corrections, f, indent=2)
        
        return correction
    
    def list_corrections(self, symbol: str = None) -> List[CorrectionEntry]:
        """列出更正记录"""
        corrections_file = os.path.join(self.corrections_path, "corrections.json")
        if not os.path.exists(corrections_file):
            return []
        
        with open(corrections_file, 'r') as f:
            corrections = json.load(f)
        
        result = [CorrectionEntry(**c) for c in corrections]
        
        if symbol:
            result = [c for c in result if c.symbol == symbol]
        
        return result
    
    def add_lineage(
        self,
        name: str,
        node_type: str,
        input_nodes: List[str] = None,
        transform_params: Dict = None
    ) -> LineageNode:
        """
        添加血缘节点
        
        Args:
            name: 节点名称
            node_type: 节点类型 (source/transform/output)
            input_nodes: 输入节点ID列表
            transform_params: 转换参数
            
        Returns:
            LineageNode对象
        """
        timestamp = datetime.now().isoformat()
        node_id = f"node_{hashlib.md5(f'{name}{timestamp}'.encode()).hexdigest()[:12]}"
        
        node = LineageNode(
            node_id=node_id,
            node_type=node_type,
            name=name,
            input_nodes=input_nodes or [],
            output_nodes=[],
            transform_params=transform_params or {},
            timestamp=timestamp
        )
        
        # 更新输入节点的输出列表
        if input_nodes:
            lineage_file = os.path.join(self.lineage_path, "lineage.json")
            lineage = {}
            if os.path.exists(lineage_file):
                with open(lineage_file, 'r') as f:
                    lineage = json.load(f)
            
            for input_id in input_nodes:
                if input_id in lineage:
                    lineage[input_id]['output_nodes'].append(node_id)
            
            with open(lineage_file, 'w') as f:
                json.dump(lineage, f, indent=2)
        
        # 保存节点
        lineage_file = os.path.join(self.lineage_path, "lineage.json")
        lineage = {}
        if os.path.exists(lineage_file):
            with open(lineage_file, 'r') as f:
                lineage = json.load(f)
        
        lineage[node_id] = node.to_dict()
        
        with open(lineage_file, 'w') as f:
            json.dump(lineage, f, indent=2)
        
        return node
    
    def get_lineage(self, node_id: str = None) -> Dict[str, LineageNode]:
        """获取血缘图"""
        lineage_file = os.path.join(self.lineage_path, "lineage.json")
        if not os.path.exists(lineage_file):
            return {}
        
        with open(lineage_file, 'r') as f:
            lineage = json.load(f)
        
        result = {k: LineageNode(**v) for k, v in lineage.items()}
        
        if node_id:
            return {k: v for k, v in result.items() if k == node_id}
        
        return result
    
    def trace_lineage(self, node_id: str) -> List[LineageNode]:
        """追溯血缘链"""
        lineage = self.get_lineage()
        result = []
        
        def trace(nid):
            if nid in lineage:
                node = lineage[nid]
                result.append(node)
                for input_id in node.input_nodes:
                    trace(input_id)
        
        trace(node_id)
        return result
    
    def verify_data(self, file_path: str) -> Dict[str, Any]:
        """验证数据完整性"""
        if not os.path.exists(file_path):
            return {'valid': False, 'error': 'File not found'}
        
        # 计算当前哈希
        current_hash = self._compute_hash(file_path)
        
        # 查找元数据中的哈希
        rel_path = os.path.relpath(file_path, self.data_path)
        
        if self.current_version and self.current_version.metadata:
            file_hashes = self.current_version.metadata.get('file_hashes', [])
            for fh in file_hashes:
                if fh['file'] == rel_path:
                    expected_hash = fh['hash']
                    return {
                        'valid': current_hash == expected_hash,
                        'current_hash': current_hash,
                        'expected_hash': expected_hash,
                        'file': rel_path
                    }
        
        return {'valid': True, 'hash': current_hash, 'file': rel_path}
    
    def get_audit_trail(self, symbol: str = None) -> Dict[str, Any]:
        """获取审计追踪"""
        versions = self.list_versions()
        corrections = self.list_corrections(symbol)
        lineage = self.get_lineage()
        
        return {
            'versions': [v.to_dict() for v in versions],
            'corrections': [c.to_dict() for c in corrections],
            'lineage_nodes': len(lineage),
            'generated_at': datetime.now().isoformat()
        }


# 便捷函数
def create_financial_store(base_path: str = None) -> FinancialDataStore:
    """创建金融数据存储"""
    if base_path is None:
        base_path = "/home/kyj/.openclaw/workspace/dss_data"
    return FinancialDataStore(base_path)