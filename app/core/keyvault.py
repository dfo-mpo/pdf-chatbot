import os  
from dotenv import load_dotenv  
from azure.identity import DefaultAzureCredential  
from azure.keyvault.secrets import SecretClient  

load_dotenv()  # loads .env into os.environ 

KEY_VAULT_NAME = os.environ.get("KEY_VAULT_NAME")
KV_URI = f"https://{KEY_VAULT_NAME}.vault.azure.net"

if not KEY_VAULT_NAME:
    print("No KEY_VAULT_NAME provided, will need keys stored in local .env file.")
    secret_client = None
else:
    credential = DefaultAzureCredential()  
    secret_client = SecretClient(vault_url=KV_URI, credential=credential)