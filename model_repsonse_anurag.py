from dotenv import load_dotenv
import logging
import json
from helper_funcs_anurag import get_client
load_dotenv()

def get_ai_response(user_input:str,deployment_name:str):
    """
    Returns chat completion message.
    Params : 
    user_input -> Query of the user.
    deployment_name -> model name that the user wants to use (Must be available in endpoint).
    
    Note:
    client.chat.completions.create is different for gpt-4o and o1.
     
    """

    chat_completion_models = ["gpt-4o"]
    reasoning_models = ["o1"]
    try:

        if deployment_name in reasoning_models: 
            client = get_client(deployment_name)
            if client == "Failed to connect to client":
                return client
            chat_prompt = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_input
                        }
                    ]
                }
            ] 
                
            # Include speech result if speech is enabled  
            messages = chat_prompt 
            # response does not have completion tokens because o1 takes into account resoning and output tokens. 
            # An arugment will be given once the completion tokens can be accurately estimated for user inputs.
            response = client.chat.completions.create(  
                model=deployment_name,  
                messages=messages
            )  
            json_response = json.dumps({"model response": response.choices[0].message.content})
            logging.debug(json_response)
            return json_response
         
                    
        elif deployment_name in chat_completion_models:

            client = get_client(deployment_name)
            if client == "Failed to connect to client":
                return client
            response = client.chat.completions.create(
            model = deployment_name,
            messages=[{"role": "system", "content": """You are helpful chat assistant that will respond to user queries. Be honest in your answers."""},
                    {"role": "user", "content": f"{user_input}"}],
            temperature=0.7
        )   
            json_response = json.dumps({"model response": response.choices[0].message.content})
            logging.debug(json_response)
            return json_response
        else:
            logging.error("Invalid model name")
            return "Invalid model name"
    except Exception as e:
        logging.error(f"Failed to get response from model. Error :{e}")
        return "Failed to get response from model"