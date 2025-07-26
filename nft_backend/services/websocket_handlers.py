import logging
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request
from functools import wraps
from flask import current_app
import time

# Initialize logger
logger = logging.getLogger(__name__)

# Rate limiting dictionary: {sid: {'last_message_time': float, 'message_count': int}}
# This is a simple in-memory rate limiter. For production, consider a more robust solution (e.g., Redis).
RATE_LIMIT_WINDOW_SECONDS = 5
MAX_MESSAGES_PER_WINDOW = 10
rate_limits = {}

def rate_limit(f):
    """
    Decorator for rate limiting WebSocket messages per client.
    Prevents a single client from spamming the server.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        sid = request.sid
        current_time = time.time()

        if sid not in rate_limits:
            rate_limits[sid] = {'last_message_time': current_time, 'message_count': 0}

        client_data = rate_limits[sid]

        # Reset count if outside the window
        if (current_time - client_data['last_message_time']) > RATE_LIMIT_WINDOW_SECONDS:
            client_data['last_message_time'] = current_time
            client_data['message_count'] = 0

        client_data['message_count'] += 1

        if client_data['message_count'] > MAX_MESSAGES_PER_WINDOW:
            logger.warning(f"Rate limit exceeded for SID: {sid}")
            emit('error', {'message': 'Rate limit exceeded. Please slow down.'})
            return False # Prevent the original function from executing
        
        return f(*args, **kwargs)
    return decorated_function

# --- WebSocket Event Handlers ---

def setup_websocket_handlers(socketio: SocketIO):
    """
    Sets up all WebSocket event handlers for Flask-SocketIO.
    This function should be called from the main app.py.
    """

    @socketio.on('connect')
    def handle_connect():
        """Handles client connection to the WebSocket."""
        logger.info(f"Client connected: {request.sid}")
        emit('status', {'message': 'Connected to NFT backend WebSocket', 'sid': request.sid})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handles client disconnection from the WebSocket."""
        logger.info(f"Client disconnected: {request.sid}")
        # Clean up rate limit data for disconnected clients
        if request.sid in rate_limits:
            del rate_limits[request.sid]

    @socketio.on('join_scarcity_room')
    @rate_limit
    def handle_join_scarcity_room(data):
        """
        Handles a client joining a scarcity update room.
        Data should contain 'artist' and 'event_type'.
        """
        artist = data.get('artist')
        event_type = data.get('event_type')

        if not artist or not event_type:
            logger.warning(f"Invalid data for join_scarcity_room from {request.sid}: {data}")
            emit('error', {'message': 'Artist and event_type are required to join scarcity room.'})
            return

        room_name = f"scarcity-{artist}-{event_type}"
        # Prevent duplicate joins
        if hasattr(socketio.server, 'manager') and request.sid in socketio.server.manager.rooms.get(room_name, {}):
            logger.info(f"Client {request.sid} already in room: {room_name}")
            return
        join_room(room_name)
        logger.info(f"Client {request.sid} joined scarcity room: {room_name}")
        emit('status', {'message': f'Joined scarcity room: {room_name}'}, room=request.sid)

    @socketio.on('leave_scarcity_room')
    @rate_limit
    def handle_leave_scarcity_room(data):
        """
        Handles a client leaving a scarcity update room.
        Data should contain 'artist' and 'event_type'.
        """
        artist = data.get('artist')
        event_type = data.get('event_type')

        if not artist or not event_type:
            logger.warning(f"Invalid data for leave_scarcity_room from {request.sid}: {data}")
            emit('error', {'message': 'Artist and event_type are required to leave scarcity room.'})
            return

        room_name = f"scarcity-{artist}-{event_type}"
        # Only leave if actually in room
        if request.sid in socketio.server.manager.rooms.get(room_name, {}):
            leave_room(room_name)
        else:
            logger.info(f"Client {request.sid} was not in room: {room_name}")
            return
        logger.info(f"Client {request.sid} left scarcity room: {room_name}")
        emit('status', {'message': f'Left scarcity room: {room_name}'}, room=request.sid)

    @socketio.on('join_evolution_room')
    @rate_limit
    def handle_join_evolution_room(data):
        """
        Handles a client joining an NFT evolution tracking room.
        Data should contain 'nft_id'.
        """
        nft_id = data.get('nft_id')

        if not nft_id:
            logger.warning(f"Invalid data for join_evolution_room from {request.sid}: {data}")
            emit('error', {'message': 'NFT ID is required to join evolution room.'})
            return

        room_name = f"evolution-{nft_id}"
        # Prevent duplicate joins
        if request.sid in socketio.server.manager.rooms.get(room_name, {}):
            logger.info(f"Client {request.sid} already in room: {room_name}")
            return
        join_room(room_name)
        logger.info(f"Client {request.sid} joined evolution room: {room_name}")
        emit('status', {'message': f'Joined evolution room: {room_name}'}, room=request.sid)

    @socketio.on('leave_evolution_room')
    @rate_limit
    def handle_leave_evolution_room(data):
        """
        Handles a client leaving an NFT evolution tracking room.
        Data should contain 'nft_id'.
        """
        nft_id = data.get('nft_id')

        if not nft_id:
            logger.warning(f"Invalid data for leave_evolution_room from {request.sid}: {data}")
            emit('error', {'message': 'NFT ID is required to leave evolution room.'})
            return

        room_name = f"evolution-{nft_id}"
        # Only leave if actually in room
        if request.sid in socketio.server.manager.rooms.get(room_name, {}):
            leave_room(room_name)
        else:
            logger.info(f"Client {request.sid} was not in room: {room_name}")
            return
        logger.info(f"Client {request.sid} left evolution room: {room_name}")
        emit('status', {'message': f'Left evolution room: {room_name}'}, room=request.sid)

    @socketio.on('test_message')
    @rate_limit
    def handle_test_message(data):
        """Handles a test message from a client and echoes it back."""
        logger.info(f"Received test message from {request.sid}: {data}")
        emit('test_response', {'message': 'Echo from server', 'data': data}, room=request.sid)


