"""
Step 4: 数据分析器（增强版）
新增功能：
1. 生成RAG友好的结构化洞察文档
2. 将统计数据转换为自然语言描述
3. 提供可查询的数据摘要
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
import json
from config import Config


@dataclass
class AnalysisInsight:
    """分析洞察数据类"""
    category: str  # 洞察类别（如：分布统计、子类分析等）
    title: str  # 洞察标题
    content: str  # 自然语言描述
    data: dict  # 结构化数据
    

class EnhancedDataAnalyzer:
    """增强版数据分析器 - 生成RAG可用的洞察"""
    
    def __init__(self, input_file: str, output_dir: str = "results"):
        """
        初始化分析器
        
        Args:
            input_file: 输入CSV文件（batch_classification_results.csv）
            output_dir: 输出目录
        """
        self.input_file = input_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 加载数据
        self.df = pd.read_csv(input_file, encoding='utf-8-sig').fillna("")
        self.df['text_len'] = self.df['text'].astype(str).apply(len)
        
        # 设置绘图风格
        sns.set_theme(style="whitegrid")
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC', 'SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 存储生成的洞察
        self.insights: List[AnalysisInsight] = []
    
    def run_full_analysis(self):
        """运行完整分析流程"""
        print("🔍 开始数据分析...")
        
        # 1. 基础统计
        self._analyze_basic_distribution()
        
        # 2. STRONG类深度分析
        self._analyze_strong_subtypes()
        
        # 3. WEAK类引证分析
        self._analyze_weak_sources()
        
        # 4. NONE类描述分析
        self._analyze_none_focus()
        
        # 5. 综合统计
        self._analyze_comprehensive_stats()
        
        # 6. 生成可视化
        self._generate_visualizations()
        
        # 7. 导出RAG友好的文档
        self._export_rag_documents()
        
        print(f"✅ 分析完成！已生成 {len(self.insights)} 条洞察")
    
    def _analyze_basic_distribution(self):
        """分析基础分布"""
        counts = self.df['resolution_type'].value_counts()
        total = len(self.df)
        
        # 生成自然语言描述
        content = f"""数据集总体分布概况：

本数据集共包含 {total} 条地名记录，分类分布如下：

"""
        for label, count in counts.items():
            pct = (count / total * 100)
            content += f"• **{label}类**：{count} 条（{pct:.1f}%）\n"
        
        # 添加解释
        content += """

分类说明：
- **STRONG类**：作者直接陈述的命名解释，明确标注"因...故名"等因果关系
- **WEAK类**：引用他人说法或典籍记载的命名解释
- **NONE类**：仅包含地理位置、距离、行政沿革等描述，不涉及命名原因
"""
        
        self.insights.append(AnalysisInsight(
            category="基础统计",
            title="地名记录分类分布",
            content=content,
            data=counts.to_dict()
        ))
    
    def _analyze_strong_subtypes(self):
        """分析STRONG类的命名逻辑子类"""
        strong_df = self.df[self.df['resolution_type'] == 'STRONG'].copy()
        
        if len(strong_df) == 0:
            return
        
        # 定义子类型分类逻辑
        def get_strong_subtype(text):
            if re.search(r"山|岭|峰|岩|岳|冈", text):
                return "自然山岳"
            if re.search(r"水|河|江|川|溪|池|湖|潭|源", text):
                return "自然水文"
            if re.search(r"人|王|公|姓|氏|皇|后|妃", text):
                return "人物姓氏"
            if re.search(r"故|旧|改|徙|废|罢|新置", text):
                return "历史沿革"
            if re.search(r"取.*?之义|取.*?名之|以.*?为名", text):
                return "抽象语义"
            return "其他"
        
        strong_df['logic_type'] = strong_df['text'].apply(get_strong_subtype)
        logic_counts = strong_df['logic_type'].value_counts()
        
        # 生成自然语言描述
        content = f"""STRONG类命名逻辑深度分析：

在 {len(strong_df)} 条明确命名解释中，命名逻辑分布如下：

"""
        for logic, count in logic_counts.items():
            pct = (count / len(strong_df) * 100)
            content += f"• **{logic}型命名**：{count} 条（{pct:.1f}%）\n"
        
        # 添加典型案例（如果有）
        content += "\n**典型案例**：\n"
        for logic in logic_counts.head(3).index:
            examples = strong_df[strong_df['logic_type'] == logic].head(2)
            for _, ex in examples.iterrows():
                content += f"- 【{ex['placename']}】{ex['text'][:50]}...\n"
        
        self.insights.append(AnalysisInsight(
            category="STRONG类分析",
            title="命名逻辑类型分布",
            content=content,
            data=logic_counts.to_dict()
        ))
        
        # 保存详细CSV
        strong_logic_report = pd.DataFrame({
            '数量': logic_counts,
            '百分比(%)': (logic_counts / len(strong_df) * 100).round(2)
        })
        strong_logic_report.to_csv(
            self.output_dir / "mining_strong_logic.csv",
            encoding='utf-8-sig'
        )
    
    def _analyze_weak_sources(self):
        """分析WEAK类的引证特征"""
        weak_df = self.df[self.df['resolution_type'] == 'WEAK'].copy()
        
        if len(weak_df) == 0:
            return
        
        # 定义引证类型
        def get_weak_source(text):
            if re.search(r"《.*?》", text):
                return "书证引用"
            if re.search(r"云|曰|谓之", text):
                return "口传记载"
            if re.search(r"按|注|据", text):
                return "考据注释"
            if re.search(r"相传|传说", text):
                return "民间传说"
            return "其他引证"
        
        weak_df['source_type'] = weak_df['text'].apply(get_weak_source)
        source_counts = weak_df['source_type'].value_counts()
        
        # 生成自然语言描述
        content = f"""WEAK类引证方式分析：

