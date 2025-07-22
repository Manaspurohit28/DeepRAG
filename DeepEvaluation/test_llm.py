from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

def get_ollama_response(prompt: str,model="devstral_sd", base_url="http://10.0.7.190:8082") -> str:
   
    messages = [
        SystemMessage(content="You are a helpful assistant, answer very specific to the context no additional information"),
        HumanMessage(content=prompt)
    ]

    llm = ChatOllama(model=model, base_url=base_url)
    response = llm.invoke(messages)
    
    return response.content
