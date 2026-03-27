import type { Alert, StreamData } from '../types';

type SocketCallback<T> = (data: T) => void;

class MockWebSocketClient {
  private detectionsListeners: Set<SocketCallback<StreamData[]>> = new Set();
  private alertsListeners: Set<SocketCallback<Alert>> = new Set();
  private isConnected = false;

  connect() {
    this.isConnected = true;
    console.log('[WebSocket] Connected');
  }

  disconnect() {
    this.isConnected = false;
    console.log('[WebSocket] Disconnected');
  }

  onDetections(callback: SocketCallback<StreamData[]>) {
    this.detectionsListeners.add(callback);
    return () => this.detectionsListeners.delete(callback);
  }

  onNewAlert(callback: SocketCallback<Alert>) {
    this.alertsListeners.add(callback);
    return () => this.alertsListeners.delete(callback);
  }

  // Used internally to mock server pushing data
  emitDetections(data: StreamData[]) {
    if (!this.isConnected) return;
    this.detectionsListeners.forEach(cb => cb(data));
  }

  emitAlert(alert: Alert) {
    if (!this.isConnected) return;
    this.alertsListeners.forEach(cb => cb(alert));
  }
}

export const socketClient = new MockWebSocketClient();
