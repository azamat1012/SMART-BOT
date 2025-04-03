import os
import json

from dotenv import load_dotenv
from google.cloud import dialogflow


def create_intent(project_id, intent_name, training_phrases_parts, message_texts):
    """Create an intent of the given intent type."""
    intents_client = dialogflow.IntentsClient()
    parent = dialogflow.AgentsClient.agent_path(project_id)
    training_phrases = []
    for training_phrases_part in training_phrases_parts:
        part = dialogflow.Intent.TrainingPhrase.Part(
            text=training_phrases_part)

        training_phrase = dialogflow.Intent.TrainingPhrase(parts=[part])
        training_phrases.append(training_phrase)

    text = dialogflow.Intent.Message.Text(text=message_texts)
    message = dialogflow.Intent.Message(text=text)

    intent = dialogflow.Intent(
        display_name=intent_name,
        training_phrases=training_phrases,
        messages=[message]
    )

    response = intents_client.create_intent(
        request={"parent": parent, "intent": intent}
    )

    print("Intent created: {}".format(response))


def main():
    load_dotenv()
    project_id = os.environ['PROJECT_ID']

    with open('phrases.json', 'r', encoding="utf-8") as file:
        intents = json.load(file)

    for intent_name, intent_content in intents.items():
        training_phrases = intent_content['questions']
        message_texts = intent_content['answer']

        create_intent(project_id, intent_name,
                      training_phrases, [message_texts])


if __name__ == "__main__":
    main()
