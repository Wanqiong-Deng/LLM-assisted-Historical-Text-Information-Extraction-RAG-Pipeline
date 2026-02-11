from bs4 import BeautifulSoup
import os

input_path = "/Users/johnjennings/Desktop/地名自动化/"   
output_path = "/Users/johnjennings/Desktop/地名自动化/database"      
os.makedirs(output_path, exist_ok=True)

def extract_ctext_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    nodes = soup.find_all("td", class_="ctext")
    texts = []
    for n in nodes:
        t = n.get_text(separator="\n", strip=True)
        texts.append(t)
    return "\n\n".join(texts)

for file in os.listdir(input_path):
    if file.endswith(".html"):
        with open(os.path.join(input_path, file), "r", encoding="utf-8") as f:
            html = f.read()

        clean_text = extract_ctext_text(html)

        with open(os.path.join(output_path, file.replace(".html", ".txt")), 
                  "w", encoding="utf-8") as f:
            f.write(clean_text)

print("全部转换完成！")
