"""Skill to work with the Grocy App."""
import os
import io
import logging
import configparser
from rhasspyhermes.nlu import NluIntent
from rhasspyhermes_app import EndSession, HermesApp
from pygrocy.data_models.generic import EntityType
from pygrocy import Grocy
from pygrocy.grocy_api_client import GrocyApiClient,TransactionType

_LOGGER = logging.getLogger("GrocyApp")

app = HermesApp("GrocyApp")
grocy = None

def read_configuration_file():
    try:
        cp = configparser.ConfigParser()
        with io.open(os.path.dirname(__file__) + "/config/config.ini", encoding="utf-8") as f:
            cp.read_file(f)
        return {section: {option_name: option for option_name, option in cp.items(section)}
                for section in cp.sections()}
    except (IOError, configparser.Error):
        return dict()

def grocy_add_product(
    grocyapiclient: GrocyApiClient,
    product_id,
    amount: float,
    price: float,
    best_before_date: None,
    transaction_type: TransactionType = TransactionType.PURCHASE,
    location: int = None,
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
   
@app.on_intent("GrocyGetLocations")
async def get_locations(intent: NluIntent):
    """List the locations."""
    _LOGGER.info(f"Intent: {intent.id} | Started: GrocyGetLocations")

    global grocy
    
    sentence = None
    locations = None
    isfreezers = 0

    #Check if the "freezer" slot was sent
    if any(slot for slot in intent.slots if slot.slot_name == 'freezer'):
        _LOGGER.info(f"Intent: {intent.id} | Is Freezer: {str(isfreezers)}")
        #Get locations, filter for freezers
        locations = grocy.get_generic_objects_for_type(EntityType.LOCATIONS, "is_freezer=1")
    else:
        _LOGGER.info(f"Intent: {intent.id} | Is Freezer: <none>")
        #Get locations, no filter
        locations = grocy.get_generic_objects_for_type(EntityType.LOCATIONS)
    _LOGGER.info(f"Intent: {intent.id} | Location count: {len(locations)}")
        
    #Build response sentence
    sentence = "The available locations are "
    for location in locations[:len(locations)-1]:
        sentence = sentence + location["name"] + ", "
    sentence = sentence + "and " + locations[-1]["name"]
                
    _LOGGER.info(f"Intent: {intent.id} | Responded to GrocyGetLocations")
    _LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")
    _LOGGER.info(f"Intent: {intent.id} | Completed: GrocyGetLocations")
    return EndSession(sentence)

@app.on_intent("GrocyPurchaseProduct")
async def purchase_product(intent: NluIntent):
    """Purchase a product."""
    _LOGGER.info(f"Intent: {intent.id} | Started: GrocyPurchaseProduct")

    global grocy
    
    sentence = None

    #Check if the "product" slot was sent
    if any(slot for slot in intent.slots if slot.slot_name == 'product'):
        product = next((slot for slot in intent.slots if slot.slot_name == 'product'), None)
        _LOGGER.info(f"Intent: {intent.id} | Product: {str(product.value['value'])} ({str(product.raw_value)})")

    #Check if the "measure" slot was sent
    if any(slot for slot in intent.slots if slot.slot_name == 'measure'):
        measure = next((slot for slot in intent.slots if slot.slot_name == 'measure'), None)
        _LOGGER.info(f"Intent: {intent.id} | Measure: {str(measure.value['value'])} ({str(measure.raw_value)})")

    #Check if the "location" slot was sent
    if any(slot for slot in intent.slots if slot.slot_name == 'location'):
        location = next((slot for slot in intent.slots if slot.slot_name == 'location'), None)
        _LOGGER.info(f"Intent: {intent.id} | Location: {str(location.value['value'])} ({str(location.raw_value)})")

    #Check if the "quantity" slot was sent
    if any(slot for slot in intent.slots if slot.slot_name == 'quantity'):
        quantity = next((slot for slot in intent.slots if slot.slot_name == 'quantity'), None)
        _LOGGER.info(f"Intent: {intent.id} | Quantity: {str(quantity.value['value'])} ({str(quantity.raw_value)})")
    
    #"Purchase" the product into Grocy inventory
    #Temporarily commented out until the pygrocy library is updated to accept the location_id
    #addedproduct = grocy.add_product(product_id=product.value['value'], amount=quantity.value['value'], price=0.0, best_before_date=None, location=location.value['value'])
    addedproduct = grocy_add_product(grocy._api_client, product_id=product.value['value'], amount=quantity.value['value'], price=0.0, best_before_date=None, location=location.value['value'])
    _LOGGER.info(f"Intent: {intent.id} | Added Product: {str(addedproduct)}")

    #Build response sentence
    sentence = f"Added {str(quantity.value['value'])} {str(product.raw_value)}s to {str(location.raw_value)}"
                
    _LOGGER.info(f"Intent: {intent.id} | Responded to GrocyPurchaseProduct")
    _LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")
    _LOGGER.info(f"Intent: {intent.id} | Completed: GrocyPurchaseProduct")
    return EndSession(sentence)

@app.on_intent("GrocyGetChores")
async def get_chores(intent: NluIntent):
    """List the chores."""
    _LOGGER.info(f"Intent: {intent.id} | Started: GrocyGetChores")

    global grocy
    
    sentence = None
    chores = None

    #Check if the "person" slot was sent
    person_slot_active = any(slot for slot in intent.slots if slot.slot_name == 'person')
    if person_slot_active:
        person = next((slot for slot in intent.slots if slot.slot_name == 'person'), None)
        _LOGGER.info(f"Intent: {intent.id} | Person: {str(person.value['value'])} ({str(person.raw_value)})")
        chores = grocy.chores(get_details=True, query_filters=f"next_execution_assigned_to_user_id={str(person.value['value'])}")
    else:
        _LOGGER.info(f"Intent: {intent.id} | Person: <none>")
        chores = grocy.chores(get_details=True)
    _LOGGER.info(f"Intent: {intent.id} | Chore count: {len(chores)}")

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
                
    _LOGGER.info(f"Intent: {intent.id} | Responded to GrocyGetChores")
    _LOGGER.info(f"Intent: {intent.id} | Sentence: {sentence}")
    _LOGGER.info(f"Intent: {intent.id} | Completed: GrocyGetChores")
    return EndSession(sentence)    

if __name__ == "__main__":
    _LOGGER.info("Starting Hermes App: Grocy")
    config = read_configuration_file()
    _LOGGER.info(f"Config - Host: {config['setup']['host']}")
    _LOGGER.info(f"Config - Port: {config['setup']['port']}")
    _LOGGER.info(f"Config - Verify SSL: {config['setup']['verifyssl']}")
    _LOGGER.info(f"Config - API Key: {config['setup']['apikey']}")

    grocy = Grocy(config['setup']['host'], config['setup']['apikey'], port = config['setup']['port'], verify_ssl = config['setup']['verifyssl'])
    try:
        sysinfo = grocy.get_system_info()
        _LOGGER.info(f"Connected to host: {config['setup']['host']}:{config['setup']['port']} grocy version: {sysinfo.grocy_version}")
        app.run()
    except:
        _LOGGER.error(f"Error connecting to host: {config['setup']['host']}")