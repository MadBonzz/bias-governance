import base64
import random
import time
import aiohttp
import requests
import json
import os
import asyncio
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--userkey', dest='userkey', type=str, help='Set Rchilli UserKey')
parser.add_argument('--sub-userid', dest='sub_userid', type=str, help='Set Rchilli Sub-UserId')
parser.add_argument('--resume-files-dir', dest='resume_files_dir', type=str, help='Set RESUME_FILES_DIR_PATH: Path to the files to be parsed!')
parser.add_argument('-f', '--force', help="Force Create Required Dir", action="store_true")
args = parser.parse_args()

API_ENDPOINT = "https://rest.rchilli.com/RChilliParser/Rchilli/parseResumeBinary" 
USERKEY = args.userkey
SUBUSERID = args.sub_userid
VERSION = '8.0.0' 


PROJECT_DIR = os.path.dirname(__file__)
# RESUME_FILES_DIR_PATH = os.path.join(PROJECT_DIR, 'naukri_resumes')
# RESUME_FILES_DIR_PATH = '/home/attentioncker/dev/TR/tr-recommendation-ai/dataset/categorized_resumes/unzipped/sales'
# RESUME_FILES_DIR_PATH = '/home/attentioncker/dev/TR/tr-recommendation-ai/dataset/Job-Offered-And-Hired-Candidate/RenewBuy/Resume/selected_dir'
RESUME_FILES_DIR_PATH = args.resume_files_dir

INPUT_DIR = os.path.join(RESUME_FILES_DIR_PATH)
OUTPUT_DIR = os.path.join(RESUME_FILES_DIR_PATH, 'parsed_json')
FAILED_FILES_DIR = os.path.join(RESUME_FILES_DIR_PATH, 'failed_files')
SUCCESS_FILES_DIR = os.path.join(RESUME_FILES_DIR_PATH, 'parsed_files')
# print("This Script Must Be Present in the Same Project Directory where the Input and Output Folders are present")
# print(f"Add all input resume files in {INPUT_DIR}")
# print(f"Add all output parsed files in {OUTPUT_DIR}")

if not os.path.exists(INPUT_DIR):
    inp = input(f"Dir {INPUT_DIR} does not exist. Press 'y' to create or 'n' to quit program: ") if not args.force else 'y'
    if inp == 'y':
        os.makedirs(INPUT_DIR)
    else:
        exit()
else:
    print(f"INPUT dir Exists: {INPUT_DIR}")

if not os.path.exists(OUTPUT_DIR):
    inp = input(f"Dir {OUTPUT_DIR} does not exist. Press 'y' to create or 'n' to quit program: ") if not args.force else 'y'
    if inp == 'y':
        os.makedirs(OUTPUT_DIR)
    else:
        exit()
else:
    print(f"OUTPUT dir Exists: {OUTPUT_DIR}")

if not os.path.exists(FAILED_FILES_DIR):
    inp = input(f"Dir {FAILED_FILES_DIR} does not exist. Press 'y' to create or 'n' to quit program: ") if not args.force else 'y'
    if inp == 'y':
        os.makedirs(FAILED_FILES_DIR)
    else:
        exit()
else:
    print(f"FAILED FILES dir Exists: {FAILED_FILES_DIR}")
    
if not os.path.exists(SUCCESS_FILES_DIR):
    inp = input(f"Dir {SUCCESS_FILES_DIR} does not exist. Press 'y' to create or 'n' to quit program: ") if not args.force else 'y'
    if inp == 'y':
        os.makedirs(SUCCESS_FILES_DIR)
    else:
        exit()
else:
    print(f"SUCCESS FILES dir Exists: {SUCCESS_FILES_DIR}")    


def moveAlreadyParsedFilesToParsedFolder(filenames: list[str]):
    print(f"moving {len(filenames)} to {SUCCESS_FILES_DIR}")
    for filename in filenames:
        src = os.path.join(INPUT_DIR, filename)
        dest = os.path.join(SUCCESS_FILES_DIR, filename)
        try:
            os.replace(src, dest)
        except Exception as e:
            print(e)    

def getUnParsedFiles(inputDir: str, outputDir: str) -> list[str]:
    """
    returns - list of files in inputDir that are not parsed as json in the outputDir
    """
    # inputFiles =
    resumeFiles = [f for f in os.listdir(inputDir) if os.path.isfile(os.path.join(inputDir, f))] 
    failedFiles = [f for f in os.listdir(FAILED_FILES_DIR) if os.path.isfile(os.path.join(inputDir, f))] 
    basenameToExtensionMap = dict(list(map(lambda filename: (filename[0:filename.rfind('.')], filename[filename.rfind('.')+1:]), resumeFiles)))
    # return basenameToExtensionMap
    # idToName = dict(resumeFiles) 
    jsonCounterPartsThatShouldExist = list(map(lambda basename: basename+'.json', basenameToExtensionMap.keys()))
    # already parsed jsons:
    jsonFilesThatExists = [f for f in os.listdir(outputDir) if os.path.isfile(os.path.join(outputDir, f))] 
    unparsedFilesJson = set(jsonCounterPartsThatShouldExist).difference(set(jsonFilesThatExists))
    
    unparsedFiles = []
    for jsonFilename in unparsedFilesJson:
        baseFileName = jsonFilename[:-5]   # remove .json from filename
        filename = baseFileName + '.' + basenameToExtensionMap[baseFileName]
        unparsedFiles.append(filename)
    unparsedFiles = list(set(unparsedFiles).difference(set(failedFiles)))
    # TODO add funcionality for moving those files that are already parsed into the parsed dir
    alreadyParsedFiles = []
    # set(list(map(lambda basename: basename+'.json', basenameToExtensionMap.keys())))
    for parsedJsonFilename in jsonFilesThatExists:
        baseFileName = parsedJsonFilename[:-5]
        if baseFileName in basenameToExtensionMap.keys():
            filename = baseFileName + '.' + basenameToExtensionMap[baseFileName]
            alreadyParsedFiles.append(filename)
    moveAlreadyParsedFilesToParsedFolder(alreadyParsedFiles)
    return unparsedFiles


