from google import genai
from pathlib import Path
import os, json, sys
from dotenv import load_dotenv
from llmCall import ask_llm

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if GEMINI_API_KEY is None:
	print("There is no GEMINI_API_KEY. Please create a .env file, the .env.example file shows how.")
	sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

def start(fname, keys):
	file = Path(fname)
	fileState = file.exists()
 
	if fileState:
		with open(fname, "r") as f:
			fileContent = f.read()

		output=expand(fileContent)
	else:
		output=create(keys)
  
	with open(fname, "w") as f:
			f.write(json.dumps(output, indent=2))
		
def create(keys):
	with open("createPrompt.txt", "r") as f:
		content=f.read()
  
	content=content.replace("{keys}", keys)
  
	jason=ask_llm(client, content)

	return jason

def expand(fileContent):
	with open("expandPrompt.txt", "r") as f:
		content=f.read()

	content=content.replace("{fileContent}", fileContent)

	jason=ask_llm(client, content)

	return jason


start("fields.json", "employee_count, revenue, is_public, year_founded, address")
start("roles.json", "supplier, manufacturer, distributor, retailer, buyer, competitor, service_provider")