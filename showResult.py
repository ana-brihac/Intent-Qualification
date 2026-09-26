import json
import sqlite3

con = sqlite3.connect("companies.sqlite")
cur = con.cursor()

file = open("embeddedResult.json")
results = json.load(file)

file3 = open("inputParse.json")
input_data = json.load(file3)

line_width = 66

def read_name(company_id):
	rows = cur.execute("SELECT operational_name, website FROM COMPANIES WHERE id = ?", (company_id,))

	row = None
	for one_row in rows:
		row = one_row

	if row is None:
		return "unknown company"

	if row[0] is not None:
		return row[0]

	if row[1] is not None:
		return row[1]

	return "unknown company"

def read_country(company_id):
	rows = cur.execute("SELECT country_code FROM COMPANIES WHERE id = ?", (company_id,))

	row = None
	for one_row in rows:
		row = one_row

	if row is None:
		return "unknown"

	if row[0] is None:
		return "unknown"

	return row[0]

def pad(text, size):
	result = text

	while len(result) < size:
		result = result + " "

	return result

def separator():
	line = ""

	while len(line) < line_width:
		line = line + "="

	return line

matches = []

for item in results:
	if item['decision'] == 0:
		matches.append(item)

inconclusive = []

for item in results:
	if item['decision'] == 3:
		inconclusive.append(item)

checked = len(results) - len(inconclusive)

unique_matches = []
already_shown = []

for item in matches:
	name = item['name']

	if name is None:
		name = read_name(item['id'])

	key = str(name).lower() + " " + read_country(item['id'])

	if key not in already_shown:
		already_shown.append(key)
		unique_matches.append(item)

print("")
print(separator())
print("  " + input_data['raw_query'])
print(separator())
print("")

if len(input_data['extras']) > 0:
	print("  Conditions read from the query:")

	for extra in input_data['extras']:
		value = extra['value']

		if isinstance(value, list):
			value = ", ".join(value)

		print("    " + extra['field'] + " " + extra['operator'] + " " + str(value))

	print("")

if len(input_data['roles']) > 0:
	print("  Roles asked by the query: " + ", ".join(input_data['roles']))
	print("")

if len(unique_matches) == 0:
	print("  NO MATCHES")
	print("  " + str(checked) + " companies were checked and none of them matched the query.")
else:
	print("  MATCHES: " + str(len(unique_matches)) + " out of " + str(checked) + " companies checked")
	print("")

	number = 0

	for item in unique_matches:
		number = number + 1

		name = item['name']

		if name is None:
			name = read_name(item['id'])

		role_text = "no"

		if item['role_match'] == True:
			role_text = "yes"

		print("   " + pad(str(number) + ".", 4) + pad(str(name), 38) + "similarity " + str(round(item['similarity'], 3)) + "   role match " + role_text)

print("")

if len(inconclusive) > 0:
	print("  INCONCLUSIVE FIRMS (NOT ENOUGH DATA): " + str(len(inconclusive)))
	print("  These companies pass every condition we could check, but a field the query")
	print("  needs is empty for them, so we cannot say yes or no.")
	print("  The closest ones to the query are first.")
	print("")

	shown = 0

	for item in inconclusive:
		if shown < 10:
			name = item['name']

			if name is None:
				name = read_name(item['id'])

			print("   - " + str(name))
			shown = shown + 1

	if len(inconclusive) > 10:
		left = len(inconclusive) - 10
		print("   ... and " + str(left) + " more")

	print("")

con.close()