# the following module is intended to build a SIP pipeline for call initiation
from app.models.sip_calling_models import UserCalling, CheckCallStatus
import app.services.sip_server as sip_details
from fastapi import APIRouter
from twilio.rest import Client
from typing import Annotated
from fastapi import Form, Response, Request
from dotenv import load_dotenv
import uuid,json,time, os

load_dotenv()
router=APIRouter()
open_json=open("app/app.json",'r')
conf_path=json.load(open_json)
database=list(conf_path.get("Databases").keys())[0]
# ngrok_base_url_id="a6ce-223-190-80-248.ngrok-free.app"
# ngrok_server_id="438d-122-162-150-88.ngrok-free.app"

# twilio configurations
TWILIO_SID = os.getenv("twilio_sid")
TWILIO_AUTH = os.getenv("twilio_auth_token")
twilio_number = os.getenv("sip_number")
client=Client(TWILIO_SID,TWILIO_AUTH)

# following api is to fetch the data from frontend basis of which the SIP session will the prepared  

@router.post("/calling_data")
async def get_calling_user_data(calls:UserCalling) -> dict:
    calls.call_id=str(uuid.uuid4()) # following is the unique uuid for each user
    username=calls.username
    user_number=calls.phone_number
    print("Data recieved of the user is {}".format(calls))
    # authenticating the data recieved
    user_collection_name=conf_path.get("Databases").get(database).get("collections").get("usersdata")
    # basic level of user validation
    validate_user_data_from_db=sip_details.user_data_authentication(database,user_collection_name,username,user_number)
    print("Initial level of validation of user is completed : {}".format(validate_user_data_from_db))
    # now creating the data in SIP server
    sip_collection=conf_path.get("Databases").get(database).get("collections").get("sipuserdata")
    sip_server_details=conf_path.get("sip_details")
    create_data=sip_details.create_sip_user_details(database,sip_collection,calls,sip_server_details)

@router.get("/generate_twiml")
async def make_twiml_file():
    # here Stream url will be same url as set in twilio twiml of ngrok
    # <Start>
    #         <Stream name="Example Audio Stream" url="wss://{ngrok_server_id}/" />
    #     </Start>
    twiml_response=f"""
    <Response>
        <Dial callerId="{twilio_number}">
            <Number>+91 9555455456</Number>
        </Dial>
    </Response>
    """
    # http://2be9-223-190-83-53.ngrok-free.app/sip/audio_stream
    return Response(content=twiml_response, media_type="application/xml")

# @router.post("/call_status")
# async def check_call_status(request:Request):
#     """
#     The following api is used by twilio to make a 
#     POST request to check the call status .
#     """
#     json_body={}
#     response=await request.body()
#     twilio_data=response.decode().split("&")
#     for data in twilio_data:
#         key,value=data.split('=')
#         json_body[key]=value
#     base_path="/home/samarthjangda/testing/salesphony_testing/recordings"
#     call_status=json_body.get("CallStatus")
#     call_sid=json_body.get("CallSid")
#     recording_sid=json_body.get("RecordingSid")
#     if call_status == "completed":
#         print(f"Call is completed with sid:{call_sid} and now processing the same to ASR model")
#         # retrieve the recording
#         recording_data=client.recordings(recording_sid).fetch()
#         print(recording_data.uri)
#         recording_status=recording_data.status
#         while recording_status=='processing':
#             time.sleep(2)
#             recording_data=client.recordings(recording_sid).fetch()
#             recording_status=recording_data.status
#         recording_url=recording_data.uri.replace(".json",".wav")
#         audio_url=f"https://api.twilio.com/{recording_url}"
#         # check if recording is completed
#         save_recording=sip_details.get_recording(base_path,account_sid,auth_token,call_sid,audio_url)

@router.post("/get_recording")
async def get_recording(recording_url:Annotated[str,Form()],account_sid:Annotated[str,Form],auth_token:Annotated[str,Form],call_sid:Annotated[str,Form()]):
    """
    The following api is used to:
    1) Save the live call in the form of recording
    2) Fetch the transcript from the recording
    3) Fetch the entities based on the transcript 
    """
    base_path="/home/samarthjangda/testing/salesphony_testing/recordings"
    recording_url=recording_url.replace(".json",".wav")
    audio_url=f"https://api.twilio.com/{recording_url}"
    # check if recording is completed
    save_recording=sip_details.get_recording(base_path,account_sid,auth_token,call_sid,audio_url)

# prepare api for vonage 
# http://localhost:8000/voip_user_data
@router.post("/voip_user_data")
async def get_user_data(username:Annotated[str,Form()],password:Annotated[str,Form()],number:Annotated[int,Form()],client_number:Annotated[int,Form()]):
    # This will give the following data in parameters
    # authenticating the data recieved
    user_collection_name=conf_path.get("Databases").get(database).get("collections").get("usersdata")
    # authenticate_user=await sip_details.user_data_authentication(database,user_collection_name,username,number)
    # let's start initiating the call
    initiate_call=sip_details.make_call(client,twilio_number,str(number),ngrok_base_url_id = "")
    return {"StatusCode":200,"Message":"Call Initiated","CallSID":initiate_call.get("Calling_ID")}