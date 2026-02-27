from dataclasses import dataclass
from typing import List, Dict
import pandas as pd
from config import Config

@dataclass
class EvaluationMetrics:
    """评估指标"""
    label: str
    total: int
    true_positive: int
    precision: float
    false_negative_rate: float = 0.0

class ManualEvaluator:
    """人工评估器"""
    
    def __init__(self, sample_frac: float = 0.02):
        self.sample_frac = sample_frac
    
    def load_samples(self, files_dict: Dict[str, str]) -> pd.DataFrame:
        """加载并合并样本"""
        dfs = []
        for label, file_path in files_dict.items():
            if not Path(file_path).exists():
                print(f"⚠️  文件不存在: {file_path}")
                continue
            
            df = pd.read_csv(file_path)
            sample_size = max(1, int(len(df) * self.sample_frac))
            sample = df.sample(n=min(sample_size, len(df)), random_state=42)
            sample['system_label'] = label
            dfs.append(sample)
        
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    
    def calculate_metrics(self, df: pd.DataFrame) -> List[EvaluationMetrics]:
        """计算评估指标"""
        metrics = []
        
        for label in df['system_label'].unique():
            subset = df[df['system_label'] == label]
            total = len(subset)
            tp = sum(subset['human_label'] == 1)
            
            if label in ["STRONG", "WEAK"]:
                precision = tp / total if total > 0 else 0
                metrics.append(EvaluationMetrics(
                    label=label,
                    total=total,
                    true_positive=tp,
                    precision=precision
                ))
            else: 
                fn = tp  
                fnr = fn / total if total > 0 else 0
                metrics.append(EvaluationMetrics(
                    label=label,
                    total=total,
                    true_positive=0,
                    precision=0,
                    false_negative_rate=fnr
                ))
        
        return metrics