import asyncio
import os
import io
import aiohttp
import configparser
import json
import random
from typing import Optional
from rhasspyclient import RhasspyClient
from enum import Enum
from pydantic import BaseModel
from enum import Enum
from datetime import datetime
from rhasspyhermes.nlu import NluIntent
from rhasspyhermes_app import ContinueSession, EndSession, HermesApp
from pygrocy.data_models.generic import EntityType
from pygrocy import Grocy
from pygrocy.grocy_api_client import GrocyApiClient,TransactionType,ProductData

class SessionCustomData(BaseModel):
    intent_name: str
    input_text: str
    intent_slots: Optional[str]

class IntentNames(str, Enum):
    GROCYGETLOCATIONS = "GrocyGetLocations"

    GROCYPURCHASEPRODUCT = "GrocyPurchaseProduct"
    GROCYCREATEPRODUCT = "GrocyCreateProduct"
    GROCYGETPRODUCTINVENTORY = "GrocyGetProductInventory"

    GROCYGETCHORES = "GrocyGetChores"
    GROCYTRACKCHORE = "GrocyTrackChore"

    GROCYGETSHOPPINGLISTS = "GrocyGetShoppingLists"
    GROCYCREATESHOPPINGLIST = "GrocyCreateShoppingList"
    GROCYADDPRODUCTTOSHOPPINGLIST = "GrocyAddProductToShoppingList"
    GROCYREMOVEPRODUCTFROMSHOPPINGLIST = "GrocyRemoveProductFromShoppingList"
    
    GROCYGETBATTERIES = "GrocyGetBatteries"
    GROCYGETBATTERYNEXTCHARGETIME = "GrocyGetBatteryNextChargeTime"
    GROCYTRACKBATTERYCHARGE = "GrocyTrackBatteryCharge"

