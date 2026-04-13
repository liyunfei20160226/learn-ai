import SimplePeer from 'simple-peer';

// Collaboration WebRTC manager
export class CollaborationManager {
  constructor(options) {
    this.options = {
      onRemoteAction: null,
      onRemoteElements: null,
      onPeerConnect: null,
      onPeerDisconnect: null,
      onSignal: null,
      ...options
    };

    this.roomId = null;
    this.userId = this.generateUserId();
    this.peers = new Map(); // peerId -> { peer, metadata }
    this.isInitiator = false;
    this.connected = false;
    this.signalingServer = null;
  }

  generateUserId() {
    return 'user_' + Math.random().toString(36).substr(2, 9);
  }

  generateRoomId() {
    // Generate a 6-character room code
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let result = '';
    for (let i = 0; i < 6; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  // Simple signaling via WebSocket using a free public signaling server
  // For MVP, we use a simple websocket-based signaling approach
  async connect(roomId, isInitiator = false) {
    this.roomId = roomId;
    this.isInitiator = isInitiator;

    // Use a public signaling server for demonstration
    // In production you'd want to host your own
    const signalingUrl = this.getSignalingUrl();

    try {
      this.signalingServer = new WebSocket(signalingUrl);

      this.signalingServer.onopen = () => {
        console.log('Connected to signaling server');
        // Join the room
        this.sendSignal({
          type: 'join',
          roomId: this.roomId,
          userId: this.userId
        });
      };

      this.signalingServer.onmessage = (event) => {
        const message = JSON.parse(event.data);
        this.handleSignalingMessage(message);
      };

      this.signalingServer.onerror = (error) => {
        console.error('Signaling server error:', error);
        this.connected = false;
        this.options.onConnectionChange?.(false);
      };

      this.signalingServer.onclose = () => {
        console.log('Disconnected from signaling server');
        this.connected = false;
        this.options.onConnectionChange?.(false);
      };

      return true;
    } catch (e) {
      console.error('Failed to connect:', e);
      return false;
    }
  }

  getSignalingUrl() {
    // For development, you can use a local signaling server
    // For demo purposes, we use wss://signal.vigoo.dev:3000 - a free public signaling server
    // Alternative: you could implement your own using Node.js
    return 'wss://signal.vigoo.dev:3000';
  }

  handleSignalingMessage(message) {
    switch (message.type) {
      case 'peer-joined':
        // Another peer joined, create a new peer connection
        if (message.userId !== this.userId) {
          this.createPeer(message.userId, message.userId === this.userId ? false : this.isInitiator);
        }
        break;

      case 'signal':
        // Received signal from another peer
        this.handleSignal(message.fromUserId, message.data);
        break;

      case 'room-joined':
        console.log('Joined room successfully');
        this.connected = true;
        this.options.onConnectionChange?.(true);
        break;

      case 'error':
        console.error('Signaling error:', message.message);
        break;
    }
  }

  createPeer(peerId, isInitiator) {
    console.log(`Creating peer for ${peerId}, initiator: ${isInitiator}`);

    const peer = new SimplePeer({
      initiator: isInitiator,
      trickle: false
    });

    peer.on('signal', (data) => {
      // Send signal through signaling server
      this.sendSignal({
        type: 'signal',
        roomId: this.roomId,
        fromUserId: this.userId,
        toUserId: peerId,
        data: data
      });
    });

    peer.on('connect', () => {
      console.log(`Peer ${peerId} connected`);
      this.peers.set(peerId, { peer, connected: true });
      this.options.onPeerConnect?.(peerId);

      // Send our full current state to the new peer
      this.options.onPeerConnected?.(peerId, this.sendFullElementsToPeer.bind(this, peer));
    });

    peer.on('data', (data) => {
      this.handleData(peerId, data);
    });

    peer.on('close', () => {
      console.log(`Peer ${peerId} disconnected`);
      this.peers.delete(peerId);
      this.options.onPeerDisconnect?.(peerId);
    });

    peer.on('error', (err) => {
      console.error(`Peer ${peerId} error:`, err);
    });

    this.peers.set(peerId, { peer, connected: false });
  }

  handleSignal(fromUserId, signalData) {
    const peerInfo = this.peers.get(fromUserId);
    if (peerInfo && peerInfo.peer) {
      peerInfo.peer.signal(signalData);
    }
  }

  sendSignal(data) {
    if (this.signalingServer && this.signalingServer.readyState === WebSocket.OPEN) {
      this.signalingServer.send(JSON.stringify(data));
    }
  }

  handleData(fromUserId, data) {
    try {
      const message = JSON.parse(new TextDecoder().decode(data));
      switch (message.type) {
        case 'action':
          // Remote action to apply
          this.options.onRemoteAction?.(fromUserId, message.action);
          break;
        case 'full-elements':
          // Full state sync when joining
          this.options.onRemoteElements?.(fromUserId, message.elements);
          break;
        case 'cursor':
          // Remote cursor position for collaboration
          this.options.onRemoteCursor?.(fromUserId, message.position, message.username);
          break;
      }
    } catch (e) {
      console.error('Failed to parse message:', e);
    }
  }

  sendFullElementsToPeer(peerId, elements) {
    // Send full elements list to new peer
    const peerInfo = this.peers.get(peerId);
    if (peerInfo && peerInfo.connected && peerInfo.peer.connected) {
      const message = {
        type: 'full-elements',
        elements: elements
      };
      peerInfo.peer.send(JSON.stringify(message));
    }
  }

  broadcastAction(action) {
    // Broadcast an action to all connected peers
    if (!this.isConnected()) return;

    const message = {
      type: 'action',
      action: action
    };

    this.broadcast(message);
  }

  broadcastCursor(position, username) {
    // Broadcast cursor position to all connected peers
    if (!this.isConnected()) return;

    const message = {
      type: 'cursor',
      position: position,
      username: username || this.userId
    };

    this.broadcast(message);
  }

  broadcast(message) {
    const data = JSON.stringify(message);
    this.peers.forEach((peerInfo) => {
      if (peerInfo.connected && peerInfo.peer.connected) {
        try {
          peerInfo.peer.send(data);
        } catch (e) {
          console.error('Failed to send message:', e);
        }
      }
    });
  }

  disconnect() {
    // Close all peer connections
    this.peers.forEach((peerInfo) => {
      peerInfo.peer.destroy();
    });
    this.peers.clear();

    // Close signaling connection
    if (this.signalingServer) {
      this.signalingServer.close();
      this.signalingServer = null;
    }

    this.connected = false;
    this.roomId = null;
    this.options.onConnectionChange?.(false);
  }

  isConnected() {
    return this.connected && this.peers.size > 0;
  }

  getConnectedPeerCount() {
    let count = 0;
    this.peers.forEach(peerInfo => {
      if (peerInfo.connected) count++;
    });
    return count;
  }
}

// Fallback if simple-peer is not available via import
// Load from CDN dynamically
export async function loadSimplePeer() {
  return new Promise((resolve, reject) => {
    if (window.SimplePeer) {
      resolve(window.SimplePeer);
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/simple-peer@9.11.1/simplepeer.min.js';
    script.onload = () => {
      SimplePeer = window.SimplePeer;
      resolve(SimplePeer);
    };
    script.onerror = () => {
      reject(new Error('Failed to load SimplePeer from CDN'));
    };
    document.head.appendChild(script);
  });
}
