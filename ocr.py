

from glob import glob
from importlib.resources import path
from logging import root
from re import T
from textwrap import wrap



import io
import os
import shutil
import re
import argparse
from threading import Thread
import threading
import time



import tkinter as tk
from tkinter import filedialog
import json
from google.cloud import storage
from google.cloud import vision
from google.cloud.vision_v1 import types


class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self,  *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()
        

    def stopped(self):
        return self._stop_event.is_set()


def sort_blob(blob):
    """Sorts blobs based on the numerical part of their name."""
    
    return f"{int(re.search('output-([0-9]+)-', blob.name).group(1)):0>{4}}"


def getPdfJsonFiles(pdf_file):
    ret = []
    with open('sample.json', 'r',encoding='utf-8') as f:
        data = json.load(f)
    
    ret.append(data)

    return ret
    

def load_config(config_file_path):
    with open(config_file_path, 'r') as f:
        config = json.load(f)
    return config

def upload_to_bucket( file_path, destination_blob_name):
    """Uploads a file to a Google Cloud Storage bucket."""
    pathDir,pathName = os.path.split(destination_blob_name)
    config_file_path = "config/config.json" 
    config = load_config(config_file_path)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config["service_account_key_path"]
    bucket_name = config["bucket_name"]
    storage_client = storage.Client(project=config["project_id"])
    bucket = storage_client.bucket(bucket_name)
    
    blob_list = [
        blob.name
        for blob in list(bucket.list_blobs(prefix=pathDir))
        if not blob.name.endswith("/")
    ]
    
    if destination_blob_name in blob_list:
        return
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(file_path)

    print(f"File {file_path} uploaded to {destination_blob_name} in bucket {bucket_name}.")


def async_detect_document(gcs_source_uri, gcs_destination_uri):
    """OCR with PDF/TIFF as source files on GCS"""
    
    
    config_file_path = "config/config.json" 
    config = load_config(config_file_path)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config["service_account_key_path"]
    bucket_name = config["bucket_name"]
    storage_client = storage.Client(project=config["project_id"])
    bucket = storage_client.get_bucket(bucket_name)
    # List objects with the given prefix, filtering out folders.
    blob_list = None
    try:
        blob_list = [
            blob
            for  blob in list(bucket.list_blobs(prefix=gcs_destination_uri))
            if not blob.name.endswith("/")
        ]
    except Exception as ex:
        blob_list = None


    if blob_list is None or len(blob_list) == 0:

        # Supported mime_types are: 'application/pdf' and 'image/tiff'
        mime_type = "application/pdf"

        # How many pages should be grouped into each json output file.
        batch_size = 1

        client = vision.ImageAnnotatorClient()
        feature = types.Feature(
            type=vision.enums.Feature.Type.DOCUMENT_TEXT_DETECTION
        )
        #feature = vision.enums.Feature.Type.DOCUMENT_TEXT_DETECTION
        sourcePath  = "gs://" + bucket_name + "/" + gcs_source_uri
        destPath  = "gs://" + bucket_name + "/" + gcs_destination_uri
        gcs_source = types.GcsSource(uri=sourcePath)
        #gcs_source = vision.GcsSource(uri=sourcePath)
        input_config = types.InputConfig(gcs_source=gcs_source, mime_type=mime_type)
        gcs_destination = types.GcsDestination(uri=destPath)
        #gcs_destination = vision.GcsDestination(uri=destPath)
        output_config = types.OutputConfig(
            gcs_destination=gcs_destination, batch_size=batch_size
        )

        async_request = types.AsyncAnnotateFileRequest(
            features=[feature], input_config=input_config, output_config=output_config
        )

        operation = client.async_batch_annotate_files(requests=[async_request])

        print("Waiting for the operation to finish.")
        operation.result(timeout=420)

        # Once the request has completed and the output has been
        # written to GCS, we can list all the output files.
        

        
        
        prefix = gcs_destination_uri

        

        # List objects with the given prefix, filtering out folders.
        blob_list = [
            blob
            for  blob in list(bucket.list_blobs(prefix=prefix))
            if not blob.name.endswith("/")
        ]
        
        print("Output files:")
    out_str = ''
    blob_list.sort(key=sort_blob)
    for blob in blob_list:
        print(blob.name)

        # Process the first output file from GCS.
        # Since we specified batch_size=2, the first response contains
        # the first two pages of the input file.
        output = blob

        json_string = output.download_as_bytes().decode("utf-8")
        response = json.loads(json_string)

        # The actual response for the first page of the input file.
        first_page_response = response["responses"][0]
        if first_page_response is not None and "fullTextAnnotation" in first_page_response :
            annotation = first_page_response["fullTextAnnotation"]

            # Here we print the full text from the first page.
            # The response contains more information:
            # annotation/pages/blocks/paragraphs/words/symbols
            # including confidence scores and bounding boxes
            #print("Full text:\n")
            #print(annotation["text"])
            if annotation is not None and "text" in annotation :
                out_str = out_str + getJsonHtmlFromStr(annotation["text"])
    return out_str
        
        



