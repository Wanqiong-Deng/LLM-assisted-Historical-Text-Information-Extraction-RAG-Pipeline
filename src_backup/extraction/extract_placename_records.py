import os
import re
import csv

INPUT_DIR = ""
OUTPUT_CSV = "placename..........................................................................................................................>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>_records.csv"

DYNASTIES = ["漢", "魏", "晉", "隋", "唐", "宋", "元", "明", "清", "秦", "齊", "梁", "周", "後漢", "元魏", "北齊"]
ADMIN_LEVELS = ["郡", "州", "府", "道", "路"]
PREFIX_VERBS = ["置", "改", "分", "析", "移", "隸", "屬", "并", "於", "在", "本", "舊", "今", "尋", "此"]
STOP_START_WORDS = ["在", "及", "与", "与", "之", "其", "此", "旧", "从", "至", "界", "有", "谓"]
PLACE_SUFFIXES = ["縣", "州", "郡", "府", "道", "山", "水", "河", "川", "原", "谷", "城", "關", "津", "坡", "陵", "宮", "溪", "岩", "潭"]

def clean_line_start(line):
    line = re.sub(r"^\d+\s*", "", line).strip()
    
    changed = True
    while changed:
        original = line
        for d in DYNASTIES:
            if line.startswith(d):
                line = line[len(d):].lstrip(" ；，。")
        for a in ADMIN_LEVELS:
            match = re.match(rf"^[一-龥]{{1,2}}{a}", line)
            if match:
                line = line[len(match.group(0)):].lstrip(" ；，。")
        for v in PREFIX_VERBS:
            if line.startswith(v):
                line = line[len(v):].lstrip(" ；，。")
        
        changed = (original != line)
    return line

def extract_valid_placename(line):
    cleaned_start = clean_line_start(line)
    if not cleaned_start: return None

    for suffix in PLACE_SUFFIXES:
        if suffix in cleaned_start:
            idx = cleaned_start.find(suffix)
            potential_name = cleaned_start[:idx+1]
            
            if not (2 <= len(potential_name) <= 3):
                continue

            if any(potential_name.startswith(w) for w in STOP_START_WORDS):
                continue

            after_name = cleaned_start[idx+1:]
            if after_name and not re.match(r"^[，。；\s]", after_name):
                if any(after_name.startswith(dir_word) for dir_word in ["南", "北", "西", "东", "治", "界"]):
                    continue
            
            return potential_name
    return None

def main():
    aggregated_data = {} 
    files = sorted([f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")], 
                   key=lambda x: int(x.replace(".txt", "")) if x.replace(".txt", "").isdigit() else x)

    for fname in files:
        last_place = None
        path = os.path.join(INPUT_DIR, fname)
        
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                
                p_name = extract_valid_placename(line)
                
                if p_name:
                    last_place = p_name
                    content_start_idx = line.find(p_name) + len(p_name)
                    content = line[content_start_idx:].lstrip("，。； ")
                    
                    key = (last_place, fname)
                    if key not in aggregated_data: aggregated_data[key] = []
                    if content: aggregated_data[key].append(content)
                elif last_place:
                    aggregated_data[(last_place, fname)].append(line)

    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["placename", "text", "source"])
        for (name, src), texts in aggregated_data.items():
            combined_text = " ".join(dict.fromkeys(texts))
            combined_text = re.sub(r"\b\d{2,4}\b", "", combined_text).strip()
            writer.writerow([name, combined_text, src])
            
    print(f"提取完成。通过前缀剥离与黑名单过滤，已大幅减少误判。")

if __name__ == "__main__":
    main()
