from openai import AzureOpenAI
from langchain_openai import AzureOpenAIEmbeddings
from langchain_core.documents import Document
from langchain_chroma import Chroma
from dotenv import load_dotenv
from uuid import uuid4
import tiktoken
import chromadb
import json
import os
from app.utils.azure_key_vault import get_OPENAI_API_KEY, get_OPENAI_API_KEY_US
    
# Load enviroment variables, was in main but backend failed to run unless placed here
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# Configure OpenAI settings
US_models = ['o1', 'o3-mini']
_openai_client_us = None  
def get_openai_client_us():
    global _openai_client_us
    if _openai_client_us is None:
        _openai_client_us = AzureOpenAI(
            azure_endpoint = os.getenv('OPENAI_API_ENDPOINT_US'), 
            api_key = get_OPENAI_API_KEY_US(),  
            api_version = os.getenv('OPENAI_API_VERSION')
        )
    return _openai_client_us

CAD_models = ['gpt-4o', 'gpt-4o-mini']
_openai_client_cad = None
def get_openai_client_cad():
    global _openai_client_cad
    if _openai_client_cad is None:
        _openai_client_cad = AzureOpenAI(
            azure_endpoint = os.getenv('OPENAI_API_ENDPOINT'), 
            api_key = get_OPENAI_API_KEY(),  
            api_version = os.getenv('OPENAI_API_VERSION')
        )
    return _openai_client_cad

_openai_client_embeddings = None
def get_openai_client_embeddings():
    global _openai_client_embeddings
    if _openai_client_embeddings is None:
        _openai_client_embeddings = AzureOpenAIEmbeddings(
            model="text-embedding-3-large",
            azure_endpoint = os.getenv('OPENAI_API_EMBEDDING_ENDPOINT'), 
            api_key = get_OPENAI_API_KEY(),
            openai_api_version = os.getenv('OPENAI_API_EMBEDDING_VERSION')
        )
    return _openai_client_embeddings

# External (non-Azure) provider model lists — require user-supplied api_key
ANTHROPIC_models = ['claude-35-sonnet', 'claude-3-haiku']
GOOGLE_models    = ['gemini-15-flash', 'gemini-15-pro']
XAI_models       = ['grok-3']

# Maps frontend model keys to the provider's actual model string
EXTERNAL_MODEL_MAP = {
    'claude-35-sonnet': 'claude-3-5-sonnet-20241022',
    'claude-3-haiku':   'claude-3-haiku-20240307',
    'gemini-15-flash':  'gemini-1.5-flash',
    'gemini-15-pro':    'gemini-1.5-pro',
    'grok-3':           'grok-3',
}

'''
Determines the amount of tokens for OpenAI's newer models a given string will consume.
'''
def num_tokens_from_string(string) -> int:
    encoding = tiktoken.get_encoding('cl100k_base')
    num_tokens = len(encoding.encode(string))
    return num_tokens

"""
Streams responses from external (non-Azure) LLM providers via LangChain.
Yields SSE-formatted chunks matching the format used by the Azure streaming path.
"""
async def _stream_external(messages, model, api_key, tokens_used):
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

    model_name = EXTERNAL_MODEL_MAP.get(model, model)

    lc_messages = []
    for msg in messages:
        if msg['role'] == 'system':
            lc_messages.append(SystemMessage(content=msg['content'] or ''))
        elif msg['role'] == 'user':
            lc_messages.append(HumanMessage(content=msg['content'] or ''))
        elif msg['role'] == 'assistant':
            lc_messages.append(AIMessage(content=msg['content'] or ''))

    if model in ANTHROPIC_models:
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model=model_name, api_key=api_key)
    elif model in GOOGLE_models:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)
    elif model in XAI_models:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=model_name, api_key=api_key, base_url="https://api.x.ai/v1")
    else:
        raise ValueError(f"{model} is not a supported external model.")

    try:
        async for chunk in llm.astream(lc_messages):
            content = chunk.content if hasattr(chunk, 'content') else ''
            data = json.dumps({'content': content, 'finish_reason': None, 'tokens_used': tokens_used})
            yield f"data: {data}\n\n"
        data = json.dumps({'content': None, 'finish_reason': 'stop', 'tokens_used': tokens_used})
        yield f"data: {data}\n\n"
    except Exception as e:
        print(e)
        yield f"data: {{\"error\": \"Error fetching data from external provider: {str(e)}\"}}\n\n"

