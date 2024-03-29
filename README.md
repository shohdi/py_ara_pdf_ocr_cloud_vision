# Arabic PDF Ocr

This is an arabic pdf ocr<br />
it first extract pdf to images<br />
read images by ocr using tesseract (tesseract should be installed)<br />
then output it as html page<br />
before run the code read help.txt file<br />
this help is for mac os <br />
in order for hunspell to work :<br />
extract arabic dictionary from ayaspell (http://sourceforge.net/projects/ayaspell/files/hunspell-ar_3.5.2014-11-08.zip/download) to hunspell-ar_3.1 folder in root path<br />
to run the app : <br />
in the folder where ocr.py found <br />
python ocr.py --filename={pdf file full path} --allowSpell={True to allow spell check}<br />
the output file will be created in same path with same name but end with html not pdf<br />



