from google import genai
from pathlib import Path
import os, json
import sqlite3
import sys
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

client = genai.Client(api_key=GEMINI_API_KEY)

con = sqlite3.connect("companies.sqlite")
cur = con.cursor()

cur.execute("""
		CREATE TABLE IF NOT EXISTS COMPANIES (
		website TEXT PRIMARY KEY,
		operational_name TEXT,
		year_founded INTEGER,
		address TEXT,
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
		role TEXT
	)
""")

with open('companies.jsonl', 'r') as json_file:
	for json_str in json_file:
		result = json.loads(json_str)

		website = result.get('website')
		operational_name = result.get('operational_name')

		cur.execute(
			"SELECT 1 FROM COMPANIES WHERE website = ? OR (website IS NULL AND operational_name = ?)",
			(website, operational_name)
		)
		if cur.fetchone():
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

		interaction=client.interactions.create(
			model="gemini-3.8-flash",
			input=prompt
		)
  
		jason=json.loads(interaction.output_text)

		enriched_description=jason[enriched_description]
		role=jason[role]

		cur.execute(
			"""INSERT INTO COMPANIES (
				website, operational_name, year_founded, address, employee_count,
				revenue, primary_naics, secondary_naics, description, enriched_description,
				business_model, target_markets, core_offerings, is_public, role
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
			(
				website, operational_name, year_founded, address_json, employee_count,
				revenue, primary_naics_json, secondary_naics_json, description, enriched_description,
				business_model_json, target_markets_json, core_offerings_json, is_public_int, role
			)
		)

		con.commit()
  
con.close()