import asyncio
import json
import os
import websockets

# Guardamos las conexiones de los dos jugadores activos
jugadores = []

async def registrar(websocket):
    if len(jugadores) >= 2:
        await websocket.send(json.dumps({"tipo": "error", "mensaje": "Partida llena"}))
        await websocket.close()
        return

    jugadores.append(websocket)
    id_jugador = len(jugadores)
    
    # Informar al cliente qué jugador es (0 o 1)
    await websocket.send(json.dumps({"tipo": "asignar_id", "id": id_jugador - 1}))
    print(f"Jugador {id_jugador} conectado.")

    if len(jugadores) == 2:
        # Notificar a ambos que la partida puede iniciar
        for j in jugadores:
            await j.send(json.dumps({"tipo": "iniciar"}))
        print("Partida iniciada.")

async def desregistrar(websocket):
    if websocket in jugadores:
        jugadores.remove(websocket)
        print("Un jugador se ha desconectado.")
    # Notificar al jugador restante si el otro se sale
    for j in jugadores:
        try:
            await j.send(json.dumps({"tipo": "desconexion"}))
        except Exception:
            pass

async def manejador(websocket):
    await registrar(websocket)
    try:
        async for mensaje in websocket:
            datos = json.loads(mensaje)
            print(f"Mensaje recibido: {datos}") # Esto te servirá para ver los logs en Render
            
            # 1. Si es un movimiento, se lo mandamos al oponente
            if datos["tipo"] == "movimiento":
                for j in jugadores:
                    if j != websocket:
                        await j.send(json.dumps({
                            "tipo": "movimiento",
                            "index": datos["index"]
                        }))
            
            # 2. Si es un reinicio, se lo mandamos OBLIGATORIAMENTE A AMBOS
            elif datos["tipo"] == "reiniciar":
                print("Enviando orden de reinicio a ambos jugadores...")
                for j in jugadores:
                    await j.send(json.dumps({"tipo": "reiniciar"}))
                    
    except websockets.ConnectionClosed:
        pass
    finally:
        await desregistrar(websocket)

async def main():
    puerto = int(os.environ.get("PORT", 8080))
    print(f"Iniciando servidor global WAN en el puerto {puerto}...")
    async with websockets.serve(manejador, "0.0.0.0", puerto):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
