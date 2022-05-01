# PokéBot 🤖

A 'Pokédex' type chatbot built with Google Cloud Dialogflow, Django, and Bootstrap. 

The users input texts are mapped to queries set up as intents in the Dialogflow agent. Once the agent successfully matches an intent, it sends that along a webhook, which in turn communicates with the PokéAPI to query the appropriate Pokémon information to display to the user. 

Sample dialog:

<img width="514" alt="Screenshot 2022-05-01 133533" src="https://user-images.githubusercontent.com/51416604/166157767-bee1ad00-6413-41df-a248-925be21a5ed7.png">
