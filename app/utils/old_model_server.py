# The following script is the model_server which is used to:
# 1) Live Streams: Fetch live audio streams from twilio
# 2) Predict Transcript: Predict the transcript using HuggingFace Wav2Vec2.0 model of the live chunks
# 3) Predict entities: Predict the entities from the live transcript of chunks
# 4) Report Generation: Finally generating the report on the basis of transcript and entities

import asyncio
import base64
import websockets
import json,torchaudio,torch
import numpy as np
import base64,noisereduce
from gensim.models import FastText
from pydub import AudioSegment
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
from test_model import process_chunk
# from predict_tags import process_data

# initializing parameters
HTTP_PORT=5000
UPSAMPLE_RATE=16000
sample_width=2
chunk_size=2054
channels=1
partials=[] # dictionary pool for the chunks
chunks_list=[] # --------------------------> [b'1',b'2',b'3'.......] upto size of 1054
recording=[]
resampler=torchaudio.transforms.Resample(8000,16000)
base_path="/home/samarth/testing/salesphony_testing/backend/app/utils"
model_base_path="/home/samarthjangda/testing/salesphony_testing/backend/app/utils/Models/fastText"
# output_file=wave.open(f"{base_path}/NewRecordedAudio.wav",'wb')
# output_file.setparams((channels, 2, 8000, 0, 'NONE', 'not compressed'))

def save_audio_recording(audio_chunk_list,output_filepath):
    """
    Following function is used to save the live call data
    to a wav file
    """
    total_frames=len(audio_chunk_list[0])
    complete_audio=np.frombuffer(b''.join(audio_chunk_list),dtype=np.uint8)
    remove_noise=noisereduce.reduce_noise(complete_audio,sr=UPSAMPLE_RATE)
    # normalized_array=complete_audio/np.max(np.abs(complete_audio))
    audio_segment=AudioSegment(remove_noise.tobytes(),sample_width,UPSAMPLE_RATE,channels)
    audio_segment.export(f"{output_filepath}/RecordedSampleAudio.wav",format="wav")
    return {"Message":"Total number of frames are {} and saved in...{}".format(total_frames,output_filepath)}        

def upsample_live_chunks(chunk_array):
    """
    Following functio is used to:
    1) Check sample rate of chunks to be 16khz
    2) To upsample the audio to 16khz , since Huggingface works on 16khz
    """
    audio_tensor=torch.from_numpy(chunk_array).float()
    upsampled_tensor=resampler(audio_tensor)
    upsampled_array=upsampled_tensor.numpy()
    # upsampled_chunk=signal.resample(chunk_array,chunk_size*sample_rate//old_sample_rate)
    return {"UpsampledChunk":upsampled_array}

# def predict_transcript(new_sampled_chunks):
#     """
#     The following function is used to :
#     1) Predict the transcript of live streamed chunks 
#     2) Senc the chunks to the NER model for entity recognition
#     """
#     # predicted_chunk_transcript=predict_chunk_transcript(new_sampled_chunks,UPSAMPLE_RATE,-1)
#     predicted_chunk_transcript = process_chunk(new_sampled_chunks,UPSAMPLE_RATE,processor,model,word_list,fasttext_model)
#     return predicted_chunk_transcript
    
def entity_prediction(chunk_transcript):
    """
    The following function is used to :
    1) Predict the entities from the live streamed transcript
    2) Send the entities,transcript for report generation
    """
    return chunk_transcript
    # tags=process_data(chunk_transcript)

