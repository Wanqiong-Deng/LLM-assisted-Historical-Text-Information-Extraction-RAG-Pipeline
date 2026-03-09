import pandas as pd
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
import os
import opencc
import jieba
from rank_bm25 import BM25Okapi
from langsmith import traceable
from config import Config

Config.setup_environment()

class RAGSystem:
    """BM25检索的RAG系统"""
    
    SIMILARITY_THRESHOLD = 0.3
    
    def __init__(self, 
                 data_csv: str = Config.BATCH_CLASSIFICATION,
                 insights_csv: str = "results/analysis_insights.csv"):
        self.data_csv = data_csv
        self.insights_csv = insights_csv
        
        # API配置
        os.environ["OPENAI_API_KEY"] = Config.API_KEY
        os.environ["OPENAI_BASE_URL"] = Config.API_BASE_URL
        
        # 繁简转换
        self.converter_t2s = opencc.OpenCC('t2s')
        
        # 初始化组件
        self.llm = None
        self.bm25 = None
        self.bm25_documents = []
    
    def setup(self):
        """设置系统"""
        print("🔧 正在初始化BM25-only RAG系统...")
        
        # 1. 构建BM25索引
        print("🔍 构建BM25索引...")
        self._build_bm25_index()
        
        # 2. 初始化LLM
        self.llm = ChatOpenAI(
            model=Config.RAG_MODEL,
            temperature=0.1,
            max_tokens=2048
        )
        
        print(f"\n✅ RAG系统就绪！")
        print(f"📊 BM25索引: {len(self.bm25_documents)} 条文档")
    
    def _normalize_text(self, text: str) -> str:
        """繁简统一"""
        return self.converter_t2s.convert(text)
    
    def _build_bm25_index(self):
        """构建BM25索引"""
        if not os.path.exists(self.data_csv):
            return
        
        df = pd.read_csv(self.data_csv, encoding='utf-8-sig').fillna("")
        filtered_df = df[df['resolution_type'].isin(['STRONG', 'WEAK'])]
        
        tokenized_docs = []
        
        for idx, row in filtered_df.iterrows():
            # 繁简统一
            placename = self._normalize_text(row['placename'])
            text = self._normalize_text(row['text'])
            
            combined = f"{placename} {text}"
            tokens = list(jieba.cut(combined))
            
            tokenized_docs.append(tokens)
            self.bm25_documents.append(row.to_dict())
        
        self.bm25 = BM25Okapi(tokenized_docs)
        print(f"  ✓ BM25索引构建完成 ({len(self.bm25_documents)} 条)")
    
    def _bm25_search(self, query: str, k: int = 6):
        """BM25检索"""
        query_normalized = self._normalize_text(query)
        query_tokens = list(jieba.cut(query_normalized))
        
        bm25_scores = self.bm25.get_scores(query_tokens)
        top_k_indices = bm25_scores.argsort()[-k:][::-1]
        
        results = []
        for idx in top_k_indices:
            doc_dict = self.bm25_documents[idx]
            score = bm25_scores[idx]
            
            # 构造Document对象
            placename = doc_dict['placename']
            text = doc_dict['text']
            
            content = f"地名：{placename}\n记载：{text}"
            
            doc = Document(
                page_content=content,
                metadata={
                    "type": "placename_record",
                    "source": doc_dict.get('source', 'unknown'),
                    "resolution_type": doc_dict.get('resolution_type', 'unknown'),
                    "placename": placename
                }
            )
            
            # BM25分数转换为相似度
            if score > 10:
                similarity = min(0.95, 0.8 + (score - 10) * 0.01)
            elif score > 5:
                similarity = 0.5 + (score - 5) * 0.06
            else:
                similarity = max(0.3, score * 0.06)
            
            results.append((doc, similarity))
        
        return results
    
    @traceable(name="RAG_Query_Process", run_type="chain")
    def query(self, user_query: str):
        """查询"""
        q_type = self.get_question_type(user_query)
        
        # 统计类问题
        if q_type == "statistical":
            print("  📊 [统计类问题]")
            insights_df = pd.read_csv(self.insights_csv)
            context = "以下是全量数据的统计洞察报告：\n" + insights_df.to_string()
            
            full_prompt = f"根据以下统计信息回答问题：\n\n{context}\n\n问题：{user_query}"
            response = self.llm.invoke(full_prompt)
            if hasattr(response, 'content'):
                return response.content
            return str(response)
        
        # 具体地名问题
        print(f"\n🔍 [具体地名问题] 查询: {user_query}")
        
        query_normalized = self._normalize_text(user_query)
        if query_normalized != user_query:
            print(f"  📝 繁简统一: {user_query} → {query_normalized}")
        
        # BM25检索
        print("  🔎 执行BM25检索...")
        docs_with_sim = self._bm25_search(user_query, k=Config.RAG_RETRIEVAL_K)
        
        if not docs_with_sim:
            return "抱歉，未能检索到相关内容。"
        
        max_similarity = max([sim for _, sim in docs_with_sim])
        print(f"  📊 最高相似度: {max_similarity:.3f}")
        
        # 显示检索结果
        retrieved_placenames = []
        for doc, sim in docs_with_sim[:3]:
            placename = doc.metadata.get('placename', '未知')
            retrieved_placenames.append(f"{placename} (BM25分数: {sim:.3f})")
        print(f"  📍 检索到的地名: {', '.join(retrieved_placenames)}")
        
        # 相似度检查
        if max_similarity < self.SIMILARITY_THRESHOLD:
            print(f"  ⚠️  相似度低于阈值 {self.SIMILARITY_THRESHOLD}")
            return f"抱歉，未能检索到与'{user_query}'相关的内容。"
        
        print(f"  ✅ 相似度可接受")
        
        # 生成答案
        docs = [doc for doc, _ in docs_with_sim]
        context = "\n\n".join([doc.page_content for doc in docs])
        
        full_prompt = f"""根据以下检索到的古籍地名信息回答问题：

{context}

问题：{user_query}

回答要求：
- 基于检索到的信息回答
- 引用来源文献
- 不用区分繁体和简体
P.S.：请注意检索到的信息中的标签
‘STRONG
满足以下全部条件：
1. 文本中明确给出地名命名原因（因、故、以、取、改曰等）。
2. 命名解释为作者直接陈述，而非转述。
3. 该句或其直接语境中【不存在】以下任何引证或转述标志：
   - 云、曰、注、按、谓、相传
   - 《书名》《志》《记》等典籍标记
   - 引号内的内容
4. 命名解释语句在语义上可独立成立，不依赖外部权威。

WEAK
满足以下任一条件：
1. 存在命名解释，但明确来源于：
   - 他人说法（云、曰、相传）
   - 作者按语（按、谨按）
   - 典籍引用（《》《》）
2. 命名逻辑嵌套在引文或转述中，即使形式上出现"因、故、以"等词。

NONE
仅包含以下内容之一：
- 地理位置、距离、方位
- 水系流向、山势描述
- 户数、行政沿革、建置时间
- 未出现任何命名因果关系

请严格区分【作者判断】与【作者记录他人说法】。’
"""

        response = self.llm.invoke(full_prompt)
        if hasattr(response, 'content'):
            return response.content
        return str(response)
    
    def get_question_type(self, question: str) -> str:
        """判断问题类型"""
        statistical_keywords = [
            "多少", "数量", "比例", "分布", "统计", "总共", "占比",
            "类型", "分类", "有哪些", "主要", "典型"
        ]
        
        for keyword in statistical_keywords:
            if keyword in question:
                return "statistical"
        
        return "specific"


def run_interactive_session():
    """交互式会话"""
    rag = RAGSystem()
    rag.setup()
    
    print("\n" + "="*60)
    print("🏛️  古籍地名考据系统")
    print("="*60)
    print("\n💡 特性:")
    print("  • ✨ 繁简体自动识别")
    print("  • 🔍 BM25精确检索")
    print("  • 📊 相似度阈值检查")
    print("\n" + "="*60)
    
    while True:
        user_input = input("\n💬 请输入您的问题 > ").strip()
        
        if user_input.lower() in ['exit', 'quit']:
            print("\n👋 系统已退出")
            break
        
        if not user_input:
            continue
        
        if user_input.lower() == 'test':
            print("\n  示例问题:")
            print("  1. 思鄉城名字由來")
            print("  2. 長樂坡的由来")
            continue
        
        try:
            answer = rag.query(user_input)
            
            print("\n" + "-"*60)
            print("📖 回答:")
            print("-"*60)
            print(answer)
            print("-"*60)
            
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    run_interactive_session()