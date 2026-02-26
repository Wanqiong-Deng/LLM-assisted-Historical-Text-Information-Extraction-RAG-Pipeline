import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re

sns.set_theme(style="whitegrid")
plt.rcParams['axes.unicode_minus'] = False 

def run_analysis():
    input_file = "batch_classification_results.csv"
    if not os.path.exists(input_file):
        print("Error: Input file not found.")
        return

    df = pd.read_csv(input_file).fillna("")
    
    print("Generating Category Pie Chart...")
    plt.figure(figsize=(10, 8))
    counts = df['resolution_type'].value_counts()
    plt.pie(counts, labels=counts.index, autopct='%1.1f%%', startangle=140, 
            colors=sns.color_palette("muted"), textprops={'fontsize': 14})
    plt.title("Distribution of Placename Explanations", fontsize=16, fontweight='bold')
    plt.savefig("stat_category_pie.png", dpi=300)
    plt.close()

    print("Generating Length Distribution Boxplot...")
    df['text_len'] = df['text'].astype(str).apply(len)
    
    plt.figure(figsize=(10, 6))
    sns.boxplot(x='resolution_type', y='text_len', data=df, palette="Set2")
    plt.title("Text Length Distribution by Category", fontsize=16, fontweight='bold')
    plt.xlabel("Category Label", fontsize=12)
    plt.ylabel("Character Length", fontsize=12)
    plt.savefig("stat_length_boxplot.png", dpi=300)
    plt.close()

    print("Generating Sub-type Bar Chart...")
    strong_df = df[df['resolution_type'] == 'STRONG'].copy()
    
    def sub_classify(text):
        if not isinstance(text, str): return "Other"
        if re.search(r"山|岭|峰|岩", text): return "Mountain"
        if re.search(r"水|河|江|川|溪|池", text): return "Hydrology"
        if re.search(r"人|王|公|姓|氏", text): return "Person/Clan"
        if re.search(r"故|旧|改|徙", text): return "Admin/History"
        return "Other"

    strong_df['sub_type'] = strong_df['text'].apply(sub_classify)
    sub_counts = strong_df['sub_type'].value_counts()
    
    plt.figure(figsize=(12, 7))
    sns.barplot(x=sub_counts.index, y=sub_counts.values, palette="viridis")
    plt.title("Sub-categories of STRONG Explanations", fontsize=16, fontweight='bold')
    plt.xlabel("Naming Logic Pattern", fontsize=12)
    plt.ylabel("Number of Records", fontsize=12)
    plt.xticks(rotation=15) 
    plt.savefig("stat_strong_subtypes.png", dpi=300)
    plt.close()

    summary = df.groupby('resolution_type').agg({
        'placename': 'count',
        'text_len': 'mean'
    }).rename(columns={'placename': 'Count', 'text_len': 'Avg_Length'})
    summary.to_csv("analysis_summary_en.csv")
    
    print("\nAnalysis Complete! Files generated:")
    print("1. analysis_summary_en.csv")
    print("2. stat_category_pie.png")
    print("3. stat_length_boxplot.png")
    print("4. stat_strong_subtypes.png")

if __name__ == "__main__":
    run_analysis()