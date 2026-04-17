# the following code is intended to build the SIP server and integrate with the
# the model server 
from openai import OpenAI
from dotenv import load_dotenv
from fastapi import HTTPException
from app.utils import predict_tags
from requests.auth import HTTPBasicAuth
import os, subprocess, requests, base64, logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.services.connect_db import connect_mysql_database

client = AsyncIOMotorClient("mongodb://localhost:27017/")
load_dotenv()

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

def fetch_call_data():
    """
    The following function is used to
    fetch the calling data on the basis of latest date.
    """
    check_connection = connect_mysql_database()
    if check_connection.get("status_code") == 200:
        connection = check_connection.get("Message")
        logging.info("Database is connected")
        fetch_data_query = """
            SELECT * FROM twilio_call
            ORDER BY created_at DESC
            LIMIT 1;
        """
        cursor = connection.cursor()
        try:
            cursor.execute(fetch_data_query)
            latest_call_data = cursor.fetchone()
            return latest_call_data
        except Exception as e:
            logging.error(f"Unable to fetch latest call data: {e}")
        finally:
            cursor.close()
            connection.close()    
        

def save_user_call_data(data_json):
    """
    The following function is used to save the
    calling data of the user in the mysql server
    Data: {customer_name, customer_number, caller_name, call_type, call_date, call_sid}
    """
    check_connection = connect_mysql_database()
    if check_connection.get("status_code") == 200:
        logging.info("Database is Connected")
        data_values = (
            data_json.get('customer_name'),
            data_json.get("call_type"),
            data_json.get("caller_name"),
            data_json.get("call_date"),
            data_json.get("customer_number"),
            data_json.get("call_sid")
        )    
        insert_data_query = f"""
            INSERT INTO twilio_call(
                customer_name,
                call_type,
                caller_name,
                call_date,
                customer_number,
                call_sid
            )
            VALUES (%s, %s, %s, %s, %s, %s);
        """
        cursor = check_connection.get("Message").cursor()
        try:
            cursor.execute(insert_data_query, data_values)
            check_connection.get("Message").commit()
        except Exception as e:
            logging.error(f"Unable to enter data: {e}")    
        finally:
            cursor.close()
            check_connection.get("Message").close()      
    else:
        logging.error("Database Not Connected")

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
        url=f"https://{ngrok_base_url}/sip/generate_twiml?to=+{sales_number}",
        to=f"+919999044903", # --------------> This number should be the one to which twilio calls first
        from_= twilio_number,
        # status_callback=f'https://{ngrok_base_url}/sip/call_status',
        # status_callback_method='POST'
    )
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
    resp=requests.get(f"{recording_url}",headers=auth_header)
    if resp.status_code ==200:
        # save the audio and parallely process to model
        file_name=open(f"{file_path}/{call_sid}.wav",'wb')
        file_name.write(resp.content)
        # start the client to process call
        print("Starting the audio synthesis")
        
        # call the openai ASR api for:
            # 1) speaker diariazation
            # 2) generating the transcript
        
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
        
def fetch_twilio_call_recording(call_sid):
    """
    The following function is used to fetch the 
    twilio call recording using the provided call_sid:
    1) First it will call the twilio api to fetch the recording_uri.
    2) Using the recording_uri it will call another api to fetch the recording.
    """
    twilio_account_sid = os.getenv("twilio_sid")
    twilio_account_token = os.getenv("twilio_auth_token")
    recording_uri_api = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_account_sid}/Recordings.json"
    recording_uri_parameters = {
        "CallSid": call_sid,
        "PageSize": 1
    }
    
    recording_uri_response = requests.get(
        recording_uri_api,
        params = recording_uri_parameters,
        auth = HTTPBasicAuth(twilio_account_sid, twilio_account_token)
    )
    fetch_data = recording_uri_response.json()
    if fetch_data['recordings']:
        recording = fetch_data['recordings'][0]
        recording_sid = recording['sid']
        recording_url = f"https://api.twilio.com{recording['uri'].replace('.json', '.mp3')}"
        return{"Recording SID": recording_sid, "Recording URL": recording_url}
    else:
        return("No Recording Found")   

def fetch_call_transcript(local_path_to_save):
    """
    The following function is used to fetch the 
    transcript of the provided recording
    """
    
    input_file = local_path_to_save + r"\audio.mp3"
    caller_file = local_path_to_save + r"\caller.wav"
    customer_file = local_path_to_save + r"\customer.wav"
    os.remove(caller_file)
    os.remove(customer_file)
    subprocess.run([
        "ffmpeg",
        "-i", f"{input_file}",
        "-filter_complex", "[0:a]channelsplit=channel_layout=stereo[left][right]",
        "-map", "[left]", f"{caller_file}",
        "-map", "[right]", f"{customer_file}"
    ])
    
    # fetch transcript
    openai_key = os.getenv("openai_api_key")
    client = OpenAI(api_key = openai_key)
    # transcribing caller data
    with open(caller_file, 'rb') as caller_media:
        caller_text = client.audio.transcriptions.create(
            model = "gpt-4o-transcribe",
            file = caller_media
        ).text
    
    with open(customer_file, 'rb') as customer_media:
        customer_text = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file = customer_media
        ).text
    return {"Caller_Data": caller_text, "Customer_Data": customer_text}        
    
    
         
            