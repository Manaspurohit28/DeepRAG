from langchain.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
from langchain.text_splitter import CharacterTextSplitter
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate

#This is the function your Streamlit app is trying to import
def create_rag_chain(raw_text: str):
    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_text(raw_text)
    documents = [Document(page_content=chunk) for chunk in chunks]

    embedding_model = OllamaEmbeddings(model="devstral_sd", base_url="http://10.0.7.190:8082")
    db = FAISS.from_documents(documents, embedding_model)
    retriever = db.as_retriever()
    

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
        You are an expert retrival augmented generation application
        Use the context below to answer the question.
        Context: {context}
        Question: {question}
        Answer:
        
        Do NOT include any introduction, summary, or explanation and points, try to keep the text short and crisp according to context only.
        """
    )
    chain = RetrievalQA.from_chain_type(
        llm = Ollama(model="devstral_sd", base_url="http://10.0.7.190:8082"),
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": prompt}
    )
    return chain

# Optionally keep this for direct testing
def rag_answer(question: str) -> str:
    # This uses a hardcoded PDF (if you're still using it somewhere else)
    return "Placeholder answer"
