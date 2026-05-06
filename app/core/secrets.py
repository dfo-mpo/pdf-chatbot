# Cache secrets from AKV to minimize the number of requests to get keys
from cachetools import TTLCache  
from app.core.keyvault import secret_client  
import os

cache = TTLCache(maxsize=100, ttl=300)  # 5 minutes  
  
def get_secret(name: str) -> str:  
    if name in cache:  
        return cache[name]

    if secret_client is None:  
        return os.getenv(name)    
    
    try:
        secret = secret_client.get_secret(name).value  
        cache[name] = secret  
        return secret  
    except Exception as e:  
        raise RuntimeError(f"Failed to retrieve secret '{name}' from AKV") from e 