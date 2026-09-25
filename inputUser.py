import nltk, json, difflib, os, spacy, sys
from google import genai
from dotenv import load_dotenv
from llmCall import ask_llm
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
nltk.download('stopwords')
nltk.download('punkt')
nltk.download('punkt_tab')

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if GEMINI_API_KEY is None:
	print("There is no GEMINI_API_KEY. Please create a .env file, the .env.example file shows how.")
	sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

userInput = input()

nlp = spacy.load("en_core_web_sm")
doc = nlp(userInput)

data = {'roles': [], 'fields': [], 'ambiguous_roles': [], 'ambiguous_fields': [], "extras": [], "query_text": "", "raw_query": ""}
tokens = word_tokenize(userInput.lower())

stop_words = set(stopwords.words('english'))
filtered_tokens = [word for word in tokens if word not in stop_words]

data['query_text'] = " ".join(filtered_tokens)
data['raw_query'] = userInput

with open("fields.json", "r") as file:
	unflat_fields = json.load(file)

with open("roles.json", "r") as file:
	unflat_roles = json.load(file)

with open("countries.json", "r") as file:
	countries = json.load(file)

def flatten_file(content):
	keys = content.keys()
	synonyms = []

	for key in keys:
		synonyms.append(key)
		synonyms.extend(content[key])

	return synonyms

flatten_fields = flatten_file(unflat_fields)
flatten_roles = flatten_file(unflat_roles)

def find_matches(synonyms):
	all_matches = []
	for word in filtered_tokens:
		matches = difflib.get_close_matches(word, synonyms, 1, 0.85)
		all_matches.extend(matches)
	return all_matches

field_matches = find_matches(flatten_fields)
role_matches = find_matches(flatten_roles)

def reverse_lookup(matches, unflat_file, name, ambiguous):
	keys = unflat_file.keys()
	needs_llm = False

	for match in matches:
		matched = []

		for key in keys:
			found = False

			if key == match:
				found = True

			for synonym in unflat_file[key]:
				if synonym == match:
					found = True

			if found:
				matched.append(key)

		if len(matched) > 1:
			needs_llm = True
			data[ambiguous].append({
				'word': match,
				'candidates': matched
			})
		else:
			for key in matched:
				if key not in data[name]:
					data[name].append(key)

	return needs_llm

needs_llm_roles = reverse_lookup(role_matches, unflat_roles, 'roles', 'ambiguous_roles')
needs_llm_fields = reverse_lookup(field_matches, unflat_fields, 'fields', 'ambiguous_fields')

def llm_resolve(key):
	with open("ambiguousPrompt.txt", "r") as f:
		content = f.read()

	ambiguous_key = 'ambiguous_' + key
	prompt = content.replace("{x}", key).replace("{data}", json.dumps(data[ambiguous_key])).replace("{userInput}", userInput)

	jason = ask_llm(client, prompt)
	data[key].extend(jason[key])
	data[ambiguous_key] = []

if (needs_llm_roles == True):
	llm_resolve('roles')

if (needs_llm_fields == True):
	llm_resolve('fields')

operator = {">"  : ["over", "more than", "above", "exceeding", "greater than", "after"], "<": ["under", "less than", "below", "fewer than", "before"], ">=": ["at least", "minimum", "since"], "<=" : ["at most", "maximum"], "==": ["exactly", "precisely"]}

def find_location(text):
	name = text.lower()

	if name.startswith("the "):
		name = name[4:]

	if name in countries['countries']:
		return [countries['countries'][name]]

	if name in countries['regions']:
		return countries['regions'][name]

	return None

def clean_number(text):
	text = text.lower()
	number = ""

	for character in text:
		if character.isdigit() or character == ".":
			number = number + character

	if number == "":
		return None

	value = float(number)

	if "billion" in text:
		value = value * 1000000000
	elif "million" in text:
		value = value * 1000000
	elif "thousand" in text:
		value = value * 1000

	return int(value)

def find_operator(ent):
	before = ""

	if ent.start >= 2:
		before = doc[ent.start - 2].text + " " + doc[ent.start - 1].text
	elif ent.start == 1:
		before = doc[0].text

	text = " " + before.lower() + " " + ent.text.lower() + " "

	for key in operator:
		for word in operator[key]:
			if " " + word + " " in text:
				return key

	return "=="

def add_number_extra(field, ent):
	value = clean_number(ent.text)

	if value is not None:
		data['extras'].append({"field": field, "operator": find_operator(ent), "value": value})

for ent in doc.ents:
	label = ent.label_

	if label == "GPE" or label == "LOC":
		codes = find_location(ent.text)

		if codes is not None:
			data['extras'].append({"field": "country_code", "operator": "IN", "value": codes})
	elif label == "MONEY":
		add_number_extra("revenue", ent)
	elif label == "DATE":
		add_number_extra("year_founded", ent)
	elif label == "CARDINAL":
		if "employee_count" in data['fields'] and "revenue" not in data['fields']:
			add_number_extra("employee_count", ent)

if "is_public" in data['fields']:
	data['extras'].append({"field": "is_public", "operator": "==", "value": 1})

with open("inputParse.json", "w") as result:
	json.dump(data, result)