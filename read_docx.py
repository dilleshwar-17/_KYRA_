import zipfile
import xml.etree.ElementTree as ET
import sys

def read_docx(path):
    with zipfile.ZipFile(path, 'r') as z:
        xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        paragraphs = []
        for p in tree.findall('.//w:p', ns):
            texts = [t.text for t in p.findall('.//w:t', ns) if t.text]
            if texts:
                paragraphs.append(''.join(texts))
        return '\n'.join(paragraphs)

try:
    content = read_docx(r'C:\Users\srira\OneDrive\Desktop\New folder (4)\KYRA_Doc.docx')
    with open('kyra_doc_content.txt', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Success")
except Exception as e:
    print(f"Error: {e}")
