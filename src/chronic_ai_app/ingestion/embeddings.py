from langchain_community.embeddings import HuggingFaceEmbeddings


def get_embedding_model():
    """Initialize and return the HuggingFace embedding model."""

    model_name = "BAAI/bge-small-en"
    model_kwargs = {"device": "cpu"}  # Or 'cuda' if you have GPU
    encode_kwargs = {
        "normalize_embeddings": True
    }  # Normalizing embeddings can improve similarity search
    embedding_model = HuggingFaceEmbeddings(
        model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs
    )
    print("Embedding model initialized.")

    return embedding_model
