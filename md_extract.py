import re
import json
import os
from pymongo import MongoClient

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['lawbot_database']
collection = db['case_metadata']

def extract_metadata(file_path):
  with open(file_path, 'r', encoding='utf-8') as file:
    text = file.read()

  filename = os.path.basename(file_path)

  metadata = {
      'Filename': filename,
      'Location': '',
      'Date': '',
      'Judges': [],
      'Case Number': '',
      'Appellant': '',
      'Respondent': '',
      'Counsel for the Appellant': [],
      'Counsel for the Respondent': [],
      'Judgements/Case law relied upon': []
  }

  # Define synonym sets
  appellant_synonyms = {"Appellant", "Petitioner","Appellants","Applicant","Petitioners"}
  respondent_synonyms = {"Respondent", "Respondents", "Defendant", "Defendants", "Opposite Party","Opposite Parties"}
  counsel_synonyms = {"Counsel", "Advocate", "Advocates", "Attorney", "Attorneys"}

  # Regex patterns with synonyms and optional plural forms
  location_match = re.search(r'DATED: (.*?) \d{2}\.\d{2}\.\d{4}', text)
  if location_match:
    metadata['Location'] = location_match.group(1).strip()

  date_match = re.search(r'DATED: .*? (\d{2}\.\d{2}\.\d{4})', text)
  if date_match:
    metadata['Date'] = date_match.group(1).strip()

  judges_match = re.search(r'BEFORE\n(.*?)\n\n', text, re.DOTALL)
  if judges_match:
    judges_text = judges_match.group(1).replace('\u2019', "'").strip()
    metadata['Judges'] = [judge.strip() for judge in judges_text.split('\n')]

  case_number_match = re.search(r'(?:.*?, J\.\n)+(.+?)\n\n', text, re.DOTALL)
  if case_number_match:
    metadata['Case Number'] = case_number_match.group(1).strip()

  case_number_metadata = metadata['Case Number']
  appellant_match = re.search(rf"{re.escape(case_number_metadata)}\n\n({'|'.join(appellant_synonyms)})\s*\n(.*?)\s*\.{3}", text, re.DOTALL)
  if appellant_match:
    metadata['Appellant'] = appellant_match.group(2).strip()

  parties_match = re.search(rf'({"|".join(appellant_synonyms)})\s+Versus\s+({"|".join(respondent_synonyms)})\s+\u2026', text, re.DOTALL)
  if parties_match:
    metadata['Respondent'] = parties_match.group(2).strip()

  # Counsel with synonyms (considering singular/plural)
  counsel_appellant_match = re.search(rf'({"|".join(counsel_synonyms)}) for the ({"|".join(appellant_synonyms)})?:\n(.+?)(?=\n{1,2}Counsel|$)', text, re.DOTALL)
  if counsel_appellant_match:
    metadata['Counsel for the Appellant'] = [name.strip() for name in re.split(r',|\n', counsel_appellant_match.group(1).strip()) if name.strip()]

  counsel_respondent_match = re.search(rf'({"|".join(counsel_synonyms)}) for the ({"|".join(respondent_synonyms)})[s]?:\n(.+?)(?=\n\n|$)', text, re.DOTALL)
  if counsel_respondent_match:
    metadata['Counsel for the Respondent'] = [name.strip() for name in re.split(r',|\n', counsel_respondent_match.group(1).strip()) if name.strip()]

  judgments_match = re.search(r':-\s*\n\n(.*?)(?=\n\(Delivered by)', text, re.DOTALL)
  if judgments_match:
    cases = judgments_match.group(1).strip().split('\n\n')
    metadata['Judgements/Case law relied upon'] = [case.strip() for case in cases]

  return metadata

def save_metadata_to_mongodb(metadata):
    # Insert metadata into MongoDB
    result = collection.insert_one(metadata)
    print(f"Metadata inserted with ObjectId: {result.inserted_id}")

def process_all_txt_files(directory):
    for filename in os.listdir(directory):
        if filename.lower() == 'index.txt':
            continue
        elif filename.endswith('.txt') and filename.lower() != 'index.txt':
            file_path = os.path.join(directory, filename)
            print(f"Processing {filename}...")
            metadata = extract_metadata(file_path)
            save_metadata_to_mongodb(metadata)
            print(f"Metadata saved to MongoDB")

directory = "C:\\Users\\skdwi\\OneDrive\\Desktop\\LawBot\\Cases"
process_all_txt_files(directory)
