"""
完整改进版RAG系统
保留你所有原有功能，新增：
1. 相似度阈值检查
2. 问题改写重试
3. 防止LLM胡编乱造
"""

import pandas as pd
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import os
import re
from pathlib import Path
from config import Config
Config.setup_environment()


class EnhancedRAGSystem:
    """改进版RAG系统 - 在原有基础上新增相似度检查"""
    
    # 新增配置
    SIMILARITY_THRESHOLD = 0.3  # 相似度阈值
    MAX_REWRITE_ATTEMPTS = 1    # 最大改写次数
    
    def __init__(self, 
                 data_csv: str = Config.BATCH_CLASSIFICATION,
                 insights_csv: str = "results/analysis_insights.csv",
                 index_path: str = Config.FAISS_INDEX_PATH):
        """
        初始化RAG系统
        
        Args:
            data_csv: 原始地名数据CSV
            insights_csv: 分析洞察CSV
            index_path: 向量库存储路径
        """
        self.data_csv = data_csv
        self.insights_csv = insights_csv
        self.index_path = index_path
        
        # API配置
        os.environ["OPENAI_API_KEY"] = "sk-gswitcfpsevlgfleazpwptqtpuolngnbzqvtbkeuexeqiyid"
        os.environ["OPENAI_BASE_URL"] = "https://api.siliconflow.cn/v1"
        
        # 初始化组件
        self.embeddings = None
        self.vectorstore = None
        self.llm = None
        self.rag_chain = None
    
    def setup(self):
        """设置RAG系统"""
        print("🔧 正在初始化增强版RAG系统...")
        
        # 1. 初始化嵌入模型
        self.embeddings = OpenAIEmbeddings(
            model=Config.EMBEDDING_MODEL,
            chunk_size=64
        )
        
        # 2. 加载或构建向量库
        if os.path.exists(self.index_path):
            print("检测到本地索引，正在加载...")
            self.vectorstore = FAISS.load_local(
                self.index_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
        else:
            print("首次构建向量库...")
            self.vectorstore = self._build_vectorstore()
            self.vectorstore.save_local(self.index_path)
            print("向量库已保存")
        
        # 3. 初始化LLM
        self.llm = ChatOpenAI(
            model=Config.RAG_MODEL,
            temperature=0.1,
            max_tokens=2048
        )
        
        # 4. 构建RAG链
        self._build_rag_chain()
        
        # 显示统计信息
        total_docs = self.vectorstore.index.ntotal
        print(f"RAG系统就绪！")
        print(f"知识库包含: {total_docs} 条文档")
        print(f"  • 地名记录: {self._count_placename_docs()} 条")
        print(f"  • 分析洞察: {self._count_insight_docs()} 条")
    
    def _build_vectorstore(self):
        """构建向量库 - 整合地名数据和分析洞察"""
        documents = []
        
        # 1. 加载原始地名数据
        print("加载地名数据...")
        if os.path.exists(self.data_csv):
            df = pd.read_csv(self.data_csv, encoding='utf-8-sig').fillna("")
            
            # 只加载STRONG和WEAK类型（有命名解释的）
            filtered_df = df[df['resolution_type'].isin(['STRONG', 'WEAK'])]
            
            for _, row in filtered_df.iterrows():
                content = f"地名：{row['placename']}\n记载：{row['text']}"
                documents.append(Document(
                    page_content=content,
                    metadata={
                        "type": "placename_record",
                        "source": row['source'],
                        "resolution_type": row['resolution_type'],
                        "placename": row['placename']
                    }
                ))
            
            print(f"  ✓ 已加载 {len(documents)} 条地名记录")
        
        # 2. 加载分析洞察
        print("加载分析洞察...")
        insights_count = 0
        
        if os.path.exists(self.insights_csv):
            insights_df = pd.read_csv(self.insights_csv, encoding='utf-8-sig').fillna("")
            
            for _, row in insights_df.iterrows():
                # 将每条洞察作为一个独立文档
                content = f"【{row['category']}】{row['title']}\n\n{row['content']}"
                documents.append(Document(
                    page_content=content,
                    metadata={
                        "type": "analysis_insight",
                        "category": row['category'],
                        "title": row['title']
                    }
                ))
                insights_count += 1
            
            print(f"  ✓ 已加载 {insights_count} 条分析洞察")
        else:
            print(f"  ⚠️  未找到分析洞察文件: {self.insights_csv}")
            print(f"     请先运行 step4_data_analyzer.py 生成分析结果")
        
        # 3. 添加总体摘要文档（方便回答宏观问题）
        if os.path.exists(self.data_csv):
            df = pd.read_csv(self.data_csv, encoding='utf-8-sig').fillna("")
            
            summary_content = f"""古籍地名数据集总体概况：

本数据集包含 {len(df)} 条地名记录，分类如下：
- STRONG类（明确命名解释）: {len(df[df['resolution_type']=='STRONG'])} 条
- WEAK类（引证命名解释）: {len(df[df['resolution_type']=='WEAK'])} 条
- NONE类（非命名解释）: {len(df[df['resolution_type']=='NONE'])} 条

数据来源涵盖多部古代地理文献，包括历代方志、地理总志等。
"""
            documents.append(Document(
                page_content=summary_content,
                metadata={
                    "type": "dataset_summary",
                    "category": "总体概况"
                }
            ))
        
        print(f"📦 构建向量库: 共 {len(documents)} 条文档")
        
        return FAISS.from_documents(documents, self.embeddings)
    
    def _build_rag_chain(self):
        """构建增强版RAG链"""
        # 创建检索器
        retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": 6}  # 增加检索数量，同时获取地名记录和洞察
        )
        
        # 增强版提示词模板
        template = """你是一名严谨的历史地理学家和数据分析专家。你可以回答两类问题：

1. **具体地名的命名考据问题**（如"某某地名的由来是什么？"）
2. **数据统计分析问题**（如"有多少条STRONG记录？""命名逻辑有哪些类型？"）

请根据以下检索到的信息回答用户问题：

[检索到的信息]:
{context}

[用户提问]: {question}

**回答要求**：
- 如果是具体地名问题，重点引用【地名记录】中的原文
- 如果是统计分析问题，重点参考【分析洞察】中的数据
- 明确区分"作者直接陈述"(STRONG)和"引证他人说法"(WEAK)
- 引用时标注来源文献

[回答]:"""
        
        prompt = ChatPromptTemplate.from_template(template)
        
        # 构建LCEL链
        self.rag_chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )
    
    # ==================== 新增方法 ====================
    
    def _search_with_similarity_scores(self, query: str, k: int = 6):
        """
        检索并返回相似度分数
        
        Returns:
            [(Document, similarity_score), ...]
            similarity_score: 0-1之间，越大越相似
        """
        # FAISS返回的是距离（越小越相似），转换为相似度
        docs_and_distances = self.vectorstore.similarity_search_with_score(query, k=k)
        
        # 转换：similarity = 1 / (1 + distance)
        docs_with_similarity = []
        for doc, distance in docs_and_distances:
            similarity = 1.0 / (1.0 + distance)
            docs_with_similarity.append((doc, similarity))
        
        return docs_with_similarity
    
    def _rewrite_question(self, original_question: str) -> str:
        """
        改写问题（让LLM优化表述）
        
        例子：
        - "这地儿叫啥？" → "这个地名的由来是什么？"
        """
        rewrite_prompt = f"""你是问题优化助手。用户的问题可能表达不够准确，请改写成更适合检索古籍地名数据的形式。

原始问题：{original_question}

改写要求：
1. 保持问题核心意图
2. 使用规范表达
3. 如果涉及地名，明确说明"地名的由来"或"命名原因"
4. 只返回改写后的问题，不要解释

改写后："""
        
        response = self.llm.invoke(rewrite_prompt)
        rewritten = response.content if hasattr(response, 'content') else str(response)
        
        print(f"  🔄 问题改写: {original_question} → {rewritten}")
        return rewritten.strip()
    
    # ==================== 改进的query方法 ====================
    
    def query(self, user_query: str):
        """
        改进版查询 - 新增相似度阈值检查
        
        流程：
        1. 检查问题类型（统计 vs 具体地名）
        2. 执行检索
        3. [新增] 检查相似度
        4. [新增] 相似度低 → 改写问题重试
        5. [新增] 仍然低 → 返回"检索不到"
        6. 相似度OK → 生成答案
        """
        q_type = self.get_question_type(user_query)
        
        # 统计类问题：直接用分析洞察
        if q_type == "statistical":
            insights_df = pd.read_csv(self.insights_csv)
            context = "以下是全量数据的统计洞察报告：\n" + insights_df.to_string()
            
            full_prompt = f"根据以下统计信息回答问题：\n\n{context}\n\n问题：{user_query}"
            response = self.llm.invoke(full_prompt)
            if hasattr(response, 'content'):
                return response.content
            return str(response)
        
        # 具体地名问题：需要相似度检查
        print(f"\n🔍 查询: {user_query}")
        
        # 第1次检索
        docs_with_sim = self._search_with_similarity_scores(user_query, k=Config.RAG_RETRIEVAL_K)
        max_similarity = max([sim for _, sim in docs_with_sim])
        
        print(f"  📊 最高相似度: {max_similarity:.3f}")
        
        # 检查相似度
        if max_similarity < self.SIMILARITY_THRESHOLD:
            print(f"  ⚠️  相似度低于阈值 {self.SIMILARITY_THRESHOLD}")
            
            # 尝试改写问题（只试1次，防止套娃）
            print(f"  🔄 尝试改写问题...")
            rewritten_question = self._rewrite_question(user_query)
            
            # 第2次检索
            docs_with_sim = self._search_with_similarity_scores(rewritten_question, k=Config.RAG_RETRIEVAL_K)
            max_similarity = max([sim for _, sim in docs_with_sim])
            
            print(f"  📊 改写后相似度: {max_similarity:.3f}")
            
            # 仍然太低 → 放弃
            if max_similarity < self.SIMILARITY_THRESHOLD:
                print(f"  ❌ 改写后仍低于阈值")
                
                return f"""抱歉，未能检索到与'{user_query}'相关的内容。

💡 可能的原因：
1. 您的问题可能不在古籍地名数据范围内
2. 可以尝试更换表述方式
3. 确认地名是否在数据库中

📚 本系统支持的查询类型：
- 具体地名的由来（如"隋县的由来是什么？"）
- 统计类问题（如"有多少条STRONG记录？"）"""
            else:
                print(f"  ✅ 改写后相似度可接受")
                question_to_use = rewritten_question
        else:
            print(f"  ✅ 相似度可接受")
            question_to_use = user_query
        
        # 相似度OK，生成答案
        docs = [doc for doc, _ in docs_with_sim]
        context = "\n\n".join([doc.page_content for doc in docs])
        
        full_prompt = f"""根据以下检索到的古籍地名信息回答问题：

{context}

问题：{question_to_use}

回答要求：
- 基于检索到的信息回答
- 引用来源文献
- 如果信息不完整，说明局限性"""

        response = self.llm.invoke(full_prompt)
        if hasattr(response, 'content'):
            return response.content
        return str(response)
    
    # ==================== 保留原有方法 ====================
    
    def search_documents(self, query: str, k: int = 6):
        """
        检索相关文档（用于调试）
        
        Args:
            query: 查询文本
            k: 返回文档数量
            
        Returns:
            文档列表
        """
        docs = self.vectorstore.similarity_search(query, k=k)
        
        result = []
        for i, doc in enumerate(docs, 1):
            result.append({
                "rank": i,
                "type": doc.metadata.get("type", "unknown"),
                "content": doc.page_content[:200] + "...",
                "metadata": doc.metadata
            })
        
        return result
    
    def _count_placename_docs(self) -> int:
        """统计地名记录文档数量"""
        try:
            df = pd.read_csv(self.data_csv, encoding='utf-8-sig')
            return len(df[df['resolution_type'].isin(['STRONG', 'WEAK'])])
        except:
            return 0
    
    def _count_insight_docs(self) -> int:
        """统计分析洞察文档数量"""
        try:
            df = pd.read_csv(self.insights_csv, encoding='utf-8-sig')
            return len(df)
        except:
            return 0
    
    def get_question_type(self, question: str) -> str:
        """
        判断问题类型
        
        Returns:
            'statistical': 统计类问题
            'specific': 具体地名问题
        """
        statistical_keywords = [
            "多少", "数量", "比例", "分布", "统计", "总共", "占比",
            "类型", "分类", "有哪些", "主要", "典型"
        ]
        
        for keyword in statistical_keywords:
            if keyword in question:
                return "statistical"
        
        return "specific"


