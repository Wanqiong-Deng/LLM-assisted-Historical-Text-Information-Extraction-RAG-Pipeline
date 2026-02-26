import pandas as pd 
import os
import time
import requests
import re
import json

os.environ["PYTHONIOENCODING"] = "utf-8"

INPUT_CSV = "placename_records_resolved.csv"
PROGRESS_FILE = "batch_classification_results.csv"
API_KEY = "sk-gswitcfpsevlgfleazpwptqtpuolngnbzqvtbkeuexeqiyid"
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
SELECTED_MODEL = 'deepseek-ai/DeepSeek-V3' 

STRONG_PATTERNS = [r"因.*?名之", r"因.*?為名", r"因.*?故名", r"以.*?為名", r"取.*?之義", r"取.*?名之", r"故名", r"故曰", r"改曰"]

SYSTEM_PROMPT = """你是一名历史地名学研究中的文本标注助手。

你的任务是判断【命名解释是否为作者本人的直接判断】，
而不是是否“文本中出现了解释”。

请特别注意【话语层级】与【引证来源】。

分类标准：

【STRONG】
满足以下全部条件：
1. 文本中明确给出地名命名原因（因、故、以、取、改曰等）。
2. 命名解释为作者直接陈述，而非转述。
3. 该句或其直接语境中【不存在】以下任何引证或转述标志：
   - 云、曰、注、按、谓、相传
   - 《书名》《志》《记》等典籍标记
   - 引号内的内容
4. 命名解释语句在语义上可独立成立，不依赖外部权威。

【WEAK】
满足以下任一条件：
1. 存在命名解释，但明确来源于：
   - 他人说法（云、曰、相传）
   - 作者按语（按、谨按）
   - 典籍引用（《》《》）
2. 命名逻辑嵌套在引文或转述中，即使形式上出现“因、故、以”等词。

【NONE】
仅包含以下内容之一：
- 地理位置、距离、方位
- 水系流向、山势描述
- 户数、行政沿革、建置时间
- 未出现任何命名因果关系

请严格区分【作者判断】与【作者记录他人说法】。

仅返回 JSON：
{
  "label": "STRONG | WEAK | NONE",
  "evidence": "直接支持该判断的原文片段"
}
"""

def check_strong_by_regex(text):
    for pat in STRONG_PATTERNS:
        if re.search(pat, text): return True
    return False

def call_api_single(placename, text):
    """单条调用，极高容错"""
    payload = {
        "model": SELECTED_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"地名：【{placename}】\n文本：{text[:120]}"}
        ],
        "temperature": 0
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    for attempt in range(2):
        try:
            response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
            if response.status_code != 200:
                time.sleep(2)
                continue
            
            content = response.json()['choices'][0]['message']['content']
            clean_json = re.search(r'\{.*\}', content, re.DOTALL)
            if clean_json:
                res = json.loads(clean_json.group())
                return res.get('label', 'NONE'), res.get('evidence', '')
        except:
            time.sleep(1)
    return "ERROR", "API_FAILED"

def main():
    if not os.path.exists(INPUT_CSV): return
    df = pd.read_csv(INPUT_CSV, encoding='utf-8-sig').fillna("")
    
    if os.path.exists(PROGRESS_FILE):
        processed_df = pd.read_csv(PROGRESS_FILE, encoding='utf-8-sig')
        processed_keys = set(processed_df['placename'] + processed_df['text'].str[:10])
        results = processed_df.to_dict('records')
    else:
        processed_keys = set()
        results = []

    print(f"已加载进度：{len(processed_keys)} 条。剩余待处理：{len(df)-len(processed_keys)} 条。")

    for idx, row in df.iterrows():
        key = row['placename'] + row['text'][:10]
        if key in processed_keys:
            continue

        placename = row['placename']
        text = row['text']
        
        if check_strong_by_regex(text):
            label, evidence, mode = "STRONG", "Regex Match", "[REGEX]"
        else:
            label, evidence = call_api_single(placename, text)
            mode = "[LLM  ]"
            time.sleep(0.6) # 稳健频率

        print(f"[{idx+1}/{len(df)}] {mode} {placename} -> {label}")
        
        res_row = row.to_dict()
        res_row.update({"resolution_type": label, "evidence": evidence})
        results.append(res_row)

        if (idx + 1) % 5 == 0:
            pd.DataFrame(results).to_csv(PROGRESS_FILE, index=False, encoding='utf-8-sig')

    full_df = pd.DataFrame(results)
    for l in ["STRONG", "WEAK", "NONE"]:
        full_df[full_df["resolution_type"] == l][["placename", "text", "source", "evidence"]].to_csv(f"extracted_{l}.csv", index=False, encoding='utf-8-sig')
    
    print("全部任务处理完毕。")

if __name__ == "__main__":
    main()