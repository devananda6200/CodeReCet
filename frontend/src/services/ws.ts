export function createSocket(url: string, onMessage: (payload: unknown) => void): WebSocket | null {
  try {
    const socket = new WebSocket(url);
    socket.onmessage = (event) => {
      onMessage(JSON.parse(event.data));
    };
    return socket;
  } catch {
    return null;
  }
}

