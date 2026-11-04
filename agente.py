import time
import requests

# Copia exactamente el token que se generó al presionar "One-Click Generation"
TENSOR_API_KEY = "0e9d2822-3e76-4198-a1ab-7baaf2f85639" 

BASE_URL = "https://ap-east-1.tensorart.cloud/v1"

# La cabecera oficial para autenticación simple por Token
HEADERS = {
    "Authorization": f"Bearer {TENSOR_API_KEY}",
    "Content-Type": "application/json"
}
# IDs numéricos estándar de modelos económicos en Tensor Art
MODELO_BASE_REALISTA = "600423083519508503"  # SD 1.5 Base Checkpoint
MODELO_BASE_ANIMADO = "600423083519508503"   # Puedes usar el mismo ID o el de un modelo Anime/Cartoon especifico

class AgenteTGS:
    def __init__(self, presupuesto_diario=50):
        self.creditos = presupuesto_diario
        self.modelos_guardados = {}  # Memoria del sistema para almacenar LoRAs guardados

    def monitorear_trabajo(self, job_id: str) -> dict:
        """Feedback Loop: Consulta progresiva del estado del trabajo en la nube."""
        print(f"[*] Monitoreando trabajo {job_id} en los servidores de Tensor Art...")
        while True:
            res = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=HEADERS)
            if not res.ok:
                print(f"[X] Error en consulta API: {res.status_code}")
                print(res.text)
                res.raise_for_status()
                
            data = res.json()["job"]
            status = data["status"]
            
            if status == "SUCCESS":
                return data
            elif status == "FAILED":
                raise Exception("El proceso en Tensor Art finalizó con estado FAILED.")
            
            time.sleep(8)

    # ==========================================
    # OPCIÓN 1: SUBSISTEMA DE ENTRENAMIENTO LORA
    # ==========================================
    def opcion_entrenar_lora(self, dataset_url: str, nombre_persona: str, trigger_word: str, num_imagenes: int):
        print("\n=== INICIANDO SUBSISTEMA DE ENTRENAMIENTO (BAJO COSTO) ===")
        
        # Ajuste dinámico de parámetros de bajo costo basado en el número de imágenes (Máx 5)
        params_economicos = {
            "base_model": MODELO_BASE_REALISTA,
            "repeats": 8,
            "epochs": 4,
            "rank": 16,
            "alpha": 16
        }
        
        # Estimación defensiva del costo de créditos según el número de imágenes
        costo_estimado = 15 + (num_imagenes * 2)
        
        if costo_estimado > self.creditos:
            print(f"[!] Créditos insuficientes. Requieres ~{costo_estimado} y tienes {self.creditos}.")
            return

        payload = {
            "request_id": f"train_{int(time.time())}",
            "stages": [
                {
                    "type": "LORA_TRAINING",
                    "lora_training": {
                        "dataset_url": dataset_url,
                        "trigger_word": trigger_word,
                        "base_model": params_economicos["base_model"],
                        "epochs": params_economicos["epochs"],
                        "repeats": params_economicos["repeats"],
                        "rank": params_economicos["rank"],
                        "alpha": params_economicos["alpha"]
                    }
                }
            ]
        }

        res = requests.post(f"{BASE_URL}/jobs", json=payload, headers=HEADERS)
        if not res.ok:
            print(f"[X] Error HTTP {res.status_code}:")
            print(res.text)  # Esto te mostrará la causa exacta del rechazo
            return

        job_id = res.json()["job"]["id"]
        resultado = self.monitorear_trabajo(job_id)
        
        # Extraer ID del modelo generado y guardarlo en la memoria del Agente
        model_id = resultado["successInfo"]["model_id"]
        self.modelos_guardados[nombre_persona] = {
            "model_id": model_id,
            "trigger_word": trigger_word
        }
        
        self.creditos -= costo_estimado
        print(f"\n✅ Entrenamiento Exitoso con {num_imagenes} imágenes.")
        print(f"📦 LoRA de '{nombre_persona}' almacenado con ID: {model_id}")
        print(f"🪙 Créditos restantes: ~{self.creditos}")

    # ==========================================
    # OPCIÓN 2: SUBSISTEMA DE GENERACIÓN DE IMAGEN
    # ==========================================
    def opcion_generar_imagen(self, nombre_persona: str, prompt_usuario: str, estilo: str):
        print("\n=== INICIANDO SUBSISTEMA DE GENERACIÓN DE IMAGEN ===")
        
        if nombre_persona not in self.modelos_guardados:
            print(f"[X] Error: No se encuentra ningún LoRA guardado para '{nombre_persona}'.")
            return
            
        if self.creditos < 2:
            print("[X] Créditos insuficientes para generar la imagen de muestra.")
            return

        info_lora = self.modelos_guardados[nombre_persona]
        model_id = info_lora["model_id"]
        trigger_word = info_lora["trigger_word"]

        # Selección dinámica del modelo base según el estilo solicitado
        if estilo.lower() == "animado":
            modelo_base_elegido = MODELO_BASE_ANIMADO
            peso_lora = 0.7  # Peso óptimo para no sobrescribir el estilo animado
        else:
            modelo_base_elegido = MODELO_BASE_REALISTA
            peso_lora = 0.85

        prompt_final = f"portrait of {trigger_word}, {prompt_usuario}"

        payload = {
            "request_id": f"gen_{int(time.time())}",
            "stages": [
                {
                    "type": "INPUT_INITIALIZE",
                    "input_initialize": {
                        "seed": 42,
                        "count": 1  # 1 sola imagen para mantener el costo mínimo
                    }
                },
                {
                    "type": "DIFFUSION",
                    "diffusion": {
                        "sd_model": modelo_base_elegido,
                        "prompts": [{"text": prompt_final}],
                        "lora": [{"model_id": model_id, "weight": peso_lora}],
                        "steps": 20
                    }
                }
            ]
        }

        res = requests.post(f"{BASE_URL}/jobs", json=payload, headers=HEADERS)
        if not res.ok:
            print(f"Error al solicitar generación: {res.status_code}\n{res.text}")
            return

        job_id = res.json()["job"]["id"]
        resultado = self.monitorear_trabajo(job_id)
        
        url_imagen = resultado["successInfo"]["images"][0]["url"]
        self.creditos -= 2
        
        print(f"\n🖼️ Imagen Generada con Éxito ({estilo.upper()}):")
        print(f"🔗 Enlace: {url_imagen}")
        print(f"🪙 Créditos restantes: ~{self.creditos}")

