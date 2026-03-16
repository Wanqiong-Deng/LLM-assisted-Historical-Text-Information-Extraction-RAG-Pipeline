"""
古籍地名RAG Agent - Streamlit UI (完整版)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_agent import RAGAgent

# ==================== Page Config ====================

st.set_page_config(
    page_title="古籍地名RAG Agent系统",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== Custom CSS ====================

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
    
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 20%;
    }
    
    .assistant-message {
        background: #f8f9fa;
        border-left: 4px solid #1f77b4;
        margin-right: 20%;
    }
    
    .workflow-node {
        background: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        border: 2px solid #ddd;
        margin: 0.5rem 0;
        display: inline-block;
    }
    
    .node-completed {
        border-color: #4caf50;
        background: #e8f5e9;
    }
    
    .tool-result {
        background: #fff3cd;
        padding: 0.8rem;
        border-left: 4px solid #ffc107;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== Session State Initialization ====================

def init_session_state():
    """初始化所有session state变量"""
    if 'agent_initialized' not in st.session_state:
        st.session_state.agent_initialized = False
    
    if 'conversation' not in st.session_state:
        st.session_state.conversation = []
    
    # 🔥 关键：独立的conversation_history用于Agent memory
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    
    if 'stats' not in st.session_state:
        st.session_state.stats = {
            'total_queries': 0,
            'guardrail_rejections': 0,
            'tools_used_count': {},
            'avg_confidence': []
        }

init_session_state()

# ==================== Helper Functions ====================

def format_workflow_steps(steps):
    """格式化workflow步骤为可视化展示"""
    html = "<div style='display: flex; align-items: center; overflow-x: auto; padding: 1rem;'>"
    
    for i, step in enumerate(steps):
        node_name = step.get('node', 'Unknown')
        timestamp = step.get('timestamp', '')
        
        node_class = 'node-completed'
        icon = '✅'
        
        html += f"""
        <div class='workflow-node {node_class}'>
            <div style='font-weight: bold;'>{icon} {node_name}</div>
            <div style='font-size: 0.8rem; color: #666;'>{timestamp.split('T')[1][:8] if 'T' in timestamp else ''}</div>
        </div>
        """
        
        if i < len(steps) - 1:
            html += "<div style='padding: 0 0.5rem; font-size: 1.5rem;'>→</div>"
    
    html += "</div>"
    return html


def display_tool_results(tool_results):
    """展示工具调用结果"""
    if not tool_results:
        return
    
    st.markdown("### 🧰 工具调用结果")
    
    for tool_name, result in tool_results.items():
        with st.expander(f"📊 {tool_name}", expanded=True):
            if isinstance(result, dict):
                if result.get('error'):
                    st.error(f"❌ {result.get('message', '工具执行失败')}")
                else:
                    # 🔥 特殊处理：data_visualization工具返回plot_html
                    if 'plot_html' in result:
                        st.markdown(f"**{result.get('summary', '')}**")
                        # 直接显示HTML图表
                        st.components.v1.html(result['plot_html'], height=500, scrolling=True)
                        
                        # 显示原始数据
                        if st.checkbox("显示原始数据", key=f"show_data_{tool_name}"):
                            st.json({k: v for k, v in result.items() if k != 'plot_html'})
                    else:
                        st.json(result)
            else:
                st.write(result)


def display_metadata(metadata):
    """展示查询元数据"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("意图类型", metadata.get('intent', '未知'))
    
    with col2:
        entities = metadata.get('entities', [])
        st.metric("提取实体", len(entities))
        if entities:
            st.caption(", ".join(entities))
    
    with col3:
        similarity = metadata.get('retrieval_similarity', 0)
        st.metric("检索相似度", f"{similarity:.3f}")
    
    with col4:
        confidence = metadata.get('answer_confidence', 0)
        st.metric("答案置信度", f"{confidence:.2f}")


def update_stats(metadata):
    """更新统计数据"""
    st.session_state.stats['total_queries'] += 1
    
    if metadata.get('guardrail_rejected'):
        st.session_state.stats['guardrail_rejections'] += 1
    
    for tool in metadata.get('tools_used', []):
        st.session_state.stats['tools_used_count'][tool] = \
            st.session_state.stats['tools_used_count'].get(tool, 0) + 1
    
    if 'answer_confidence' in metadata:
        st.session_state.stats['avg_confidence'].append(metadata['answer_confidence'])


