from google import genai
import os, json, sys
import sqlite3
import math
from dotenv import load_dotenv
from llmCall import ask_llm

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if GEMINI_API_KEY is None:
	print("There is no GEMINI_API_KEY. Please create a .env file, the .env.example file shows how.")
	sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

con = sqlite3.connect("companies.sqlite")
cur = con.cursor()

file = open("candidates.json")
candidates_data = json.load(file)

file2 = open("inputParse.json")
input_data = json.load(file2)

companies = candidates_data['companies']
query_roles = input_data['roles']

all_roles = []

rows = cur.execute("SELECT role FROM COMPANIES")
for row in rows:
	if row[0] is not None:
		for one_role in row[0].split(","):
			all_roles.append(one_role.strip())

usable_roles = []
for role in query_roles:
	if role in all_roles:
		usable_roles.append(role)

match_margin = 0.03
debatable_margin = 0.06
llm_limit = 10

embedding_response = client.models.embed_content(
	model="gemini-embedding-2",
	contents=input_data['query_text']
)
query_embedding = embedding_response.embeddings[0].values

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

def llm_verify(company_id, description, role, similarity_score, role_match):
	prompt_file = open("verifyPrompt.txt")
	content = prompt_file.read()

	prompt = content.replace("{userInput}", input_data['raw_query'])
	prompt = prompt.replace("{description}", str(description))
	prompt = prompt.replace("{role}", str(role))
	prompt = prompt.replace("{similarity}", str(similarity_score))
	prompt = prompt.replace("{role_match}", str(role_match))

	try:
		jason = ask_llm(client, prompt)
		return jason["decision"]
	except Exception as error:
		print("The LLM could not be reached (" + str(error)[:80] + "), keeping this company out of the matches")
		return 1

def llm_recheck(rejected):
	prompt_file = open("recheckPrompt.txt")
	content = prompt_file.read()

	companies_text = ""

	for item in rejected:
		companies_text = companies_text + "id " + str(item['id']) + ", role " + str(item['role_text']) + ", " + str(item['description'])[:400] + "\n"

	prompt = content.replace("{userInput}", input_data['raw_query'])
	prompt = prompt.replace("{companies}", companies_text)

	try:
		jason = ask_llm(client, prompt)
		return jason["matches"]
	except Exception as error:
		print("The LLM could not be reached (" + str(error)[:80] + "), keeping the result as it is")
		return []

results = []

for company_id in companies:
	rows = cur.execute("SELECT embedding, role, enriched_description, operational_name FROM COMPANIES WHERE id = ?", (company_id,))

	row = None
	for one_row in rows:
		row = one_row

	company_embedding = json.loads(row[0])

	company_roles = []

	if row[1] is not None:
		for one_role in row[1].split(","):
			company_roles.append(one_role.strip())

	similarity_score = cosine_similarity(query_embedding, company_embedding)

	role_match = False
	for role in usable_roles:
		if role in company_roles:
			role_match = True

	results.append({
		"id": company_id,
		"name": row[3],
		"similarity": similarity_score,
		"role_match": role_match,
		"decision": 1,
		"role_text": row[1],
		"description": row[2]
	})

def by_similarity(item):
	return item['similarity']

results.sort(key=by_similarity, reverse=True)

if len(results) > 0:
	best_similarity = results[0]['similarity']
	llm_calls = 0

	for item in results:
		if item['similarity'] >= best_similarity - match_margin:
			if len(usable_roles) == 0 or item['role_match'] == True:
				item['decision'] = 0
			else:
				item['decision'] = llm_verify(item['id'], item['description'], item['role_text'], item['similarity'], item['role_match'])
		elif item['similarity'] >= best_similarity - debatable_margin and llm_calls < llm_limit:
			item['decision'] = llm_verify(item['id'], item['description'], item['role_text'], item['similarity'], item['role_match'])
			llm_calls = llm_calls + 1
		else:
			item['decision'] = 1

matches = 0

for item in results:
	if item['decision'] == 0:
		matches = matches + 1

if len(results) > 0 and (matches == 0 or (matches <= 2 and len(results) >= 20)):
	print("Only " + str(matches) + " matches out of " + str(len(results)) + " companies, asking the LLM if the filters were too strict")

	rejected = []

	for item in results:
		if item['decision'] == 1 and len(rejected) < 10:
			rejected.append(item)

	found = llm_recheck(rejected)

	for item in results:
		if item['id'] in found:
			item['decision'] = 0

inconclusive_results = []

for company_id in candidates_data['inconclusive']:
	rows = cur.execute("SELECT embedding, role, enriched_description, operational_name FROM COMPANIES WHERE id = ?", (company_id,))

	row = None
	for one_row in rows:
		row = one_row

	company_embedding = json.loads(row[0])

	inconclusive_results.append({
		"id": company_id,
		"name": row[3],
		"similarity": cosine_similarity(query_embedding, company_embedding),
		"role_match": False,
		"decision": 3,
		"role_text": row[1],
		"description": row[2]
	})

inconclusive_results.sort(key=by_similarity, reverse=True)

for item in inconclusive_results:
	results.append(item)

clean_results = []

for item in results:
	clean_results.append({
		"id": item['id'],
		"name": item['name'],
		"similarity": item['similarity'],
		"role_match": item['role_match'],
		"decision": item['decision']
	})

result_file = open("embeddedResult.json", "w")
json.dump(clean_results, result_file)

con.close()