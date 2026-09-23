import nltk, json, difflib, os, spacy
from google import genai
from dotenv import load_dotenv
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
nltk.download('stopwords')
nltk.download('punkt')
nltk.download('punkt_tab')

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

client = genai.Client(api_key=GEMINI_API_KEY)

userInput = input()

nlp = spacy.load("en_core_web_sm")
doc = nlp(userInput)

data = {'roles': [], 'fields': [], 'ambiguous_roles': [], 'ambiguous_fields': [], "extras": [], "query_text": ""}
tokens = word_tokenize(userInput.lower())

stop_words = set(stopwords.words('english'))
filtered_tokens = [word for word in tokens if word not in stop_words]

data['query_text'] = " ".join(filtered_tokens)

with open("fields.json", "r") as file:
	unflat_fields = json.load(file)

with open("roles.json", "r") as file:
	unflat_roles = json.load(file)

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
		matches = difflib.get_close_matches(word, synonyms)
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
			for synonym in unflat_file[key]:
				if synonym == match:
					matched.append(key)

		if len(matched) > 1:
			needs_llm = True
			data[ambiguous].append({
				'word': match,
				'candidates': matched
			})
		else:
			data[name].extend(matched)

	return needs_llm

needs_llm_roles = reverse_lookup(role_matches, unflat_roles, 'roles', 'ambiguous_roles')
needs_llm_fields = reverse_lookup(field_matches, unflat_fields, 'fields', 'ambiguous_fields')

def llm_resolve(key):
	with open("ambiguousPrompt.txt", "r") as f:
		content = f.read()

	ambiguous_key = 'ambiguous_' + key
	prompt = content.replace("{x}", key).replace("{data}", json.dumps(data[ambiguous_key])).replace("{userInput}", userInput)

	interaction = client.interactions.create(
		model="gemini-3.8-flash",
		input=prompt
	)

	jason = json.loads(interaction.output_text)
	data[key].extend(jason[key])
	data[ambiguous_key] = []

if (needs_llm_roles == True):
	llm_resolve('roles')

if (needs_llm_fields == True):
	llm_resolve('fields')

operator = {">"  : ["over", "more than", "above", "exceeding", "greater than"], "<": ["under", "less than", "below", "fewer than"], ">=": ["at least", "minimum"], "<=" : ["at most", "maximum"], "==": ["exactly", "precisely"]}

for ent in doc.ents:
	label = ent.label_

	if label == "GPE":
		data['extras'].append({"field": "address", "operator": "==", "value": ent.text})
	elif label == "MONEY":
		pre = doc[max(0, ent.start - 2)].text + " " + doc[max(0, ent.start - 1)].text

		for key in operator:
			for text in operator[key]:
				if text in pre:
					data['extras'].append({"field": "revenue", "operator": key, "value": ent.text})
	elif label == "DATE":
		pre = doc[max(0, ent.start - 2)].text + " " + doc[max(0, ent.start - 1)].text

		for key in operator:
			for text in operator[key]:
				if text in pre:
					data['extras'].append({"field": "year_founded", "operator": key, "value": ent.text})
	elif label == "CARDINAL":
		if "employee_count" in data['fields'] and "revenue" not in data['fields']:
			pre = doc[max(0, ent.start - 2)].text + " " + doc[max(0, ent.start - 1)].text
			for key in operator:
				for text in operator[key]:
					if text in pre:
						data['extras'].append({"field": "employee_count", "operator": key, "value": ent.text})

with open("inputParse.json", "w") as result:
	json.dump(data, result)