"""
Streams responses from OpenAI for the chat view. 
"""
async def request_openai_chat(chat_history: list, document_content: str, type="chat", model="gpt-4o", temperature=0.3, reasoning_effort="high", token_remaining=100000, isAuth=False, api_key: str = None):
    if type == "chat":
        if chat_history[0] == '' or chat_history[0]['role'] != "system":
            messages = [{
                "role": "system","content": "You are a helpful assistant that ALWAYS responds in consistent and pleasing HTML formatted text. Also, make sure to use borders ONLY IF you use a table in your response. Only answer the LAST QUESTION based on the document provided. Do not answer any questions not related to the document or PDF. Also, at the end of the entire total response tell me what documents and pages you found the information on separated by commas ONLY. For example, at the end include: Source_page: <document-name1.pdf, 1, 4, etc, document-name2.pdf, 2, 5, etc,>." + document_content
            }]
        else:
            messages = []
    else:
        messages = [{
            "role": "system","content": "You are a helpful assistant that ALWAYS responds in consistent and pleasing HTML formatted text. Also, make sure to use borders ONLY IF you use a table in your response. Only answer the LAST QUESTION based on the document provided. Do not answer any questions not related to the document or PDF. Also, at the end of the entire total response tell me what documents and pages you found the information on separated by commas ONLY. For example, at the end include: Source_page: <document-name1.pdf, 1, 4, etc, document-name2.pdf, 2, 5, etc,>." + document_content
        }] 
    messages.extend(chat_history)
    if messages[1] == '':
        del messages[1]
    new_message_string = json.dumps(messages)
    tokens_used = num_tokens_from_string(new_message_string)
    print(f"Input tokens: {tokens_used}")

    if (tokens_used > token_remaining) and not isAuth:
        data = json.dumps({'content': "Model session usage reached, login to allow for larger sessions", 'finish_reason': 'end','tokens_used': token_remaining})
        yield f"data: {data}\n\n"
    else:
        try:
            if model in CAD_models:
                openAIClient_CAD_models = get_openai_client_cad()
                stream = openAIClient_CAD_models.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    frequency_penalty=0,
                    presence_penalty=0,
                    stop=None,
                    stream=True
                )
            elif model in US_models:
                openAIClient_US_models = get_openai_client_us()
                stream = openAIClient_US_models.chat.completions.create(
                    model=model,
                    messages=messages,
                    reasoning_effort=reasoning_effort,
                    stop=None,
                    stream=True
                )
            elif model in ANTHROPIC_models or model in GOOGLE_models or model in XAI_models:
                async for chunk_data in _stream_external(messages, model, api_key, tokens_used):
                    yield chunk_data
                return
            else:
                raise ValueError(f"{model} is not a supported model name.")

            for response in stream:
                content = response.choices[0].delta.content if len(response.choices) > 0 else []
                finish_reason = response.choices[0].finish_reason if len(response.choices) > 0 else None
                data = json.dumps({'content': content, 'finish_reason': finish_reason,'tokens_used': tokens_used})
                yield f"data: {data}\n\n"

        except Exception as e:
            print(e)
            yield f"data: {{'error': 'Error fetching data from OpenAI: {str(e)}'}}\n\n"

"""
Obtain relevent document chunks for a given LLM chatbot question
"""
def get_relevent_chunks(chat_history: list[dict], document_chunks: list[str], document_metadata: list[dict]):
    chromadb.api.client.SharedSystemClient.clear_system_cache()

    document_content = ''
    try:
        document_objects = [Document(id=index,page_content=chunk,metadata={"document_name": document_metadata[index]['document_name'], "page_numbers": document_metadata[index]["page_numbers"]},) for index, chunk in enumerate(document_chunks)]
        
        embeddings = get_openai_client_embeddings()
        vector_store = Chroma("example_collection", embedding_function=embeddings)
        uuids = [str(uuid4()) for _ in range(len(document_objects))]

        vector_store.add_documents(documents=document_objects, ids=uuids)
        results = vector_store.similarity_search(chat_history[-1]['content'])
        vector_store.reset_collection()
        print("Number of chunks used: "+str(len(results)))

        for result in results:
            document_content += json.dumps(result.metadata, indent=4) 
            document_content += result.page_content
    except Exception as e:
        print(e)
    return document_content