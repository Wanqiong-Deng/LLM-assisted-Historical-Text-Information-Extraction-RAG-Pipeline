"""
Agent状态定义模块
"""

from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.documents import Document


class AgentState(TypedDict):
    """Agent状态定义"""
    # 输入
    user_query: str
    conversation_history: List[Dict[str, str]]
    
    # Intent Classification
    intent: str  # "specific_place", "statistical", "followup", "irrelevant"
    intent_confidence: float
    
    # NER
    extracted_entities: List[str]  # 提取的地名
    ner_confidence: float
    
    # Guardrails
    guardrail_passed: bool
    guardrail_message: Optional[str]
    
    # Tool Calling
    tools_to_call: List[str]
    tool_results: Dict[str, Any]
    
    # RAG Retrieval
    retrieved_docs: List[Document]
    retrieval_similarity: float
    
    # Answer Generation
    answer: str
    answer_confidence: float
    
    # Metadata
    processing_steps: List[Dict[str, Any]]
    timestamp: str
