# PDF Chatbot Tool API
This tool uses OpenAI's language model to answer questions about uploaded documents. It provides direct responses with sourced references, making document exploration faster and more efficient. 

Like the CSV/PDF Analyzer, this tool originates from pilot projects using OCR and OpenAI to extract and summarize data from documents; however, it does one prompt at a time and uses retrieval-augmented generation (RAG) using chromadb (non persistent database). RAG allows only relevant chunks of the uploaded document to be passed to OpenAI for a given prompt, reducing processing time and cost. 

A detailed documentation can be found [here](https://086gc.sharepoint.com/:w:/r/sites/OCDO/_layouts/15/Doc.aspx?sourcedoc=%7BCFB8CB0C-145E-4218-BD70-F0D0A1E9C110%7D&file=PDF%20Chatbot%20Documentation.docx&action=default&mobileredirect=true).

Note that this repository is strictly the backend logic for this tool. The frontend is hosted on the OCDS Educational AI Hub found [here](https://github.com/dfo-mpo/SDPA-AI-Portal).

## HTTP Requests Handled Internally   
Requests are handled in the `app/main.py` file. The API exposes the following endpoints:  
  
- **`POST /di_extract_document/`**    
  Request that takes a `PDF` document then uses an Azure document intelligence prebuilt model to convert the `PDF` into a stringified `JSON` and return it. 
- **`WS /ws/chat_stream`**    
  `Web socket` that will create chunked objects with documents string, get relevant chunks to the given question using an embedding model, then ask the question on the selected document chunks with a LLM, the response is returned as a stream (in chunks).
- **`POST /di_chunk_single_document/`**    
  Request that takes a single `PDF` document and uses an Azure document intelligence prebuilt model to convert a `PDF` into markdown chunks, they are combined into a `JSON` containing text chunks and metadata then returned.
- **`POST /di_chunk_ multi_document/`**    
  Request that takes multiple `PDF` documents and uses an Azure document intelligence prebuilt model to convert a `PDF` into markdown chunks, they are combined into a `JSON` containing text chunks and metadata then returned. 
  
All endpoints support CORS and are designed to be consumed by the associated frontend applications.  

## Intial Setup
Before this API can be run, the enviroment variables need to be intialized.
1. Create a new file in `/app` called `.env` by copying `app/.env.example` and filling in the missing keys for the required Azure resources. Instead of adding in the keys to the `.env` file you can add a `KEY_VAULT_NAME` for a key vault containing the keys either in the `.env`, a `docker-compose.yml`, or in the resource running the docker instance. Note that if you are using a key vault for API secrets, it will only work when hosted on Azure resources with access to the key vault.

## Run API
You can run the API by building the docker image then running a container for it. Use the following commands:
```bash
docker build -t pdf-chatbot:latest .
docker run -d -p 8080:8000 --name pdf-chatbot pdf-chatbot
```
This will create an image called `pdf-chatbot` then run it in a container called `pdf-chatbot` hosted on port `8080`.

## Update Deployment
This tool is currently hosted in the OCDS SSC (Shared Services Canada) Azure environment to be used by the OCDS Educational AI Hub. To upload the deployment follow the steps below:
1. Run the command `docker build -t pdf-chatbot:latest .` to update your local docker instance with the latest changes.
2. Update the docker image used hosted in the SSC Azure environment by running the following commands in a terminal (note you will need to download [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows?view=azure-cli-latest&pivots=msi) if you don't have it):
```bash
az login --tenant 8c1a4d93-d828-4d0e-9303-fd3bd611c822
az acr login --name AIPortal
docker tag pdf-chatbot aiportal.azurecr.io/ocds-ai-portal/pssi-chatbot:latest
docker push aiportal.azurecr.io/ocds-ai-portal/pssi-chatbot:latest
```
3. Lastly, you will need to SSH into the [VM](https://portal.azure.com/#@163oxygen.onmicrosoft.com/resource/subscriptions/4858d1be-583d-42d6-a4a3-44172168b003/resourceGroups/ocds-ai-portal/providers/Microsoft.Compute/virtualMachines/OCDS-AI-Portal-VM/overview) hosting the API and rerun its `docker-compose.yml` to use the latest version of the docker image.

## External APIs Used 
### Azure OpenAI 
Azure Open AI is used for large language models for generating AI responses and embedding models for implementing RAG. The PDF Chatbot, CSV/PDF Analyzer, Web Scraper, and Document OCR tools rely on OpenAI models.  

Azure Open AI provides advanced machine learning models that can interpret and respond to user queries, and analyze text data extracted from documents. This integration allows for: 
* Enhanced natural language processing for real-time conversation with documents. 
* Sophisticated data extraction and analysis from various file formats, enabling deep insights into document content. 

### Azure Document Intelligence 
Document Intelligence is used to read and interpret the contents of documents uploaded to the AI Hub’s PDF Chatbot, CSV/PDF Analyzer, PII Redactor, Sensitivity Score Calculator, French Translation, and Document OCR tools. It helps in: 
* Automatically extract text and data from structured and unstructured documents including non-machine-readable files. 
* Organize extracted text into markdown format allowing for LLMs and embedding models to easily process document text. 