def run_interactive_session():
    """运行交互式问答会话"""
    # 初始化系统
    rag = EnhancedRAGSystem()
    rag.setup()
    
    print("\n" + "="*60)
    print("🏛️  古籍地名考据系统（增强版）")
    print("="*60)
    print("\n💡 提示:")
    print("  • 可以询问具体地名的命名由来")
    print("  • 也可以询问统计信息（如'有多少条STRONG记录？'）")
    print("  • [新功能] 相似度阈值检查，防止胡编乱造")
    print("  • [新功能] 自动改写问题重试")
    print("  • 输入 'exit' 或 'quit' 退出")
    print("  • 输入 'test' 查看示例问题")
    print("\n" + "="*60)
    
    while True:
        user_input = input("\n💬 请输入您的问题 > ").strip()
        
        # 退出命令
        if user_input.lower() in ['exit', 'quit']:
            print("\n👋 系统已退出")
            break
        
        # 忽略空输入
        if not user_input:
            continue
        
        # 测试命令
        if user_input.lower() == 'test':
            print("\n  示例问题:")
            print("  1. 京师这个地名的由来是什么？")
            print("  2. 数据集中有多少条STRONG类记录？")
            print("  3. 命名逻辑主要有哪些类型？")
            print("  4. 秦始皇的生日是几号？  ← 测试相似度检查")
            continue
        
        # 显示问题类型
        q_type = rag.get_question_type(user_input)
        if q_type == "statistical":
            print("  [统计分析问题]")
        else:
            print("  [具体地名问题]")
        
        try:
            # 执行查询
            answer = rag.query(user_input)
            
            print("\n" + "-"*60)
            print("📖 回答:")
            print("-"*60)
            print(answer)
            print("-"*60)
            
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")


def main():
    """主函数"""
    # 检查必要文件
    required_files = {
        Config.BATCH_CLASSIFICATION: "地名数据文件",
        "results/analysis_insights.csv": "分析洞察文件"
    }
    
    missing_files = []
    for file_path, description in required_files.items():
        if not os.path.exists(file_path):
            missing_files.append((file_path, description))
    
    if missing_files:
        print("⚠️  缺少必要文件:")
        for file_path, description in missing_files:
            print(f"  • {file_path} ({description})")
        
        if "results/analysis_insights.csv" in [f[0] for f in missing_files]:
            print("\n  提示: 请先运行 step4_data_analyzer.py 生成分析结果")
        
        return
    
    # 运行交互式会话
    run_interactive_session()


if __name__ == "__main__":
    main()