from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
import requests
import traceback
import json

# Create your views here.
def home(request):
    return HttpResponse(request)

@csrf_exempt
def webhook(request):
    req = json.loads(request.body)
    # get data from json
    intent = req.get('queryResult').get('intent')
    print(f'\ndata from dialogflow: {req.get("queryResult")}')
    parameters = req.get('queryResult').get('parameters')
    outputContext = req.get('queryResult').get('outputContext')
    queryText = req.get('queryResult').get('queryText')
    # return a fulfillment message
    fulfillmentText = fulfillmentResponse(outputContext, intent, parameters, queryText)
    home(fulfillmentText)
    # return response
    return JsonResponse(fulfillmentText)

# Handles requests to and from pokeapi
@csrf_exempt
def pokeapi(url, payload):
    print(f'\npokeapi: {url} / {payload}')
    req = requests.get('https://pokeapi.co/api/v2/' + url + '/' + payload)
    poke = json.loads(req.content)
    return poke

# Creates and returns a formatted fulfilment response for DialogFlow
@csrf_exempt
def fulfillmentResponse(outputContexts, intent, parameters, queryText):
  try:
    pokemon_endpoint = ['abilities', 'moves', 'photo']
    pokemon_species_endpoint = ['description', 'evolution']

    pokemon = (parameters['pokes'].lower().replace('.', '-').replace(' ', '').replace("'", '') 
                if 'pokes' in parameters 
                else '')
    specs = parameters['objects']
    get_type_effectiveness = 'type_effectiveness' in parameters

    fulfillmentText = ''
    response = {}

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
      response['fulfillmentText'] = f'{pokemon}\'s {specs} are: {value}'

      # if photo needs to be included
      if (specs == 'photo'):
        response['fulfillmentText'] = pokemon
        response['payload'] = {'is_image': True, 'url': f'https://www.pkparaiso.com/imagenes/xy/sprites/global_link/{id}.png'}

    # if processing description/evolution request
    if (specs in pokemon_species_endpoint or intent['displayName'] == 'evolution'):
      data = pokeapi('pokemon-species', pokemon)

      evolution_chain_id = data['evolution_chain']['url'].split('/')[6]
      flavor_text = list(filter(lambda item: item['language']['name'] == 'en', data['flavor_text_entries']))[0]['flavor_text'].replace('\x0c', ' ')

      if (specs == 'description'):
        response['fulfillmentText'] = f'{pokemon}: \n\n {flavor_text}'
      
      if (intent['displayName'] == 'evolution'):
        data = pokeapi('evolution-chain', evolution_chain_id)
        evolution_requirement = parameters['evolution']

        pokemon_evolutions = list(data['chain']['species']['name'])
        response['fulfillmentText'] = f'{pokemon} has no evolution chain'

        # if pokemon has further evolutions
        if (data['chain']['evolves_to']):
          pokemon_evolutions.append(data['chain']['evolves_to'][0]['evovles_to'][0]['species']['name'])
        
        evolution_chain = ' -> '.join(pokemon_evolutions)
        order_in_evolution_chain = pokemon_evolutions.indexOf(pokemon)
        next_form = pokemon_evolutions[order_in_evolution_chain + 1]
        previous_form = pokemon_evolutions[order_in_evolution_chain - 1]

        evolution_text = {
            'evolution_chain': f'{pokemon}\'s evolution chain is: {evolution_chain}',
            'first_evolution': 'This is already the first form' if (pokemon == pokemon_evolutions[0]) else f'{pokemon_evolutions[0]} is the first evolution',
            'last_evolution': 'This is already the final form' if (pokemon == pokemon_evolutions[-1]) else f'{pokemon_evolutions[-1]} is the last evolution',
            'next_form': f'{pokemon} evolves to {next_form}',
            'previous_form': f'{pokemon} evolves from {previous_form}'
        }

        if (evolution_text[evolution_requirement]):
            response['fulfillmentText'] = evolution_text[evolution_requirement]
      

    if (get_type_effectiveness):
      pokemon_type = parameters['pokemon']['type']
      type_effectiveness = parameters['type_effectiveness']
      type_effectiveness_formatted = type_effectiveness.replace('_', ' ')
      type_effectiveness_word = outputContexts[0]['parameters']['type_effectiveness.original']
      
      preposition = type_effectiveness.split('_')[2]
      pokemon_type_comes_first = queryText.index(pokemon_type) < queryText.index(type_effectiveness_word)

      exempt_words = ['resistant', 'no damage', 'zero damage', 'no effect']
      has_exempt_words = any(type_effectiveness_word.includes(x) for x in exempt_words)
      
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
      if len(data['damage_relations'][type_effectiveness] > 0):
        damage_relations = ', '.join(map(lambda item: item['name'], data['damage_relations'][type_effectiveness]))
     
      nature_of_damage = 'receives' if (preposition == 'from') else 'inflicts'

      response['fulfillmentText'] = f'{pokemon_type} {nature_of_damage} {type_effectiveness_formatted} the following: {damage_relations}'
      if (nature_of_damage == 'inflicts'):
        response['fulfillmentResponse'] = f'{pokemon_type} type inflicts {type_effectiveness_formatted} {damage_relations} type'
    
    # return fulfillment response
    print(f'fulfillment response: {response}')
    return response

  except Exception as e:
    traceback.print_exc()
    return {'fulfillmentText': 'currently experiencing disruptions, try agian later please!'}




      
