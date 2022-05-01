from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from google.cloud import dialogflow_v2
import os
import requests
import traceback
import json

# Create your views here.
@require_http_methods(['GET'])
def index_view(request):
    return render(request, 'home.html')

@csrf_exempt
@require_http_methods(['POST'])
def chat_view(request):
    print('\n***Body', request.body)
    input_dict = convert(request.body)
    input_text = json.loads(input_dict)['text']

    GOOGLE_AUTHENTICATION_FILE_NAME = "Pokebot.json"
    current_directory = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(current_directory, GOOGLE_AUTHENTICATION_FILE_NAME)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path

    GOOGLE_PROJECT_ID = "your-project-id"
    session_id = "1234567878"
    context_short_name = "does_not_matter"

    context_name = "projects/" + GOOGLE_PROJECT_ID + "/agent/sessions/" + session_id + "/contexts/" + \
               context_short_name.lower()

    parameters = {}
    context_1 = dialogflow_v2.types.Context(
        name=context_name,
        lifespan_count=2,
        parameters=parameters
    )
    query_params_1 = {"contexts": [context_1]}

    language_code = 'en'
    
    response = detect_intent_with_parameters(
        project_id=GOOGLE_PROJECT_ID,
        session_id=session_id,
        query_params=query_params_1,
        language_code=language_code,
        user_input=input_text
    )
    return HttpResponse(response.query_result.fulfillment_text, status=200)

def detect_intent_with_parameters(project_id, session_id, query_params, language_code, user_input):
    """Returns the result of detect intent with texts as inputs.

    Using the same `session_id` between requests allows continuation
    of the conversaion."""
    session_client = dialogflow_v2.SessionsClient()

    session = session_client.session_path(project_id, session_id)

    #text = "this is as test"
    text = user_input

    text_input = dialogflow_v2.types.TextInput(
        text=text, language_code=language_code)

    query_input = dialogflow_v2.types.QueryInput(text=text_input)

    response = session_client.detect_intent(
        session=session, query_input=query_input
    )

    # print('=' * 20)
    # print('Query text: {}'.format(response.query_result.query_text))
    # print('Detected intent: {} (confidence: {})\n'.format(
    #     response.query_result.intent.display_name,
    #     response.query_result.intent_detection_confidence))
    # print('Fulfillment text: {}\n'.format(
    #     response.query_result.fulfillment_text))

    return response

def convert(data):
    if isinstance(data, bytes):
        return data.decode('ascii')
    if isinstance(data, dict):
        return dict(map(convert, data.items()))
    if isinstance(data, tuple):
        return map(convert, data)

    return data



@csrf_exempt
def webhook(request):
    req = json.loads(request.body)
    # get data from json
    intent = req.get('queryResult').get('intent')
    print(f'\ndata from dialogflow: {req.get("queryResult")}')
    parameters = req.get('queryResult').get('parameters')
    outputContext = req.get('queryResult').get('outputContexts')
    queryText = req.get('queryResult').get('queryText')
    # return a fulfillment message
    fulfillmentText = fulfillmentResponse(outputContext, intent, parameters, queryText)
    # return response
    return JsonResponse(fulfillmentText)

# Handles requests to and from pokeapi
@csrf_exempt
def pokeapi(url, payload):
    print(f'\n***** url: {url} ----- payload: {payload}')
    req = requests.get('https://pokeapi.co/api/v2/' + url + '/' + payload)
    poke = json.loads(req.content)
    return poke