def initialize_agent():
    """
    初始化Agent - 不使用缓存
    每次创建新Agent，但传入session_state.conversation_history作为引用
    """
    agent = RAGAgent(conversation_history=st.session_state.conversation_history)
    agent.setup()
    return agent

# ==================== Sidebar ====================

with st.sidebar:
    st.markdown("# 🤖 Agent控制台")
    st.markdown("---")
    
    # Agent状态
    if st.session_state.agent_initialized:
        st.success("✅ Agent已初始化")
    else:
        if st.button("🚀 初始化Agent", type="primary", use_container_width=True):
            with st.spinner("正在初始化Agent..."):
                try:
                    # 初始化一次测试
                    test_agent = initialize_agent()
                    st.session_state.agent_initialized = True
                    st.success("初始化成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"初始化失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    st.markdown("---")
    
    # 对话管理
    st.markdown("### 💭 对话管理")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 清除历史", use_container_width=True):
            st.session_state.conversation = []
            st.session_state.conversation_history = []
            st.success("历史已清除")
            st.rerun()
    
    with col2:
        if st.button("📊 导出报告", use_container_width=True):
            if st.session_state.conversation:
                st.info("报告导出功能开发中...")
    
    st.markdown(f"**对话轮数**: {len(st.session_state.conversation) // 2}")
    st.markdown(f"**Memory长度**: {len(st.session_state.conversation_history)} 条")
    
    # 显示Memory内容（调试用）
    if st.session_state.conversation_history:
        with st.expander("🔍 查看Memory详情"):
            for i, item in enumerate(st.session_state.conversation_history[-10:]):
                role_icon = "👤" if item['role'] == 'user' else "🤖"
                entities_str = str(item.get('entities', 'N/A'))
                st.caption(f"{role_icon} [{i+1}] {item['role']}: entities={entities_str}")
    
    st.markdown("---")
    
    # 统计信息
    st.markdown("### 📈 系统统计")
    
    stats = st.session_state.stats
    
    st.metric("总查询数", stats['total_queries'])
    st.metric("Guardrail拦截", stats['guardrail_rejections'])
    
    if stats['avg_confidence']:
        avg_conf = sum(stats['avg_confidence']) / len(stats['avg_confidence'])
        st.metric("平均置信度", f"{avg_conf:.2f}")
    
    # 工具使用统计
    if stats['tools_used_count']:
        st.markdown("#### 工具使用次数")
        for tool, count in stats['tools_used_count'].items():
            st.caption(f"• {tool}: {count}次")

# ==================== Main Content ====================

st.markdown('<div class="main-header">🏛️ 古籍地名RAG Agent系统</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💬 智能对话", "🔍 Workflow可视化", "📚 使用指南"])

# ==================== Tab 1: 智能对话 ====================

with tab1:
    # 显示对话历史
    chat_container = st.container()
    
    with chat_container:
        if not st.session_state.conversation:
            st.info("👋 欢迎使用古籍地名RAG Agent！请开始提问。")
            
            st.markdown("### 💡 示例问题")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📍 思鄉城的由来？", use_container_width=True):
                    st.session_state.example_query = "思鄉城的由来是什么？"
                    st.rerun()
            
            with col2:
                if st.button("📖 查思鄉城的文献出处", use_container_width=True):
                    st.session_state.example_query = "查找思鄉城在所有古籍中的文献出处"
                    st.rerun()
            
            with col3:
                if st.button("📊 分析'城'的命名模式", use_container_width=True):
                    st.session_state.example_query = "分析所有'城'的命名模式和规律"
                    st.rerun()
        
        else:
            # 显示历史对话
            for msg in st.session_state.conversation:
                with st.chat_message(msg['role']):
                    st.markdown(msg['content'])
                    
                    # 如果是assistant且有metadata
                    if msg['role'] == 'assistant' and 'metadata' in msg:
                        with st.expander("📊 查看详情"):
                            display_metadata(msg['metadata'])
                            
                            # 显示workflow流程
                            if 'processing_steps' in msg['metadata']:
                                st.markdown("#### 🔄 处理流程")
                                steps_html = format_workflow_steps(msg['metadata']['processing_steps'])
                                st.markdown(steps_html, unsafe_allow_html=True)
                            
                            # 显示工具结果
                            if msg.get('tool_results'):
                                display_tool_results(msg['tool_results'])
    
    st.markdown("---")
    
    # 输入区域
    if st.session_state.agent_initialized:
        # 获取示例查询
        default_query = st.session_state.pop('example_query', '')
        
        user_input = st.text_input(
            "💬 输入您的问题：",
            value=default_query,
            placeholder="例如：思鄉城的由来是什么？或查找思鄉城的文献出处",
            key="user_input"
        )
        
        col1, col2, col3 = st.columns([1, 1, 4])
        
        with col1:
            submit_button = st.button("🚀 发送", type="primary", use_container_width=True)
        
        with col2:
            if st.button("🔄 重新生成", use_container_width=True):
                if st.session_state.conversation and len(st.session_state.conversation) >= 2:
                    if st.session_state.conversation[-2]['role'] == 'user':
                        user_input = st.session_state.conversation[-2]['content']
                        submit_button = True
        
        if submit_button and user_input:
            # 添加用户消息到对话
            st.session_state.conversation.append({
                'role': 'user',
                'content': user_input,
                'timestamp': datetime.now().isoformat()
            })
            
            # 创建新Agent（不缓存，传入conversation_history引用）
            agent = initialize_agent()
            
            # 在chat_message内流式显示
            with st.chat_message("assistant"):
                answer_placeholder = st.empty()
                
                current_answer = ""
                final_state = None
                
                try:
                    # 处理streaming
                    for chunk in agent.query(user_input):
                        chunk_type = chunk.get("type")
                        
                        if chunk_type == "workflow_step":
                            # 可选：显示workflow进度
                            pass
                        
                        elif chunk_type == "answer_token":
                            # 实时更新答案（在对话框内）
                            current_answer = chunk["partial_answer"]
                            answer_placeholder.markdown(current_answer + " ▌")
                        
                        elif chunk_type == "final_state":
                            final_state = chunk["final_state"]
                            # 移除光标
                            answer_placeholder.markdown(current_answer)
                        
                        elif chunk_type == "guardrail_reject":
                            answer_placeholder.warning(chunk["message"])
                            final_state = chunk["final_state"]
                    
                    # 保存到conversation
                    if final_state:
                        assistant_msg = {
                            'role': 'assistant',
                            'content': current_answer or final_state.get("answer", ""),
                            'metadata': {
                                'intent': final_state.get('intent'),
                                'entities': final_state.get('extracted_entities', []),
                                'retrieval_similarity': final_state.get('retrieval_similarity', 0.0),
                                'answer_confidence': final_state.get('answer_confidence', 0.0),
                                'processing_steps': final_state.get('processing_steps', []),
                                'guardrail_rejected': not final_state.get('guardrail_passed', True),
                                'guardrail_message': final_state.get('guardrail_message'),
                                'tools_used': list(final_state.get('tool_results', {}).keys())
                            },
                            'tool_results': final_state.get('tool_results', {}),
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        st.session_state.conversation.append(assistant_msg)
                        
                        # 更新统计
                        update_stats(assistant_msg['metadata'])
                    
                    # 刷新页面以显示完整对话
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ 查询失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    else:
        st.warning("⚠️ 请先在侧边栏初始化Agent")

# ==================== Tab 2: Workflow可视化 ====================

with tab2:
    st.markdown("### 🔍 Agent Workflow可视化")
    
    if st.session_state.conversation:
        # 选择查询
        query_options = [
            f"Query {i//2 + 1}: {msg['content'][:50]}..."
            for i, msg in enumerate(st.session_state.conversation)
            if msg['role'] == 'user'
        ]
        
        selected_query = st.selectbox("选择查询", query_options)
        query_idx = query_options.index(selected_query) * 2 + 1
        
        if query_idx < len(st.session_state.conversation):
            assistant_msg = st.session_state.conversation[query_idx]
            metadata = assistant_msg.get('metadata', {})
            
            st.markdown("---")
            
            # Workflow流程图
            st.markdown("#### 1️⃣ 处理流程")
            
            if 'processing_steps' in metadata:
                steps = metadata['processing_steps']
                steps_html = format_workflow_steps(steps)
                st.markdown(steps_html, unsafe_allow_html=True)
                
                st.markdown("#### 2️⃣ 步骤详情")
                
                for step in steps:
                    with st.expander(f"📍 {step.get('node', 'Unknown Node')}"):
                        st.json(step)
            
            st.markdown("---")
            
            # Intent & NER
            st.markdown("#### 3️⃣ Intent & NER")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Intent分类**")
                intent = metadata.get('intent', 'unknown')
                intent_map = {
                    'specific_place': '🎯 具体地名查询',
                    'statistical': '📊 统计分析',
                    'followup': '💬 追问',
                    'tool_request': '🧰 工具请求',
                    'irrelevant': '❌ 无关查询'
                }
                st.info(intent_map.get(intent, intent))
            
            with col2:
                st.markdown("**提取实体**")
                entities = metadata.get('entities', [])
                if entities:
                    for entity in entities:
                        st.success(f"📍 {entity}")
                else:
                    st.warning("未提取到实体")
            
            # 工具调用结果
            if assistant_msg.get('tool_results'):
                st.markdown("---")
                st.markdown("#### 4️⃣ 工具调用结果")
                display_tool_results(assistant_msg['tool_results'])
    
    else:
        st.info("暂无对话记录，请先在'智能对话'标签页进行查询")

# ==================== Tab 3: 使用指南 ====================

with tab3:
    st.markdown("""
    ## 📚 系统使用指南
    
    ### ✨ 核心功能
    
    #### 1. 智能对话 💬
    - **多轮对话**: 支持上下文理解和追问
    - **代词消解**: 自动理解"这个"、"那个"、"它"等代词
    - **实体提取**: 自动提取地名等关键实体
    
    #### 2. Guardrails保护 🛡️
    - 输入验证、意图过滤、实体验证
    - 置信度检查、歧义检查、敏感词过滤
    
    #### 3. 研究工具 🧰
    
    **6个专业工具**：
    1. 文献溯源 - 查找地名在所有古籍中的出处
    2. 地名演变 - 追踪地名历史变迁
    3. 同名消歧 - 区分同名不同地的地名
    4. 相关推荐 - 推荐地理相近的地名
    5. 命名模式分析 - 分析某类地名的命名规律
    6. 学术报告导出 - 生成可引用的研究报告
    
    #### 4. 对话记忆 💭
    - 容量: 5轮对话（10条消息）
    - 功能: 代词消解、上下文理解、追问处理
    
    ---
    
    ### 🎯 使用技巧
    
    **追问示例**：
    ```
    第1轮: 思鄉城的由来？
    第2轮: 查找它的文献出处（自动理解"它"=思鄉城）
    第3轮: 这个地方周边有哪些相关地名？
    ```
    
    **工具调用**：
    ```
    查找思鄉城在所有古籍中的文献出处
    分析思鄉城的历史演变
    思鄉城周边有哪些相关地名
    ```
    
    ---
    
    ### 🔧 技术架构
    
    **LangGraph Workflow**:
    ```
    Intent → NER → Guardrails → Tool → RAG → Answer → Memory
    ```
    
    **核心技术**:
    - 检索: BM25 (精确关键词匹配)
    - LLM: Qwen2.5-72B-Instruct
    - Memory: 自定义conversation_history（同步session_state）
    - Tracing: LangSmith全链路追踪
    - Streaming: 真正的LLM token级流式输出
    
    ---
    
    ### ❓ 常见问题
    
    **Q: 如何清除对话历史？**
    A: 点击侧边栏的"清除历史"按钮
    
    **Q: 为什么我的查询被拒绝？**
    A: 检查Guardrails状态，可能是：长度不符、无关内容、未提取到地名等
    
    **Q: 如何查看详细的处理流程？**
    A: 点击"查看详情"或切换到"Workflow可视化"Tab
    
    **Q: 代词消解如何工作？**
    A: 系统会自动检测"这个"、"那个"、"它"等代词，并从对话历史中提取最近提到的地名
    
    ---
    
    ### 🔍 调试技巧
    
    **查看Memory内容**:
    - 侧边栏 → "查看Memory详情"
    - 可以看到每条消息保存的entities
    
    **查看Workflow详情**:
    - "Workflow可视化"Tab → 选择查询
    - 可以看到每个节点的详细信息
    
    ---
    
    *💡 提示: 本系统特别适合考古学者、古籍研究者和历史地理学研究*
    """)

# ==================== Footer ====================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 1rem;'>
    🤖 古籍地名RAG Agent系统 | 基于LangGraph + LangSmith | Powered by Streamlit
</div>
""", unsafe_allow_html=True)