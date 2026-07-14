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
    id_jugador = len(jugadores) # Jugador 1 o Jugador 2
    
    # Informar al cliente qué jugador es (0 o 1)
    await websocket.send(json.dumps({"tipo": "asignar_id", "id": id_jugador - 1}))
    print(f"Jugador {id_jugador} conectado desde {websocket.remote_address}")

    if len(jugadores) == 2:
        # Notificar a ambos que la partida puede iniciar en la WAN
        for j in jugadores:
            await j.send(json.dumps({"tipo": "iniciar"}))
        print("Partida iniciada: ambos jugadores conectados.")

async def desregistrar(websocket):
    if websocket in jugadores:
        jugadores.remove(websocket)
        print("Un jugador se ha desconectado.")
    # Notificar al jugador restante si el otro se sale
    for j in jugadores:
        await j.send(json.dumps({"tipo": "desconexion"}))

async def manejador(websocket):
    await registrar(websocket)
    try:
        async_iterator = websocket.__aiter__()
        while True:
            try:
                mensaje = await asyncio.wait_for(async_iterator.__anext__(), timeout=30.0)
                datos = json.loads(mensaje)
                if datos["tipo"] == "movimiento":
                    # Reenviar el movimiento del jugador al oponente
                    for j in jugadores:
                        if j != websocket:
                            await j.send(json.dumps({
                                "tipo": "movimiento",
                                "index": datos["index"]
                            }))
            except asyncio.TimeoutError:
                # Ping para mantener activa la conexión en Render (evita desconexiones por inactividad)
                try:
                    pong_waiter = await websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=10.0)
                except Exception:
                    break
    except websockets.ConnectionClosed:
        pass
    except StopAsyncIteration:
        pass
    finally:
        await desregistrar(websocket)

async def main():
    # Render asigna dinámicamente un puerto en la variable PORT. Si no existe, usa el 8080.
    puerto = int(os.environ.get("PORT", 8080))
    print(f"Iniciando servidor global WAN en el puerto {puerto}...")
    async with websockets.serve(manejador, "0.0.0.0", puerto):
        await asyncio.Future()  # Mantiene el servidor corriendo indefinidamente

if __name__ == "__main__":
    asyncio.run(main())