def getJsonHtmlFromStr(jsonStr):
    myExtractedText = re.sub('[\s]',' ',jsonStr)
    myExtractedText = re.sub('[\t]',' &nbsp;&nbsp;&nbsp; ',myExtractedText)
    myExtractedText = re.sub('[\n]+','<br />',myExtractedText)
    
    
    myExtractedText =  "<p>" +   myExtractedText + "</p>"
    return myExtractedText


spellChecker = None
def pdf_to_txt(pdf_file,allowSpell,rootWindow):
    global wordReplaced
    global txtInput
    global currentExtracted
    global lblBefore
    global lblWord
    global lblAfter
    global lblSuggest
    global currentWord
    global myThread
    global spellChecker
    global lblPageNo
    
    pathDir,pathName = os.path.split(pdf_file)
    pathNameExt = pathName + "_ext"
    extFullPath = pathDir + os.path.sep + pathNameExt
    lblStatus.config(text=extFullPath)
    
    print(extFullPath)
 
    if(os.path.exists(extFullPath)):
        shutil.rmtree(extFullPath)
    
    if(not os.path.exists(extFullPath)):
        os.mkdir(extFullPath)
    
    '''
    with io.open(pdf_file,'rb') as myFile:
        btArr = myFile.read()
    images = pdf2image.convert_from_bytes(btArr)#,output_folder=extFullPath)
    '''
    lblStatus.config(text='getting pdf info ')
    
    print('getting pdf info ')
    #infoFile = pdf2image.pdfinfo_from_path(pdf_file)
    #lblStatus.config(text=str(infoFile))
    
    #print(infoFile)
    #lastPage = (3 if int(infoFile["Pages"]) > 3 else infoFile["Pages"] )
    #images = pdf2image.convert_from_path(pdf_file,last_page=lastPage)#,output_folder=extFullPath)
    lblStatus.config(text='start converting pdf to images in '+ extFullPath + os.path.sep)
    
    
    #print('start converting pdf to images in ',extFullPath + os.path.sep)
    #cmdLine = 'pdftoppm '
    #cmdLine = cmdLine + '-l ' + str(lastPage) + ' '
    #cmdLine = cmdLine  +'"' +pdf_file+'"' + ' '
    #cmdLine = cmdLine  + '"' + extFullPath + os.path.sep + '"'


    #stream = os.popen(cmdLine)
    #output = stream.read()
    #if "error" in output.lower():
    #    raise Exception(output)
    
    #imageNames =  os.listdir(extFullPath)
    #imageNames.sort()


    # Example usage:
    
    file_path = pdf_file
    destination_blob_name = "books/" + pathName  # Optional - include a folder path if desired

    upload_to_bucket( file_path, destination_blob_name)
    innerDoc = async_detect_document(destination_blob_name,'books/' + pathName + '/out/')
    indx = 1
    #files = getPdfJsonFiles(pdf_file)
    out_str = '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8" /></head><body>'

    '''
    for jsonPage in files:
        if myThread.stopped():
            return
    
        lblPageNo.config(text='extracting page no ' + str(indx) +' from ' + str(len(files)))

        if jsonPage["textAnnotations"] is not None:
            if len(jsonPage["textAnnotations"]) > 0:
                if jsonPage["textAnnotations"][0]["description"] is not None:
                    myExtractedText = jsonPage["textAnnotations"][0]["description"]
                    myExtractedText = re.sub('[\s]',' ',myExtractedText)
                    myExtractedText = re.sub('[\t]',' &nbsp;&nbsp;&nbsp; ',myExtractedText)
                    myExtractedText = re.sub('[\n]+','<br />',myExtractedText)
                    
                    
                    out_str = out_str + "<p>" +   myExtractedText + "</p>"

        

        indx+=1
    '''
    out_str = out_str + innerDoc

    #out_str = re.sub('[\n]+','<br />',out_str)        
    out_str = out_str + '</body></html>'
    with io.open(pdf_file + '.html','w',encoding='utf-8') as outFile :
        outFile.write(out_str)
    if(os.path.exists(extFullPath)):
        shutil.rmtree(extFullPath)
    rootWindow.quit()
    return





def ocr_core(file):
    #text = pytesseract.image_to_string(file,lang="ara")#,config="--oem 1")
    text = ''
    return text


def print_pages(pdf_file,allowSpell,rootWindow):
    pdf_to_txt(pdf_file,allowSpell,rootWindow)
    
rootWindow = None
allowSpellPrm = None
filenamePrm = None
myThread = None

lblStatus = None
lblSuggest = None
lblBefore = None
lblWord = None
lblAfter = None
txtInput = None
btnIgnore = None
btnCorrect = None

currentExtracted = None
currentWord = None
wordReplaced = None
started = None
btnUpload = None
lblFileName = None
chkDoSpellCheck = None
chkDoSpellCheckVal = None
lblPageNo = None