# Creates and returns a formatted fulfilment response for DialogFlow
@csrf_exempt
def fulfillmentResponse(outputContexts, intent, parameters, queryText):
  print(f'\n**** pinging webhook properly :)')
  try:
    pokemon_endpoint = ['abilities', 'moves', 'photo']
    pokemon_species_endpoint = ['description', 'evolution']

    pokemon = (parameters['pokes'].lower().replace('.', '-').replace(' ', '').replace("'", '') 
                if 'pokes' in parameters 
                else '')
    formatted_pokemon = pokemon.capitalize()
    specs = ''
    if 'objects' in parameters:
      specs = parameters['objects'][0].lower()
    get_type_effectiveness = 'type_effectiveness' in parameters

    fulfillmentText = ''
    response = {}

    print(f'\n*** specs: {specs}')

    # if processing abilities/moves/photo request
    if (specs in pokemon_endpoint):
      # grab data from pokeapi
      data = pokeapi('pokemon', pokemon)

      # format data from pokeapi
      id = '{:03d}'.format(int(data['id']))
      value = ', '.join(map(lambda item: item['move']['name'], data['moves']))
      if (specs == 'abilities'):
        value = ', '.join(map(lambda item: item['ability']['name'], data['abilities']))
      
      # create fulfillmentText
      response['fulfillmentText'] = f'{formatted_pokemon}\'s {specs} are: {value}'

      # if photo needs to be included
      if (specs == 'photo'):
        response['fulfillmentText'] = pokemon
        response['payload'] = {'is_image': True, 'url': f'https://www.pkparaiso.com/imagenes/xy/sprites/global_link/{id}.png'}

    # if processing description/evolution request
    if (specs in pokemon_species_endpoint or intent['displayName'] == 'evolution'):
      data = pokeapi('pokemon-species', pokemon)
      print(f'\n**** data from pokeapi: {data}')

      evolution_chain_id = data['evolution_chain']['url'].split('/')[6]
      flavor_text = list(filter(lambda item: item['language']['name'] == 'en', data['flavor_text_entries']))[0]['flavor_text'].replace('\x0c', ' ')
      if (specs == 'description'):
        response['fulfillmentText'] = f'{formatted_pokemon}: \n\n {flavor_text}'
      
      if (intent['displayName'] == 'evolution'):
        data = pokeapi('evolution-chain', evolution_chain_id)
        evolution_requirement = parameters['evolution']

        pokemon_evolutions = [data['chain']['species']['name'].capitalize()]
        response['fulfillmentText'] = f'{formatted_pokemon} has no evolution chain'

        # if pokemon has further evolutions
        chain = data['chain']
        while (chain['evolves_to']):
          pokemon_evolutions.append(chain['evolves_to'][0]['species']['name'].capitalize())
          chain = chain['evolves_to'][0]
        
        evolution_chain = ' -> '.join(pokemon_evolutions)
        order_in_evolution_chain = pokemon_evolutions.index(formatted_pokemon)
        next_form = pokemon_evolutions[order_in_evolution_chain + 1]
        previous_form = pokemon_evolutions[order_in_evolution_chain - 1]

        evolution_text = {
            'evolution_chain': f'{formatted_pokemon}\'s evolution chain is: {evolution_chain}',
            'first_evolution': 'This is already the first form' if (pokemon == pokemon_evolutions[0]) else f'{pokemon_evolutions[0]} is the first evolution',
            'second_evolution': 'This is already the second form' if (pokemon == pokemon_evolutions[1]) else f'{pokemon_evolutions[1]} is the second evolution',
            'last_evolution': 'This is already the final form' if (pokemon == pokemon_evolutions[-1]) else f'{pokemon_evolutions[-1]} is the last evolution',
            'next_form': f'{formatted_pokemon} evolves to {next_form}',
            'previous_form': f'{formatted_pokemon} evolves from {previous_form}'
        }

        if (evolution_text[evolution_requirement]):
            response['fulfillmentText'] = evolution_text[evolution_requirement]
      

    if (get_type_effectiveness):
      pokemon_type = parameters['poke_types']
      type_effectiveness = parameters['type_effectiveness']
      type_effectiveness_formatted = type_effectiveness.replace('_', ' ')
      print(f'\n*** outputputContexts: {outputContexts}\n')
      type_effectiveness_word = outputContexts[0]['parameters']['type_effectiveness.original']
      
      preposition = type_effectiveness.split('_')[2]
      pokemon_type_comes_first = queryText.index(pokemon_type) < queryText.index(type_effectiveness_word)

      exempt_words = ['resistant', 'no damage', 'zero damage', 'no effect']
      has_exempt_words = any(x in type_effectiveness_word for x in exempt_words)
      
      # handles complex grammatical phrasing of original query
      # what is effective against type         
      # vs.
      # what is type effective against
      if ((pokemon_type_comes_first and not(has_exempt_words)) or (not(pokemon_type_comes_first) and has_exempt_words)): 
        new_preposition = 'to' if (preposition == 'from') else 'from'
        type_effectiveness = type_effectiveness.replace(preposition, new_preposition)
        preposition = new_preposition
     
      data = pokeapi('type', pokemon_type)
      damage_relations = 'none' 
      if len(data['damage_relations'][type_effectiveness]) > 0:
        damage_relations = ', '.join(map(lambda item: item['name'], data['damage_relations'][type_effectiveness]))
     
      nature_of_damage = 'receives' if (preposition == 'from') else 'inflicts'
      pokemon_type = pokemon_type.capitalize()
      response['fulfillmentText'] = f'{pokemon_type} {nature_of_damage} {type_effectiveness_formatted} the following: {damage_relations}'
      if (nature_of_damage == 'inflicts'):
        response['fulfillmentResponse'] = f'{pokemon_type} type inflicts {type_effectiveness_formatted} {damage_relations} type'
    
    # return fulfillment response
    print(f'\n**** response: {response}\n')
    return response

  except Exception as e:
    traceback.print_exc()
    return {'fulfillmentText': 'Currently experiencing disruptions, try agian later please!'}




      
