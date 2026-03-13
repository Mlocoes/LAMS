"""
WebSocket endpoint for interactive container console (exec).
Provides bidirectional communication with container TTY.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict
import asyncio
import json
import logging

from database.models import RemoteCommand, DockerContainer, Host
from api.dependencies import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# Active console connections: {connection_id: websocket}
console_connections: Dict[str, WebSocket] = {}

@router.websocket("/ws/console/{host_id}/{container_id}/{exec_id}")
async def console_websocket(
    websocket: WebSocket,
    host_id: str,
    container_id: str,
    exec_id: str
):
    """
    WebSocket endpoint for interactive console communication.
    
    Flow:
    1. Client connects with exec_id from exec.create
    2. Server creates exec.start command for agent
    3. Bidirectional data flow:
       - Client → Server → Agent → Container (stdin)
       - Container → Agent → Server → Client (stdout/stderr)
    4. Connection cleanup on disconnect
    
    Message format:
    - Client → Server: {"type": "input", "data": "command\\n"}
    - Client → Server: {"type": "resize", "rows": 24, "cols": 80}
    - Server → Client: {"type": "output", "data": "response"}
    - Server → Client: {"type": "exit", "code": 0}
    """
    await websocket.accept()
    connection_id = f"{host_id}:{container_id}:{exec_id}"
    console_connections[connection_id] = websocket
    
    logger.info(f"Console WebSocket connected: {connection_id}")
    
    try:
        # Get database session (manual management in WebSocket)
        async for db in get_db():
            # Verify host and container
            stmt_host = select(Host).where(Host.id == host_id)
            result_host = await db.execute(stmt_host)
            host = result_host.scalar_one_or_none()
            
            if not host:
                await websocket.send_json({"type": "error", "message": "Host not found"})
                await websocket.close()
                return
            
            stmt_container = select(DockerContainer).where(
                DockerContainer.id == container_id,
                DockerContainer.host_id == host_id
            )
            result_container = await db.execute(stmt_container)
            container = result_container.scalar_one_or_none()
            
            if not container:
                await websocket.send_json({"type": "error", "message": "Container not found"})
                await websocket.close()
                return
            
            # Create exec.start command
            start_command = RemoteCommand(
                host_id=host_id,
                command_type="container.exec.start",
                target_id=exec_id,
                parameters={
                    "exec_id": exec_id,
                    "connection_id": connection_id
                },
                status="pending"
            )
            
            db.add(start_command)
            await db.commit()
            await db.refresh(start_command)
            
            # Send ready signal
            await websocket.send_json({"type": "ready", "exec_id": exec_id})
            
            # Message handling loop
            while True:
                try:
                    # Receive data from client
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                    message = json.loads(data)
                    
                    if message["type"] == "input":
                        # Forward stdin to agent via command
                        input_command = RemoteCommand(
                            host_id=host_id,
                            command_type="container.exec.input",
                            target_id=exec_id,
                            parameters={
                                "exec_id": exec_id,
                                "data": message["data"]
                            },
                            status="pending"
                        )
                        db.add(input_command)
                        await db.commit()
                    
                    elif message["type"] == "resize":
                        # Terminal resize
                        resize_command = RemoteCommand(
                            host_id=host_id,
                            command_type="container.exec.resize",
                            target_id=exec_id,
                            parameters={
                                "exec_id": exec_id,
                                "rows": message["rows"],
                                "cols": message["cols"]
                            },
                            status="pending"
                        )
                        db.add(resize_command)
                        await db.commit()
                    
                    elif message["type"] == "ping":
                        await websocket.send_json({"type": "pong"})
                
                except asyncio.TimeoutError:
                    # No message received, check for output from agent
                    # In production, agent would push output via another command type
                    # For now, we poll for exec.output commands
                    stmt_output = select(RemoteCommand).where(
                        RemoteCommand.command_type == "container.exec.output",
                        RemoteCommand.target_id == exec_id,
                        RemoteCommand.status == "completed"
                    ).order_by(RemoteCommand.created_at.desc()).limit(10)
                    
                    result_output = await db.execute(stmt_output)
                    output_commands = result_output.scalars().all()
                    
                    for cmd in output_commands:
                        if cmd.result and "data" in cmd.result:
                            await websocket.send_json({
                                "type": "output",
                                "data": cmd.result["data"]
                            })
                            # Mark as processed
                            cmd.status = "processed"
                    
                    await db.commit()
                    continue
                
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from client: {data}")
                    continue
                
                except WebSocketDisconnect:
                    raise  # Re-raise to outer handler
    
    except WebSocketDisconnect:
        logger.info(f"Console WebSocket disconnected: {connection_id}")
    
    except Exception as e:
        logger.error(f"Console WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    
    finally:
        # Cleanup
        if connection_id in console_connections:
            del console_connections[connection_id]
        
        # Send exec.stop command to agent
        try:
            async for db in get_db():
                stop_command = RemoteCommand(
                    host_id=host_id,
                    command_type="container.exec.stop",
                    target_id=exec_id,
                    parameters={"exec_id": exec_id},
                    status="pending"
                )
                db.add(stop_command)
                await db.commit()
                break
        except Exception as e:
            logger.error(f"Failed to send exec.stop: {e}")
        
        try:
            await websocket.close()
        except:
            pass
