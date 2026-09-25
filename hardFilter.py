import json
import sqlite3

def build_condition(item, values):
	if item['operator'] == "IN":
		marks = ""

		for one_value in item['value']:
			if marks != "":
				marks = marks + ", "

			marks = marks + "?"
			values.append(one_value)

		return item['field'] + " IN (" + marks + ")"

	values.append(item['value'])
	return item['field'] + " " + item['operator'] + " ?"

con = sqlite3.connect("companies.sqlite")
cur = con.cursor()

file = open("inputParse.json")
content = json.load(file)
companies = []
inconclusive = []

if len(content['extras']) == 0:
	rows = cur.execute("SELECT id FROM COMPANIES")

	for row in rows:
		companies.append(row[0])
else:
	conditions = []
	maybe_conditions = []
	values = []

	for item in content['extras']:
		condition = build_condition(item, values)
		conditions.append(condition)
		maybe_conditions.append("(" + item['field'] + " IS NULL OR " + condition + ")")

	where_clause = conditions[0]
	for i in range(1, len(conditions)):
		where_clause = where_clause + " AND " + conditions[i]

	query = "SELECT id FROM COMPANIES WHERE " + where_clause
	rows = cur.execute(query, values)

	for row in rows:
		companies.append(row[0])

	maybe_clause = maybe_conditions[0]
	for i in range(1, len(maybe_conditions)):
		maybe_clause = maybe_clause + " AND " + maybe_conditions[i]

	maybe_query = "SELECT id FROM COMPANIES WHERE " + maybe_clause
	maybe_rows = cur.execute(maybe_query, values)

	for row in maybe_rows:
		if row[0] not in companies:
			inconclusive.append(row[0])

result = open("candidates.json", "w")
json.dump({"companies": companies, "inconclusive": inconclusive}, result)

con.close()