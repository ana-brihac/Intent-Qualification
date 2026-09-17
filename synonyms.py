from google import genai
from pathlib import Path
import os, json
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

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
  
	interaction=client.interactions.create(
		model="gemini-3.8-flash",
		input=content
	)

	try:
		jason=json.loads(interaction.output_text)
	except json.JSONDecodeError:
		print(f"Failed to parse JSON response for keys: {keys}")
		print(interaction.output_text)
		raise
	return jason

def expand(fileContent):
	with open("expandPrompt.txt", "r") as f:
		content=f.read()

	content=content.replace("{fileContent}", fileContent)

	interaction=client.interactions.create(
		model="gemini-3.8-flash",
		input=content
	)

	try:
		jason=json.loads(interaction.output_text)
	except json.JSONDecodeError:
		print(f"Failed to parse JSON response for keys: {fileContent}")
		print(interaction.output_text)
		raise
	return jason


start("fields.json", "employee_count, revenue, is_public, year_founded, address")
start("roles.json", "supplier, manufacturer, distributor, retailer, buyer, competitor, service_provider")