"""Test app built to continue session and respond to the user"""
import logging

from rhasspyhermes_app import HermesApp
from rhasspyhermes.nlu import NluIntent
from rhasspyhermes_app import EndSession, ContinueSession, HermesApp
from rhasspyhermes.dialogue import DialogueIntentNotRecognized

_LOGGER = logging.getLogger("TestResponseApp")

app = HermesApp("TestResponseApp")

@app.on_intent("TestResponse")
async def test_response(intent: NluIntent):
    """Respond to the user"""
    _LOGGER.info(f"Session: {intent.session_id} | TestResponse intent: Fired")  
    #start_session = DialogueStartSession(init=DialogueNotification(text="Say something back?"), site_id=intent.site_id, lang=intent.lang, custom_data="TestResponse") 
    
    data = {
        "intent_name": "TestResponse",
        "input_text": intent.input,
        "intent_slots": intent.slots
    }
    
    _LOGGER.info(f"Session: {intent.session_id} | Continuing session")  
    return ContinueSession(
        text="Say something back?", custom_data=data, send_intent_not_recognized=True
    )

@app.on_dialogue_intent_not_recognized
async def not_understood(intent_not_recognized: DialogueIntentNotRecognized):
    _LOGGER.info(f"Session: {intent_not_recognized.session_id} | Started: Intent Not Recognized Handler for test app")    
    customData = intent_not_recognized.custom_data
    if customData is not None:
        _LOGGER.debug(f"Session: {intent_not_recognized.session_id} | ContinueSession Handler: customData exists: {customData}")
        if customData['intent_name'] == "TestResponse":
            _LOGGER.info(f"Session: {intent_not_recognized.session_id} | ContinueSession Handler: Handling: {customData['intent_name']}")
            if intent_not_recognized.input.lower() != "no":
                _LOGGER.info(f"Session: {intent_not_recognized.session_id} | ContinueSession Handler: Responding to: {intent_not_recognized.input}")
                customData['input_text'] = intent_not_recognized.input
                return ContinueSession(text=f"you said {intent_not_recognized.input}, now say something back?", custom_data=customData, send_intent_not_recognized=True)
            else:
                customData['input_text'] = intent_not_recognized.input
                _LOGGER.info(f"Session: {intent_not_recognized.session_id} | ContinueSession Handler: Ending session in response to: {intent_not_recognized.input}")
                return EndSession(text="Fine be that way!", custom_data=customData)            

if __name__ == "__main__":
    _LOGGER.info("Starting Hermes App: Test")
    app.run()