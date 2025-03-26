import logging
import os
import azure.functions as func
from upload_sharepoint_data_to_blob import upload_sharepoint_lists
from access_token import get_access_token
from dotenv import load_dotenv
load_dotenv(dotenv_path="config.env")
logger = logging.getLogger("tt_sharepoint_logger")

container_name = os.getenv("container_name")
app = func.FunctionApp()

@app.timer_trigger(schedule="0 0 * * * *", arg_name="myTimer", run_on_startup=True,
              use_monitor=False) 
def sharepoint_timer_trigger(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('Trigger lagging behind schedule')

    logging.info('Trigger func executed')
    
    ACCESS_TOKEN = get_access_token()
    upload_sharepoint_lists(ACCESS_TOKEN,container_name)

