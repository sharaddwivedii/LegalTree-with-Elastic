from docx import Document
import os

def docx_to_txt(docx_path, txt_path):
    doc = Document(docx_path)
    if not os.path.exists(os.path.dirname(txt_path)):
        os.makedirs(os.path.dirname(txt_path))
    with open(txt_path, 'w', encoding='utf-8') as file:
        for para in doc.paragraphs:
            file.write(para.text + '\n')


docx_path = 'Aug2022.docx'
txt_path = 'output/Aug2022.txt'
docx_to_txt(docx_path, txt_path)

with open(txt_path, 'r', encoding='utf-8') as file:
    text = file.read()
cases = text.split("----------")
if not os.path.exists('Cases'):
    os.makedirs("Cases")

for index, case in enumerate(cases):
    if index == 0:
        section_file_path = os.path.join('Cases', 'index.txt')
    else:
        section_file_path = os.path.join('Cases', f'Case_{index}.txt')
    with open(section_file_path, 'w', encoding='utf-8') as file_section:
        file_section.write(case.strip())
