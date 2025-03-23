import uuid
from services.get_model import Call_Models
from services.vectorDB import PGVectorDB
import pandas as pd
from services.chat_history import *
import numpy as np


#Call Embedding model
model_call = Call_Models()
llm,embed = model_call.get_open_ai_model()

#Chat History Object
chat_history_obj = ChatHistory()

#Call VectorDB
open_vecDB = PGVectorDB(embed)
parent_vecDB = open_vecDB.call_vectorDB("parent_embedding")
child_vecDB = open_vecDB.call_vectorDB("child_embedding")

#Class to read PDF files
class RUN_Inference:
    
    def __init__(self):
        pass

    def get_unique_docids(self,docs):
        unique_ids = []
        unique_metadata = []
        for doc in docs:
            meta_data = doc.metadata
            id_ = meta_data['document_id']
            if id_ not in unique_ids:
                unique_metadata.append(meta_data)
                unique_ids.append(id_)
        return unique_metadata


    def get_docs(self,question,threshold = 0.8):
        child_chunks = []
        get_parent_docs =  parent_vecDB.similarity_search(question,k=10)

        #Extract unique document ids
        filtered_metadata = self.get_unique_docids(get_parent_docs)
        
        #Child chunks
        for filter_sample in filtered_metadata:
            temp_child_docs = child_vecDB.similarity_search_with_relevance_scores(question,filter = filter_sample,k=30)
            for chunk in temp_child_docs:
                if chunk[1] >= threshold:
                    child_chunks.append(chunk)
        return child_chunks
    
    def get_docs_v1(self,question,document_type,threshold=0.6,k=5):
        thresh_filter_chunks = []
        parent_chunk_filtered = []
        child_chunks = child_vecDB.similarity_search_with_relevance_scores(question,k=30,filter = {"doc_type":document_type})
        print(child_chunks)
        for chunk in child_chunks:
                if chunk[1] >= threshold:
                    thresh_filter_chunks.append(chunk[0])
        
        filtered_metadata = self.get_unique_docids(thresh_filter_chunks)

        for filter in filtered_metadata:
             parent_chunk_filtered.append(parent_vecDB.similarity_search(question,k=1,filter = filter)[0])
        
        parent_chunk_filtered = parent_chunk_filtered[:k]
        parent_chunk_filtered = [i.page_content for i in parent_chunk_filtered]
        return parent_chunk_filtered
    
    def get_docs_v2(self,question,document_type,threshold=None,k=5):
        thresh_filter_chunks = []
        parent_chunk_filtered = []
        child_chunks = child_vecDB.similarity_search_with_relevance_scores(question,k=30,filter = {"doc_type":document_type})
        chunk_scores = [chunk[1] for chunk in child_chunks]
        threshold = np.mean(chunk_scores)
        for chunk in child_chunks:
                if chunk[1] >= threshold:
                    thresh_filter_chunks.append(chunk[0])
        
        filtered_metadata = self.get_unique_docids(thresh_filter_chunks)

        for filter in filtered_metadata:
             parent_chunk_filtered.append(parent_vecDB.similarity_search(question,k=1,filter = filter)[0])
        
        parent_chunk_filtered = parent_chunk_filtered[:k]
        parent_chunk_filtered = [i.page_content for i in parent_chunk_filtered]
        return child_chunks,parent_chunk_filtered
    
    def conversation_rephrase(self,question,selected_doc_type,session_id):
        #Get history
        df_history = chat_history_obj.get_chat_history(selected_doc_type,session_id=session_id)
        
        if df_history.shape[0]==0:
            return question
        
        else:
            json_history = df_history[['question','response','time_stamp']].to_dict(orient='records')

            prompt = f"""
                Your job is to read the chat history and if the question is a follow up question of chat history then add details of history in the question and rephrase it.
                If question is unrelated to history then return the original question as it is as rephrased question.

                User question: {question}

                Chat history:
                {json_history}

                Rephrased question:
                **Only return rephrased question in the output**
                """
            result = llm.invoke(prompt).content
            print("Rephrased question: ",result)
            return result

    

    def get_answer(self,question,selected_doc_type, user_id):

        session_id = str(uuid.uuid4())
        
        context = self.get_docs_v2(question,document_type=selected_doc_type)
        
        question = self.conversation_rephrase(question,selected_doc_type, session_id)
        
        #context = ''.join(context)
        prompt = f"""
        <Problem Statement>
        Using only the context, Think carefully then craft your detailed(if required) answer the user question. If answer is not in the context then say "I don't have the answer".
        user question: {question}
        </Problem Statement>

        <Answer Structure>
        **Detailed answer here**
        **Cite the source of your answer here**
        </Answer Structure>
        
        <content>
        {context}
        </context>
        """
        result = llm.invoke(prompt).content
        
        #add to chat history
        chat_history_obj.update_chat_history(user_id, session_id,selected_doc_type,question,result)
        return result