"""
研究工具模块 - 完整版
包含5个工具：
1. literature_source_lookup - 文献溯源（修复：动态获取source）
2. place_name_evolution - 地名演变
3. disambiguate_placenames - 同名消歧
4. find_related_places - 相关推荐
5. data_visualization - 数据可视化（新增：统计分析+画图）
6. export_academic_report - 学术报告导出
"""

import pandas as pd
import opencc
import jieba
import re
from typing import Dict, Any, List
from langsmith import traceable
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px


class ResearchTools:
    """研究者工具集 - 5个专业工具"""
    
    def __init__(self, data_csv: str):
        self.df = pd.read_csv(data_csv, encoding='utf-8-sig').fillna("")
        self.converter_t2s = opencc.OpenCC('t2s')
    
    def _normalize_text(self, text: str) -> str:
        """繁简统一"""
        return self.converter_t2s.convert(text)
    
    # ==================== Tool 1: 文献溯源（修复版）====================
    
    @traceable(name="Tool_Literature_Source")
    def literature_source_lookup(self, placename: str) -> Dict[str, Any]:
        """
        文献溯源工具 - 动态获取source，不硬编码
        查找某个地名在所有古籍中的出处
        
        Args:
            placename: 地名
        
        Returns:
            包含文献来源信息的字典
        """
        placename_normalized = self._normalize_text(placename)
        
        matches = self.df[
            self.df['placename'].apply(lambda x: self._normalize_text(x)) == placename_normalized
        ]
        
        if len(matches) == 0:
            return {
                "found": False,
                "message": f"未找到地名 '{placename}' 的文献记录"
            }
        
        # 🔥 修复：动态获取source，不硬编码"大清一统志"
        sources = matches['source'].value_counts().to_dict()
        
        # 详细的source信息
        source_info = []
        for source, count in sources.items():
            source_info.append({
                "source_name": source,  # 实际的文献名称
                "count": count,
                "percentage": f"{count/len(matches)*100:.1f}%"
            })
        
        # 排序（按数量降序）
        source_info = sorted(source_info, key=lambda x: x['count'], reverse=True)
        
        result = {
            "found": True,
            "placename": placename,
            "total_records": len(matches),
            "sources": source_info,  # 动态获取的文献列表
            "resolution_types": matches['resolution_type'].value_counts().to_dict(),
            "sample_records": matches.head(3)[['text', 'source', 'resolution_type']].to_dict('records')
        }
        
        return result
    
    # ==================== Tool 2: 地名演变 ====================
    
    @traceable(name="Tool_Place_Evolution")
    def place_name_evolution(self, placename: str) -> Dict[str, Any]:
        """
        地名演变工具
        分析地名在历史上的演变
        """
        placename_normalized = self._normalize_text(placename)
        
        matches = self.df[
            self.df['placename'].apply(lambda x: self._normalize_text(x)) == placename_normalized
        ]
        
        if len(matches) == 0:
            return {
                "found": False,
                "message": f"未找到地名 '{placename}' 的演变记录"
            }
        
        evolution_records = []
        for _, row in matches.iterrows():
            text = row['text']
            dynasties = self._extract_dynasties(text)
            evolution_records.append({
                "text": text,
                "source": row['source'],
                "dynasties": dynasties,
                "resolution_type": row['resolution_type']
            })
        
        return {
            "found": True,
            "placename": placename,
            "evolution_records": evolution_records,
            "total_mentions": len(matches),
            "dynasties_involved": list(set([d for record in evolution_records for d in record['dynasties']]))
        }
    
    def _extract_dynasties(self, text: str) -> List[str]:
        """从文本中提取朝代信息"""
        dynasties = []
        dynasty_patterns = [
            '秦', '汉', '魏', '晋', '隋', '唐', '宋', '元', '明', '清',
            '三国', '南北朝', '五代', '十国'
        ]
        for dynasty in dynasty_patterns:
            if dynasty in text:
                dynasties.append(dynasty)
        return dynasties
    

    # ==================== Tool 5: 数据可视化（新增）====================
    
    @traceable(name="Tool_Data_Visualization")
    def data_visualization(self, query: str) -> Dict[str, Any]:
        """
        数据可视化工具 - 智能识别用户query并生成图表
        
        识别模式：
        - "占比"/"比例"/"分布" + "STRONG/WEAK/NONE" → resolution_distribution（饼图）
        - "文献"/"来源"/"出处" + "分布" → source_distribution（柱状图）
        - "朝代" + "分布" → dynasty_distribution（柱状图）
        - "后缀"/"类型" + "分布" → placename_suffix（柱状图）
        
        Args:
            query: 用户查询
        
        Returns:
            包含统计数据和图表HTML的字典
        """
        # 智能识别用户意图
        analysis_type = self._detect_analysis_type(query)
        
        if analysis_type == "resolution_distribution":
            return self._plot_resolution_distribution()
        
        elif analysis_type == "source_distribution":
            return self._plot_source_distribution()
        
        elif analysis_type == "dynasty_distribution":
            return self._plot_dynasty_distribution()
        
        elif analysis_type == "placename_suffix":
            return self._plot_placename_suffix()
        
        else:
            # 默认返回resolution_distribution
            return self._plot_resolution_distribution()
    
    def _detect_analysis_type(self, query: str) -> str:
        """检测用户想要的分析类型"""
        query_lower = query.lower()
        
        # STRONG/WEAK/NONE占比
        if any(word in query for word in ["strong", "weak", "none", "占比", "比例", "类型分布", "分类"]):
            return "resolution_distribution"
        
        # 文献分布
        if any(word in query for word in ["文献", "来源", "出处"]):
            return "source_distribution"
        
        # 朝代分布
        if "朝代" in query:
            return "dynasty_distribution"
        
        # 后缀分布
        if any(word in query for word in ["后缀", "县", "州", "府", "城"]):
            return "placename_suffix"
        
        # 默认
        return "resolution_distribution"
    
    def _plot_resolution_distribution(self) -> Dict[str, Any]:
        """STRONG/WEAK/NONE占比 - 饼状图"""
        resolution_counts = self.df['resolution_type'].value_counts()
        
        # 创建饼状图
        fig = go.Figure(data=[go.Pie(
            labels=resolution_counts.index,
            values=resolution_counts.values,
            hole=0.3,
            marker=dict(colors=['#2ecc71', '#f39c12', '#95a5a6']),
            textinfo='label+percent',
            textfont_size=14
        )])
        
        fig.update_layout(
            title="地名记载类型分布 (STRONG/WEAK/NONE)",
            font=dict(size=12),
            showlegend=True,
            height=400
        )
        
        # 转为HTML
        plot_html = fig.to_html(include_plotlyjs='cdn', div_id='resolution_plot')
        
        return {
            "analysis_type": "resolution_distribution",
            "data": resolution_counts.to_dict(),
            "total": len(self.df),
            "plot_html": plot_html,
            "summary": f"STRONG: {resolution_counts.get('STRONG', 0)}条 ({resolution_counts.get('STRONG', 0)/len(self.df)*100:.1f}%), "
                      f"WEAK: {resolution_counts.get('WEAK', 0)}条 ({resolution_counts.get('WEAK', 0)/len(self.df)*100:.1f}%), "
                      f"NONE: {resolution_counts.get('NONE', 0)}条 ({resolution_counts.get('NONE', 0)/len(self.df)*100:.1f}%)"
        }
    
    def _plot_source_distribution(self) -> Dict[str, Any]:
        """文献来源分布 - 柱状图"""
        source_counts = self.df['source'].value_counts().head(10)
        
        fig = go.Figure(data=[go.Bar(
            x=source_counts.index,
            y=source_counts.values,
            marker_color='#3498db',
            text=source_counts.values,
            textposition='auto'
        )])
        
        fig.update_layout(
            title="文献来源分布（Top 10）",
            xaxis_title="文献来源",
            yaxis_title="记载数量",
            font=dict(size=12),
            height=400,
            xaxis=dict(tickangle=-45)
        )
        
        plot_html = fig.to_html(include_plotlyjs='cdn', div_id='source_plot')
        
        return {
            "analysis_type": "source_distribution",
            "data": source_counts.to_dict(),
            "total_sources": len(self.df['source'].unique()),
            "plot_html": plot_html,
            "summary": f"共有{len(self.df['source'].unique())}个不同的文献来源"
        }
    
    def _plot_dynasty_distribution(self) -> Dict[str, Any]:
        """朝代分布 - 柱状图"""
        dynasty_patterns = ['秦', '汉', '魏', '晋', '隋', '唐', '宋', '元', '明', '清']
        dynasty_counts = {}
        
        for dynasty in dynasty_patterns:
            count = self.df['text'].str.contains(dynasty, na=False).sum()
            if count > 0:
                dynasty_counts[dynasty] = count
        
        if not dynasty_counts:
            return {
                "error": True,
                "message": "未找到朝代相关信息"
            }
        
        sorted_dynasties = sorted(dynasty_counts.items(), key=lambda x: x[1], reverse=True)
        labels, values = zip(*sorted_dynasties)
        
        fig = go.Figure(data=[go.Bar(
            x=labels,
            y=values,
            marker_color='#e74c3c',
            text=values,
            textposition='auto'
        )])
        
        fig.update_layout(
            title="朝代提及频次分布",
            xaxis_title="朝代",
            yaxis_title="提及次数",
            font=dict(size=12),
            height=400
        )
        
        plot_html = fig.to_html(include_plotlyjs='cdn', div_id='dynasty_plot')
        
        return {
            "analysis_type": "dynasty_distribution",
            "data": dynasty_counts,
            "plot_html": plot_html,
            "summary": f"涉及{len(dynasty_counts)}个朝代，共提及{sum(dynasty_counts.values())}次"
        }
    
    def _plot_placename_suffix(self) -> Dict[str, Any]:
        """地名后缀分布 - 柱状图"""
        suffixes = ['城', '县', '州', '府', '郡', '道', '关', '镇', '堡', '营']
        suffix_counts = {}
        
        for suffix in suffixes:
            count = self.df['placename'].str.contains(suffix, na=False).sum()
            if count > 0:
                suffix_counts[suffix] = count
        
        if not suffix_counts:
            return {
                "error": True,
                "message": "未找到地名后缀信息"
            }
        
        sorted_suffixes = sorted(suffix_counts.items(), key=lambda x: x[1], reverse=True)
        labels, values = zip(*sorted_suffixes)
        
        fig = go.Figure(data=[go.Bar(
            x=labels,
            y=values,
            marker_color='#9b59b6',
            text=values,
            textposition='auto'
        )])
        
        fig.update_layout(
            title="地名后缀分布",
            xaxis_title="后缀",
            yaxis_title="数量",
            font=dict(size=12),
            height=400
        )
        
        plot_html = fig.to_html(include_plotlyjs='cdn', div_id='suffix_plot')
        
        return {
            "analysis_type": "placename_suffix",
            "data": suffix_counts,
            "plot_html": plot_html,
            "summary": f"共有{sum(suffix_counts.values())}个带后缀的地名，涉及{len(suffix_counts)}种后缀"
        }
    
    # ==================== Tool 6: 学术报告导出 ====================
    
    @traceable(name="Tool_Export_Report")
    def export_academic_report(self, query_history: List[Dict], format: str = "markdown") -> Dict[str, Any]:
        """
        学术报告导出工具
        将查询历史导出为学术格式报告
        """
        if format == "markdown":
            report = self._generate_markdown_report(query_history)
        else:
            report = self._generate_plain_report(query_history)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"place_name_research_report_{timestamp}.md"
        
        return {
            "format": format,
            "filename": filename,
            "content": report,
            "message": f"报告已生成：{filename}"
        }
    
    def _generate_markdown_report(self, query_history: List[Dict]) -> str:
        """生成Markdown格式报告"""
        report = f"""# 古籍地名研究报告

**生成时间**: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}

---

## 研究摘要

本报告基于对古籍地名数据库的查询，包含{len(query_history)}个研究问题的详细分析。

---

## 研究内容

"""
        
        for i, item in enumerate(query_history, 1):
            report += f"""
### {i}. {item.get('content', '未记录的查询')}

**查询时间**: {item.get('timestamp', '未知')}

**分析结果**:

{item.get('content', '无答案记录')}

---
"""
        
        report += """
## 研究说明

- 本报告数据来源于古籍地名数据库
- 分类标准：STRONG（明确命名解释）、WEAK（引证他人）、NONE（无命名解释）

---

*本报告由古籍地名RAG系统自动生成*
"""
        
        return report
    
    def _generate_plain_report(self, query_history: List[Dict]) -> str:
        """生成纯文本格式报告"""
        report = "=" * 60 + "\n"
        report += "古籍地名研究报告\n"
        report += "=" * 60 + "\n\n"
        
        for i, item in enumerate(query_history, 1):
            report += f"{i}. {item.get('content', '未记录')}\n"
            report += f"   时间: {item.get('timestamp', '未知')}\n\n"
        
        return report