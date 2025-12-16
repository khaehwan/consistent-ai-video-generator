/**
 * WebSocket 클라이언트 for Virtual Production
 */

/**
 * @typedef {Object} SensorEvent
 * @property {string} timestamp
 * @property {string} sensor_id
 * @property {string} behavior
 * @property {Object} [metadata]
 */

/**
 * @typedef {Object} BackgroundChangeEvent
 * @property {'action_change'|'scene_change'} type
 * @property {number} scene_id
 * @property {string} action
 * @property {string} new_background
 * @property {SensorEvent} [sensor_event]
 */

/**
 * @callback EventCallback
 * @param {BackgroundChangeEvent} event
 */

export class VPWebSocket {
	constructor(url = 'ws://localhost:8001/vp/player-events') {
		this.ws = null;
		this.url = url;
		this.callbacks = [];
		this.reconnectInterval = 3000;
		this.reconnectTimer = null;
	}

	connect() {
		if (this.ws && this.ws.readyState === WebSocket.OPEN) {
			console.log('[Frontend WS] WebSocket already connected');
			return;
		}

		console.log('[Frontend WS] Connecting to WebSocket:', this.url);

		this.ws = new WebSocket(this.url);

		this.ws.onopen = () => {
			console.log('[Frontend WS] ✓ WebSocket connected successfully!');
			if (this.reconnectTimer) {
				clearTimeout(this.reconnectTimer);
				this.reconnectTimer = null;
			}
		};

		this.ws.onmessage = (event) => {
			console.log('[Frontend WS] <<<< Message received (raw):', event.data);
			try {
				const data = JSON.parse(event.data);
				console.log('[Frontend WS] <<<< Message parsed:', data);
				console.log('[Frontend WS] Number of callbacks registered:', this.callbacks.length);

				// 모든 콜백 실행
				this.callbacks.forEach((callback, index) => {
					console.log(`[Frontend WS] Executing callback #${index + 1}`);
					callback(data);
				});

				console.log('[Frontend WS] All callbacks executed');
			} catch (error) {
				console.error('[Frontend WS] Failed to parse WebSocket message:', error);
			}
		};

		this.ws.onerror = (error) => {
			console.error('[Frontend WS] ✗ WebSocket error:', error);
		};

		this.ws.onclose = () => {
			console.log('[Frontend WS] WebSocket disconnected. Reconnecting...');
			this.scheduleReconnect();
		};
	}

	disconnect() {
		if (this.reconnectTimer) {
			clearTimeout(this.reconnectTimer);
			this.reconnectTimer = null;
		}

		if (this.ws) {
			this.ws.close();
			this.ws = null;
		}
	}

	scheduleReconnect() {
		if (this.reconnectTimer) return;

		this.reconnectTimer = window.setTimeout(() => {
			this.reconnectTimer = null;
			this.connect();
		}, this.reconnectInterval);
	}

	/**
	 * @param {EventCallback} callback
	 */
	onMessage(callback) {
		this.callbacks.push(callback);
	}

	/**
	 * @param {EventCallback} callback
	 */
	removeCallback(callback) {
		const index = this.callbacks.indexOf(callback);
		if (index > -1) {
			this.callbacks.splice(index, 1);
		}
	}

	/**
	 * @param {SensorEvent} event
	 */
	sendEvent(event) {
		if (this.ws && this.ws.readyState === WebSocket.OPEN) {
			this.ws.send(JSON.stringify(event));
		} else {
			console.error('WebSocket not connected');
		}
	}

	isConnected() {
		return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
	}
}

// 싱글톤 인스턴스
let vpWebSocket = null;

export function getVPWebSocket() {
	if (!vpWebSocket) {
		vpWebSocket = new VPWebSocket();
	}
	return vpWebSocket;
}
