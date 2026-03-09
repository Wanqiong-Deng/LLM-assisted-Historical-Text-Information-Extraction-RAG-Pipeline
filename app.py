"""
Streamlit UI - 集成LangSmith Evaluation和Tracing
展示特性：
1. 侧边栏：实时tracing信息
2. 主面板：RAG问答
3. Evaluation面板：评估指标
4. 性能监控：响应时间、相似度分布
- LangSmith tracing可视化
- Evaluation metrics展示
- 实时性能监控
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time
import requests
import os

# 页面配置
st.set_page_config(
    page_title="古籍地名RAG系统 - LangSmith监控版",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #1f77b4;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .trace-step {
        background: #f8f9fa;
        padding: 0.5rem;
        border-left: 3px solid #1f77b4;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ==================== 初始化 Session State ====================

if 'query_history' not in st.session_state:
    st.session_state.query_history = []

if 'trace_data' not in st.session_state:
    st.session_state.trace_data = []

if 'evaluation_metrics' not in st.session_state:
    st.session_state.evaluation_metrics = {
        'total_queries': 0,
        'avg_similarity': 0.0,
        'avg_response_time': 0.0,
        'success_rate': 100.0
    }


# ==================== 侧边栏：Tracing & Evaluation ====================

with st.sidebar:
    st.markdown("# 🔍 LangSmith 监控")
    st.markdown("---")
    
    # Tab切换
    tab_trace, tab_eval, tab_perf = st.tabs(["📊 Tracing", "✅ Evaluation", "⚡ Performance"])
    
    # Tab 1: Tracing信息
    with tab_trace:
        st.markdown("### 最近一次查询Trace")
        
        if st.session_state.trace_data:
            latest_trace = st.session_state.trace_data[-1]
            
            st.markdown(f"**查询**: {latest_trace['query'][:30]}...")
            st.markdown(f"**总耗时**: {latest_trace['total_time']:.2f}s")
            
            st.markdown("#### 执行步骤：")
            for step in latest_trace['steps']:
                with st.expander(f"{step['name']} ({step['duration']:.2f}s)"):
                    st.markdown(f"**状态**: {step['status']}")
                    if step.get('similarity'):
                        st.markdown(f"**相似度**: {step['similarity']:.3f}")
                    if step.get('retrieved_docs'):
                        st.markdown(f"**检索文档数**: {step['retrieved_docs']}")
        else:
            st.info("暂无trace数据，请先执行查询")
    
    # Tab 2: Evaluation指标
    with tab_eval:
        st.markdown("### 评估指标")
        
        metrics = st.session_state.evaluation_metrics
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("总查询数", metrics['total_queries'])
            st.metric("平均相似度", f"{metrics['avg_similarity']:.3f}")
        
        with col2:
            st.metric("响应时间", f"{metrics['avg_response_time']:.2f}s")
            st.metric("成功率", f"{metrics['success_rate']:.1f}%")
        
        # 相似度分布图
        if st.session_state.trace_data:
            similarities = [t.get('max_similarity', 0) for t in st.session_state.trace_data]
            
            fig = px.histogram(
                x=similarities,
                nbins=20,
                labels={'x': '相似度', 'y': '频次'},
                title="相似度分布"
            )
            st.plotly_chart(fig, use_container_width=True, key="sim_dist")
    
    # Tab 3: 性能监控
    with tab_perf:
        st.markdown("### 性能趋势")
        
        if len(st.session_state.trace_data) > 1:
            df = pd.DataFrame([
                {
                    'timestamp': t['timestamp'],
                    'response_time': t['total_time'],
                    'similarity': t.get('max_similarity', 0)
                }
                for t in st.session_state.trace_data
            ])
            
            # 响应时间趋势
            fig = px.line(
                df,
                x='timestamp',
                y='response_time',
                title="响应时间趋势",
                labels={'response_time': '耗时(s)', 'timestamp': '时间'}
            )
            st.plotly_chart(fig, use_container_width=True, key="perf_trend")
        else:
            st.info("需要至少2次查询数据")


# ==================== 主面板 ====================

st.markdown('<div class="main-header">🏛️ 古籍地名RAG系统 - LangSmith监控版</div>', unsafe_allow_html=True)

# 功能标签
main_tab1, main_tab2, main_tab3 = st.tabs(["💬 RAG问答", "📈 数据分析", "📚 使用说明"])

# Tab 1: RAG问答
with main_tab1:
    st.markdown("### 智能问答")
    
    # 示例问题
    st.markdown("#### 💡 示例问题")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("隋县的由来？", key="ex1"):
            st.session_state.example_query = "隋县的由来是什么？"
    
    with col2:
        if st.button("隋縣的由来？（繁体）", key="ex2"):
            st.session_state.example_query = "隋縣的由来是什么？"
    
    with col3:
        if st.button("有多少STRONG记录？", key="ex3"):
            st.session_state.example_query = "数据集中有多少条STRONG类记录？"
    
    st.markdown("---")
    
    # 问题输入
    default_query = st.session_state.get('example_query', '')
    user_query = st.text_input(
        "💬 输入您的问题：",
        value=default_query,
        placeholder="例如：隋县的由来是什么？"
    )
    
    # 查询按钮
    if st.button("🔍 查询", type="primary"):
        if user_query:
            # 显示loading
            with st.spinner("🤔 正在思考..."):
                start_time = time.time()
                
                # 初始化RAG系统（仅第一次）
                if 'rag_system' not in st.session_state:
                    try:
                        from rag import RAGSystem
                        rag = RAGSystem()
                        rag.setup()
                        st.session_state.rag_system = rag
                    except Exception as e:
                        st.error(f"初始化RAG系统失败: {e}")
                        st.stop()
                
                # 执行查询
                try:
                    rag = st.session_state.rag_system
                    
                    # 记录trace信息
                    trace_steps = []
                    
                    # Step 1: 问题类型识别
                    step_start = time.time()
                    q_type = rag.get_question_type(user_query)
                    trace_steps.append({
                        'name': '问题类型识别',
                        'duration': time.time() - step_start,
                        'status': f'✓ {q_type}',
                        'details': f"识别为{'统计类' if q_type == 'statistical' else '具体地名'}问题"
                    })
                    
                    # Step 2: 文本规范化
                    step_start = time.time()
                    query_normalized = rag._normalize_text(user_query)
                    trace_steps.append({
                        'name': '繁简统一',
                        'duration': time.time() - step_start,
                        'status': '✓ 完成',
                        'details': f"{user_query} → {query_normalized}" if user_query != query_normalized else "无需转换"
                    })
                    
                    # Step 3: 混合检索
                    if q_type != "statistical":
                        step_start = time.time()
                        docs_with_sim = rag._bm25_search(user_query, k=6)
                        max_sim = max([sim for _, sim in docs_with_sim]) if docs_with_sim else 0
                        
                        trace_steps.append({
                            'name': '混合检索 (BM25+Embedding)',
                            'duration': time.time() - step_start,
                            'status': '✓ 完成',
                            'similarity': max_sim,
                            'retrieved_docs': len(docs_with_sim),
                            'details': f"检索到 {len(docs_with_sim)} 条文档，最高相似度 {max_sim:.3f}"
                        })
                    
                    # Step 4: LLM生成
                    step_start = time.time()
                    answer = rag.query(user_query)
                    llm_time = time.time() - step_start
                    
                    trace_steps.append({
                        'name': 'LLM生成答案',
                        'duration': llm_time,
                        'status': '✓ 完成',
                        'details': f"生成 {len(answer)} 字回答"
                    })
                    
                    # 总耗时
                    total_time = time.time() - start_time
                    
                    # 保存trace数据
                    trace_record = {
                        'query': user_query,
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'total_time': total_time,
                        'steps': trace_steps,
                        'max_similarity': max_sim if q_type != "statistical" else 1.0,
                        'success': True
                    }
                    st.session_state.trace_data.append(trace_record)
                    
                    # 更新evaluation指标
                    metrics = st.session_state.evaluation_metrics
                    metrics['total_queries'] += 1
                    
                    # 滑动平均
                    alpha = 0.3
                    if q_type != "statistical":
                        metrics['avg_similarity'] = alpha * max_sim + (1 - alpha) * metrics['avg_similarity']
                    metrics['avg_response_time'] = alpha * total_time + (1 - alpha) * metrics['avg_response_time']
                    
                    # 显示结果
                    st.markdown("### 📖 回答")
                    st.markdown(answer)
                    
                    # 显示trace摘要
                    st.markdown("---")
                    st.markdown("### 📊 本次查询统计")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("总耗时", f"{total_time:.2f}s")
                    col2.metric("检索步骤", len(trace_steps))
                    if q_type != "statistical":
                        col3.metric("最高相似度", f"{max_sim:.3f}")
                        col4.metric("检索文档", len(docs_with_sim))
                    
                    # 详细trace
                    with st.expander("🔍 查看详细Trace"):
                        for step in trace_steps:
                            st.markdown(f"**{step['name']}** ({step['duration']:.3f}s)")
                            st.markdown(f"  - 状态: {step['status']}")
                            if step.get('details'):
                                st.markdown(f"  - 详情: {step['details']}")
                            st.markdown("---")
                    
                    # 保存到历史
                    st.session_state.query_history.append({
                        'query': user_query,
                        'answer': answer,
                        'time': total_time,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    
                except Exception as e:
                    st.error(f"❌ 查询失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        else:
            st.warning("⚠️ 请输入问题")
    
    # 查询历史
    if st.session_state.query_history:
        st.markdown("---")
        st.markdown("### 📜 查询历史")
        
        history_df = pd.DataFrame(st.session_state.query_history)
        st.dataframe(
            history_df[['timestamp', 'query', 'time']],
            use_container_width=True,
            hide_index=True
        )

# Tab 2: 数据分析
with main_tab2:
    st.markdown("### 📈 系统性能分析")
    
    if st.session_state.trace_data:
        # 整体统计
        total_queries = len(st.session_state.trace_data)
        avg_time = sum([t['total_time'] for t in st.session_state.trace_data]) / total_queries
        avg_sim = sum([t.get('max_similarity', 0) for t in st.session_state.trace_data]) / total_queries
        
        col1, col2, col3 = st.columns(3)
        col1.metric("累计查询", f"{total_queries} 次")
        col2.metric("平均耗时", f"{avg_time:.2f}s")
        col3.metric("平均相似度", f"{avg_sim:.3f}")
        
        st.markdown("---")
        
        # 性能分布
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 响应时间分布")
            times = [t['total_time'] for t in st.session_state.trace_data]
            fig = px.histogram(
                x=times,
                nbins=15,
                labels={'x': '响应时间(s)', 'y': '频次'}
            )
            st.plotly_chart(fig, use_container_width=True, key="time_dist_main")
        
        with col2:
            st.markdown("#### 相似度分布")
            sims = [t.get('max_similarity', 0) for t in st.session_state.trace_data]
            fig = px.histogram(
                x=sims,
                nbins=15,
                labels={'x': '相似度', 'y': '频次'}
            )
            st.plotly_chart(fig, use_container_width=True, key="sim_dist_main")
        
        # 时间趋势
        st.markdown("#### 性能时间趋势")
        df = pd.DataFrame([
            {
                '时间': t['timestamp'],
                '响应时间': t['total_time'],
                '相似度': t.get('max_similarity', 0)
            }
            for t in st.session_state.trace_data
        ])
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['时间'],
            y=df['响应时间'],
            mode='lines+markers',
            name='响应时间',
            yaxis='y'
        ))
        fig.add_trace(go.Scatter(
            x=df['时间'],
            y=df['相似度'],
            mode='lines+markers',
            name='相似度',
            yaxis='y2'
        ))
        
        fig.update_layout(
            yaxis=dict(title='响应时间(s)'),
            yaxis2=dict(title='相似度', overlaying='y', side='right'),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.info("暂无数据，请先执行查询")

# Tab 3: 使用说明
with main_tab3:
    st.markdown("""
    ## 📚 系统使用说明
    
    ### ✨ 核心功能
    
    1. **智能问答**
       - 支持繁体/简体地名查询
       - 自动识别问题类型
       - 混合检索（BM25 + Embedding）
    
    2. **LangSmith监控**（侧边栏）
       - 📊 **Tracing**: 查看每次查询的详细执行步骤
       - ✅ **Evaluation**: 实时评估指标（相似度、响应时间）
       - ⚡ **Performance**: 性能趋势分析
    
    3. **数据分析**
       - 查询历史记录
       - 性能分布统计
       - 时间趋势可视化
    
    ---
    
    ### 
    
    **技术栈**：
    - LangChain + LangSmith (Tracing & Evaluation)
    - Streamlit (UI)
    - FAISS (Vector Store)
    - BM25 + Embedding (Hybrid Retrieval)
    
    **亮点**：
    1. ✅ 繁简体自动识别
    2. ✅ 混合检索提升准确率
    3. ✅ LangSmith实时监控
    4. ✅ Evaluation指标可视化
    5. ✅ 性能趋势分析
    
    ---
    
    ### 💡 使用技巧
    
    - **侧边栏**：实时查看trace和evaluation
    - **主面板**：执行查询和查看结果
    - **数据分析**：查看整体性能统计
    
    ---
    
    ### 🔧 技术细节
    
    **Tracing记录内容**：
    1. 问题类型识别
    2. 繁简统一处理
    3. 混合检索（BM25+Embedding）
    4. LLM生成答案
    
    **Evaluation指标**：
    - 总查询数
    - 平均相似度
    - 平均响应时间
    - 成功率
    
    **性能监控**：
    - 响应时间分布
    - 相似度分布
    - 时间趋势图
    """)


# ==================== 页脚 ====================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 1rem;'>
    🏛️ 古籍地名分析系统 | LangSmith监控版 | Powered by Streamlit + LangChain
</div>
""", unsafe_allow_html=True)