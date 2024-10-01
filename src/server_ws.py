import asyncio
from websockets import ConnectionClosed
from websockets.server import serve


connected_clients = []

async def client_connect(sock):
    print("Received a message.")
    
    try:
        global connected_clients
        for client in connected_clients:
            if client.id == sock.id:
                break
        else:
            connected_clients.append(sock)
            print("New client connected:", sock.id)
        
        await sock.send("ok")
    
    except ConnectionClosed:
        print("Client disconnected:", sock.id)


async def main():
    print("Started.")
    async with serve(client_connect, "localhost", 8765):
        await asyncio.get_running_loop().create_future()  # run forever

asyncio.run(main())