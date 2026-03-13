"""
WebSocket endpoint for real-time container logs streaming.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict
import asyncio
import json
from datetime import datetime, timezone

from database.models import DockerContainer, Host, RemoteCommand
from database.database import get_db

router = APIRouter()

# Active WebSocket connections: key = "host_id:container_id", value = WebSocket
active_log_streams: Dict[str, WebSocket] = {}

@router.websocket("/ws/containers/{host_id}/{container_id}/logs")
async def container_logs_websocket(
    websocket: WebSocket,
    host_id: str,
    container_id: str
):
    """
    WebSocket endpoint for streaming container logs in real-time.
    
    Protocol:
    - Client connects
    - Server sends logs as JSON messages: {"type": "log", "line": "...", "timestamp": "..."}
    - Server sends heartbeat: {"type": "heartbeat"}
    - Server sends errors: {"type": "error", "message": "..."}
    - Client can send: {"type": "close"} to disconnect
    """
    await websocket.accept()
    
    connection_key = f"{host_id}:{container_id}"
    active_log_streams[connection_key] = websocket
    
    try:
        # Verify host and container exist
        async for db in get_db():
            stmt_host = select(Host).where(Host.id == host_id)
            result_host = await db.execute(stmt_host)
            host = result_host.scalar_one_or_none()
            
            if not host:
                await websocket.send_json({
                    "type": "error",
                    "message": "Host not found"
                })
                await websocket.close()
                return
            
            stmt_container = select(DockerContainer).where(
                DockerContainer.id == container_id,
                DockerContainer.host_id == host_id
            )
            result_container = await db.execute(stmt_container)
            container = result_container.scalar_one_or_none()
            
            if not container:
                await websocket.send_json({
                    "type": "error",
                    "message": "Container not found"
                })
                await websocket.close()
                return
            
            # Create command for agent to start streaming logs
            command = RemoteCommand(
                host_id=host_id,
                command_type="container.logs.stream",
                target_id=container_id,
                parameters={
                    "container_id": container_id,
                    "follow": True,
                    "tail": 100
                },
                status="pending",
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(command)
            await db.commit()
            await db.refresh(command)
            
            # Send initial success message
            await websocket.send_json({
                "type": "connected",
                "message": f"Streaming logs for {container.name}",
                "command_id": command.id
            })
            
            break  # Exit the async for loop
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (with timeout for heartbeat)
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                data = json.loads(message)
                if data.get("type") == "close":
                    break
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except:
                    break  # Connection lost
                    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        # Cleanup
        if connection_key in active_log_streams:
            del active_log_streams[connection_key]
        
        # TODO: Send command to agent to stop streaming


async def push_log_line_to_websocket(host_id: str, container_id: str, log_line: str):
    """
    Helper function for agent to push log lines to active WebSocket connections.
    
    This should be called by a separate endpoint that the agent POSTs to.
    """
    connection_key = f"{host_id}:{container_id}"
    
    if connection_key in active_log_streams:
        ws = active_log_streams[connection_key]
        try:
            await ws.send_json({
                "type": "log",
                "line": log_line,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except:
            # Connection lost, remove it
            del active_log_streams[connection_key]


@router.post("/internal/push-log-line")
async def push_log_line(
    host_id: str,
    container_id: str,
    line: str
):
    """
    Internal endpoint for agent to push log lines to active WebSocket streams.
    
    This is called by the agent when it has new log lines to send.
    """
    await push_log_line_to_websocket(host_id, container_id, line)
    return {"status": "ok"}
