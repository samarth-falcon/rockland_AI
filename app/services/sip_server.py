# the following code is intended to build the SIP server and integrate with the
# the model server 
import subprocess,requests,base64
# from pjsua2 import Account,AccountConfig,AudDevManager,Call,Endpoint,EpConfig,AuthCredInfo
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException
from app.utils import predict_tags

client = AsyncIOMotorClient("mongodb://localhost:27017/")

async def user_data_authentication(db_name,collection,user_name,phone_number):
    """
    The following function is used to authenticate the user data being
    login, mean both should be the same
    """
    database=client[db_name]
    collection_name=database[collection]
    if await collection_name.find_one({"username":user_name}) == None and await collection_name.find_one({"phone_number":phone_number}) == None:
        raise HTTPException(status_code=404, detail="Unauthorized")
    return {"UserName":user_name,"PhoneNumber":phone_number}

# async def create_sip_user_details(db_name,collection,call_details,sip_details):
#     """
#     The following function is used to create: 
#     1) user details in mongodb sip collection 
#     2) user details in the SIP server
#     """
#     sip_admin=sip_details.get("AdminName")
#     sip_password=sip_details.get("Adminpassword")
#     sip_server=sip_details.get("SipServer")
#     sip_server_domain=sip_details.get("SipServerDomain")
#     database=client[db_name]
#     collection_name=database[collection]
#     if await collection_name.find_one({"phone_number":call_details.phone_number}) == None:
#         print("User is already registered in the SIP, hence ignoring user data creation")
#     else:
#         # Creating the user details in the SIP collection
#         creating_sip_detail=await collection_name.insert_one(call_details.dict())
#         print("User data created successfully")
#     # creating the user data in SIP pjsua account
#     account=AccountConfig()
#     account.id=f"sip:{sip_admin}@{sip_server}"
#     account.realm=f"{sip_server_domain}"
#     account.regConfig.registrarUri=f"sip:{sip_server_domain}"
#     account.regConfig.registrarOnAdd=True
#     auth_cred_info= AuthCredInfo("digest", "*",sip_admin, 0, sip_password)
#     account.sipConfig.authCreds.append(auth_cred_info)
#     create_account=Account()
#     create_account.create(account)
#     return {"StatusCode":200,"SipAccount":create_account,"Message":"The User SIP details are finally registered in MongoDB and SIP server"}

def make_call(twilio_client,twilio_number,sales_number,ngrok_base_url):
    """
    The following function is the main code which will start the SIP server
    and connect the incoming call from frontend 
    1) authenticate the user data
    2) check if the models are loaded and server is started
    3) start the multithreading part for recording and sending chunks to model server
    """
    call=twilio_client.calls.create(
        record=True,
        url=f"http://{ngrok_base_url}/sip/generate_twiml",
        to=f"+91 {sales_number}",
        from_=twilio_number,
        # status_callback=f'https://{ngrok_base_url}/sip/call_status',
        # status_callback_method='POST'
    )
    print(call.sid)
    # start_streams=sip_client(twilio_client,call.sid,ngrok_base_url)
    return{"Calling_ID":call.sid}
 
def get_recording(file_path,account_sid,auth_token,call_sid,recording_url):
    """
    The following function is to save the twilio recorded
    call in backend and process the same to ASR model
    """
    # send a request to get the contents of url
    credentials=f"{account_sid}:{auth_token}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    auth_header = {
        'Authorization': 'Basic ' + encoded_credentials
    }
    print(recording_url)
    resp=requests.get(f"{recording_url}",headers=auth_header)
    print(resp)
    if resp.status_code ==200:
        # save the audio and parallely process to model
        file_name=open(f"{file_path}/{call_sid}.wav",'wb')
        file_name.write(resp.content)
        # start the client to process call
        print("Starting the audio synthesis")
        client="/home/samarthjangda/testing/salesphony_testing/backend/app/utils/test_wav.py"
        process=subprocess.run(['python3',client,f"{file_path}/{call_sid}.wav"])
        # logic to check if the above process is ended
        if process.returncode==0:
            print("Processing data to entities")
            get_etys=predict_tags.process_data("/home/samarthjangda/testing/salesphony_testing/prediction.txt")
            print(get_etys)
            return {"StatusCode":200,"transcript":open("/home/samarthjangda/testing/salesphony_testing/prediction.txt",'r'),"entities":get_etys}
    else:
        print("Applicaation error")   