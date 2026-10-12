from agent import graph

result = graph.invoke({
    "user_message": "I want to apply for an income certificate",
    "service_id": "",
    "service_data": {},
    "final_response": ""
})

print("Service:", result["service_id"])
print("\nResponse:")
print(result["final_response"])