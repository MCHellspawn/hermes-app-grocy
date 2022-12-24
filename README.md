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
```

The following intents are implemented on the hermes MQTT topic:

```ini
[GrocyGetLocations]

[GrocyPurchaseProduct]
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
    * Create
    * Remove
    * Add items
      * By product
      * By "below min stock"
      * By "expired"
      * By recipe
    * Remove items
      * By product
      * Push items to stock
  * Recipies
    * Consume ingredients
  * Chores
    * Assign
    * Complete/Skip
    * List
      * All
      * Per person
  * Batteries
    * Change/Track
  * Locations
    * List
    * Create
* Slot programs
  * people/users
  * products
  * locations
  * chores
  * batteries
  * recipes