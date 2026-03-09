"""
检索问题诊断脚本
用于定位为什么检索不到已有的地名
"""

import pandas as pd
from config import Config
import opencc
import jieba
from rank_bm25 import BM25Okapi

print("="*60)
print("🔍 检索问题诊断")
print("="*60)

# 1. 检查CSV数据
print("\n[1] 检查CSV数据")
print("-"*60)

df = pd.read_csv(Config.BATCH_CLASSIFICATION, encoding='utf-8-sig').fillna("")

print(f"CSV总行数: {len(df)}")
print(f"\nCSV列名: {df.columns.tolist()}")
print(f"\n前5行数据:")
print(df.head())

# 检查"思鄉城"是否存在
print("\n[2] 检查'思鄉城'是否在CSV中")
print("-"*60)

search_placename = "思鄉城"
matches = df[df['placename'].str.contains(search_placename, na=False)]

if len(matches) > 0:
    print(f"✅ 找到 {len(matches)} 条记录")
    for idx, row in matches.iterrows():
        print(f"\n记录 {idx}:")
        print(f"  placename: {row['placename']}")
        print(f"  text: {row['text'][:50]}...")
        print(f"  source: {row['source']}")
        print(f"  resolution_type: {row['resolution_type']}")
        print(f"  evidence: {row.get('evidence', 'N/A')}")
else:
    print(f"❌ 在CSV中找不到 '{search_placename}'")
    
    # 尝试模糊搜索
    print("\n尝试模糊搜索（包含'思'的地名）:")
    fuzzy = df[df['placename'].str.contains('思', na=False)]
    if len(fuzzy) > 0:
        print(f"找到 {len(fuzzy)} 条:")
        for idx, row in fuzzy.head(5).iterrows():
            print(f"  - {row['placename']}")
    else:
        print("没有找到包含'思'的地名")

# 3. 检查过滤后的数据
print("\n[3] 检查resolution_type过滤")
print("-"*60)

print(f"STRONG类记录数: {len(df[df['resolution_type'] == 'STRONG'])}")
print(f"WEAK类记录数: {len(df[df['resolution_type'] == 'WEAK'])}")
print(f"NONE类记录数: {len(df[df['resolution_type'] == 'NONE'])}")

filtered_df = df[df['resolution_type'].isin(['STRONG', 'WEAK'])]
print(f"\n过滤后记录数: {len(filtered_df)}")

# 检查"思鄉城"是否在过滤后的数据中
matches_filtered = filtered_df[filtered_df['placename'].str.contains(search_placename, na=False)]
if len(matches_filtered) > 0:
    print(f"✅ '思鄉城'在过滤后的数据中")
else:
    print(f"❌ '思鄉城'不在过滤后的数据中（被过滤掉了！）")
    
    # 显示这条记录的resolution_type
    original = df[df['placename'].str.contains(search_placename, na=False)]
    if len(original) > 0:
        print(f"   原因: resolution_type = '{original.iloc[0]['resolution_type']}'")

# 4. 检查繁简转换
print("\n[4] 检查繁简转换")
print("-"*60)

converter = opencc.OpenCC('t2s')

test_query = "思鄉城為什麼叫這個"
converted_query = converter.convert(test_query)

print(f"原始查询: {test_query}")
print(f"转换后: {converted_query}")

test_placename = "思鄉城"
converted_placename = converter.convert(test_placename)
print(f"\n原始地名: {test_placename}")
print(f"转换后: {converted_placename}")

# 5. 测试BM25检索
print("\n[5] 测试BM25检索")
print("-"*60)

if len(filtered_df) > 0:
    # 构建BM25索引
    tokenized_docs = []
    docs = []
    
    for idx, row in filtered_df.iterrows():
        placename_norm = converter.convert(row['placename'])
        text_norm = converter.convert(row['text'])
        combined = f"{placename_norm} {text_norm}"
        tokens = list(jieba.cut(combined))
        
        tokenized_docs.append(tokens)
        docs.append(row.to_dict())
    
    bm25 = BM25Okapi(tokenized_docs)
    
    # 测试查询
    query_tokens = list(jieba.cut(converted_query))
    print(f"查询分词: {query_tokens}")
    
    scores = bm25.get_scores(query_tokens)
    top_10_indices = scores.argsort()[-10:][::-1]
    
    print(f"\nBM25 Top 10结果:")
    for i, idx in enumerate(top_10_indices, 1):
        doc = docs[idx]
        score = scores[idx]
        print(f"{i}. {doc['placename'][:20]:20s} (分数: {score:.2f})")
        
        # 特别标记"思鄉城"
        if '思' in doc['placename']:
            print(f"   ⭐ 包含'思'！")
else:
    print("❌ 过滤后没有数据，无法测试BM25")

# 6. 检查向量库
print("\n[6] 检查FAISS向量库")
print("-"*60)

import os
if os.path.exists(Config.FAISS_INDEX_PATH):
    print(f"✅ 向量库存在: {Config.FAISS_INDEX_PATH}")
    
    # 重建向量库建议
    print("\n⚠️  如果数据已更新，建议删除旧向量库重建:")
    print(f"   rm -rf {Config.FAISS_INDEX_PATH}")
    print(f"   然后重新运行RAG系统")
else:
    print(f"❌ 向量库不存在: {Config.FAISS_INDEX_PATH}")

print("\n" + "="*60)
print("诊断完成！")
print("="*60)