"""
配置文件 - 地名自动化项目
作用：统一管理所有配置参数

使用方法：
    from config import Config
    api_key = Config.API_KEY
"""

import os
from pathlib import Path


class Config:
    """项目配置"""
    
    # ==================== 项目根目录 ====================
    PROJECT_ROOT = Path(__file__).parent
     
    # ==================== API配置 ====================
    API_KEY = "sk-gswitcfpsevlgfleazpwptqtpuolngnbzqvtbkeuexeqiyid"
    API_BASE_URL = "https://api.siliconflow.cn/v1"
    
    # ==================== 模型配置 ====================
    
    # 分类任务我用的qwen-plus
    CLASSIFICATION_MODEL = "Qwen/Qwen2.5-7B-Instruct"
    CLASSIFICATION_TEMP = 0.0
    CLASSIFICATION_MAX_TOKENS = 500
    
    # RAG生成我用的qwen-max  
    RAG_MODEL = "Qwen/Qwen2.5-72B-Instruct"
    RAG_TEMP = 0.1
    RAG_MAX_TOKENS = 2048
    RAG_RETRIEVAL_K = 6
    
    # Embedding用的bge
    EMBEDDING_MODEL = "BAAI/bge-m3"
    EMBEDDING_CHUNK_SIZE = 64
    
    # ==================== 路径配置 ====================
    
    # 输入输出目录
    DATABASE_DIR = str(PROJECT_ROOT / "database")
    RESULTS_DIR = str(PROJECT_ROOT / "results")
    
    # 向量库路径
    FAISS_INDEX_PATH = str(PROJECT_ROOT / "faiss_index_storage")
    
    # ==================== 文件名配置 ====================
    
    # Step 2 输出
    PLACENAME_RECORDS = "placename_records.csv"
    PLACENAME_RECORDS_RESOLVED = "placename_records_resolved.csv"
    
    # Step 3 输出
    BATCH_CLASSIFICATION = "batch_classification_results.csv"
    EXTRACTED_STRONG = "extracted_STRONG.csv"
    EXTRACTED_WEAK = "extracted_WEAK.csv"
    EXTRACTED_NONE = "extracted_NONE.csv"
    
    # Step 4 输出（在results/目录下）
    ANALYSIS_INSIGHTS_CSV = "analysis_insights.csv"
    ANALYSIS_INSIGHTS_MD = "analysis_insights.md"
    ANALYSIS_INSIGHTS_JSON = "analysis_insights.json"
    
    # ==================== Pipeline参数 ====================
    
    # Step 3: 正则表达式模式
    STRONG_PATTERNS = [
        r"因.*?名之", r"因.*?為名", r"因.*?故名",
        r"以.*?為名", r"取.*?之義", r"取.*?名之",
        r"故名", r"故曰", r"改曰"
    ]
    
    # Step 2: 地名后缀
    PLACE_SUFFIXES = [
        "縣", "州", "郡", "府", "道", "山", "水", "河", "川",
        "原", "谷", "城", "關", "津", "坡", "陵", "宮", "溪", "岩", "潭"
    ]
    
    # Step 2: 停用词
    STOP_START_WORDS = [
        "在", "及", "与", "之", "其", "此", "旧", "从", "至", "界", "有", "谓"
    ]
    
    # Step 2: 朝代
    DYNASTIES = [
        "漢", "魏", "晉", "隋", "唐", "宋", "元", "明", "清", 
        "秦", "齊", "梁", "周", "後漢", "元魏", "北齊"
    ]
    
    # Step 2: 行政区划
    ADMIN_LEVELS = ["郡", "州", "府", "道", "路"]
    
    # Step 2: 前缀动词
    PREFIX_VERBS = [
        "置", "改", "分", "析", "移", "隸", "屬", "并", 
        "於", "在", "本", "舊", "今", "尋", "此"
    ]
    
    # ==================== 运行参数 ====================
    
    # API调用间隔（秒）
    API_CALL_INTERVAL = 0.6
    
    # 进度保存频率
    SAVE_FREQUENCY = 5
    
    # Manual Evaluation抽样比例
    SAMPLE_FRAC = 0.02
    
    # ==================== 辅助方法 ====================
    
    @classmethod
    def setup_environment(cls):
        """设置环境变量（供langchain使用）"""
        os.environ["OPENAI_API_KEY"] = cls.API_KEY
        os.environ["OPENAI_BASE_URL"] = cls.API_BASE_URL
        os.environ["PYTHONIOENCODING"] = "utf-8"
    
    @classmethod
    def ensure_dirs(cls):
        """确保目录存在"""
        Path(cls.DATABASE_DIR).mkdir(exist_ok=True)
        Path(cls.RESULTS_DIR).mkdir(exist_ok=True)
    
    @classmethod
    def print_config(cls):
        """打印当前配置"""
        print("="*60)
        print("当前配置")
        print("="*60)
        print(f"分类模型: {cls.CLASSIFICATION_MODEL}")
        print(f"RAG模型: {cls.RAG_MODEL}")
        print(f"Embedding: {cls.EMBEDDING_MODEL}")
        print("="*60)


# 测试
if __name__ == "__main__":
    Config.print_config()
    Config.ensure_dirs()
    print("\n Config配置正常")