async def handle_websocket(websocket, path):
    # global predicted_chunk_transcript
    loop=asyncio.get_running_loop()
    print("WebSocket connection established")
    # Function to handle incoming WebSocket messages
    await asyncio.sleep(2)
    async for message in websocket:
        json_data=json.loads(message)
        if json_data.get("event") == "connected":
            print("Model Server is connected....")
        if json_data.get("evemt") == "start":
            print("Model Server is started listening to streams.....")    
        if json_data.get("event") == "media":
            data={
                "StreamID":json_data.get("streamSid"),
                "SequenceNo":json_data.get("sequenceNumber"),
                "Message_Payload":base64.b64decode(json_data.get("media").get("payload"))
            }
            
            chunks_list.append(data.get("Message_Payload"))
            if len(chunks_list) > 1:
                streamed_bufer=b''.join(chunks_list)
                if len(streamed_bufer) >= chunk_size:
                    # print(len(streamed_bufer))
                    chunk_array=np.frombuffer(streamed_bufer,dtype=np.int8)
                    # normalized_array=chunk_array/np.max(np.abs(chunk_array))
                    resulted_upsample_chunk= upsample_live_chunks(chunk_array).get("UpsampledChunk")
                    # print(len(resulted_upsample_chunk))
                    predicted_chunk_transcript = process_chunk(resulted_upsample_chunk,UPSAMPLE_RATE,processor,model)
                    print(f"Partials:{predicted_chunk_transcript}")
                    chunks_list.clear()
            # if voice_detection(pcm_audio_data.tobytes()).get("Message") ==True:
            #     chunks_list.append(pcm_audio_data.tobytes())
            #     recording.append(data.get("Message_Payload"))
            #     if len(chunks_list) > 1:
            #         streamed_bufer=b''.join(chunks_list)
            #         if len(streamed_bufer) >= chunk_size:
            #             # print(f"Streamed_Buffer:{streamed_bufer}")
            #             chunk_array=np.frombuffer(streamed_bufer,dtype=np.int16)
            #             normalized_array=chunk_array/np.max(np.abs(chunk_array))
            #             resulted_upsample_chunk= upsample_live_chunks(16000,normalized_array,len(streamed_bufer))
            #             with concurrent.futures.ThreadPoolExecutor() as executor:
            #                 predict_chunk_transcript=executor.submit(predict_transcript,resulted_upsample_chunk.get("UpsampledChunk"))
            #                 resulted_chunk=predict_chunk_transcript.result()
            #                 print(f"Partials:{resulted_chunk}")
            #                 partials.append(resulted_chunk[0])
            # else:
            #     print("Message:{}".format(voice_detection(data.get("Message_Payload")).get("Message")))                
                    #     entities=executor.submit(entity_prediction,resulted_chunk)
                    #     predicted_entities=entities.result()
                    #     # save the entities in some memory
                    # final_response=' '.join(partials)
                    # print("Final:{}".format(final_response))
                    # chunks_list.clear()
            
        if json_data.get("event") == "stop":
                print("Model Server has stopped listening....")
                    
                   
       
    print("Length of recording list is: {}".format(len(recording)))
    # save the live call to a wav file
    save_audio_recording(recording,base_path)
    # await websocket.send()

# Start the WebSocket server
start_server = websockets.serve(handle_websocket, 'localhost', HTTP_PORT,ping_interval=None)  # Replace 'localhost' with your server's IP if needed
# load all models fastText/fastText_500.bin
asr_model_path="/home/sbt/HuggingFaceModels/build6/checkpoint-10000"
FastText_model_path=f"{model_base_path}/fastText_500.bin"
# fasttext_model=FastText.load(FastText_model_path)
processor = Wav2Vec2Processor.from_pretrained("theainerd/Wav2Vec2-large-xlsr-hindi")
model = Wav2Vec2ForCTC.from_pretrained("theainerd/Wav2Vec2-large-xlsr-hindi")
model.to("cuda")
word_list=["हाँ","राजा","नहीं","बजट","लोन","पैसे","रुपए","जगह","करोड़","गुडगाँव"]
print("Started listening on https://localhost:{}".format(HTTP_PORT))
# processor = Wav2Vec2Processor.from_pretrained(asr_model_path)
# model = Wav2Vec2ForCTC.from_pretrained(asr_model_path)
asyncio.get_event_loop().run_until_complete(start_server)

asyncio.get_event_loop().run_forever()
