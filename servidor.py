import asyncio
import json
import os
import websockets

jugadores = []

async def registrar(websocket):
    if len(jugadores) >= 2:
        await websocket.send(json.dumps({"tipo": "error", "mensaje": "Partida llena"}))
        await websocket.close()
        return

    jugadores.append(websocket)
    id_jugador = len(jugadores)
    
    await websocket.send(json.dumps({"tipo": "asignar_id", "id": id_jugador - 1}))
    print(f"Jugador {id_jugador} conectado.")

    if len(jugadores) == 2:
        for j in jugadores:
            await j.send(json.dumps({"tipo": "iniciar"}))
        print("Partida iniciada.")

async def desregistrar(websocket):
    if websocket in jugadores:
        jugadores.remove(websocket)
        print("Un jugador se ha desconectado.")
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
                
                # Reenviar movimientos
                if datos["tipo"] == "movimiento":
                    for j in jugadores:
                        if j != websocket:
                            await j.send(json.dumps({
                                "tipo": "movimiento",
                                "index": datos["index"]
                            }))
                
                # Reenviar orden de reinicio
                elif datos["tipo"] == "reiniciar":
                    for j in jugadores:
                        await j.send(json.dumps({"tipo": "reiniciar"}))
                            
            except asyncio.TimeoutError:
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
    puerto = int(os.environ.get("PORT", 8080))
    print(f"Iniciando servidor global WAN en el puerto {puerto}...")
    async with websockets.serve(manejador, "0.0.0.0", puerto):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
