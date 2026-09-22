from pathlib import Path
import os, json
import sqlite3
import sys

con = sqlite3.connect("companies.sqlite")
cur = con.cursor()

file = open("inputParse.json")
content = json.load(file)
companies = []
inconclusive = []

if len(content['extras']) == 0:
	rows = cur.execute("SELECT website FROM COMPANIES")

	for row in rows:
		companies.append(row[0])
else:
	conditions = []
	values = []

	for item in content['extras']:
		conditions.append(item['field'] + " " + item['operator'] + " ?")
		values.append(item['value'])

	where_clause = conditions[0]
	for i in range(1, len(conditions)):
		where_clause = where_clause + " AND " + conditions[i]

	query = "SELECT website FROM COMPANIES WHERE " + where_clause
	rows = cur.execute(query, values)

	for row in rows:
		companies.append(row[0])

	null_cases = content['extras'][0]['field'] + " IS NULL"

	for i in range(1, len(content['extras'])):
		null_cases = null_cases + " OR " + content['extras'][i]['field'] + " IS NULL"

	null_query = "SELECT website FROM COMPANIES WHERE " + null_cases
	null_rows = cur.execute(null_query)

	for row in null_rows:
		inconclusive.append(row[0])

result = open("candidates.json", "w")
json.dump({"companies": companies, "inconclusive": inconclusive}, result)

con.close()