async def simulateAPICall(*args, **kwargs):
    ts = random.randint(1, 3)
    print(f"Simulating api call for {json.loads(kwargs['data'])['filename']}... will take {ts} seconds")
    
    time.sleep(ts)
    
    fakeResponse = json.dumps({"result": "Done"})
    # throw error 40% of time randomly
    if random.randint(1,10) < 4:
        raise Exception("Server Error")
    return fakeResponse


async def saveParsedJSONToOutputDir(filename, jsonData):
    savefilepath = os.path.join(OUTPUT_DIR, filename[0:filename.rfind('.')] + '.json')
    print(savefilepath)
    try:
        with open(savefilepath, "w") as outfile: 
                json.dump(jsonData, outfile)
    except Exception as e:
        print(f"Failed to save json: {e}")
        return None

async def moveFile(src, dest):
    try:
        os.replace(src, dest)
    except Exception as e:
        print(e)

async def processResponse(response, filename):
    try:
        if response.status == 200:
            data = await response.text()
            jsonData = json.loads(data)
            if 'error' in jsonData.keys():
                raise Exception(f"Error recieved from Response", jsonData['error']) 
            await saveParsedJSONToOutputDir(filename, jsonData)
            await moveFile(os.path.join(INPUT_DIR, filename), os.path.join(SUCCESS_FILES_DIR, filename))
            return "success"
        else:
            raise Exception(f"Response did not return status code 200 (OK). returned {response.status}")
    except Exception as e:
        print(e)
        eArgs = e.args
        if eArgs[0] == f"Error recieved from Response":
            error = eArgs[1]
            if error['errorcode'] == 1003:
                print(error["errormsg"] + " Terminating!")
                exit()                
        await moveFile(os.path.join(INPUT_DIR, filename), os.path.join(FAILED_FILES_DIR, filename))
        return "failed"

async def parseFileUsingRchilli(session, filedir, filename):
    print(f"Parsing: {filename}")
    try:
        st = time.time()
        # Read file and convert it to base64 string:
        with open(os.path.join(filedir, filename), "rb") as file:
            encoded_string_val = base64.b64encode(file.read())
        data64_str = encoded_string_val.decode('UTF-8')

        # Prepare headers and request body
        headers = {'content-type': 'application/json'}
        requestBody = {
            "filedata": data64_str,
            "filename": filename,
            "userkey": USERKEY,
            "version": VERSION,
            "subuserid": SUBUSERID
        }

        # Make API request
        async with session.post(API_ENDPOINT, data=json.dumps(requestBody), headers=headers) as response:
        # async with session.get('https://www.google.com') as response:
            et = time.time()
            print(f"{filename} [SUCCESS] in {et-st}")
            # data = await response.text()
            # jsonData = json.loads(data)
            res = await processResponse(response, filename)
            return (filename, res)
            # await saveParsedJSONToOutputDir(filename, jsonData)
            # return data
            
            
            
        # response = requests.post(API_ENDPOINT, data=json.dumps(requestBody), headers=headers)
        # response.raise_for_status() 
        # res = await simulateAPICall(API_ENDPOINT, data=json.dumps(requestBody), headers=headers)
        # return res
    except Exception as e:
        et = time.time()
        print(f"{filename} [FAILED] in {et-st}")
        return e


BATCH_SIZE = 10
MAX_FILES_PER_FOLDER = 200
async def main():
    total_st = time.time()
    unparsedFiles = getUnParsedFiles(INPUT_DIR, OUTPUT_DIR)
    unparsedFiles = unparsedFiles[0:MAX_FILES_PER_FOLDER]
    print(f"Unparsed Files: {unparsedFiles}")
    tasks = []
    st = time.time()
    successful = []
    failed = []
    NUM_BATCHES = (len(unparsedFiles) // BATCH_SIZE) + (1 if (len(unparsedFiles) % BATCH_SIZE != 0) else 0)  
    print(f"Number of Batches: {NUM_BATCHES}")
    for iBatch in range(NUM_BATCHES):
    # for filename in unparsedFiles:
        st = time.time()
        batch = unparsedFiles[iBatch*BATCH_SIZE:(iBatch+1)*BATCH_SIZE]
        print(batch)
        # async with asyncio.TaskGroup() as tg:
        async with aiohttp.ClientSession() as session:
            tasks = [parseFileUsingRchilli(session, INPUT_DIR, filename) for filename in batch]
            res = await asyncio.gather(*tasks)
            et = time.time()
            print(f"Processing for Batch {iBatch + 1} finished: in {et - st}")
            for item in res:
                if item[1] == "failed":
                    failed.append(item[0])
                else:
                    successful.append(item[0])
    print("failed: ", failed)
    total_et = time.time()
    print(f"Total Time Taken: {total_et - total_st} seconds")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    # print(USERKEY, SUBUSERID, RESUME_FILES_DIR_PATH)

# # if __name__ == "__main__":
# loop = asyncio.get_event_loop()
# loop.run_until_complete(main())