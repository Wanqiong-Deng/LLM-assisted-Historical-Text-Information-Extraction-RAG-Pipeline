import pandas as pd
import re
import os

INPUT_CSV = "placename_records.csv"
OUTPUT_CSV = "placename_records_resolved.csv"
PLACE_SUFFIXES = ["縣", "州", "郡", "府", "道", "山", "水", "河", "川", "原", "谷", "城", "關", "津", "坡", "陵", "宮", "溪", "岩", "潭"]
STOP_START_WORDS = ["在", "及", "与", "之", "其", "此", "旧", "从", "至", "界", "有", "谓"]

def is_valid_name(name):
    if not (2 <= len(name) <= 3):
        return False
    if any(name.startswith(w) for w in STOP_START_WORDS):
        return False
    if not any(name.endswith(s) for s in PLACE_SUFFIXES):
        return False
    return True

def resolve_target(row):
    text = str(row["text"])
    original = str(row["placename"])
    
    pattern = re.compile(rf"([一-龥]{{1,2}}(?:{'|'.join(PLACE_SUFFIXES)}))")
    candidates = pattern.findall(text)
    valid_candidates = [c for c in candidates if is_valid_name(c)]

    if valid_candidates:
        if original not in valid_candidates or not is_valid_name(original):
            return valid_candidates[0]
            
    return original if is_valid_name(original) else "未知"

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"错误：找不到 {INPUT_CSV}")
        return
        
    df = pd.read_csv(INPUT_CSV).fillna("")
    
    df["placename"] = df.apply(resolve_target, axis=1)
    
    df = df[df['placename'] != "未知"]
    

    final_df = df[["placename", "text", "source"]]
    final_df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print("完成：resolve_naming_target 已同步最新的过滤逻辑，剔除了方位词干扰。")

if __name__ == "__main__":
    main()