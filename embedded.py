from google import genai
from pathlib import Path
import os, json
import sqlite3
import math
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

client = genai.Client(api_key=GEMINI_API_KEY)

con = sqlite3.connect("companies.sqlite")
cur = con.cursor()

file = open("candidates.json")
candidates_data = json.load(file)

file2 = open("inputParse.json")
input_data = json.load(file2)

companies = candidates_data['companies']
query_roles = input_data['roles']

embedding_response = client.models.embed_content(
	model="gemini-embedding-2",
	contents=input_data['query_text']
)
query_embedding = embedding_response.embeddings

def cosine_similarity(vec1, vec2):
	dot_product = 0
	for i in range(len(vec1)):
		dot_product = dot_product + vec1[i] * vec2[i]

	norm1 = 0
	for value in vec1:
		norm1 = norm1 + value * value
	norm1 = math.sqrt(norm1)

	norm2 = 0
	for value in vec2:
		norm2 = norm2 + value * value
	norm2 = math.sqrt(norm2)

	return dot_product / (norm1 * norm2)

results = []

for website in companies:
	cur.execute("SELECT embedding, role FROM COMPANIES WHERE website = ?", (website,))
	row = cur.fetchone()

	company_embedding = json.loads(row[0])
	company_roles = row[1].split(",")

	similarity_score = cosine_similarity(query_embedding, company_embedding)

	role_match = False
	for role in query_roles:
		if role in company_roles:
			role_match = True

	results.append({
		"website": website,
		"similarity": similarity_score,
		"role_match": role_match
	})

result_file = open("embeddedResult.json", "w")
json.dump(results, result_file)

con.close()