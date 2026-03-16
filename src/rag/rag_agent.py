"""
古籍地名RAG Agent系统 - 完整版
修复：
1. 无限streaming bug
2. 所有功能完整保留
"""

import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
import os
import opencc
import jieba
from rank_bm25 import BM25Okapi
from langsmith import traceable
from config import Config
from typing import Dict, List, Any, Generator
from langgraph.graph import StateGraph, END
from datetime import datetime
import json
import re

# 导入模块
from agent_modules.agent_state import AgentState
from agent_modules.tools import ResearchTools

Config.setup_environment()


# ==================== Agent Core ====================

class AgentCore:
    """Agent核心 - 包含所有workflow节点"""
    
    def __init__(self, llm, bm25, bm25_documents, tools, insights_csv, converter_t2s, similarity_threshold):
        self.llm = llm
        self.bm25 = bm25
        self.bm25_documents = bm25_documents
        self.tools = tools
        self.insights_csv = insights_csv
        self.converter_t2s = converter_t2s
        self.SIMILARITY_THRESHOLD = similarity_threshold
    
    @traceable(name="Node_Intent_Classification")
    def intent_classification_node(self, state: Dict) -> Dict:
        """意图分类节点"""
        user_query = state["user_query"]
        conversation_history = state.get("conversation_history", [])
        
        prompt = f"""你是意图分类专家。分析用户查询的意图类型。

对话历史：
{self._format_conversation_history(conversation_history)}

当前查询：{user_query}

意图类型：
1. specific_place - 查询具体地名的由来、信息
2. statistical - 统计分析类问题（数量、分布、比例、占比等）
3. followup - 追问上一个问题（"还有吗"、"更详细"、"它的由来"等）
4. tool_request - 明确要求使用某个工具（"查文献"、"分析演变"等）
5. irrelevant - 与古籍地名无关的问题

请以JSON格式返回：
{{
    "intent": "意图类型",
    "confidence": 0.0-1.0的置信度,
    "reasoning": "判断理由"
}}
"""
        
        response = self.llm.invoke(prompt)
        result = self._parse_json_response(response.content)
        
        state["intent"] = result.get("intent", "specific_place")
        state["intent_confidence"] = result.get("confidence", 0.5)
        
        if "processing_steps" not in state:
            state["processing_steps"] = []
        
        state["processing_steps"].append({
            "node": "Intent Classification",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
        return state
    
    @traceable(name="Node_NER_Extraction")
    def ner_extraction_node(self, state: Dict) -> Dict:
        """NER提取节点"""
        user_query = state["user_query"]
        conversation_history = state.get("conversation_history", [])
        intent = state.get("intent", "specific_place")
        
        # 检测代词
        pronouns = ["这个", "那个", "它", "该", "此", "其", "這個", "那個"]
        has_pronoun = any(p in user_query for p in pronouns)
        
        # 如果是followup或包含代词 → 从历史提取
        if (intent == "followup" or has_pronoun) and conversation_history:
            entities = self._extract_entities_from_history(conversation_history)
            state["ner_confidence"] = 0.8 if entities else 0.3
        else:
            # 正常提取
            prompt = f"""提取以下查询中的所有地名实体。

查询：{user_query}

要求：
1. 提取所有古代地名（包括县、城、州、府、郡等）
2. 如果查询中没有明确地名，返回空列表
3. 返回JSON格式：{{"entities": ["地名1", "地名2"], "confidence": 0.0-1.0}}
"""
            
            response = self.llm.invoke(prompt)
            result = self._parse_json_response(response.content)
            entities = result.get("entities", [])
            state["ner_confidence"] = result.get("confidence", 0.5)
        
        state["extracted_entities"] = entities
        
        state["processing_steps"].append({
            "node": "NER Extraction",
            "entities": entities,
            "pronoun_detected": has_pronoun,
            "timestamp": datetime.now().isoformat()
        })
        
        return state
    
    @traceable(name="Node_Guardrails_Check")
    def guardrails_check_node(self, state: Dict) -> Dict:
        """Guardrails检查节点"""
        user_query = state["user_query"]
        intent = state["intent"]
        entities = state["extracted_entities"]
        intent_confidence = state.get("intent_confidence", 0.5)
        
        guardrail_passed = True
        guardrail_message = None
        
        if len(user_query) < 3:
            guardrail_passed = False
            guardrail_message = "查询过短，请提供更详细的问题。"
        elif len(user_query) > 500:
            guardrail_passed = False
            guardrail_message = "查询过长，请简化问题。"
        
        if guardrail_passed and intent_confidence < 0.3:
            guardrail_passed = False
            guardrail_message = "无法理解您的问题，请重新表述。"
        
        if guardrail_passed and intent == "irrelevant":
            guardrail_passed = False
            guardrail_message = "您的问题与古籍地名无关。本系统专注于古代地名考据和分析。"
        
        if guardrail_passed and intent == "specific_place" and len(entities) == 0:
            guardrail_passed = False
            guardrail_message = "未能识别到具体地名，请明确您要查询的地名。例如：'思鄉城的由来是什么？'"
        
        if guardrail_passed and len(entities) > 3:
            guardrail_passed = False
            guardrail_message = f"检测到多个地名（{', '.join(entities)}），请明确您要查询哪一个。"
        
        state["guardrail_passed"] = guardrail_passed
        state["guardrail_message"] = guardrail_message
        
        state["processing_steps"].append({
            "node": "Guardrails Check",
            "passed": guardrail_passed,
            "message": guardrail_message,
            "timestamp": datetime.now().isoformat()
        })
        
        return state
    
    @traceable(name="Node_Tool_Selection")
    def tool_selection_node(self, state: Dict) -> Dict:
        """工具选择节点"""
        user_query = state["user_query"]
        intent = state["intent"]
        entities = state.get("extracted_entities", [])
        
        tools_to_call = []
        
        # 统计分析类 - 使用data visualization
        if intent == "statistical" or any(word in user_query for word in ["占比", "比例", "分布", "统计", "数量", "可视化", "图表"]):
            tools_to_call.append("data_visualization")
        
        if intent == "tool_request" or "文献" in user_query or "出处" in user_query:
            tools_to_call.append("literature_source_lookup")
        
        if "演变" in user_query or "历史" in user_query or "朝代" in user_query:
            tools_to_call.append("place_name_evolution")
        
        if "同名" in user_query or "区分" in user_query or len(entities) > 1:
            tools_to_call.append("disambiguate_placenames")
        
        if "相关" in user_query or "周边" in user_query or "附近" in user_query:
            tools_to_call.append("find_related_places")
        
        if "导出" in user_query or "报告" in user_query:
            tools_to_call.append("export_academic_report")
        
        state["tools_to_call"] = tools_to_call
        
        state["processing_steps"].append({
            "node": "Tool Selection",
            "tools": tools_to_call,
            "timestamp": datetime.now().isoformat()
        })
        
        return state
    
    @traceable(name="Node_Tool_Execution")
    def tool_execution_node(self, state: Dict) -> Dict:
        """工具执行节点"""
        tools_to_call = state.get("tools_to_call", [])
        entities = state.get("extracted_entities", [])
        user_query = state["user_query"]
        
        tool_results = {}
        
        for tool_name in tools_to_call:
            try:
                if tool_name == "data_visualization":
                    result = self.tools.data_visualization(user_query)
                    tool_results[tool_name] = result
                
                elif tool_name == "literature_source_lookup" and entities:
                    result = self.tools.literature_source_lookup(entities[0])
                    tool_results[tool_name] = result
                
                elif tool_name == "place_name_evolution" and entities:
                    result = self.tools.place_name_evolution(entities[0])
                    tool_results[tool_name] = result
                
                elif tool_name == "disambiguate_placenames" and entities:
                    result = self.tools.disambiguate_placenames(entities[0])
                    tool_results[tool_name] = result
                
                elif tool_name == "find_related_places" and entities:
                    result = self.tools.find_related_places(entities[0], k=5)
                    tool_results[tool_name] = result
                
                elif tool_name == "export_academic_report":
                    history = state.get("conversation_history", [])
                    result = self.tools.export_academic_report(history)
                    tool_results[tool_name] = result
                    
            except Exception as e:
                tool_results[tool_name] = {"error": True, "message": str(e)}
        
        state["tool_results"] = tool_results
        
        state["processing_steps"].append({
            "node": "Tool Execution",
            "tools_executed": list(tool_results.keys()),
            "timestamp": datetime.now().isoformat()
        })
        
        return state
    
    @traceable(name="Node_RAG_Retrieval")
    def rag_retrieval_node(self, state: Dict) -> Dict:
        """RAG检索节点"""
        user_query = state["user_query"]
        intent = state["intent"]
        
        if intent == "statistical":
            state["retrieved_docs"] = []
            state["retrieval_similarity"] = 1.0
            return state
        
        docs_with_sim = self._bm25_search(user_query, k=6)
        
        if docs_with_sim:
            docs, sims = zip(*docs_with_sim)
            state["retrieved_docs"] = list(docs)
            state["retrieval_similarity"] = max(sims)
        else:
            state["retrieved_docs"] = []
            state["retrieval_similarity"] = 0.0
        
        state["processing_steps"].append({
            "node": "RAG Retrieval",
            "num_docs": len(state["retrieved_docs"]),
            "max_similarity": state["retrieval_similarity"],
            "timestamp": datetime.now().isoformat()
        })
        
        return state
    
    def _bm25_search(self, query: str, k: int = 6):
        """BM25检索"""
        query_normalized = self.converter_t2s.convert(query)
        query_tokens = list(jieba.cut(query_normalized))
        
        bm25_scores = self.bm25.get_scores(query_tokens)
        top_k_indices = bm25_scores.argsort()[-k:][::-1]
        
        results = []
        for idx in top_k_indices:
            doc_dict = self.bm25_documents[idx]
            score = bm25_scores[idx]
            
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
            
            if score > 10:
                similarity = min(0.95, 0.8 + (score - 10) * 0.01)
            elif score > 5:
                similarity = 0.5 + (score - 5) * 0.06
            else:
                similarity = max(0.3, score * 0.06)
            
            results.append((doc, similarity))
        
        return results
    
    def _format_conversation_history(self, history: List[Dict]) -> str:
        """格式化历史"""
        if not history:
            return "无对话历史"
        
        formatted = []
        for item in history[-6:]:
            role = item.get("role", "unknown")
            content = item.get("content", "")
            if role == "user":
                formatted.append(f"用户: {content}")
            elif role == "assistant":
                formatted.append(f"助手: {content[:100]}...")
        
        return "\n".join(formatted)
    
    def _extract_entities_from_history(self, history: List[Dict]) -> List[str]:
        """从历史提取entities"""
        for item in reversed(history):
            if item.get("role") == "user" and item.get("entities"):
                return item["entities"]
        return []
    
    def _parse_json_response(self, response: str) -> Dict:
        """解析JSON"""
        try:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(response)
        except:
            return {"intent": "specific_place", "confidence": 0.5}


# ==================== Main Agent ====================

class RAGAgent:
    """RAG Agent - 完整版"""
    
    SIMILARITY_THRESHOLD = 0.3
    
    def __init__(self, conversation_history: List[Dict] = None):
        """
        初始化Agent
        
        Args:
            conversation_history: 外部传入的对话历史引用
        """
        self.data_csv = Config.BATCH_CLASSIFICATION
        self.insights_csv = "results/analysis_insights.csv"
        
        os.environ["OPENAI_API_KEY"] = Config.API_KEY
        os.environ["OPENAI_BASE_URL"] = Config.API_BASE_URL
        
        self.converter_t2s = opencc.OpenCC('t2s')
        
        self.llm = None
        self.bm25 = None
        self.bm25_documents = []
        self.tools = None
        
        # 使用外部传入的conversation_history引用
        self._external_conversation_history = conversation_history if conversation_history is not None else []
        
        self.workflow = None
        self.agent_core = None
    
    def setup(self):
        """设置系统"""
        print("🔧 正在初始化RAG Agent系统...")
        
        print("🔍 构建BM25索引...")
        self._build_bm25_index()
        
        self.llm = ChatOpenAI(
            model=Config.RAG_MODEL,
            temperature=0.1,
            max_tokens=2048,
            streaming=True
        )
        
        self.tools = ResearchTools(self.data_csv)
        
        self.agent_core = AgentCore(
            llm=self.llm,
            bm25=self.bm25,
            bm25_documents=self.bm25_documents,
            tools=self.tools,
            insights_csv=self.insights_csv,
            converter_t2s=self.converter_t2s,
            similarity_threshold=self.SIMILARITY_THRESHOLD
        )
        
        print("🔗 构建workflow...")
        self._build_workflow()
        
        print(f"\n✅ RAG Agent系统就绪！")
        print(f"📊 BM25索引: {len(self.bm25_documents)} 条文档")
        print(f"🧰 工具数量: 5 个研究工具")
        print(f"💭 记忆容量: 保留最近5轮对话")
    
    def _build_bm25_index(self):
        """构建BM25索引"""
        if not os.path.exists(self.data_csv):
            return
        
        df = pd.read_csv(self.data_csv, encoding='utf-8-sig').fillna("")
        filtered_df = df[df['resolution_type'].isin(['STRONG', 'WEAK'])]
        
        tokenized_docs = []
        
        for idx, row in filtered_df.iterrows():
            placename = self.converter_t2s.convert(row['placename'])
            text = self.converter_t2s.convert(row['text'])
            combined = f"{placename} {text}"
            tokens = list(jieba.cut(combined))
            tokenized_docs.append(tokens)
            self.bm25_documents.append(row.to_dict())
        
        self.bm25 = BM25Okapi(tokenized_docs)
        print(f"  ✓ BM25索引构建完成 ({len(self.bm25_documents)} 条)")
    
    def _build_workflow(self):
        """构建workflow（不包含answer generation）"""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("intent_classification", self.agent_core.intent_classification_node)
        workflow.add_node("ner_extraction", self.agent_core.ner_extraction_node)
        workflow.add_node("guardrails_check", self.agent_core.guardrails_check_node)
        workflow.add_node("tool_selection", self.agent_core.tool_selection_node)
        workflow.add_node("tool_execution", self.agent_core.tool_execution_node)
        workflow.add_node("rag_retrieval", self.agent_core.rag_retrieval_node)
        
        workflow.set_entry_point("intent_classification")
        
        workflow.add_edge("intent_classification", "ner_extraction")
        workflow.add_edge("ner_extraction", "guardrails_check")
        
        workflow.add_conditional_edges(
            "guardrails_check",
            lambda state: "reject" if not state.get("guardrail_passed", True) else "continue",
            {"reject": END, "continue": "tool_selection"}
        )
        
        workflow.add_conditional_edges(
            "tool_selection",
            lambda state: "use_tools" if len(state.get("tools_to_call", [])) > 0 else "skip_tools",
            {"use_tools": "tool_execution", "skip_tools": "rag_retrieval"}
        )
        
        workflow.add_edge("tool_execution", "rag_retrieval")
        workflow.add_edge("rag_retrieval", END)
        
        self.workflow = workflow.compile()
    
    @traceable(name="Agent_Query")
    def query(self, user_query: str) -> Generator[Dict, None, None]:
        """
        Agent查询 - 流式输出
        
        修复：添加max_iterations防止无限循环
        """
        initial_state = {
            "user_query": user_query,
            "conversation_history": self._external_conversation_history.copy(),
            "timestamp": datetime.now().isoformat(),
            "processing_steps": []
        }
        
        # 第1阶段：workflow
        final_state = {}
        for chunk in self.workflow.stream(initial_state, stream_mode="values"):
            final_state = chunk
            yield {
                "type": "workflow_step",
                "state": chunk
            }
        
        # Guardrails检查
        if not final_state.get("guardrail_passed", True):
            yield {
                "type": "guardrail_reject",
                "message": final_state.get("guardrail_message", "查询被拒绝"),
                "final_state": final_state
            }
            return
        
        # 第2阶段：构建prompt
        prompt = self._build_answer_prompt(final_state)
        
        # 第3阶段：LLM streaming（🔥 修复：添加限制防止无限循环）
        full_answer = ""
        token_count = 0
        MAX_TOKENS = 3000  # 最大token数限制
        
        try:
            for chunk in self.llm.stream(prompt):
                if chunk.content:
                    full_answer += chunk.content
                    token_count += 1
                    
                    yield {
                        "type": "answer_token",
                        "token": chunk.content,
                        "partial_answer": full_answer
                    }
                    
                    # 🔥 防止无限循环
                    if token_count >= MAX_TOKENS:
                        print(f"⚠️ 达到最大token数限制({MAX_TOKENS})，停止生成")
                        break
        except Exception as e:
            print(f"⚠️ Streaming错误: {e}")
            if not full_answer:
                full_answer = "生成回答时出现错误，请重试。"
        
        # 第4阶段：更新外部conversation_history
        entities = final_state.get("extracted_entities", [])
        
        self._external_conversation_history.append({
            "role": "user",
            "content": user_query,
            "entities": entities,
            "timestamp": datetime.now().isoformat()
        })
        
        self._external_conversation_history.append({
            "role": "assistant",
            "content": full_answer,
            "timestamp": datetime.now().isoformat()
        })
        
        # 保持长度限制
        if len(self._external_conversation_history) > 10:
            del self._external_conversation_history[:-10]
        
        # 返回完整final_state
        final_state["answer"] = full_answer
        final_state["answer_confidence"] = 0.9 if final_state.get("retrieval_similarity", 0) > 0.7 else 0.6
        
        yield {
            "type": "final_state",
            "final_state": final_state
        }
    
    def _build_answer_prompt(self, state: Dict) -> str:
        """构建prompt（完整保留）"""
        user_query = state["user_query"]
        intent = state["intent"]
        retrieved_docs = state.get("retrieved_docs", [])
        retrieval_similarity = state.get("retrieval_similarity", 0.0)
        tool_results = state.get("tool_results", {})
        
        if intent == "statistical":
            insights_df = pd.read_csv(self.insights_csv)
            context = "以下是全量数据的统计洞察报告：\n" + insights_df.to_string()
            return f"根据以下统计信息回答问题：\n\n{context}\n\n问题：{user_query}"
        
        if retrieval_similarity < self.SIMILARITY_THRESHOLD:
            return f"抱歉，未能检索到与'{user_query}'相关的内容。\n\n可能原因：\n1. 该地名不在数据库中\n2. 尝试使用繁体或简体的不同写法\n3. 确认地名拼写是否正确"
        
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        
        if tool_results:
            tool_context = "\n\n=== 工具分析结果 ===\n"
            for tool_name, result in tool_results.items():
                tool_context += f"\n[{tool_name}]:\n{json.dumps(result, ensure_ascii=False, indent=2)}\n"
            context = tool_context + "\n\n=== 古籍记载 ===\n" + context
        
        return f"""根据以下检索到的古籍地名信息回答问题：

{context}

问题：{user_query}

回答要求：
- 基于检索到的信息回答
- 引用来源文献
- 不用区分繁体和简体
P.S.：请注意检索到的信息中的标签
STRONG
满足以下全部条件，你只需要知道，不需要在组织回复时过度强调：
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

请严格区分【作者判断】与【作者记录他人说法】。
"""
    
    def clear_memory(self):
        """清除对话历史"""
        self._external_conversation_history.clear()