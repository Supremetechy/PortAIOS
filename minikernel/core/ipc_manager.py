"""
IPC (Inter-Process Communication) Manager

Provides message passing between processes in user space
Essential for microkernel architecture where services are isolated
"""

import logging
import threading
import queue
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("MiniKernel.IPC")


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Message:
    """IPC Message structure"""
    id: str
    sender: str
    recipient: str
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    reply_to: Optional[str] = None
    
    def __lt__(self, other):
        """For priority queue ordering"""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.timestamp < other.timestamp


@dataclass
class MessageQueue:
    """Per-process message queue"""
    process_id: str
    queue: queue.PriorityQueue = field(default_factory=lambda: queue.PriorityQueue())
    handlers: Dict[str, Callable] = field(default_factory=dict)
    
    def put(self, message: Message) -> None:
        """Add message to queue"""
        self.queue.put((message.priority.value, message))
    
    def get(self, timeout: Optional[float] = None) -> Optional[Message]:
        """Get next message from queue"""
        try:
            priority, message = self.queue.get(timeout=timeout)
            return message
        except queue.Empty:
            return None


class IPCManager:
    """
    Inter-Process Communication Manager
    
    Capabilities:
    - Message passing (send/receive)
    - Request/reply pattern
    - Broadcast messaging
    - Handler registration
    """
    
    def __init__(self):
        self.queues: Dict[str, MessageQueue] = {}
        self._lock = threading.RLock()
        self.stats = {
            "messages_sent": 0,
            "messages_delivered": 0,
            "messages_dropped": 0
        }
        logger.info("IPC Manager created")
    
    def initialize(self) -> None:
        """Initialize IPC subsystem"""
        logger.info("IPC subsystem initialized")
    
    def shutdown(self) -> None:
        """Shutdown IPC subsystem"""
        with self._lock:
            self.queues.clear()
        logger.info("IPC subsystem shutdown")
    
    def register_process(self, process_id: str) -> bool:
        """Register a process for IPC"""
        with self._lock:
            if process_id in self.queues:
                logger.warning(f"Process already registered: {process_id}")
                return False
            
            self.queues[process_id] = MessageQueue(process_id=process_id)
            logger.debug(f"Registered process for IPC: {process_id}")
            return True
    
    def unregister_process(self, process_id: str) -> bool:
        """Unregister a process"""
        with self._lock:
            if process_id in self.queues:
                del self.queues[process_id]
                logger.debug(f"Unregistered process: {process_id}")
                return True
            return False
    
    def ipc_send(
        self,
        sender: str,
        recipient: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        reply_to: Optional[str] = None
    ) -> Optional[str]:
        """
        Send a message to another process
        
        Returns: Message ID if successful, None otherwise
        """
        with self._lock:
            if recipient not in self.queues:
                logger.warning(f"Recipient not found: {recipient}")
                self.stats["messages_dropped"] += 1
                return None
            
            message = Message(
                id=str(uuid.uuid4()),
                sender=sender,
                recipient=recipient,
                payload=payload,
                priority=priority,
                reply_to=reply_to
            )
            
            self.queues[recipient].put(message)
            self.stats["messages_sent"] += 1
            logger.debug(f"Message sent: {sender} → {recipient} (id={message.id[:8]})")
            
            return message.id
    
    def ipc_receive(self, process_id: str, timeout: Optional[float] = None) -> Optional[Message]:
        """
        Receive next message for a process
        
        Returns: Message or None if timeout
        """
        with self._lock:
            if process_id not in self.queues:
                logger.warning(f"Process not registered: {process_id}")
                return None
        
        message = self.queues[process_id].get(timeout=timeout)
        if message:
            self.stats["messages_delivered"] += 1
            logger.debug(f"Message received: {process_id} ← {message.sender}")
        
        return message
    
    def ipc_request(
        self,
        sender: str,
        recipient: str,
        payload: Dict[str, Any],
        timeout: float = 5.0
    ) -> Optional[Message]:
        """
        Send request and wait for reply (synchronous RPC pattern)
        
        Returns: Reply message or None if timeout
        """
        # Send request
        request_id = self.ipc_send(sender, recipient, payload, priority=MessagePriority.HIGH)
        if not request_id:
            return None
        
        # Wait for reply
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout:
            reply = self.ipc_receive(sender, timeout=0.1)
            if reply and reply.reply_to == request_id:
                return reply
        
        logger.warning(f"Request timeout: {sender} → {recipient}")
        return None
    
    def ipc_reply(self, original_message: Message, reply_payload: Dict[str, Any]) -> Optional[str]:
        """
        Reply to a message
        
        Returns: Reply message ID or None
        """
        return self.ipc_send(
            sender=original_message.recipient,
            recipient=original_message.sender,
            payload=reply_payload,
            priority=MessagePriority.HIGH,
            reply_to=original_message.id
        )
    
    def ipc_broadcast(
        self,
        sender: str,
        payload: Dict[str, Any],
        exclude: Optional[List[str]] = None
    ) -> int:
        """
        Broadcast message to all registered processes
        
        Returns: Number of recipients
        """
        exclude = exclude or []
        count = 0
        
        with self._lock:
            for process_id in self.queues.keys():
                if process_id != sender and process_id not in exclude:
                    if self.ipc_send(sender, process_id, payload):
                        count += 1
        
        logger.debug(f"Broadcast from {sender} to {count} processes")
        return count
    
    def register_handler(
        self,
        process_id: str,
        message_type: str,
        handler: Callable[[Message], None]
    ) -> bool:
        """Register a message handler for a process"""
        with self._lock:
            if process_id not in self.queues:
                return False
            
            self.queues[process_id].handlers[message_type] = handler
            logger.debug(f"Registered handler: {process_id}.{message_type}")
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get IPC statistics"""
        with self._lock:
            return {
                "registered_processes": len(self.queues),
                "messages_sent": self.stats["messages_sent"],
                "messages_delivered": self.stats["messages_delivered"],
                "messages_dropped": self.stats["messages_dropped"],
                "queue_sizes": {
                    pid: q.queue.qsize() for pid, q in self.queues.items()
                }
            }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    ipc = IPCManager()
    ipc.initialize()
    
    # Register processes
    ipc.register_process("process_a")
    ipc.register_process("process_b")
    
    # Send message
    msg_id = ipc.ipc_send("process_a", "process_b", {"action": "test", "data": 123})
    print(f"Sent message: {msg_id}")
    
    # Receive message
    msg = ipc.ipc_receive("process_b", timeout=1.0)
    if msg:
        print(f"Received: {msg.payload}")
        
        # Reply
        ipc.ipc_reply(msg, {"status": "ok"})
    
    # Stats
    print(ipc.get_stats())