# --- Broadcast Functions ---

def broadcast_scarcity_update(socketio: SocketIO, artist: str, event_type: str, remaining_slots: int, total_supply: int, is_available: bool):
    """
    Broadcasts a scarcity update to clients subscribed to a specific artist-event room.
    """
    room_name = f"scarcity-{artist}-{event_type}"
    data = {
        'artist': artist,
        'event_type': event_type,
        'remaining_slots': remaining_slots,
        'total_supply': total_supply,
        'is_available': is_available,
        'timestamp': time.time()
    }
    logger.info(f"Broadcasting scarcity update to room {room_name}: {data}")
    socketio.emit('scarcity_update', data, room=room_name)

def broadcast_evolution_notification(socketio: SocketIO, nft_id: str, new_version: int, new_image_url: str, new_traits: dict):
    """
    Broadcasts an NFT evolution notification to clients subscribed to a specific NFT's evolution room.
    """
    room_name = f"evolution-{nft_id}"
    data = {
        'nft_id': nft_id,
        'new_version': new_version,
        'new_image_url': new_image_url,
        'new_traits': new_traits,
        'message': f"NFT {nft_id} has evolved to version {new_version}!",
        'timestamp': time.time()
    }
    logger.info(f"Broadcasting evolution notification to room {room_name}: {data}")
    socketio.emit('evolution_update', data, room=room_name)

def broadcast_new_mint(socketio: SocketIO, nft_data: dict):
    """
    Broadcasts a new NFT mint event to all connected clients (or a general 'new_mints' room).
    For simplicity, broadcasting to all for now. A dedicated 'new_mints' room could be used.
    """
    # Sanitize NFT data for public broadcast (remove sensitive info if any)
    broadcast_data = {
        'nft_id': nft_data.get('id'),
        'name': nft_data.get('name'),
        'image_url': nft_data.get('image_url'),
        'artist': nft_data.get('artist'),
        'event_type': nft_data.get('event_type'),
        'owner_address': nft_data.get('owner_address'),
        'canister_id': nft_data.get('canister_id'),
        'timestamp': time.time()
    }
    logger.info(f"Broadcasting new mint event for NFT ID: {broadcast_data.get('nft_id')}")
    socketio.emit('new_mint', broadcast_data) # Emits to all connected clients by default

# Export functions to be used by main app
__all__ = [
    'setup_websocket_handlers',
    'broadcast_scarcity_update',
    'broadcast_evolution_notification',
    'broadcast_new_mint'
]