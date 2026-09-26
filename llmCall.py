import time, json

def ask_llm(client, prompt):
	wait = 2
	attempt = 0
	output_text = None

	while attempt < 5:
		try:
			interaction = client.interactions.create(
				model="gemini-3.5-flash-lite",
				input=prompt
			)
			output_text = interaction.output_text

			if output_text is None:
				raise ValueError("the model returned no text")

			return json.loads(output_text)
		except Exception as error:
			attempt = attempt + 1

			if "per day" in str(error):
				print("The daily limit for the model is finished, I cannot ask the LLM anymore.")
				raise

			if attempt == 5:
				print("The last answer from the model was:")
				print(output_text)
				raise

			print("LLM call failed (" + str(error)[:80] + "), retry " + str(attempt) + " in " + str(wait) + "s")
			time.sleep(wait)
			wait = wait * 2