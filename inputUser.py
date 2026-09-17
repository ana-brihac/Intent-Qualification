import nltk, json, difflib, os
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

tokens = word_tokenize(userInput.lower())

stop_words = set(stopwords.words('english'))
filtered_tokens = [word for word in tokens if word not in stop_words]

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

data = {'roles': [], 'fields': [], 'ambiguous_roles': [], 'ambiguous_fields': []}
	
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
		content=f.read()
  
	ambiguous_key = 'ambiguous_' + key
	prompt = content.replace("{x}", key).replace("{data}", json.dumps(data[ambiguous_key])).replace("{userInput}", userInput)

	interaction=client.interactions.create(
		model="gemini-3.8-flash",
		input=prompt
	)
 
	jason=json.loads(interaction.output_text)
	data[key].extend(jason[key])
	data[ambiguous_key] = []
 
if (needs_llm_roles == True):
	llm_resolve('roles')
 
if (needs_llm_fields == True):
	llm_resolve('fields')

with open("inputParse.json", "w") as result:
	json.dump(data, result)
