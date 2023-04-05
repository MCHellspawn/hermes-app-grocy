# Rhasspy Grocy Skill (Rhasspy_App_Grocy)

A skill for [Rhasspy](https://github.com/rhasspy) that allows a user to interact with the open source ERP for you home, [Grocy](https://grocy.info/). This skill is implemented as a Hermes app and uses the [Rhasspy-hermes-app](https://github.com/rhasspy/rhasspy-hermes-app) library. The script can be run as a service, or as a docker container (recommended). 

## Installing

Requires:
* rhasspy-hermes-app 1.1.2
* pygrocy 1.5.0

### In Docker:
To install, clone the repository and execute docker build to build the image.

```bash
sudo docker build hermes-app-grocy -t <image_name>
```

### In Rhasspy:
Create a new sentence file and copy the sentences from the sentences.ini into the new file in Rhasspy and save. Retrain Rhasspy.

Setup the slot program:
1. SSH into the Rhasspy device 
   * If using a base/satellite setup this is typically done on the base
2. Navigate to your slot programs folder
   * for example "/profiles/en/slot_programs"
```bash
cd /profiles/en/slot_programs
```
3. Create a folder name "grocy" and navigate to it
```bash
mkdir grocy
cd grocy
```
4. Download the slot program from the github repo
```bash
wget https://raw.githubusercontent.com/MCHellspawn/hermes-app-grocy/master/slot_programs/chores
wget https://raw.githubusercontent.com/MCHellspawn/hermes-app-grocy/master/slot_programs/locations
wget https://raw.githubusercontent.com/MCHellspawn/hermes-app-grocy/master/slot_programs/products
wget https://raw.githubusercontent.com/MCHellspawn/hermes-app-grocy/master/slot_programs/quantity_units
```
5. Edit the Rhasspy config file
```bash
cd ..
nano profile.json
```
6. Add the Grocy connection settings at the end, be sure to add a comma (,) after the last entry
```json
    "grocy": {
        "url": "<url to grocy server>",
        "api_key": "<api key from grocy>"
    }
```
7. Setup the slot variables
```ini
chores = $grocy/chores
products = $grocy/products
locations = $grocy/locations
quantity_units = $grocy/quantity_units
```
8. Use the slot variables in a sentence
```ini
Purchase (1..1000){quantity} (<quantity_units>){measure} [of] (<products>){product} into [the] (<locations>){location}
Complete [the] (<chores>){chore} chore
```

## Configuration

Edit the setup section with the connection settings for Grocy:
```ini
[setup]
host = http://localhost
port = 80
verifyssl = False
apikey = apikey
```

* `host: string` - URL of the Grocy Hostname/IP
* `port: integer` - IP Port of the Grocy web API
* `verifyssl: boolean` - Verify SSL certificate
* `apikey: string` - API Key from Grocy

## Using

Build a docker container using the image created above.
Bind the config volume <path/on/host>:/app/config

```bash
sudo docker run -it -d \
        --restart always \
        --name <container_name> \
        -v <path/on/host>:/app/config \
        -e "MQTT_HOST=<MQTT Host/IP>" \
        -e "MQTT_PORT=<MQTT Port (Typically:1883)" \
        -e "MQTT_USER=<MQTT User>" \
        -e "MQTT_PASSWORD=<MQTT Password>" \
        <image_name>
```

The following intents are implemented on the hermes MQTT topic:

```ini
[GrocyGetLocations]

[GrocyPurchaseProduct]

[GrocyGetChores]

[GrocyTrackChore]
```

## To-Do

* Clean up install process
* More intents
  * Products
    * "Purchase" - Complete
    * Transfer
    * Inventory
    * Consume
    * Stock Listing
      * All
      * By location
      * By product type
      * By product
  * Shopping lists
    * List - Complete
    * Create - Complete - basic only
    * Remove?
    * Add items
      * By product - Complete - basic only
      * By "below min stock"
      * By "expired"
      * By recipe
    * Remove items
      * By product - Complete - basic only
      * Push items to stock
  * Recipies
    * Consume ingredients
  * Chores
    * Assign
    * Complete/Skip - Complete - basic only
      * Complete/skip by person
    * List - Complete
      * All - Complete
      * Per person - Complete
  * Batteries
    * List - Complete
    * Get Charge 
    * Change/Track
  * Locations
    * List - Complete
    * Create
* Slot programs
  * people/users - Complete
  * products - Complete
  * locations - Complete
  * chores - Complete
  * quantity_units - Complete
  * batteries - Complete
  * recipes