在 {len(weak_df)} 条间接命名解释中，引证方式分布如下：

"""
        for source, count in source_counts.items():
            pct = (count / len(weak_df) * 100)
            content += f"• **{source}**：{count} 条（{pct:.1f}%）\n"
        
        content += """

这表明古代地名记载具有明显的引证传统，作者往往不直接断言，而是通过引用典籍、记录传说等方式呈现命名信息。
"""
        
        self.insights.append(AnalysisInsight(
            category="WEAK类分析",
            title="引证方式特征",
            content=content,
            data=source_counts.to_dict()
        ))
    
    def _analyze_none_focus(self):
        """分析NONE类的描述维度"""
        none_df = self.df[self.df['resolution_type'] == 'NONE'].copy()
        
        if len(none_df) == 0:
            return
        
        # 定义描述重点
        def get_none_focus(text):
            if re.search(r"\d+里|\d+步|距离|远近", text):
                return "空间距离"
            if re.search(r"\d+户|\d+口|民|租|调", text):
                return "户籍经济"
            if re.search(r"东|西|南|北|至", text):
                return "四至方位"
            if re.search(r"置|废|改为|属", text):
                return "政区变更"
            return "地理特征"
        
        none_df['focus_type'] = none_df['text'].apply(get_none_focus)
        focus_counts = none_df['focus_type'].value_counts()
        
        # 生成自然语言描述
        content = f"""NONE类描述维度分析：

在 {len(none_df)} 条非命名解释记录中，描述重点分布如下：

"""
        for focus, count in focus_counts.items():
            pct = (count / len(none_df) * 100)
            content += f"• **{focus}**：{count} 条（{pct:.1f}%）\n"
        
        content += """

这些记录虽不包含命名原因，但提供了丰富的地理、行政、经济等背景信息。
"""
        
        self.insights.append(AnalysisInsight(
            category="NONE类分析",
            title="描述维度分布",
            content=content,
            data=focus_counts.to_dict()
        ))
    
    def _analyze_comprehensive_stats(self):
        """综合统计分析"""
        # 文本长度统计
        length_stats = self.df.groupby('resolution_type')['text_len'].agg([
            ('平均长度', 'mean'),
            ('最短', 'min'),
            ('最长', 'max'),
            ('中位数', 'median')
        ]).round(1)
        
        content = """文本长度综合统计：

各类别记录的平均文本长度如下：

