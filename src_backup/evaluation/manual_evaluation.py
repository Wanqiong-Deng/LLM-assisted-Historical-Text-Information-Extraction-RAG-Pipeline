import pandas as pd
import os
import re

INPUT_FILES = {
    "STRONG": "extracted_STRONG.csv",
    "WEAK": "extracted_WEAK.csv", 
    "NONE": "extracted_NONE.csv"
}
SAMPLE_FRAC = 0.02  
OUTPUT_FILE = "labeled_results.csv"

def clean_display_name(name):
    """即时清洗显示用的地名，剔除动词和朝代杂质"""
    if not isinstance(name, str):
        return str(name)
    
    noise_prefixes = r"^(置|改為|改|分|析|移|隸|屬|并入|界有|於|在|本|舊|今|隋|漢|元魏|北齊)+"
    clean_name = re.sub(noise_prefixes, "", name)
    clean_name = re.sub(r"(隋|漢|後|元魏).*", "", clean_name) if "縣" not in clean_name else clean_name
    return clean_name.replace("隋曰上縣", "").replace("隋縣", "").strip()

def load_and_sample(input_files_dict):
    """从多个文件加载并抽样"""
    results = {}
    
    for label, file_path in input_files_dict.items():
        if not os.path.exists(file_path):
            print(f"警告：找不到文件 {file_path}")
            continue
            
        df = pd.read_csv(file_path)
        
        if 'text' not in df.columns:
            print(f"警告：{file_path} 中没有 'text' 列")
            continue
        
        df['text'] = df['text'].fillna("")
        if 'placename' in df.columns:
            df['placename'] = df['placename'].fillna("未知")
        
        if len(df) > 0:
            sample_size = max(1, int(len(df) * SAMPLE_FRAC))
            sample = df.sample(n=min(sample_size, len(df)), random_state=42)
            sample['resolution_type'] = label  
            results[label] = sample
            print(f"加载 {label}: {len(df)} 条记录 -> 抽样 {len(sample)} 条")
        else:
            print(f"警告：文件 {file_path} 中没有数据")
            
    return results

def start_human_labeling(results_dict):
    final_dfs = []
    global_counter = 1 # 全局序号
    
    for label, df in results_dict.items():
        print(f"\n" + "="*30)
        print(f" 正在评估类别: {label} (样本比例: {SAMPLE_FRAC*100}%, 实取: {len(df)}条)")
        print("="*30)

        human_labels = []
        for i, row in df.iterrows():
            if 'placename' in row:
                display_name = clean_display_name(row['placename'])
            elif 'name' in row:
                display_name = clean_display_name(row['name'])
            else:
                display_name = "未知"
            
            display_text = str(row['text']).replace('\n', ' ').strip()
            display_text = re.sub(r"\s+\d+\s*$", "", display_text) 
            source = row['source'] if 'source' in row else "未知来源"

            print(f"\n{global_counter}. **【{display_name}】** {display_text[:250]} ({source})")
            
            while True:
                try:
                    val = input("是否为命名解释？(1=是, 0=否, s=跳过): ").strip().lower()
                    if val == 's':
                        y = 0 
                        break
                    y = int(val)
                    if y in [0, 1]: break
                except ValueError:
                    print("输入无效，请输入 1 或 0")
            
            human_labels.append(y)
            global_counter += 1

        df["human_label"] = human_labels
        df["system_pred"] = 1 if label != "NONE" else 0
        final_dfs.append(df)
        
    return pd.concat(final_dfs, ignore_index=True) if final_dfs else None

def calculate_metrics(full_df):
    if full_df is None or len(full_df) == 0: 
        print("没有数据可评估")
        return
    
    print("\n" + "绩效评估报告".center(40, "="))
    
    for label in ["STRONG", "WEAK", "NONE"]:
        df_sub = full_df[full_df['resolution_type'] == label]
        if len(df_sub) == 0: 
            print(f"[{label}] 没有数据")
            continue
        
        total = len(df_sub)
        
        if label in ["STRONG", "WEAK"]:
            # 对于 STRONG 和 WEAK，计算准确率
            tp = sum((df_sub["human_label"] == 1))
            prec = tp / total if total > 0 else 0
            print(f"[{label}] Precision (准确率): {round(prec, 3)} ({tp}/{total})")
            
        else:  
            fn = sum((df_sub["human_label"] == 1))
            fnr = fn / total if total > 0 else 0
            print(f"[{label}] False Negative Rate (漏报/误判率): {round(fnr, 3)} ({fn}/{total})")
    

    print("\n" + "总体统计".center(40, "-"))
    total_samples = len(full_df)
    total_human_yes = sum(full_df["human_label"] == 1)
    total_system_yes = sum(full_df["system_pred"] == 1)
    
    print(f"总样本数: {total_samples}")
    print(f"人工标注为命名解释: {total_human_yes}")
    print(f"系统预测为命名解释: {total_system_yes}")

if __name__ == "__main__":
    missing_files = []
    for label, file_path in INPUT_FILES.items():
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("以下文件不存在:")
        for f in missing_files:
            print(f"  - {f}")
        print("请确保文件在当前目录下。")
    else:
        sampled_data = load_and_sample(INPUT_FILES)
        
        if sampled_data:
            labeled_df = start_human_labeling(sampled_data)
            if labeled_df is not None:
                calculate_metrics(labeled_df)
                labeled_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
                print(f"\n标注完成！结果已保存至: {OUTPUT_FILE}")