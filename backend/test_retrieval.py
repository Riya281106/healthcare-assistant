from app.services.rag.vector_store import search_documents


queries = [
    "What is high blood pressure?",
    "What is paracetamol used for?",
    "What causes headache and fever?"
]


for query in queries:

    print("\n" + "=" * 60)
    print("QUERY:", query)
    print("=" * 60)

    results = search_documents(
        query,
        top_k=2
    )

    if not results:
        print("No relevant information found.")
        continue

    for index, result in enumerate(results, start=1):

        print(f"\nResult {index}")
        print("-" * 40)

        print("Source:")
        print(result["metadata"].get("source"))

        print("\nDistance:")
        print(result["distance"])

        print("\nRetrieved information:")
        print(result["document"])