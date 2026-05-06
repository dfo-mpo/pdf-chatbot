import os
from dotenv import load_dotenv

load_dotenv()
using_AKV = True if os.environ.get("KEY_VAULT_NAME") else False

# make request to AKV for key or get cached secret for OPENAI_API_KEY
def get_OPENAI_API_KEY():
    if using_AKV: # key vault name is only defined in web app not local .env files
        from app.core.secrets import get_secret # want managed identity to be ready before loading import, (so we don't import until running the function)
        return get_secret("azure-openai-api-key") # AKV does not allow caps and underscores in secret names
    else:
        return os.getenv("OPENAI_API_KEY")
    
# make request to AKV for key or get cached secret for OPENAI_API_KEY_US
def get_OPENAI_API_KEY_US():
    if using_AKV: # key vault name is only defined in web app not local .env files
        from app.core.secrets import get_secret # want managed identity to be ready before loading import, (so we don't import until running the function)
        return get_secret("azure-openai-api-key-us") # AKV does not allow caps and underscores in secret names
    else:
        return os.getenv("OPENAI_API_KEY_US")
    
# make request to AKV for key or get cached secret for DI_API_KEY
def get_DI_API_KEY():
    if using_AKV: # key vault name is only defined in web app not local .env files
        from app.core.secrets import get_secret # want managed identity to be ready before loading import, (so we don't import until running the function)
        return get_secret("azure-di-api-key") # AKV does not allow caps and underscores in secret names
    else:
        return os.getenv("DI_API_KEY")