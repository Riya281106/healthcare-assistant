from app.services.rag.retriever import retrieve_medical_context


query = "What is paracetamol used for?"

context = retrieve_medical_context(
    query,
    top_k=1
)

print("\n" + "=" * 60)
print("USER QUERY")
print("=" * 60)

print(query)

print("\n" + "=" * 60)
print("RETRIEVED MEDICAL CONTEXT")
print("=" * 60)

print(context)