# ==========================================
# MENÚ DE INTERACCIÓN PRINCIPAL (ORQUESTADOR)
# ==========================================
def menu_agente():
    agente = AgenteTGS(presupuesto_diario=50)

    while True:
        print("\n==========================================")
        print(f" AGENTE TGS - TENSOR ART (Créditos: {agente.creditos})")
        print("==========================================")
        print("1. Entrenar nuevo modelo LoRA (Bajo consumo)")
        print("2. Generar imagen usando un LoRA guardado")
        print("3. Salir")
        
        opcion = input("Selecciona una opción (1-3): ").strip()

        if opcion == "1":
            persona = input("Nombre o etiqueta de la persona a entrenar: ").strip()
            
            # Validación del número de imágenes
            try:
                num_imagenes = int(input("Número de imágenes en el dataset (Máximo 5): ").strip())
            except ValueError:
                print("[X] Error: Por favor ingresa un número entero válido.")
                continue

            if num_imagenes > 5:
                print(f"[X] Límite de imágenes superado. El máximo permitido para mantener bajo costo es 5 imágenes (ingresaste {num_imagenes}).")
                continue
            elif num_imagenes <= 0:
                print("[X] Error: Debes incluir al menos 1 imagen en el dataset.")
                continue

            # Pregunta por la URL únicamente si la validación del número de imágenes fue correcta
            url_zip = input("URL pública del dataset (.zip): ").strip()
            trigger = input("Palabra clave (trigger word, ej. sks_persona): ").strip()
            
            agente.opcion_entrenar_lora(url_zip, persona, trigger, num_imagenes)

        elif opcion == "2":
            persona = input("Nombre de la persona (LoRA guardado): ").strip()
            prompt = input("¿Cómo quieres la imagen? (ej. wearing a space suit): ").strip()
            estilo = input("Estilo de salida (realista / animado): ").strip()
            agente.opcion_generar_imagen(persona, prompt, estilo)

        elif opcion == "3":
            print("Finalizando agente...")
            break
        else:
            print("Opción no válida. Intenta de nuevo.")

if __name__ == "__main__":
    menu_agente()