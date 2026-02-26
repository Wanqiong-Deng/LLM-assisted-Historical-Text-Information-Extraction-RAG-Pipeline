import pandas as pd
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import os

os.environ["OPENAI_API_KEY"] = "sk-gswitcfpsevlgfleazpwptqtpuolngnbzqvtbkeuexeqiyid"
os.environ["OPENAI_BASE_URL"] = "https://api.siliconflow.cn/v1"

def run_lcel_rag():

    embeddings = OpenAIEmbeddings(
        model="BAAI/bge-m3", 
        chunk_size=64 
    ) 
    index_path = "faiss_index_storage"
    
    if os.path.exists(index_path):
        print("检测到本地索引，正在快速加载...")
        vectorstore = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    else:
        print("未检测到本地索引，正在首次构建向量库（此过程较慢）...")
        df = pd.read_csv("batch_classification_results.csv").fillna("")
        documents = [
            Document(
                page_content=f"地名：{row['placename']}\n记载：{row['text']}",
                metadata={"source": row['source'], "type": row['resolution_type']}
            ) for _, row in df[df['resolution_type'].isin(['STRONG', 'WEAK'])].iterrows()
        ]
        vectorstore = FAISS.from_documents(documents, embeddings)

        vectorstore.save_local(index_path)
        print("向量库构建完成并已保存至本地。")

    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    
    model = ChatOpenAI(
        model="deepseek-ai/DeepSeek-V3", 
        temperature=0.1,
        max_tokens=2048
    )

    template = """你是一名严谨的历史地理学家。请基于以下检索到的文献片段回答问题。

[已知文献信息]:
{context}

[用户提问]: {question}

[深度考据结果]:"""
    
    prompt = ChatPromptTemplate.from_template(template)

    lcel_rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | model
        | StrOutputParser()
    )

    print("\n" + "="*50)
    print("古籍地名命名考据系统已就绪（输入 'exit' 或 'quit' 退出）")
    print("="*50)

    while True:
        user_input = input("\n请输入您的考据问题 > ")
        
        if user_input.lower() in ['exit', 'quit']:
            print("系统已退出。")
            break
            
        if not user_input.strip():
            continue

        print("正在检索文献并生成分析...")
        try:
            result = lcel_rag_chain.invoke(user_input)
            print(f"\n【考据结论】\n{result}")
        except Exception as e:
            print(f"发生错误: {e}")

if __name__ == "__main__":
    run_lcel_rag()