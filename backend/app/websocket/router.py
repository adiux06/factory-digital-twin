import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.simulation_manager import simulation_manager

router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws/simulations/{sim_id}")
async def simulation_websocket_endpoint(websocket: WebSocket, sim_id: str):
    await websocket.accept()

    sim = None
    if sim_id and sim_id != "default":
        sim = simulation_manager.get_simulation(sim_id)
    if not sim:
        # Fallback to existing active simulation, or create default
        if simulation_manager.simulations:
            sim = next(iter(simulation_manager.simulations.values()))
        else:
            sim = simulation_manager.create_simulation(
                scheduling_policy="NEAREST_ROBOT",
                num_robots=3,
                scenario_id="default_factory",
            )
        sim_id = sim.id

    # Queue for this WebSocket client
    client_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    sim.subscribers.append(client_queue)

    # Send initial state synchronization immediately
    try:
        await websocket.send_text(
            json.dumps({
                "category": "simulation.state",
                "tick": sim.engine.tick,
                "state": sim.engine.get_state(),
            })
        )
    except Exception:
        if client_queue in sim.subscribers:
            sim.subscribers.remove(client_queue)
        return

    # Task to read incoming client messages
    async def receive_client_commands():
        try:
            while True:
                data_text = await websocket.receive_text()
                try:
                    payload = json.loads(data_text)
                    action = payload.get("action")
                    if action == "start":
                        simulation_manager.start_simulation(sim_id)
                    elif action == "pause":
                        simulation_manager.pause_simulation(sim_id)
                    elif action == "step":
                        simulation_manager.step_simulation(sim_id)
                        await websocket.send_text(json.dumps({
                            "category": "simulation.state",
                            "tick": sim.engine.tick,
                            "state": sim.engine.get_state(),
                        }))
                    elif action == "reset":
                        simulation_manager.reset_simulation(sim_id)
                        await websocket.send_text(json.dumps({
                            "category": "simulation.state",
                            "tick": sim.engine.tick,
                            "state": sim.engine.get_state(),
                        }))
                    elif action == "speed":
                        mult = float(payload.get("value", 1.0))
                        sim.speed_multiplier = max(0.2, min(5.0, mult))
                except Exception:
                    pass
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    # Task to stream simulation events from queue to client
    async def send_simulation_events():
        try:
            while True:
                msg = await client_queue.get()
                await websocket.send_text(json.dumps(msg))
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    receiver_task = asyncio.create_task(receive_client_commands())
    sender_task = asyncio.create_task(send_simulation_events())

    done, pending = await asyncio.wait(
        [receiver_task, sender_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

    if client_queue in sim.subscribers:
        sim.subscribers.remove(client_queue)
