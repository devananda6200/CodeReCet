export function createSocket(
  url: string,
  onMessage: (payload: unknown) => void,
  options: {
    maxRetries?: number;
    initialDelay?: number;
    maxDelay?: number;
  } = {}
): { close: () => void } {
  const { maxRetries = Infinity, initialDelay = 1000, maxDelay = 30000 } = options;

  let socket: WebSocket | null = null;
  let retryCount = 0;
  let isClosedManually = false;
  let reconnectTimeout: number | undefined;

  function connect() {
    if (isClosedManually) return;

    try {
      socket = new WebSocket(url);

      socket.onopen = () => {
        console.log(`[WS] Connected to ${url}`);
        retryCount = 0;
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (error) {
          console.error(`[WS] Failed to parse message from ${url}:`, error);
        }
      };

      socket.onerror = (error) => {
        console.error(`[WS] Error on ${url}:`, error);
      };

      socket.onclose = (event) => {
        if (isClosedManually) {
          console.log(`[WS] Closed manually: ${url}`);
          return;
        }

        console.warn(`[WS] Closed (code: ${event.code}) on ${url}. Reconnecting...`);
        scheduleReconnect();
      };
    } catch (error) {
      console.error(`[WS] Failed to create socket for ${url}:`, error);
      scheduleReconnect();
    }
  }

  function scheduleReconnect() {
    if (retryCount >= maxRetries) {
      console.error(`[WS] Max retries reached for ${url}`);
      return;
    }

    const delay = Math.min(initialDelay * Math.pow(2, retryCount), maxDelay);
    console.log(`[WS] Scheduling reconnect in ${delay}ms (attempt ${retryCount + 1})`);

    reconnectTimeout = window.setTimeout(() => {
      retryCount++;
      connect();
    }, delay);
  }

  connect();

  return {
    close: () => {
      isClosedManually = true;
      if (reconnectTimeout) {
        window.clearTimeout(reconnectTimeout);
      }
      if (socket) {
        socket.close();
      }
    }
  };
}
