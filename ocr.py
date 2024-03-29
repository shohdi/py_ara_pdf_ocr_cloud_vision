

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
    pathName = pathName + "_ext"
    extFullPath = pathDir + os.path.sep + pathName
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
    infoFile = pdf2image.pdfinfo_from_path(pdf_file)
    lblStatus.config(text=str(infoFile))
    
    print(infoFile)
    #lastPage = (3 if int(infoFile["Pages"]) > 3 else infoFile["Pages"] )
    #images = pdf2image.convert_from_path(pdf_file,last_page=lastPage)#,output_folder=extFullPath)
    lblStatus.config(text='start converting pdf to images in '+ extFullPath + os.path.sep)
    
    
    print('start converting pdf to images in ',extFullPath + os.path.sep)
    cmdLine = 'pdftoppm '
    #cmdLine = cmdLine + '-l ' + str(lastPage) + ' '
    cmdLine = cmdLine  +'"' +pdf_file+'"' + ' '
    cmdLine = cmdLine  + '"' + extFullPath + os.path.sep + '"'


    stream = os.popen(cmdLine)
    output = stream.read()
    if "error" in output.lower():
        raise Exception(output)
    
    imageNames =  os.listdir(extFullPath)
    imageNames.sort()
    
    indx = 1

    out_str = '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8" /></head><body>'

    for strImage in imageNames:
        if myThread.stopped():
            return
        if(".ppm" in strImage.lower()):
            #start extract ocr
            
            
            lblPageNo.config(text='extracting page no ' + str(indx) +' from ' + str(infoFile["Pages"]))
            
            print('extracting page no ',str(indx),' from ',str(infoFile["Pages"]))
            fName = extFullPath + os.path.sep + strImage
            
            img = Image.open(fName,'r')
            extracted = ocr_core(img)
            if allowSpell:
                if spellChecker is None :
                    spellChecker = Hunspell('ar', hunspell_data_dir='.' + os.path.sep+ 'hunspell-ar_3.1' + os.path.sep)
                lblStatus.config(text='start spell check : ')
                print ('start spell check : ')
                words = re.split('[ \n\r\t]+',extracted)
                words = [re.sub('[^\\u0600-\\u06FF]+','',b) for b in words ]
                words = [re.sub('[\\u0660-\\u0669]+','',b) for b in words ]
                words = [b for b in words if re.sub('[ \n\r\t]+','',b) != '']
                for i,word in enumerate(words):
                    
                    #found word
                    tes = spellChecker.spell(word)
                    if not tes:
                        suggessions = spellChecker.suggest(word)
                        strWrongWord = 'found wrong spelling : ' + str(word)
                        lblStatus.config(text=strWrongWord)
                        print ('found wrong spelling : ' , word , suggessions)
                        strWrongWord = strWrongWord + '\n' + 'من فضلك صحح الكلمة :'
                        num = i - 4
                        if(num < 0):
                            num = 0
                        
                        strBefore = ''
                        while num < i :
                            strBefore = strBefore  + ' ' + words[num]
                            num +=1
                        lblSuggest.config(text='الاحتمالات : ' + str(suggessions))
                        lblBefore.config(text=strBefore)
                        lblWord.config(text=word)
                        num = i + 4
                        if num > len(words)-1:
                            num = len(words)-1
                        strAfter = ''
                        while num > i :
                            strAfter = words[num] + ' ' +  strAfter
                            num -= 1
                        lblAfter.config(text=strAfter)
                        currentWord = word
                        currentExtracted = extracted
                        wordReplaced = False
                        while not wordReplaced and not myThread.stopped():
                            time.sleep(0.1)
                        
                        
                        
                        extracted = currentExtracted
                        words[i] = currentWord
                        

                        

            
                
            if(re.sub('[ \n\r\t]+','',extracted) != ''):
                extracted = re.sub('[ \t]+',' ',extracted)
                extracted = re.sub('[\r]+','',extracted)
                extracted = re.sub('[\n]+','\n',extracted)
                out_str = out_str + extracted + '\n'

            indx+=1


    out_str = re.sub('[\n]+','<br />',out_str)        
    out_str = out_str + '</body></html>'
    with io.open(pdf_file + '.html','w') as outFile :
        outFile.write(out_str)
    if(os.path.exists(extFullPath)):
        shutil.rmtree(extFullPath)
    rootWindow.quit()
    return





def ocr_core(file):
    text = pytesseract.image_to_string(file,lang="ara")#,config="--oem 1")
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
    chkDoSpellCheckVal = tk.BooleanVar(value=allowSpellPrm)
    
    chkDoSpellCheck =  tk.Checkbutton(rootWindow, text='اصلح الاخطاء',variable=chkDoSpellCheckVal, onvalue=True, offvalue=False, command=lambda:chkDoSpellCheck_click())
    chkDoSpellCheck.pack()
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


    btnCorrect = tk.Button(rootWindow,
                   text = "صحح",
                   command = lambda:btnCorrect_click())
    btnCorrect.pack()

    btnIgnore = tk.Button(rootWindow,
                   text = "اهمل",
                   command = lambda:btnIgnore_click())
    btnIgnore.pack()

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






