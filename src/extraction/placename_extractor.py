import re
import csv
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
from config import Config

@dataclass
class PlaceNameRecord:
    """地名记录数据类"""
    placename: str
    text: str
    source: str

class PlaceNameExtractor:
    """地名提取器"""
    
    # 类级别的常量
    DYNASTIES = ["漢", "魏", "晉", "隋", "唐", "宋", "元", "明", "清", "秦", "齊", "梁", "周", "後漢", "元魏", "北齊"]
    ADMIN_LEVELS = ["郡", "州", "府", "道", "路"]
    PREFIX_VERBS = ["置", "改", "分", "析", "移", "隸", "屬", "并", "於", "在", "本", "舊", "今", "尋", "此"]
    STOP_START_WORDS = ["在", "及", "与", "之", "其", "此", "旧", "从", "至", "界", "有", "谓"]
    PLACE_SUFFIXES = ["縣", "州", "郡", "府", "道", "山", "水", "河", "川", "原", "谷", "城", "關", "津", "坡", "陵", "宮", "溪", "岩", "潭"]
    
    def __init__(self, input_dir: str):
        self.input_dir = Path(input_dir)
    
    def clean_line_start(self, line: str) -> str:
        """
        清理行首的朝代、行政区划、动词等前缀
        这是核心的前处理步骤，去除干扰信息
        """
        # 1. 去除行首数字
        line = re.sub(r"^\d+\s*", "", line).strip()
        
        # 2. 迭代去除朝代、行政区划、动词前缀
        max_iterations = 10  
        iteration = 0
        
        while iteration < max_iterations:
            original = line
            
            # 去除朝代
            for dynasty in self.DYNASTIES:
                if line.startswith(dynasty):
                    line = line[len(dynasty):].lstrip(" ；，。")
            
            # 去除行政区划（如"某某郡"）
            for admin in self.ADMIN_LEVELS:
                match = re.match(rf"^[一-龥]{{1,2}}{admin}", line)
                if match:
                    line = line[len(match.group(0)):].lstrip(" ；，。")
            
            # 去除动词前缀
            for verb in self.PREFIX_VERBS:
                if line.startswith(verb):
                    line = line[len(verb):].lstrip(" ；，。")
            
            # 如果没有变化，说明清理完成
            if original == line:
                break
            
            iteration += 1
        
        return line
    
    def extract_valid_placename(self, line: str) -> Optional[str]:
        """
        从清理后的行中提取有效地名
        
        返回:
            有效地名或None
        """
        cleaned_start = self.clean_line_start(line)
        if not cleaned_start:
            return None
        
        # 查找后缀词
        for suffix in self.PLACE_SUFFIXES:
            if suffix not in cleaned_start:
                continue
            
            idx = cleaned_start.find(suffix)
            potential_name = cleaned_start[:idx+1]
            
            # 验证1: 长度必须在2-3之间
            if not (2 <= len(potential_name) <= 3):
                continue
            
            # 验证2: 不能以停用词开头
            if any(potential_name.startswith(w) for w in self.STOP_START_WORDS):
                continue
            
            # 验证3: 检查后面的内容
            after_name = cleaned_start[idx+1:]
            if after_name and not re.match(r"^[，。；\s]", after_name):
                # 如果紧跟方位词，可能是"某某县南"之类的描述，跳过
                if any(after_name.startswith(dir_word) for dir_word in ["南", "北", "西", "东", "治", "界"]):
                    continue
            
            return potential_name
        
        return None
    
    def extract_from_directory(self) -> List[PlaceNameRecord]:
        """
        从目录中提取所有地名记录
        
        返回:
            PlaceNameRecord列表
        """
        aggregated_data = {}
        
        # 按文件名数字排序
        files = sorted(
            [f for f in self.input_dir.iterdir() if f.suffix == ".txt"],
            key=lambda x: int(x.stem) if x.stem.isdigit() else x.stem
        )
        
        for fname in files:
            print(f"处理文件: {fname.name}")
            last_place = None
            
            with open(fname, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 尝试提取地名
                    p_name = self.extract_valid_placename(line)
                    
                    if p_name:
                        # 发现新地名，更新当前地名
                        last_place = p_name
                        # 提取地名后的内容
                        content_start_idx = line.find(p_name) + len(p_name)
                        content = line[content_start_idx:].lstrip("，。； ")
                        
                        # 使用(地名, 来源文件)作为key，避免不同文件中的同名地名冲突
                        key = (last_place, fname.name)
                        if key not in aggregated_data:
                            aggregated_data[key] = []
                        if content:
                            aggregated_data[key].append(content)
                    
                    elif last_place:
                        # 没有新地名，但有当前地名，这行属于上一个地名的延续
                        aggregated_data[(last_place, fname.name)].append(line)
        
        # 转换为PlaceNameRecord对象
        records = []
        for (name, src), texts in aggregated_data.items():
            # 去重并合并文本
            combined_text = " ".join(dict.fromkeys(texts))
            
            if combined_text:  # 只保留有内容的记录
                records.append(PlaceNameRecord(
                    placename=name,
                    text=combined_text,
                    source=src
                ))
        
        return records
    
    
    def validate_and_resolve(self, record: PlaceNameRecord) -> Optional[PlaceNameRecord]:
        """验证并解析地名目标"""
        text = record.text
        original = record.placename
        
        # 从文本中重新提取候选地名
        pattern = re.compile(rf"([一-龥]{{1,2}}(?:{'|'.join(self.PLACE_SUFFIXES)}))")
        candidates = pattern.findall(text)
        
        # 过滤有效候选
        valid_candidates = [
            c for c in candidates 
            if self.is_valid_placename(c)
        ]
        
        # 选择最佳地名
        if valid_candidates:
            if original not in valid_candidates or not self.is_valid_placename(original):
                record.placename = valid_candidates[0]
        
        # 如果最终地名无效，返回None
        if not self.is_valid_placename(record.placename):
            return None
        
        return record

    def is_valid_placename(self, name: str) -> bool:
        """验证地名是否有效"""
        if not (2 <= len(name) <= 4):
            return False
        if any(name.startswith(w) for w in self.STOP_START_WORDS):
            return False
        if not any(name.endswith(s) for s in self.PLACE_SUFFIXES):
            return False
        return True

    def save_to_csv(self, records: List[PlaceNameRecord], output_file: str):
        """保存记录到CSV"""
        with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["placename", "text", "source"])
            for record in records:
                writer.writerow([record.placename, record.text, record.source])
        
        print(f"已保存 {len(records)} 条记录到 {output_file}")

def main():
    INPUT_DIR = Config.DATABASE_DIR
    OUTPUT_CSV = Config.PLACENAME_RECORDS
    
    extractor = PlaceNameExtractor(INPUT_DIR)
    records = extractor.extract_from_directory()
    extractor.save_to_csv(records, OUTPUT_CSV)

if __name__ == "__main__":
    main()