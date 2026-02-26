"""
Step 3: LLM分类器（修正版）
修正：
1. 改进错误提示
2. 使用Config管理输入文件名
3. 更清晰的运行日志
"""

import pandas as pd 
import os
import time
import requests
import re
import json
from config import Config

# 设置环境
Config.setup_environment()

# 从Config获取配置
INPUT_CSV = Config.PLACENAME_RECORDS  
PROGRESS_FILE = Config.BATCH_CLASSIFICATION
API_KEY = Config.API_KEY
API_URL = Config.API_BASE_URL + "/chat/completions"
SELECTED_MODEL = Config.CLASSIFICATION_MODEL

STRONG_PATTERNS = Config.STRONG_PATTERNS

SYSTEM_PROMPT = """你是一名历史地名学研究中的文本标注助手。

你的任务是判断【命名解释是否为作者本人的直接判断】，
而不是是否"文本中出现了解释"。

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
2. 命名逻辑嵌套在引文或转述中，即使形式上出现"因、故、以"等词。

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
    """使用正则快速识别STRONG类"""
    for pat in STRONG_PATTERNS:
        if re.search(pat, text):
            return True
    return False


def call_api_single(placename, text):
    """单条调用API"""
    payload = {
        "model": SELECTED_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"地名：【{placename}】\n文本：{text[:120]}"}
        ],
        "temperature": 0
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
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
    """主函数"""
    print("="*60)
    print("古籍地名分类系统")
    print("="*60)
    
    # 显示配置
    print(f"\n📌 当前配置:")
    print(f"   输入文件: {INPUT_CSV}")
    print(f"   输出文件: {PROGRESS_FILE}")
    print(f"   使用模型: {SELECTED_MODEL}")
    print(f"   当前目录: {os.getcwd()}")
    
    # 检查输入文件（改进的错误提示）
    if not os.path.exists(INPUT_CSV):
        print(f"\n❌ 错误：找不到输入文件 {INPUT_CSV}")
        print(f"\n💡 可能的原因:")
        print(f"   1. 还没有运行 step2_placename_extractor.py")
        print(f"   2. 文件名不匹配")
        print(f"\n📁 当前目录的CSV文件:")
        csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
        if csv_files:
            for f in csv_files:
                print(f"   • {f}")
        else:
            print(f"   （没有CSV文件）")
        print(f"\n🔧 解决方案:")
        print(f"   方案1: 先运行 python step2_placename_extractor.py")
        print(f"   方案2: 修改代码中的 INPUT_CSV 为实际文件名")
        return
    
    # 加载数据
    print(f"\n📖 正在加载数据...")
    df = pd.read_csv(INPUT_CSV, encoding='utf-8-sig').fillna("")
    print(f"✓ 成功加载 {len(df)} 条记录")
    
    # 加载进度（断点续传）
    if os.path.exists(PROGRESS_FILE):
        print(f"✓ 检测到进度文件，加载已处理记录...")
        processed_df = pd.read_csv(PROGRESS_FILE, encoding='utf-8-sig')
        processed_keys = set(processed_df['placename'] + processed_df['text'].str[:10])
        results = processed_df.to_dict('records')
        print(f"✓ 已完成 {len(processed_keys)} 条")
    else:
        processed_keys = set()
        results = []
        print(f"✓ 从头开始处理")
    
    remaining = len(df) - len(processed_keys)
    print(f"📝 待处理: {remaining} 条")
    print("\n" + "="*60)
    
    if remaining == 0:
        print("✅ 所有记录已处理完成！")
        return

    # 处理数据
    for idx, row in df.iterrows():
        key = row['placename'] + row['text'][:10]
        if key in processed_keys:
            continue

        placename = row['placename']
        text = row['text']
        
        # 优先使用正则匹配（免费）
        if check_strong_by_regex(text):
            label, evidence, mode = "STRONG", "Regex Match", "[REGEX]"
        else:
            # 调用LLM
            label, evidence = call_api_single(placename, text)
            mode = "[LLM  ]"
            time.sleep(0.6)

        print(f"[{idx+1}/{len(df)}] {mode} {placename[:10]:10s} -> {label:6s}")
        
        res_row = row.to_dict()
        res_row.update({"resolution_type": label, "evidence": evidence})
        results.append(res_row)

        # 定期保存
        if (idx + 1) % 5 == 0:
            pd.DataFrame(results).to_csv(PROGRESS_FILE, index=False, encoding='utf-8-sig')

    # 最终保存
    print("\n📦 正在保存结果...")
    full_df = pd.DataFrame(results)
    full_df.to_csv(PROGRESS_FILE, index=False, encoding='utf-8-sig')
    
    # 按类型分别保存
    for l in ["STRONG", "WEAK", "NONE"]:
        subset = full_df[full_df["resolution_type"] == l]
        if len(subset) > 0:
            subset[["placename", "text", "source", "evidence"]].to_csv(
                f"extracted_{l}.csv",
                index=False,
                encoding='utf-8-sig'
            )
    
    # 显示统计
    print("\n" + "="*60)
    print("✅ 全部任务处理完毕")
    print("="*60)
    print(f"\n📊 分类统计:")
    for label in ["STRONG", "WEAK", "NONE", "ERROR"]:
        count = len(full_df[full_df["resolution_type"] == label])
        pct = count / len(full_df) * 100 if len(full_df) > 0 else 0
        print(f"   {label:6s}: {count:4d} 条 ({pct:5.1f}%)")
    
    print(f"\n💾 输出文件:")
    print(f"   • {PROGRESS_FILE}")
    print(f"   • extracted_STRONG.csv")
    print(f"   • extracted_WEAK.csv")
    print(f"   • extracted_NONE.csv")


if __name__ == "__main__":
    main()