# The following script is used to validate the accuracy of model by testing it on testing audio dataset
# and preapring the validation graph 

# The following script is intended to use large 
# Wav2Vec 2.0 XLSR model in hindi language
# NOTE: The following libraries must be present in the python environemnt in order to run the following script

import torch, torchaudio
from gensim.models import FastText
import os,concurrent.futures
import soundfile as sf
from scipy import signal
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor


# initializing all the parameters
asr_model_path="/home/sbt/HuggingFaceModels/build6/checkpoint-10000"
FastText_model_path="/home/samarth/testing/salesphony_testing/backend/app/utils/Models/fasttest_general/fastText/fastText_500.bin"
base_path="/home/sbt/HuggingFaceModels/data"
test_data_path=f"{base_path}/test" # the test path consisting of all the audios 
dimension=-1 # to be reduced of the final tensor

# NOTE: The column name names are aslo hardcoded in the following script 
# path: this column corresponds to the audio file ids (For e.g. 651bdd28d4c1b488bd04381f.wav)
# sentence: these are the corresponding transcript of the audio file of corresponding id

chunk_size=1550
SAMPLE_RATE=16000
# processor = Wav2Vec2Processor.from_pretrained("theainerd/Wav2Vec2-large-xlsr-hindi")
# model = Wav2Vec2ForCTC.from_pretrained("theainerd/Wav2Vec2-large-xlsr-hindi")
# processor = Wav2Vec2Processor.from_pretrained(asr_model_path)
# model = Wav2Vec2ForCTC.from_pretrained(asr_model_path)
partials=[] # dictionary pool for the chunks 
resampler = torchaudio.transforms.Resample(8000, 16000)
# load the fastText model
# fasttext_model=FastText.load(FastText_model_path)
# fasttext_model=KeyedVectors.load_word2vec_format(FastText_model_path, binary=True)


def testing_audio_chunks(audio_file_path,chunk_size,sample_rate):
    """
    The following funtion is used to:
    1) Break the audio and process in chunks
    2) Upsample the chunks in same time and give a prediction of transcript
    """
    upsampled_chunks=[]
    # current sample rate of audio files
    # open_audios=[sf.read(f"{audio_file_path}/{audio_files}") for audio_files in os.listdir(audio_file_path)[1]]
    open_audios=[sf.read(f"{audio_file_path}/{os.listdir(audio_file_path)[1]}")]
    check_frame_rate=[audio_file[1] for audio_file in open_audios]
    # break the audio file in chunks
    chunked_audio_lengths=[len(audios[0])//chunk_size for audios in open_audios]
    break_audio=[audio_data[0][i  * chunk_size:(i+1) * chunk_size] for chunked_length in chunked_audio_lengths for i in range(chunked_length) for audio_data in open_audios ]
    word_list=["हाँ","राजा","नहीं","बजट","लोन","पैसे","रुपए","जगह","करोड़","गुडगाँव"]
    
    for chunk in break_audio:
        # if len(chunk) !=0:
        upsample_chunk=[signal.resample(chunk,len(chunk)*sample_rate//old_frame_rate) for old_frame_rate in check_frame_rate ][0]
        upsampled_chunks.append(upsample_chunk)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            transcript_predict=executor.submit(predict_chunk_transcript,upsample_chunk,SAMPLE_RATE,dimension)
            asr_transcript=transcript_predict.result()
            transcript_similarity=executor.submit(find_similarity,word_list,asr_transcript)
            print(transcript_similarity.result())
            partials.append(transcript_similarity.result()) if transcript_similarity.result() != "" else partials.append(asr_transcript[0])
                
    # predicting the transcript of the usampled chunks
    transcript=''.join(partials)
    print("Chunks upsampled")

def process_chunk(chunk,sample_rate,asr_processor,asr_model):
    """
    Following function is only used to parse the chunk from model_server
    to asr and fastText model 
    """
    process_asr_model=predict_chunk_transcript(chunk,sample_rate,asr_processor,asr_model,-1)
    # process_fasttext_model=find_similarity(words_list,process_asr_model,fasttext_model)
    return process_asr_model

def predict_chunk_transcript(audio_array,audio_sample_rate,model_processor,asr_model,dimension): # parameter--> fast_text_model_path
    """
    The following function is used to prepare the ASR large Wav2Vec XLSR model
    a) test_data_path: path for the testig audio files
    b) audio_sample: the sampling rate of the audios
    c) dimension: the dimension by which the output tensor will be reduced
    """
    inputs=model_processor(audio_array, sampling_rate=audio_sample_rate, return_tensors="pt", padding=True)
    # device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # print(inputs.input_values.shape)
    # print(inputs.attention_mask.shape)
    # print(asr_model.config)
    with torch.no_grad():
        logits=asr_model(inputs.input_values.to("cuda"),attention_mask=inputs.attention_mask.to("cuda")).logits
    predicted_ids=torch.argmax(logits, dim=dimension)
    output=model_processor.batch_decode(predicted_ids)
    # partials["Partials"]=output
    return output

def find_similarity(word_list,chunk,fasttext_model):
    """
    Following function will:
    1) loads the FastText model
    2) check the similariy of chunk with words in given list
       using he FastText model
    """
    similarities=""
    for word in word_list:
        # if word in fasttext_model.vocab and chunk in fasttext_model.vocab:
        similarity=fasttext_model.wv.similarity(chunk,word)
        if similarity[0] > 0.67:
            similarities=word
            print(similarity)
    return similarities

if "__main__" == __name__:
    # audio_data_path="/home/samarth/testing/extra_testing/local_salesphony_testing/salesphony_testing/Model/db/asr/general/train/test"
    audio_data_path="/home/samarth/testing/extra_testing/local_salesphony_testing/salesphony_testing/Model/db/asr/domain/exp/audio"
    data = testing_audio_chunks(audio_data_path,chunk_size,SAMPLE_RATE)           