"""
        for label, row in length_stats.iterrows():
            content += f"• **{label}类**：平均 {row['平均长度']:.0f} 字（范围：{row['最短']:.0f}-{row['最长']:.0f}字）\n"
        
        # 来源文献分布
        source_counts = self.df['source'].value_counts().head(10)
        content += f"\n数据来源文献分布（Top 10）：\n\n"
        for source, count in source_counts.items():
            content += f"• {source}：{count} 条\n"
        
        self.insights.append(AnalysisInsight(
            category="综合统计",
            title="文本长度与来源分布",
            content=content,
            data={
                "length_stats": length_stats.to_dict(),
                "top_sources": source_counts.to_dict()
            }
        ))
        
        # 保存统计摘要
        summary = self.df.groupby('resolution_type').agg({
            'placename': 'count',
            'text_len': 'mean'
        }).rename(columns={'placename': 'Count', 'text_len': 'Avg_Length'})
        summary.to_csv(self.output_dir / "analysis_summary.csv", encoding='utf-8-sig')
    
    def _generate_visualizations(self):
        """生成可视化图表"""
        print("📊 正在生成可视化图表...")
        
        # 1. 分类分布饼图
        plt.figure(figsize=(10, 8))
        counts = self.df['resolution_type'].value_counts()
        plt.pie(counts, labels=counts.index, autopct='%1.1f%%', 
                startangle=140, colors=sns.color_palette("pastel"))
        plt.title("地名记录分类分布", fontsize=16, fontweight='bold')
        plt.savefig(self.output_dir / "stat_category_pie.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. 文本长度箱线图
        plt.figure(figsize=(10, 6))
        sns.boxplot(x='resolution_type', y='text_len', data=self.df, palette="Set2")
        plt.title("各类别文本长度分布", fontsize=16, fontweight='bold')
        plt.xlabel("分类标签", fontsize=12)
        plt.ylabel("字符长度", fontsize=12)
        plt.savefig(self.output_dir / "stat_length_boxplot.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. 三合一深度分析图
        fig, axes = plt.subplots(1, 3, figsize=(20, 7))
        
        # STRONG子类型
        strong_df = self.df[self.df['resolution_type'] == 'STRONG'].copy()
        if len(strong_df) > 0:
            strong_df['logic_type'] = strong_df['text'].apply(self._get_strong_subtype_simple)
            logic_counts = strong_df['logic_type'].value_counts()
            sns.barplot(x=logic_counts.index, y=logic_counts.values, 
                       ax=axes[0], palette="viridis")
            axes[0].set_title("STRONG类：命名逻辑分布", fontsize=14)
            axes[0].tick_params(axis='x', rotation=45)
        
        # WEAK引证方式
        weak_df = self.df[self.df['resolution_type'] == 'WEAK'].copy()
        if len(weak_df) > 0:
            weak_df['source_type'] = weak_df['text'].apply(self._get_weak_source_simple)
            weak_counts = weak_df['source_type'].value_counts()
            axes[1].pie(weak_counts, labels=weak_counts.index, 
                       autopct='%1.1f%%', startangle=140,
                       colors=sns.color_palette("pastel"))
            axes[1].set_title("WEAK类：引证方式", fontsize=14)
        
        # NONE描述重点
        none_df = self.df[self.df['resolution_type'] == 'NONE'].copy()
        if len(none_df) > 0:
            none_df['focus_type'] = none_df['text'].apply(self._get_none_focus_simple)
            none_counts = none_df['focus_type'].value_counts()
            sns.barplot(x=none_counts.index, y=none_counts.values, 
                       ax=axes[2], palette="magma")
            axes[2].set_title("NONE类：描述重点", fontsize=14)
            axes[2].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "mining_deep_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("可视化图表已生成")
    
    def _export_rag_documents(self):
        """导出RAG友好的文档"""
        print("📄 正在生成RAG知识库文档...")
        
        # 1. 导出为单个Markdown文档
        md_content = "# 古籍地名数据分析报告\n\n"
        md_content += f"生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md_content += "---\n\n"
        
        for insight in self.insights:
            md_content += f"## {insight.title}\n\n"
            md_content += f"**类别**: {insight.category}\n\n"
            md_content += insight.content
            md_content += "\n\n---\n\n"
        
        with open(self.output_dir / "analysis_insights.md", "w", encoding="utf-8") as f:
            f.write(md_content)
        
        # 2. 导出为JSON（结构化数据）
        insights_json = [
            {
                "category": insight.category,
                "title": insight.title,
                "content": insight.content,
                "data": insight.data
            }
            for insight in self.insights
        ]
        
        with open(self.output_dir / "analysis_insights.json", "w", encoding="utf-8") as f:
            json.dump(insights_json, f, ensure_ascii=False, indent=2)
        
        # 3. 导出为CSV（供RAG直接加载）
        insights_df = pd.DataFrame([
            {
                "category": insight.category,
                "title": insight.title,
                "content": insight.content
            }
            for insight in self.insights
        ])
        insights_df.to_csv(
            self.output_dir / "analysis_insights.csv",
            index=False,
            encoding='utf-8-sig'
        )
        
        print("RAG知识库文档已生成:")
        print(f"  • {self.output_dir / 'analysis_insights.md'}")
        print(f"  • {self.output_dir / 'analysis_insights.json'}")
        print(f"  • {self.output_dir / 'analysis_insights.csv'}")
    
    # 辅助方法（简化版分类函数）
    def _get_strong_subtype_simple(self, text):
        if re.search(r"山|岭|峰|岩|岳|冈", text): return "自然山岳"
        if re.search(r"水|河|江|川|溪|池|湖|潭|源", text): return "自然水文"
        if re.search(r"人|王|公|姓|氏|皇|后|妃", text): return "人物姓氏"
        if re.search(r"故|旧|改|徙|废|罢|新置", text): return "历史沿革"
        if re.search(r"取.*?之义|取.*?名之|以.*?为名", text): return "抽象语义"
        return "其他"
    
    def _get_weak_source_simple(self, text):
        if re.search(r"《.*?》", text): return "书证引用"
        if re.search(r"云|曰|谓之", text): return "口传记载"
        if re.search(r"按|注|据", text): return "考据注释"
        return "其他引证"
    
    def _get_none_focus_simple(self, text):
        if re.search(r"\d+里|\d+步|距离|远近", text): return "空间距离"
        if re.search(r"\d+户|\d+口|民|租|调", text): return "户籍经济"
        if re.search(r"东|西|南|北|至", text): return "四至方位"
        if re.search(r"置|废|改为|属", text): return "政区变更"
        return "地理特征"


def main():
    """主函数"""
    input_file = "batch_classification_results.csv"
    
    if not os.path.exists(input_file):
        print(f"❌ 错误：未找到文件 {input_file}")
        return
    
    analyzer = EnhancedDataAnalyzer(input_file)
    analyzer.run_full_analysis()
    
    print("\n" + "="*60)
    print("分析完成！文件已保存至 results/ 目录")
    print("="*60)


if __name__ == "__main__":
    main()