"""Example app using topic lists for receiving raw MQTT messages."""
import logging
import json

from rhasspyhermes_app import HermesApp, TopicData
from rhasspyhermes.nlu import NluIntent, NluIntentNotRecognized
from rhasspyhermes_app import EndSession, ContinueSession, HermesApp
from rhasspyhermes.dialogue import DialogueStartSession, DialogueNotification

_LOGGER = logging.getLogger("RawTopicApp")

app = HermesApp("RawTopicApp")

async def handle_non_recognized(intent: NluIntentNotRecognized):
    _LOGGER.info(f"Intent: {intent.id} | Started: Unrecognized intent handler")    
    if intent.custom_data is not None:
        _LOGGER.info(f"Intent: {intent.id} | customData exists: {intent.custom_data} | Input Text: {intent.input}")
        if intent.custom_data == "TestResponse":
            _LOGGER.info(f"Intent: {intent.id} | Started: {intent.custom_data}")
            if intent.input.lower() != "no":
                _LOGGER.info(f"Intent: {intent.id} | Continued: {intent.custom_data}")
                return ContinueSession(text=f"{intent.input}. say something back?", custom_data="TestResponse")
            else:
                _LOGGER.info(f"Intent: {intent.id} | Completed: {intent.custom_data}")
                return EndSession("Fine be that way!", "TestResponse")            

@app.on_intent_not_recognized(handle_non_recognized)

@app.on_intent("TestResponse")
async def test_response(intent: NluIntent):
    """Respond to the user"""
    _LOGGER.info("TestResponse intent: Fired")  
    #start_session = DialogueStartSession(init=DialogueNotification(text="Say something back?"), site_id=intent.site_id, lang=intent.lang, custom_data="TestResponse") 

    #return EndSession()
    
    return ContinueSession(
        text="Say something back?", custom_data="TestResponse", send_intent_not_recognized=True
    )

# @app.on_topic("hermes/nlu/query")
# async def test_topic4(data: TopicData, payload: bytes):
#     _LOGGER.info("Topic nlu/query: Fired")
#     _LOGGER.info(f"Topic nlu/query: {data}")
#     #+_LOGGER.info(f"Topic nlu/query: {payload}")
#     objPayload = json.loads(payload)
#     if objPayload['customData'] is not None:
#         _LOGGER.info(f"Topic nlu/query: customData exists: {objPayload['customData']} | Input Text: {objPayload['input']}")
#         if objPayload['customData'] == "TestResponse":
#             _LOGGER.info(f"Topic nlu/query: {objPayload['customData']} processing begins")
#             # if objPayload['input'] != "No":
#             #     return ContinueSession(text=f"{objPayload['input']}. say something back?", custom_data="TestResponse",)
#             # else:
#             #     return EndSession("Fine be that way!", "TestResponse")            
#             _LOGGER.info(f"Topic nlu/query: {objPayload['customData']} processing ends")
#     else:
#         _LOGGER.info(f"Topic nlu/query: query ignored, no custom data")
#     _LOGGER.info("Topic nlu/query: Completed")

# @app.on_topic("rhasspy/asr/{site_id}/{conversation_id}/audioCaptured")
# async def test_topic1(data: TopicData, payload: bytes):
#     _LOGGER.info("Topic 1 Fired!")
#     _LOGGER.info(f"Topic 1: {data}")
#     _LOGGER.info(f"Topic 1: {payload}")

# @app.on_topic("hermes/asr/textCaptured")
# async def test_topic4(data: TopicData, payload: bytes):
#     _LOGGER.info("Topic 4 Fired!")
#     _LOGGER.info(f"Topic 4: {data}")
#     _LOGGER.info(f"Topic 4: {payload}")
#     objPayload = json.loads(payload)
#     if objPayload['customData'] is not None:
#         _LOGGER.info(f"Topic 4: {objPayload['text']}")
#     else:
#         _LOGGER.info(f"Topic 4: query ignored, no custom data")
#     _LOGGER.info("Topic 4 Completed!")

# @app.on_topic("hermes/dialogueManager/sessionStarted")
# async def test_topic2(data: TopicData, payload: bytes):
#     """Receive verbatim topic."""
#     _LOGGER.info("Topic 2 Fired!")
#     _LOGGER.info("topic2: %s, payload: %s", data.topic, payload.decode("utf-8"))

# @app.on_topic("rhasspy/asr/recordingFinished")
# async def test_topic3(data: TopicData, payload: bytes):
#     """Receive verbatim topic."""
#     _LOGGER.info("Topic 3 Fired!")
#     _LOGGER.info("Topic 3: %s, payload: %s", data.topic, payload.decode("utf-8"))

if __name__ == "__main__":
    _LOGGER.info("Starting Hermes App: Test")
    app.run()