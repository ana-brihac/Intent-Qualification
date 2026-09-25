# Intent Qualification

A company matching system. You write a query like "pharmaceutical companies in Switzerland"
and it decides which companies from the database are genuine matches for it.

The idea behind it is to use algorithms instead of an LLM for most of the work, so the system
is cheaper and faster, and to call the LLM only in the moments where an algorithm is not
reliable enough. The reasoning behind every decision is explained in WRITEUP.md.

## How it works

The query passes through four stages:

1. **User input processing** (`inputUser.py`) - cleans the query, finds which fields and roles
   it talks about, and extracts the conditions (country, revenue, employees, year, public).
2. **Hard filter** (`hardFilter.py`) - runs one SQL query with those conditions. Companies that
   are missing a field the query needs are put aside as inconclusive.
3. **Embedding and role comparison** (`embedded.py`) - compares the meaning of the query with the
   description of every company that passed, compares the roles, and decides. The LLM is called
   only for the cases that are not clear.
4. **Response composer** (`showResult.py`) - prints the matches and the inconclusive firms.

`solution.py` runs the four stages one after the other.

## Setup

You need Python 3 and a Gemini API key.

```
python -m venv .venv
.venv\Scripts\activate          (on Windows)
source .venv/bin/activate       (on Linux or macOS)

pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

The spaCy model is a separate download, it does not come with pip install.

Then create a file named `.env` in this folder with your key inside:

```
GEMINI_API_KEY=your_key_here
```

`.env.example` shows the format. The `.env` file is in `.gitignore`, so the key never
goes into the repository.

## Building the database (run this once)

```
python companies-population.py
```

This reads `companies.jsonl`, asks the LLM to enrich every company and to give it a role,
generates an embedding for each one, and saves everything in `companies.sqlite`.

It takes around 40 minutes for the 456 companies, because it is one LLM call and one embedding
call per company. On the free tier the model allows 500 requests per day, so the whole
population fits in one day, but not much more than that.

If the script stops in the middle, just run it again. It checks every company before working on
it, so it continues from where it stopped and does not pay twice for the same company.

## Running a query

```
python solution.py
```

It waits for you to type the query, then prints the answer. Example:

```
==================================================================
  Pharmaceutical companies in Switzerland
==================================================================

  Conditions read from the query:
    country_code IN ch

  MATCHES: 21 out of 43 companies checked

   1.  Siegfried                         similarity 0.692   role match no
   2.  Helsinn                           similarity 0.69    role match no
   3.  Novartis                          similarity 0.685   role match no
```

You can also run the stages one by one, in this order:

```
python inputUser.py
python hardFilter.py
python embedded.py
python showResult.py
```

## Reading the answer

Every company gets one label:

- **0** - match
- **1** - not a match
- **3** - inconclusive, the company is not refused, but a field that the query needs is empty
  for it, so the system cannot say yes or no

The inconclusive firms are printed in their own section, because "we do not know" is a different
answer from "no".

## Project structure

```
solution.py                 runs the whole pipeline
inputUser.py                stage 1, reads and understands the query
hardFilter.py               stage 2, the SQL filter
embedded.py                 stages 3 and 4, similarity, roles and scoring
showResult.py               prints the final answer
llmCall.py                  one place for the LLM calls, with retries
companies-population.py     builds the database, run once
synonyms.py                 creates or extends the synonym tables

companies.jsonl             the input data, 477 companies
companies.sqlite            the database, created by companies-population.py
fields.json                 synonyms for the structured fields
roles.json                  synonyms for the roles
countries.json              country and region names to country codes

populatePrompt.txt          prompt for the enrichment
createPrompt.txt            prompt for creating a synonym table
expandPrompt.txt            prompt for extending a synonym table
ambiguousPrompt.txt         prompt for a word that can mean two things
verifyPrompt.txt            prompt for an unclear company
recheckPrompt.txt           prompt for when the filters look too strict

inputParse.json             written by stage 1
candidates.json             written by stage 2
embeddedResult.json         written by stage 3
```

## The synonym tables

`fields.json` and `roles.json` are already in the repository, so you do not need to build them.
They were written by hand first and then reviewed and extended by the LLM. If you want to
extend them again:

```
python synonyms.py
```

## Notes

- The LLM is never called once per company on a normal query. It is called at most ten times,
  only for the companies that sit on the border of a decision.
- A query needs the API key even when the database is already built, because the query itself
  has to be turned into an embedding.