def button_click():
    global started
    global myThread
    global filenamePrm
    global allowSpellPrm
    global rootWindow
    global filenamePrm

    if  started or filenamePrm is None or filenamePrm == '':
        return
    started = True
    myThread = StoppableThread(target=print_pages,args=(filenamePrm,allowSpellPrm,rootWindow))
    myThread.start()
    #print_pages(filenamePrm,allowSpellPrm,rootWindow)


def btnCorrect_click():
    global wordReplaced
    global txtInput
    global currentExtracted
    global lblBefore
    global lblWord
    global lblAfter
    global lblSuggest
    global currentWord
    
    
    if wordReplaced:
        return
    myText= txtInput.get("1.0","end")
    if(re.sub('[ \n\r\t]+','',myText) != ''):
        myText = re.sub('[\n\r\t]+','',myText)
        currentExtracted = currentExtracted.replace(currentWord,myText)
        currentWord = myText
        lblBefore.config(text='')
        lblWord.config(text='')
        lblStatus.config(text='')
        lblAfter.config(text='')
        txtInput.delete("1.0","end")
        lblSuggest.config(text='')
        wordReplaced = True
        
        
    else:
        currentExtracted = currentExtracted.replace(currentWord,'')
        currentWord = ''
        lblBefore.config(text='')
        lblWord.config(text='')
        lblStatus.config(text='')
        lblAfter.config(text='')
        txtInput.delete("1.0","end")
        lblSuggest.config(text='')
        wordReplaced = True



def btnIgnore_click():
    global wordReplaced
    global txtInput
    
    global lblBefore
    global lblWord
    global lblAfter
    global lblSuggest
    global currentWord
    global spellChecker
    if wordReplaced:
        return
    lblBefore.config(text='')
    lblWord.config(text='')
    lblAfter.config(text='')
    txtInput.delete("1.0","end")
    lblStatus.config(text='')
    lblSuggest.config(text='')
    wordReplaced = True
    spellChecker.add(currentWord)
    

def btnUpload_click():
    global filenamePrm
    global lblFileName
    if started:
        return
    filenamePrm = filedialog.askopenfilename()
    lblFileName.config(text=filenamePrm)

def chkDoSpellCheck_click():
    global allowSpellPrm
    global chkDoSpellCheckVal
    
    if started:
        return
    allowSpellPrm = chkDoSpellCheckVal.get()
    


if __name__ == '__main__':
    

    wordReplaced = True
    started = False
    parser = argparse.ArgumentParser(description='Take filename and is apply hanspell or not.')
    parser.add_argument('--filename',   default = '',
                    help='full path of the pdf file')
    parser.add_argument('--allowSpell',default=False,type=bool,
                    required=False,
                    help='run spell check on result text')

    args = parser.parse_args()
    filenamePrm = args.filename
    allowSpellPrm = args.allowSpell
    rootWindow = tk.Tk()
    btnUpload = tk.Button(rootWindow,
                   text = "اختر الملف",
                   command = lambda:btnUpload_click())
    btnUpload.pack()
    lblFileName = tk.Label(rootWindow,font=("Ariel",16),text=filenamePrm,wraplength=600)
    lblFileName.pack()
    
    '''
    chkDoSpellCheckVal = tk.BooleanVar(value=allowSpellPrm)

    
    chkDoSpellCheck =  tk.Checkbutton(rootWindow, text='اصلح الاخطاء',variable=chkDoSpellCheckVal, onvalue=True, offvalue=False, command=lambda:chkDoSpellCheck_click())
    chkDoSpellCheck.pack()
    '''
    lblPageNo = tk.Label(rootWindow,font=("Ariel",16),text='',wraplength=600)
    lblPageNo.pack()
    lblStatus = tk.Label(rootWindow,font=("Ariel",16),text='',wraplength=600)
    lblStatus.pack(anchor='w')
    lblSuggest = tk.Label(rootWindow,font=("Ariel",16),text='',wraplength=600)
    lblSuggest.pack(anchor='e')
    lblBefore = tk.Label(rootWindow,font=("Ariel",16),text='')
    lblBefore.pack()
    lblWord = tk.Label(rootWindow,fg="red",font=("Ariel",16),text='')
    lblWord.pack()
    lblAfter = tk.Label(rootWindow,font=("Ariel",16),text='')
    lblAfter.pack()
    txtInput = tk.Text(rootWindow,font=("Ariel",16),height=1)
    txtInput.pack()

    '''
    btnCorrect = tk.Button(rootWindow,
                   text = "صحح",
                   command = lambda:btnCorrect_click())
    btnCorrect.pack()
    '''
    '''
    btnIgnore = tk.Button(rootWindow,
                   text = "اهمل",
                   command = lambda:btnIgnore_click())
    btnIgnore.pack()
    '''

    tk.Button(rootWindow,
                   text = "ابدأ",
                   command = lambda:button_click()).pack()
    rootWindow.maxsize(600,800)
    rootWindow.mainloop()
    try :
        myThread.stop()
    except :
        None

    
    started = False






