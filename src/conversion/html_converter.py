from bs4 import BeautifulSoup
import os
from pathlib import Path
from config import Config

class HTMLToTextConverter:
    """HTML转文本转换器"""
    
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def extract_ctext_text(self, html_content: str) -> str:
        """从HTML中提取ctext类的文本内容"""
        soup = BeautifulSoup(html_content, "html.parser")
        nodes = soup.find_all("td", class_="ctext")
        texts = [n.get_text(separator="\n", strip=True) for n in nodes]
        return "\n\n".join(texts)
    
    def convert_all(self) -> dict:
        """转换所有HTML文件，返回统计信息"""
        html_files = list(self.input_dir.glob("*.html"))
        stats = {"success": 0, "failed": 0, "skipped": 0}
        
        for i, html_file in enumerate(html_files, 1):
            print(f"[{i}/{len(html_files)}] 处理: {html_file.name}")
            
            try:
                with open(html_file, "r", encoding="utf-8") as f:
                    html = f.read()
                
                clean_text = self.extract_ctext_text(html)
                
                # 检查是否提取到内容
                if not clean_text.strip():
                    print(f"  ⚠️  警告: 文件为空，跳过")
                    stats["skipped"] += 1
                    continue
                
                output_file = self.output_dir / html_file.name.replace(".html", ".txt")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(clean_text)
                
                stats["success"] += 1
            except Exception as e:
                print(f"  ❌ 错误: {e}")
                stats["failed"] += 1
        
        return stats

def main():
    
    input_path = "/Users/johnjennings/Desktop/地名自动化/"
    output_path = "/Users/johnjennings/Desktop/地名自动化/database"
    
    converter = HTMLToTextConverter(input_path, output_path)
    stats = converter.convert_all()
    
    print(f"\n 转换完成!")
    print(f"成功: {stats['success']} | 失败: {stats['failed']} | 跳过: {stats['skipped']}")

if __name__ == "__main__":
    main()