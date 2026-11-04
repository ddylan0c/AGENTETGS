import requests

TENSOR_API_KEY = "0e9d2822-3e76-4198-a1ab-7baaf2f85639"

HEADERS = {
    "Authorization": f"Bearer {TENSOR_API_KEY}",
    "Content-Type": "application/json"
}

# Hacemos una consulta rápida a la API de empleos
res = requests.get("https://ap-east-1.tensorart.cloud/v1/jobs/test", headers=HEADERS)

print(f"Código de Respuesta: {res.status_code}")
print(f"Respuesta del Servidor: {res.text}")