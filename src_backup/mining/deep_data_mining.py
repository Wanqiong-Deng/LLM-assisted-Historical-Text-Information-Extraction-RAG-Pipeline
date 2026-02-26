import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re
import os

plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid")

def deep_mining():
    input_file = "batch_classification_results.csv"
    if not os.path.exists(input_file):
        print("错误：未找到数据文件。")
        return
    
    df = pd.read_csv(input_file).fillna("")
    df['text_len'] = df['text'].astype(str).apply(len)

    print("正在挖掘 STRONG 类别的逻辑子类...")
    strong_df = df[df['resolution_type'] == 'STRONG'].copy()
    
    def get_strong_subtype(text):
        if re.search(r"山|岭|峰|岩|岳|冈", text): return "自然山岳"
        if re.search(r"水|河|江|川|溪|池|湖|潭|源", text): return "自然水文"
        if re.search(r"人|王|公|姓|氏|皇|后|妃", text): return "人物姓氏"
        if re.search(r"故|旧|改|徙|废|罢|徙|新置", text): return "历史沿革"
        if re.search(r"取.*?之义|取.*?名之|以.*?为名", text): return "抽象语义/取义"
        return "其他"

    strong_df['logic_type'] = strong_df['text'].apply(get_strong_subtype)
    strong_logic_counts = strong_df['logic_type'].value_counts()
    strong_logic_pct = (strong_logic_counts / len(strong_df) * 100).round(2)


    strong_logic_report = pd.DataFrame({
        '数量': strong_logic_counts,
        '百分比(%)': strong_logic_pct
    })
    strong_logic_report.to_csv("mining_strong_logic.csv", encoding='utf-8-sig')

    print("正在挖掘 WEAK 类别的引证特征...")
    weak_df = df[df['resolution_type'] == 'WEAK'].copy()
    
    def get_weak_source(text):
        if re.search(r"《.*?》", text): return "书证(带书名号)"
        if re.search(r"云|曰|谓之", text): return "口传/泛称"
        if re.search(r"按|注|据", text): return "考据注释"
        return "其他引证"

    weak_df['source_type'] = weak_df['text'].apply(get_weak_source)
    weak_counts = weak_df['source_type'].value_counts()
    

    print("正在挖掘 NONE 类别的描述维度...")
    none_df = df[df['resolution_type'] == 'NONE'].copy()

    def get_none_focus(text):
        if re.search(r"\d+?里|\d+?步|距离|远近", text): return "空间距离"
        if re.search(r"\d+?户|\d+?口|民|租|调", text): return "户籍经济"
        if re.search(r"东|西|南|北|至", text): return "四至方位"
        if re.search(r"置|废|改为|属", text): return "政区变更"
        return "纯地理特征"

    none_df['focus_type'] = none_df['text'].apply(get_none_focus)
    none_counts = none_df['focus_type'].value_counts()


    fig, axes = plt.subplots(1, 3, figsize=(20, 7))

    sns.barplot(x=strong_logic_counts.index, y=strong_logic_counts.values, ax=axes[0], palette="viridis")
    axes[0].set_title("STRONG 类：命名逻辑子类分布")
    axes[0].tick_params(axis='x', rotation=45)

    axes[1].pie(weak_counts, labels=weak_counts.index, autopct='%1.1f%%', startangle=140, colors=sns.color_palette("pastel"))
    axes[1].set_title("WEAK 类：引证方式特征")

    sns.barplot(x=none_counts.index, y=none_counts.values, ax=axes[2], palette="magma")
    axes[2].set_title("NONE 类：地理描述重点分布")
    axes[2].tick_params(axis='x', rotation=45)

    plt.tight_layout()
    plt.savefig("mining_deep_analysis.png", dpi=300)
    print("\n[成功] 深度挖掘完成。已生成：")
    print("1. mining_strong_logic.csv (STRONG类百分比详情)")
    print("2. mining_deep_analysis.png (三合一深度统计图)")

if __name__ == "__main__":
    deep_mining()