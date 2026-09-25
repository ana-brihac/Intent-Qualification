from google import genai
from pathlib import Path
import os, json, ast
import sqlite3
import sys
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

cur.execute("""
        CREATE TABLE IF NOT EXISTS COMPANIES (
        id INTEGER PRIMARY KEY,
        website TEXT,
        operational_name TEXT,
        year_founded INTEGER,
        address TEXT,
        country_code TEXT,
        employee_count INTEGER,
        revenue INTEGER,
        primary_naics TEXT,
        secondary_naics TEXT,
        description TEXT,
        enriched_description TEXT,
        business_model TEXT,
        target_markets TEXT,
        core_offerings TEXT,
        is_public INTEGER,
        role TEXT,
        embedding TEXT
    )
""")

def read_country_code(address):
	value = address

	if isinstance(value, str):
		try:
			value = ast.literal_eval(value)
		except Exception:
			value = None

	if isinstance(value, dict):
		return value.get('country_code')

	return None

with open('companies.jsonl', 'r') as json_file:
	for json_str in json_file:
		result = json.loads(json_str)

		website = result.get('website')
		operational_name = result.get('operational_name')

		rows = cur.execute(
			"SELECT 1 FROM COMPANIES WHERE website = ? OR (website IS NULL AND operational_name = ?)",
			(website, operational_name)
		)

		already_there = False
		for row in rows:
			already_there = True

		if already_there:
			continue

		year_founded = result.get('year_founded')
		address = result.get('address')
		employee_count = result.get('employee_count')
		revenue = result.get('revenue')
		primary_naics = result.get('primary_naics')
		secondary_naics = result.get('secondary_naics')
		description = result.get('description')
		business_model = result.get('business_model')
		target_markets = result.get('target_markets')
		core_offerings = result.get('core_offerings')
		is_public = result.get('is_public')

		country_code = read_country_code(address)
		address_json = json.dumps(address) if address is not None else None
		primary_naics_json = json.dumps(primary_naics) if primary_naics is not None else None
		secondary_naics_json = json.dumps(secondary_naics) if secondary_naics is not None else None
		business_model_json = json.dumps(business_model) if business_model is not None else None
		target_markets_json = json.dumps(target_markets) if target_markets is not None else None
		core_offerings_json = json.dumps(core_offerings) if core_offerings is not None else None
		is_public_int = 1 if is_public else 0

		with open("populatePrompt.txt", "r") as f:
				content=f.read()

		company_summary = json.dumps(result)
		prompt = content.replace("{company}", company_summary)

		jason=ask_llm(client, prompt)

		enriched_description=jason["enriched_description"]
		role=jason["role"]

		embedding_text = enriched_description

		if business_model is not None:
			for item in business_model:
				embedding_text = embedding_text + " " + item

		if target_markets is not None:
			for item in target_markets:
				embedding_text = embedding_text + " " + item

		if core_offerings is not None:
			for item in core_offerings:
				embedding_text = embedding_text + " " + item

		embedding_response = client.models.embed_content(
			model="gemini-embedding-2",
			contents=embedding_text
		)
		embedding = embedding_response.embeddings[0].values
		embedding_json = json.dumps(embedding)

		cur.execute(
			"""INSERT INTO COMPANIES (
                website, operational_name, year_founded, address, country_code, employee_count,
                revenue, primary_naics, secondary_naics, description, enriched_description,
                business_model, target_markets, core_offerings, is_public, role, embedding
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
			(
				website, operational_name, year_founded, address_json, country_code, employee_count,
				revenue, primary_naics_json, secondary_naics_json, description, enriched_description,
				business_model_json, target_markets_json, core_offerings_json, is_public_int, role, embedding_json
			)
		)

		con.commit()

con.close()