class RhasspySkill:
    name:str = None
    app: HermesApp = None
    config = None
    _LOGGER = None
    apiUrl = None
    satellite_id = None
    intents = None
    grocy = None
    
    def __init__(self, name: str, app: HermesApp, config = None, logger = None) -> None:
        self.name = name
        self.app = app
        if config == None:
            config = self.read_configuration_file()
        self.config = config
        self.apiUrl = f"{self.config['Rhasspy']['protocol']}://{self.config['Rhasspy']['host']}:{self.config['Rhasspy']['port']}/api"
        if logger != None:
            self._LOGGER = logger            
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.setup_skill())    
    
    async def setup_skill(self):
        
        data = {}
        sentencesString = ""
        
        # Sentence setup
        async with aiohttp.ClientSession(headers=[("accept", "application/json")]) as session:
            async with session.get(
                f"{self.apiUrl}/sentences"
            ) as response:
                response.raise_for_status()
                result = await response.json()
                self._LOGGER.debug(f"Setup: Sentences GET result: {result}")
                if result.get(f"intents/grocy.ini") == None:
                    self._LOGGER.info(f"Setup: Sentences file note found")
                    # open the sentence file in read mode and split into a list
                    sentences = configparser.ConfigParser(allow_no_value=True)
                    sentences.read("./sentences.ini")

                    if self._LOGGER != None:
                        self._LOGGER.info(f"Setup: Sentences config file read")

                        # parse sentences config file
                        for section in sentences.sections():
                            sentencesString = f"{sentencesString}[{section}-{self.satellite_id}]\n"
                            for key in sentences[section]: 
                                sentencesString = f"{sentencesString}{key}\n"
                            sentencesString = f"{sentencesString}\n"   
                        
                        data[f"intents/grocy.ini"] = sentencesString

                        if self._LOGGER != None:
                            self._LOGGER.info(f"Setup: Sentences POST data built")
                        
                        async with aiohttp.ClientSession(headers=[("Content-Type", "application/json")]) as session:
                            async with session.post(
                                    f"{self.apiUrl}/sentences", data=json.dumps(data)
                                ) as response:
                                    response.raise_for_status()
                                    result = await response.text()
                                    self._LOGGER.debug(f"Setup: Sentences POST result: {result}")
                            client = RhasspyClient(f"{self.apiUrl}", session)
                            result = await client.train(no_cache=True)
                            self._LOGGER.info(f"Setup: Train POST result: {result}")
                    else:
                        self._LOGGER.info(f"Setup: Sentences config file not read")
                else:
                    self._LOGGER.info(f"Setup: Sentences file exists")

        # Grocy setup
        self._LOGGER.info(f"Config - Host: {self.config['Grocy Setup']['host']}")
        self._LOGGER.info(f"Config - Port: {self.config['Grocy Setup']['port']}")
        self._LOGGER.info(f"Config - Verify SSL: {self.config['Grocy Setup']['verifyssl']}")
        self._LOGGER.info(f"Config - API Key: {self.config['Grocy Setup']['apikey']}")
        grocy = Grocy(self.config['Grocy Setup']['host'], self.config['Grocy Setup']['apikey'], port = self.config['Grocy Setup']['port'], verify_ssl = self.config['Grocy Setup']['verifyssl'])
        try:
            sysinfo = grocy.get_system_info()
            self._LOGGER.info(f"Connected to host: {self.config['Grocy Setup']['host']}:{self.config['Grocy Setup']['port']} grocy version: {sysinfo.grocy_version}")
            self.grocy = grocy
        except:
            self._LOGGER.error(f"Error connecting to host: {self.config['Grocy Setup']['host']}")

        # Register intent handlers
        self.app.on_intent(IntentNames.GROCYGETLOCATIONS)(self.get_locations)
        self.app.on_intent(IntentNames.GROCYPURCHASEPRODUCT)(self.purchase_product)
        self.app.on_intent(IntentNames.GROCYCREATEPRODUCT)(self.create_product)
        self.app.on_intent(IntentNames.GROCYGETCHORES)(self.get_chores)
        self.app.on_intent(IntentNames.GROCYTRACKCHORE)(self.track_chore)
        self.app.on_intent(IntentNames.GROCYGETSHOPPINGLISTS)(self.get_shoppinglist)
        self.app.on_intent(IntentNames.GROCYCREATESHOPPINGLIST)(self.create_shopping_list)
        self.app.on_intent(IntentNames.GROCYADDPRODUCTTOSHOPPINGLIST)(self.add_product_to_shopping_list)
        self.app.on_intent(IntentNames.GROCYREMOVEPRODUCTFROMSHOPPINGLIST)(self.remove_product_from_shopping_list)
        self.app.on_intent(IntentNames.GROCYGETBATTERIES)(self.get_batteries)
        self.app.on_intent(IntentNames.GROCYGETBATTERYNEXTCHARGETIME)(self.get_batterynextchangetime)
        self.app.on_intent(IntentNames.GROCYTRACKBATTERYCHARGE)(self.track_batterycharge)
        self.app.on_intent(IntentNames.GROCYGETPRODUCTINVENTORY)(self.get_productinventory)
        

    def read_configuration_file(self):
        try:
            cp = configparser.ConfigParser()
            with io.open(os.path.dirname(__file__) + "/config/config.ini", encoding="utf-8") as f:
                cp.read_file(f)
            return {section: {option_name: option for option_name, option in cp.items(section)}
                    for section in cp.sections()}
        except (IOError, configparser.Error):
            return dict()

    def response_sentence(self, intent: NluIntent, contextName:str = None, data_string: str = None) -> str:
        self._LOGGER.debug(f"Intent: {intent.id} | Started response_sentence")

        # open the responses file in read mode
        responses = configparser.ConfigParser(allow_no_value=True)
        responses.read("config/responses.ini")
        
        if contextName == None:
            intentName = intent.intent.intent_name
        else:
            intentName = f"{intent.intent.intent_name}-{contextName}"
        
        intentResponses = responses.items(intentName)
        if intentResponses[-1] == None:
            intentResponses = intentResponses[0:-1]
        
        if data_string == None:
            sentence = str(random.choice(intentResponses)[0])
        else:            
            sentence = str(random.choice(intentResponses)[0]).format(data_string)

        self._LOGGER.debug(f"Intent: {intent.id} | response_sentence sentence: {sentence}")
        self._LOGGER.debug(f"Intent: {intent.id} | Completed response_sentence")
        return sentence

    def fail_sentence(self, intent: NluIntent, errName: str):
        self._LOGGER.debug(f"Intent: {intent.id} | Started response_sentence")

        # open the responses file in read mode
        responses = configparser.ConfigParser(allow_no_value=True)
        responses.read("config/responses.ini")
        
        intentErrName = f"{intent.intent.intent_name.replace(f'-{intent.site_id}', '')}-Fail-{errName}"

        intentErrResponses = responses.items(intentErrName)[0]
        
        sentence = random.choice(intentErrResponses[0:-1])

        self._LOGGER.debug(f"Intent: {intent.id} | response_sentence sentence: {sentence}")
        self._LOGGER.debug(f"Intent: {intent.id} | Completed response_sentence")
        return sentence

    def grocy_purchase_product(
        self, 
        grocyapiclient: GrocyApiClient,
        product_id,
        amount: float,
        price: float,
        best_before_date: None,
        transaction_type: TransactionType = TransactionType.PURCHASE,
        location: int = None
    ):
        data = {
            "amount": amount,
            "transaction_type": transaction_type.value,
            "price": price,
            "location_id": location,
        }

        if location is not None:
            data["location_id"] = location

        if best_before_date is not None:
            data["best_before_date"] = best_before_date.strftime("%Y-%m-%d")

        return grocyapiclient._do_post_request(f"stock/products/{product_id}/add", data)

    #Utility Intents   
    async def get_locations(self, intent: NluIntent):
        """List the locations."""
        self._LOGGER.info(f"Intent: {intent.id} | Started: {IntentNames.GROCYGETLOCATIONS}")

        sentence = None
        locations = None
        isfreezers = 0

        #Check if the "freezer" slot was sent
        if any(slot for slot in intent.slots if slot.slot_name == 'freezer'):
            self._LOGGER.info(f"Intent: {intent.id} | Is Freezer: {str(isfreezers)}")
            #Get locations, filter for freezers
            locations = self.grocy.get_generic_objects_for_type(EntityType.LOCATIONS, "is_freezer=1")
        else:
            self._LOGGER.info(f"Intent: {intent.id} | Is Freezer: <none>")
            #Get locations, no filter
            locations = self.grocy.get_generic_objects_for_type(EntityType.LOCATIONS)
        self._LOGGER.info(f"Intent: {intent.id} | Location count: {len(locations)}")
            
        #Build response sentence
        sentence = self.response_sentence(intent) + " "
        for location in locations[:len(locations)-1]:
            sentence = sentence + location["name"] + ", "
        sentence = sentence + "and " + locations[-1]["name"]
        self._LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")

        self.app.notify(sentence, intent.site_id)
        self._LOGGER.info(f"Intent: {intent.id} | Responded to {IntentNames.GROCYGETLOCATIONS}")
        self._LOGGER.info(f"Intent: {intent.id} | Completed: {IntentNames.GROCYGETLOCATIONS}")
        return EndSession()

    #Product Intents
    async def purchase_product(self, intent: NluIntent):
        """Purchase a product."""
        self._LOGGER.info(f"Intent: {intent.id} | Started: {IntentNames.GROCYPURCHASEPRODUCT}")

        sentence = None

        #Check if the "product" slot was sent
        if any(slot for slot in intent.slots if slot.slot_name == 'product'):
            product = next((slot for slot in intent.slots if slot.slot_name == 'product'), None)
            self._LOGGER.info(f"Intent: {intent.id} | Product: {str(product.value['value'])} ({str(product.raw_value)})")

        #Check if the "measure" slot was sent
        if any(slot for slot in intent.slots if slot.slot_name == 'measure'):
            measure = next((slot for slot in intent.slots if slot.slot_name == 'measure'), None)
            self._LOGGER.info(f"Intent: {intent.id} | Measure: {str(measure.value['value'])} ({str(measure.raw_value)})")

        #Check if the "location" slot was sent
        if any(slot for slot in intent.slots if slot.slot_name == 'location'):
            location = next((slot for slot in intent.slots if slot.slot_name == 'location'), None)
            self._LOGGER.info(f"Intent: {intent.id} | Location: {str(location.value['value'])} ({str(location.raw_value)})")

        #Check if the "quantity" slot was sent
        if any(slot for slot in intent.slots if slot.slot_name == 'quantity'):
            quantity = next((slot for slot in intent.slots if slot.slot_name == 'quantity'), None)
            self._LOGGER.info(f"Intent: {intent.id} | Quantity: {str(quantity.value['value'])} ({str(quantity.raw_value)})")
        
        #"Purchase" the product into Grocy inventory
        #Temporarily commented out until the pygrocy library is updated to accept the location_id
        #addedproduct = grocy.add_product(product_id=product.value['value'], amount=quantity.value['value'], price=0.0, best_before_date=None, location=location.value['value'])
        addedproduct = self.grocy_purchase_product(self.grocy._api_client, product_id=product.value['value'], amount=quantity.value['value'], price=0.0, best_before_date=None, location=location.value['value'])
        self._LOGGER.info(f"Intent: {intent.id} | Added Product: {str(addedproduct)}")

        #Build response sentence
        sentence = self.response_sentence(intent).format(str(quantity.value['value']), str(product.raw_value), str(location.raw_value))
        self._LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")

        self.app.notify(sentence, intent.site_id)
        self._LOGGER.info(f"Intent: {intent.id} | Responded to {IntentNames.GROCYPURCHASEPRODUCT}")
        self._LOGGER.info(f"Intent: {intent.id} | Completed: {IntentNames.GROCYPURCHASEPRODUCT}")
        return EndSession()

    async def create_product(self, intent: NluIntent):
        """Create a product."""
        self._LOGGER.info(f"Intent: {intent.id} | Started: {IntentNames.GROCYCREATEPRODUCT}")

        sentence = None

        #Check if the "product" slot was sent
        if any(slot for slot in intent.slots if slot.slot_name == 'product'):
            product = next((slot for slot in intent.slots if slot.slot_name == 'product'), None)
            self._LOGGER.info(f"Intent: {intent.id} | Product: {str(product.value['value'])} ({str(product.raw_value)})")
            extractedProductName = intent.raw_input.replace("Create a new product called ", "")
        else:
            data = {
                "intent_name": "GrocyCreateProduct",
                "input_text": intent.input,
                "intent_slots": intent.slots
            }
                
            return ContinueSession(
                text="what is the name of the product", custom_data=data, send_intent_not_recognized=True
            )

        #Check if the "measure" slot was sent
        measure = self.config['Grocy Setup']['default_qu']
        if any(slot for slot in intent.slots if slot.slot_name == 'measure'):
            measureslot = next((slot for slot in intent.slots if slot.slot_name == 'measure'), None)
            self._LOGGER.info(f"Intent: {intent.id} | Measure: {str(measureslot.value['value'])} ({str(measureslot.raw_value)})")
            measure = measureslot.value['value']

        #Check if the "location" slot was sent
        location = self.config['Grocy Setup']['default_location_id']
        if any(slot for slot in intent.slots if slot.slot_name == 'location'):
            locationslot = next((slot for slot in intent.slots if slot.slot_name == 'location'), None)
            self._LOGGER.info(f"Intent: {intent.id} | Location: {str(locationslot.value['value'])} ({str(locationslot.raw_value)})")
            location = locationslot.value['value']

        #Create a new product in Grocy
        productdata = {
            "name": extractedProductName,
            "active": 1,
            "location_id": location,
            "default_consume_location_id": location,
            "qu_id_purchase": measure,
            "qu_id_stock": measure,
            "qu_factor_purchase_to_stock": measure
        }
        newproduct = self.grocy.add_generic(EntityType.PRODUCTS, productdata)
        self.grocy.product
        self._LOGGER.info(f"Intent: {intent.id} | Added Product: {str(newproduct)}")

        #Build response sentence
        sentence = self.response_sentence(intent).format(extractedProductName)
        self._LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")

        self.app.notify(sentence, intent.site_id)
        self._LOGGER.info(f"Intent: {intent.id} | Responded to {IntentNames.GROCYCREATEPRODUCT}")
        self._LOGGER.info(f"Intent: {intent.id} | Completed: {IntentNames.GROCYCREATEPRODUCT}")
        return EndSession()

    async def get_productinventory(self, intent: NluIntent):
        """Get product inventory."""
        self._LOGGER.info(f"Intent: {intent.id} | Started: {IntentNames.GROCYGETPRODUCTINVENTORY}")

        sentence = None
        
        productslot = next((slot for slot in intent.slots if slot.slot_name == 'product'), None)
        if productslot == None:
            self._LOGGER.info(f"Intent: {intent.id} | Product slot equals none")
            sentence = "I need to know the name of the product"
        else:
            product = self.grocy.product(productslot.value['value'])
            self._LOGGER.debug(f"Intent: {intent.id} | Battery: {product}")
            self._LOGGER.info(f"Intent: {intent.id} | Battery name: {product.name}")
                   
            sentence = self.response_sentence(intent).format(product.available_amount, product.default_quantity_unit_purchase.name, product.name)
            
        self._LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")
        self.app.notify(sentence, intent.site_id)
        
        self._LOGGER.info(f"Intent: {intent.id} | Responded to {IntentNames.GROCYGETPRODUCTINVENTORY}")
        self._LOGGER.info(f"Intent: {intent.id} | Completed: {IntentNames.GROCYGETPRODUCTINVENTORY}")
        return EndSession()

    #Chore Intents
    async def get_chores(self, intent: NluIntent):
        """List the chores."""
        self._LOGGER.info(f"Intent: {intent.id} | Started: {IntentNames.GROCYGETCHORES}")
        
        sentence = None
        chores = None

        #Check if the "person" slot was sent
        person_slot_active = any(slot for slot in intent.slots if slot.slot_name == 'person')
        if person_slot_active:
            person = next((slot for slot in intent.slots if slot.slot_name == 'person'), None)
            self._LOGGER.info(f"Intent: {intent.id} | Person: {str(person.value['value'])} ({str(person.raw_value)})")
            chores = self.grocy.chores(get_details=True, query_filters=f"next_execution_assigned_to_user_id={str(person.value['value'])}")
        else:
            self._LOGGER.info(f"Intent: {intent.id} | Person: <none>")
            chores = self.grocy.chores(get_details=True)
        self._LOGGER.info(f"Intent: {intent.id} | Chore count: {len(chores)}")

        #Build response sentence
        if person_slot_active:
            if len(chores) > 1:
                sentence = f"{person.raw_value} active chores are "
                for chore in chores[:len(chores)-1]:
                    sentence = sentence + chore.name + ", "
                sentence = sentence + "and " + chores[-1].name
            else:        
                sentence = f"{person.raw_value} active chore is {chores[0].name}"
        else:
            if len(chores) > 1:
                sentence = "The active chores are "
                for chore in chores[:len(chores)-1]:
                    sentence = sentence + chore.name + ", "
                sentence = sentence + "and " + chores[-1].name
            else:        
                sentence = f"The active chore is {chores[0].name}"
                    
        self._LOGGER.info(f"Intent: {intent.id} | Responded to {IntentNames.GROCYGETCHORES}")
        self._LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")
        self._LOGGER.info(f"Intent: {intent.id} | Completed: {IntentNames.GROCYGETCHORES}")
        return EndSession(sentence)    

    async def track_chore(self, intent: NluIntent):
        """Track a chore."""
        self._LOGGER.info(f"Intent: {intent.id} | Started: {IntentNames.GROCYTRACKCHORE}")

        sentence = None

        #Get the "action" slot
        action = next((slot for slot in intent.slots if slot.slot_name == 'action'), None)
        if action == None:
            return EndSession("I need to know what action to do")    
        self._LOGGER.info(f"Intent: {intent.id} | Action: {str(action.value['value'])} ({str(action.raw_value)})")

        #Get the "chore" slot
        chore = next((slot for slot in intent.slots if slot.slot_name == 'chore'), None)
        if chore == None:
            return EndSession("I need to know what chore to complete")    
        self._LOGGER.info(f"Intent: {intent.id} | Chore: {str(chore.value['value'])} ({str(chore.raw_value)})")
        
        if action.value['value'] == "Complete":
            execute_chore = self.grocy.execute_chore(chore_id=chore.value['value'], tracked_time=datetime.now())
            sentence = "The chore has been marked complete"
            self._LOGGER.info(f"Intent: {intent.id} | Execute chore response: {execute_chore}")    
            self._LOGGER.info(f"Intent: {intent.id} | Completed chore: {chore.value['value']}")    
        elif action.value['value'] == "Skip":
            execute_chore = self.grocy.execute_chore(chore_id=chore.value['value'], tracked_time=datetime.now(), skipped=True)
            sentence = "The chore has been skipped"
            self._LOGGER.info(f"Intent: {intent.id} | Execute chore response: {execute_chore}")
            self._LOGGER.info(f"Intent: {intent.id} | Skipped chore: {chore.value['value']}")

        self._LOGGER.info(f"Intent: {intent.id} | Responded to {IntentNames.GROCYTRACKCHORE}")
        self._LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")
        self._LOGGER.info(f"Intent: {intent.id} | Completed: {IntentNames.GROCYTRACKCHORE}")
        return EndSession(sentence)    

    #Shopping List Intents
    async def get_shoppinglist(self, intent: NluIntent):
        """List the shopping lists."""
        self._LOGGER.info(f"Intent: {intent.id} | Started: {IntentNames.GROCYGETSHOPPINGLISTS}")

        sentence = None

        shoppingLists = self.grocy.get_generic_objects_for_type(EntityType.SHOPPING_LISTS)    
        self._LOGGER.debug(f"Intent: {intent.id} | Shopping Lists: {shoppingLists}")
        self._LOGGER.info(f"Intent: {intent.id} | Shopping List count: {len(shoppingLists)}")

        if len(shoppingLists) > 1:
            sentence = "There is the "
            for shoppingList in shoppingLists[:len(shoppingLists)-1]:
                sentence = sentence + shoppingList['name'] + ", "
            sentence = sentence + "and " + shoppingLists[-1]['name']
        else:        
            sentence = f"There is only the {shoppingLists[0]['name']}"    

        self._LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")
        self.app.notify(sentence, intent.site_id)

        self._LOGGER.info(f"Intent: {intent.id} | Responded to {IntentNames.GROCYGETSHOPPINGLISTS}")
        self._LOGGER.info(f"Intent: {intent.id} | Completed: {IntentNames.GROCYGETSHOPPINGLISTS}")
        return EndSession(sentence)    

    async def create_shopping_list(self, intent: NluIntent):
        """Create a shopping list."""
        self._LOGGER.info(f"Intent: {intent.id} | Started: {IntentNames.GROCYCREATESHOPPINGLIST}")

        sentence = None
        shoppingListCheck = None
        shoppingList = None

        nameslot = next((slot for slot in intent.slots if slot.slot_name == 'name'), None)
        if nameslot == None:
            self._LOGGER.info(f"Intent: {intent.id} | Name slot equals none")
            sentence = "I need to know the name of the shopping list"
        elif len(nameslot.value['value']) == 0:
            self._LOGGER.info(f"Intent: {intent.id} | Name slot exists but name is blank")
            extractedListName = intent.raw_input.replace("create a new shopping list called ", "")
            self._LOGGER.info(f"Intent: {intent.id} | Name extracted: {extractedListName}")
            if len(extractedListName) > 0:
                shoppingListCheck = self.grocy.get_generic_objects_for_type(EntityType.SHOPPING_LISTS, f"name={extractedListName}")    
                if len(shoppingListCheck) == 0:
                    data = {
                        "name": extractedListName,
                    }
                    shoppingListResponse = self.grocy.add_generic(EntityType.SHOPPING_LISTS, data)
                    self._LOGGER.debug(f"Intent: {intent.id} | Shopping List response: {shoppingListResponse}")
                    self._LOGGER.info(f"Intent: {intent.id} | Shopping List created: {shoppingListResponse['created_object_id']}")
                    shoppingList = self.grocy.get_generic_objects_for_type(EntityType.SHOPPING_LISTS, f"id={shoppingListResponse['created_object_id']}")    
                    self._LOGGER.debug(f"Intent: {intent.id} | Shopping List: {shoppingList}")
                    self._LOGGER.info(f"Intent: {intent.id} | Shopping List retrieved from Grocy: {shoppingList[0]['name']}")
                    sentence = f"I created a new list called {shoppingList[0]['name']}"
                else:
                    self._LOGGER.info(f"Intent: {intent.id} | Shopping List creation failed: List exists")
                    sentence = f"A list called {extractedListName} already exists"
            else:
                self._LOGGER.info(f"Intent: {intent.id} | Unable to extract name from name slot")
                sentence = "I need to know the name of the shopping list"
        else:
            self._LOGGER.info(f"Intent: {intent.id} | Name: {str(nameslot.value['value'])} ({str(nameslot.raw_value)})")
            shoppingListCheck = self.grocy.get_generic_objects_for_type(EntityType.SHOPPING_LISTS, f"name={nameslot.value['value']}")    
            if len(shoppingListCheck) == 0:
                data = {
                    "name": nameslot.value['value'],
                }
                shoppingList = self.grocy.add_generic(EntityType.SHOPPING_LISTS, data)
                sentence = f"I created a new list called {shoppingList['name']}"

        self._LOGGER.info(f"Intent: {intent.id} | Responded to {IntentNames.GROCYCREATESHOPPINGLIST}")
        self._LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")
        self._LOGGER.info(f"Intent: {intent.id} | Completed: {IntentNames.GROCYCREATESHOPPINGLIST}")
        return EndSession(sentence)    

    async def add_product_to_shopping_list(self, intent: NluIntent):
        """Add product to a the shopping list."""
        self._LOGGER.info(f"Intent: {intent.id} | Started: {IntentNames.GROCYADDPRODUCTTOSHOPPINGLIST}")
        
        sentence = None

        listslot = next((slot for slot in intent.slots if slot.slot_name == 'list'), None)
        if listslot == None:
            self._LOGGER.info(f"Intent: {intent.id} | List slot equals none")
            sentence = "I need to know the name of the shopping list"

        productslot = next((slot for slot in intent.slots if slot.slot_name == 'product'), None)
        if productslot == None:
            self._LOGGER.info(f"Intent: {intent.id} | Product slot equals none")
            sentence = "I need to know which product to add"

        if listslot != None and productslot != None:
            self.grocy.add_product_to_shopping_list(productslot.value['value'], listslot.value['value'], 1)
            self._LOGGER.info(f"Intent: {intent.id} | Product added to Shopping List")                
            sentence = "I added the product to the list"
        
        self.app.notify(sentence, intent.site_id)
        self._LOGGER.info(f"Intent: {intent.id} | Responded to {IntentNames.GROCYADDPRODUCTTOSHOPPINGLIST}")
        self._LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")
        self._LOGGER.info(f"Intent: {intent.id} | Completed: {IntentNames.GROCYADDPRODUCTTOSHOPPINGLIST}")
        return EndSession()    

    async def remove_product_from_shopping_list(self, intent: NluIntent):
        """Remove product from a the shopping list."""
        self._LOGGER.info(f"Intent: {intent.id} | Started: {IntentNames.GROCYREMOVEPRODUCTFROMSHOPPINGLIST}")
        
        sentence = None

        listslot = next((slot for slot in intent.slots if slot.slot_name == 'list'), None)
        if listslot == None:
            self._LOGGER.info(f"Intent: {intent.id} | List slot equals none")
            sentence = "I need to know the name of the shopping list"

        productslot = next((slot for slot in intent.slots if slot.slot_name == 'product'), None)
        if productslot == None:
            self._LOGGER.info(f"Intent: {intent.id} | Product slot equals none")
            sentence = "I need to know which product to add"

        if listslot != None and productslot != None:
            self.grocy.remove_product_in_shopping_list(productslot.value['value'], listslot.value['value'])
            #.add_product_to_shopping_list(productslot.value['value'], listslot.value['value'], 1)
            self._LOGGER.info(f"Intent: {intent.id} | Product removed from Shopping List")                
            sentence = "I removed the product from the list"

        self._LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")
        self.app.notify(sentence, intent.site_id)

        self._LOGGER.info(f"Intent: {intent.id} | Responded to {IntentNames.GROCYREMOVEPRODUCTFROMSHOPPINGLIST}")
        self._LOGGER.info(f"Intent: {intent.id} | Completed: {IntentNames.GROCYREMOVEPRODUCTFROMSHOPPINGLIST}")
        return EndSession(sentence)    

    #Battery Intents
    async def get_batteries(self, intent: NluIntent):
        """List the batteries."""
        self._LOGGER.info(f"Intent: {intent.id} | Started: {IntentNames.GROCYGETBATTERIES}")

        sentence = None

        batteries = self.grocy.get_generic_objects_for_type(EntityType.BATTERIES)    
        self._LOGGER.debug(f"Intent: {intent.id} | Batteries: {batteries}")
        self._LOGGER.info(f"Intent: {intent.id} | Battery count: {len(batteries)}")

        if len(batteries) > 1:
            sentence = "There is the "
            for battery in batteries[:len(batteries)-1]:
                sentence = sentence + battery['name'] + " battery, "
            sentence = sentence + "and the " + batteries[-1]['name'] + " battery"
        else:        
            sentence = f"There is only the {batteries[0]['name']} battery"
            
        self._LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")
        self.app.notify(sentence, intent.site_id)
        
        self._LOGGER.info(f"Intent: {intent.id} | Responded to {IntentNames.GROCYGETBATTERIES}")
        self._LOGGER.info(f"Intent: {intent.id} | Completed: {IntentNames.GROCYGETBATTERIES}")
        return EndSession()

    async def get_batterynextchangetime(self, intent: NluIntent):
        """Get battery next charge time."""
        self._LOGGER.info(f"Intent: {intent.id} | Started: {IntentNames.GROCYGETBATTERYNEXTCHARGETIME}")

        sentence = None
        
        batteryslot = next((slot for slot in intent.slots if slot.slot_name == 'battery'), None)
        if batteryslot == None:
            self._LOGGER.info(f"Intent: {intent.id} | Battery slot equals none")
            sentence = "I need to know the name of the battery"
        else:
            battery = self.grocy.battery(batteryslot.value['value'])
            self._LOGGER.debug(f"Intent: {intent.id} | Battery: {battery}")
            self._LOGGER.info(f"Intent: {intent.id} | Battery name: {battery.name}")
            if battery.next_estimated_charge_time != None:
                if battery.charge_cycles_count == 1:
                    pluralString = ""
                else:
                    pluralString = "s"
                    
                sentence = self.response_sentence(intent).format(battery.next_estimated_charge_time, battery.charge_cycles_count, pluralString)
            else:
                sentence = self.response_sentence(intent, contextName="NoneResponse")
            
        self._LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")
        self.app.notify(sentence, intent.site_id)
        
        self._LOGGER.info(f"Intent: {intent.id} | Responded to {IntentNames.GROCYGETBATTERYNEXTCHARGETIME}")
        self._LOGGER.info(f"Intent: {intent.id} | Completed: {IntentNames.GROCYGETBATTERYNEXTCHARGETIME}")
        return EndSession()

    async def track_batterycharge(self, intent: NluIntent):
        """Track battery charge time."""
        self._LOGGER.info(f"Intent: {intent.id} | Started: {IntentNames.GROCYTRACKBATTERYCHARGE}")

        sentence = None
        
        batteryslot = next((slot for slot in intent.slots if slot.slot_name == 'battery'), None)
        if batteryslot == None:
            self._LOGGER.info(f"Intent: {intent.id} | Battery slot equals none")
            sentence = "I need to know the name of the battery"
        else:
            batteryCharge = self.grocy.charge_battery(batteryslot.value['value'])
            self._LOGGER.debug(f"Intent: {intent.id} | Battery charge: {batteryCharge}")
            self._LOGGER.info(f"Intent: {intent.id} | Battery charge tracked {batteryCharge['tracked_time']}")
            battery = self.grocy.battery(batteryslot.value['value'])
            if battery.charge_cycles_count == 1:
                pluralString = ""
            else:
                pluralString = "s"       
            sentence = self.response_sentence(intent).format(battery.charge_cycles_count, pluralString , battery.next_estimated_charge_time)
            
        self._LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")
        self.app.notify(sentence, intent.site_id)
        
        self._LOGGER.info(f"Intent: {intent.id} | Responded to {IntentNames.GROCYTRACKBATTERYCHARGE}")
        self._LOGGER.info(f"Intent: {intent.id} | Completed: {IntentNames.GROCYTRACKBATTERYCHARGE}")
        return EndSession()
