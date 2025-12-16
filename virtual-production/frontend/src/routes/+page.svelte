<script lang="ts">
	/**
	 * Virtual Production 메인 플레이어 페이지
	 */

	import { onMount, onDestroy } from 'svelte';
	import VideoPlayer from '$lib/VideoPlayer.svelte';
	import SensorDisplay from '$lib/SensorDisplay.svelte';
	import { getVPWebSocket } from '$lib/websocket';
	import { ALL_ACTIONS, getActionMetadata, getActionsByCategory } from '$lib/constants';

	// 상태
	let currentVideoUrl = '';
	let currentSceneId = 1;
	let currentAction = 'stop';
	let sensorEvents = [];
	let isConnected = false;
	let showControls = false;
	let lastSensorTime = null; // 마지막 센서 이벤트 시간

	// 프로젝트 설정 (URL 파라미터에서 가져오기)
	let workDir = '';
	let entitySetName = '';
	let availableScenes = []; // 사용 가능한 씬 목록

	// 재생 설정
	let minPlayDuration = 3000; // 최소 재생 시간 (ms), 기본값 3초

	// WebSocket
	let vpWs = getVPWebSocket();

	// API 베이스 URL (환경변수에서 가져오거나 기본값 사용)
	const API_BASE = 'http://localhost:8001';

	onMount(async () => {
		console.log('[Page] onMount: Initializing...');

		// URL 파라미터에서 프로젝트 설정 읽기
		const params = new URLSearchParams(window.location.search);
		workDir = params.get('workDir') || '';
		entitySetName = params.get('entitySetName') || '';
		console.log('[Page] Project settings:', { workDir, entitySetName });

		// 매핑 로드하여 씬 정보 추출
		await loadMapping();

		// 초기 배경 로드
		await loadCurrentBackground();

		// WebSocket 연결
		console.log('[Page] onMount: Connecting to WebSocket...');
		vpWs.connect();

		console.log('[Page] onMount: Registering message callback...');
		vpWs.onMessage(handleBackgroundChange);
		console.log('[Page] onMount: Callback registered');

		// 연결 상태 체크
		const checkConnection = setInterval(() => {
			isConnected = vpWs.isConnected();
		}, 1000);

		console.log('[Page] onMount: Initialization complete');

		return () => {
			clearInterval(checkConnection);
		};
	});

	onDestroy(() => {
		vpWs.disconnect();
	});

	async function loadMapping() {
		console.log('[Page] 📋 Loading mapping to extract scene info...');

		if (!workDir || !entitySetName) {
			console.log('[Page] ⚠️ No workDir or entitySetName, skipping mapping load');
			return;
		}

		try {
			const url = `${API_BASE}/vp/load-mapping?work_dir=${encodeURIComponent(workDir)}&entity_set_name=${encodeURIComponent(entitySetName)}`;
			console.log('[Page] Fetching:', url);

			const response = await fetch(url);
			console.log('[Page] Response status:', response.status);

			if (response.status === 404 || !response.ok) {
				console.warn('[Page] ⚠️ Could not load mapping');
				return;
			}

			const data = await response.json();
			console.log('[Page] 📦 Mapping data:', data);

			if (data.mapping && data.mapping.sensor_mapping) {
				// sensor_mapping의 키들이 씬 번호
				const sceneIds = Object.keys(data.mapping.sensor_mapping)
					.map(id => parseInt(id))
					.filter(id => !isNaN(id))
					.sort((a, b) => a - b);

				availableScenes = sceneIds;
				console.log('[Page] ✅ Available scenes:', availableScenes);
			} else {
				console.log('[Page] ⚠️ No sensor_mapping found in response');
			}
		} catch (error) {
			console.error('[Page] ❌ Failed to load mapping:', error);
		}
	}

	async function loadCurrentBackground() {
		console.log('[Page] 📥 Loading current background...');

		try {
			const url = `${API_BASE}/vp/current-background`;
			console.log('[Page] Fetching:', url);

			const response = await fetch(url);
			console.log('[Page] Response status:', response.status);

			if (response.status === 404) {
				console.warn('[Page] ⚠️ No background loaded yet. Please load mapping first.');
				return;
			}

			if (!response.ok) {
				console.error('[Page] ❌ Response not OK:', response.statusText);
				return;
			}

			const data = await response.json();
			console.log('[Page] 📦 Response data:', data);

			if (data.video_url) {
				// 캐시 방지를 위해 타임스탬프 추가
				const timestamp = Date.now();
				const fullVideoUrl = `${API_BASE}${data.video_url}?t=${timestamp}`;
				console.log('[Page] ✅ Video URL constructed:', fullVideoUrl);
				console.log('[Page] Scene ID:', data.scene_id);
				console.log('[Page] Action:', data.action);

				currentVideoUrl = fullVideoUrl;
				currentSceneId = data.scene_id;
				currentAction = data.action;

				console.log('[Page] 🎬 Current video URL updated to:', currentVideoUrl);
			} else {
				console.warn('[Page] ⚠️ No video_url in response data');
			}
		} catch (error) {
			console.error('[Page] ❌ Failed to load current background:', error);
			console.error('[Page] Error details:', {
				message: error.message,
				stack: error.stack
			});
		}
	}

	function handleBackgroundChange(event) {
		console.log('[Page] ===== Background change event received =====');
		console.log('[Page] Event:', event);
		console.log('[Page] Event type:', event.type);
		console.log('[Page] Scene ID:', event.scene_id);
		console.log('[Page] Action:', event.action);
		console.log('[Page] New background:', event.new_background);

		currentSceneId = event.scene_id;
		currentAction = event.action;

		if (event.new_background) {
			// 캐시 방지를 위해 타임스탬프 추가
			const timestamp = Date.now();
			const newVideoUrl = `${API_BASE}/vp/backgrounds/${event.new_background}?t=${timestamp}`;

			// URL은 timestamp 때문에 항상 다르므로 비디오 파일명만 비교
			const currentFilename = currentVideoUrl.split('?')[0].split('/').pop();
			const newFilename = event.new_background;

			// 파일명이 실제로 바뀌었을 때만 업데이트
			if (newFilename !== currentFilename) {
				console.log('[Page] 🔄 Video changed from:', currentFilename, 'to:', newFilename);
				currentVideoUrl = newVideoUrl;
			} else {
				console.log('[Page] ⏭️ Same video file, no update needed');
			}
		}

		// 센서 이벤트 추가
		if (event.sensor_event) {
			lastSensorTime = Date.now();
			sensorEvents = [...sensorEvents, event.sensor_event];
			console.log('[Page] Sensor event added. Total events:', sensorEvents.length);
			console.log('[Page] Last sensor time:', new Date(lastSensorTime).toLocaleTimeString());
		}

		console.log('[Page] ===== Event handling complete =====');
	}

	// 센서 활성 상태 체크 (마지막 이벤트가 5초 이내)
	$: sensorActive = lastSensorTime && (Date.now() - lastSensorTime < 5000);

	// 주기적으로 센서 활성 상태 갱신
	let sensorCheckInterval;
	onMount(() => {
		sensorCheckInterval = setInterval(() => {
			// 강제로 reactive 변수 재평가
			lastSensorTime = lastSensorTime;
		}, 1000);
	});

	onDestroy(() => {
		if (sensorCheckInterval) {
			clearInterval(sensorCheckInterval);
		}
	});

	async function changeScene(sceneId) {
		try {
			await fetch(`${API_BASE}/vp/change-scene`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ scene_id: sceneId })
			});
		} catch (error) {
			console.error('Failed to change scene:', error);
		}
	}

	async function simulateAction(action) {
		try {
			await fetch(`${API_BASE}/vp/simulate-action`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ action, metadata: {} })
			});
		} catch (error) {
			console.error('Failed to simulate action:', error);
		}
	}

	function toggleControls() {
		showControls = !showControls;
	}

	// 시뮬레이션 버튼용 액션 목록 (모든 센서 액션 포함)
	const actions = ALL_ACTIONS.map((id) => {
		const metadata = getActionMetadata(id);
		return {
			id,
			label: metadata.label,
			color: metadata.color
		};
	});

	// 카테고리별로 그룹화된 액션
	const actionGroups = getActionsByCategory();
</script>

<svelte:head>
	<title>Virtual Production Control</title>
</svelte:head>

<div class="main-container">
	<!-- 상태 바 -->
	<div class="status-bar">
		{#if workDir && entitySetName}
			<div class="status-item project-info">
				<span class="label">프로젝트:</span>
				<span class="value">{entitySetName}</span>
				<span class="path">({workDir})</span>
			</div>
		{/if}
		<div class="status-item">
			<span class="label">Scene:</span>
			<span class="value">{currentSceneId}</span>
		</div>
		<div class="status-item">
			<span class="label">Action:</span>
			<span class="value">{currentAction}</span>
		</div>
		<div class="status-item">
			<span class="label">서버:</span>
			<span class="value" class:connected={isConnected}>
				{isConnected ? '연결됨' : '연결 끊김'}
			</span>
		</div>
		<div class="status-item">
			<span class="label">센서:</span>
			<span class="value" class:active={sensorActive} class:inactive={!sensorActive}>
				{sensorActive ? '활성' : '비활성'}
			</span>
		</div>
		<button class="control-toggle" on:click={toggleControls}>
			{showControls ? '컨트롤 숨기기' : '컨트롤 보기'}
		</button>
	</div>

	<!-- 비디오 플레이어 -->
	<div class="player-container">
		{#if currentVideoUrl}
			<VideoPlayer
				videoUrl={currentVideoUrl}
				transitionDuration={1000}
				minPlayDuration={minPlayDuration}
			/>
		{:else}
			<div class="no-video">
				<h2>배경 영상이 로드되지 않았습니다</h2>
				<p>먼저 프로젝트 매핑을 로드하거나, 배경 영상을 생성해주세요.</p>
				<div class="action-buttons">
					<a
						href="/generate?workDir={encodeURIComponent(workDir)}&entitySetName={encodeURIComponent(entitySetName)}"
						class="btn-primary"
					>
						배경 생성 시작
					</a>
					<a
						href="/setup?workDir={encodeURIComponent(workDir)}&entitySetName={encodeURIComponent(entitySetName)}"
						class="btn-secondary"
					>
						매핑 로드
					</a>
					<a
						href="/preview?workDir={encodeURIComponent(workDir)}&entitySetName={encodeURIComponent(entitySetName)}"
						class="btn-secondary"
					>
						미리보기
					</a>
				</div>
				<div class="help-text">
					<p><strong>배경 영상 생성 방법:</strong></p>
					<ol>
						<li><strong>웹 인터페이스:</strong> 위의 "배경 생성 시작" 버튼 클릭</li>
						<li><strong>Python API:</strong> /generate 페이지에서 안내 확인</li>
					</ol>
				</div>
			</div>
		{/if}
	</div>

	<!-- 컨트롤 패널 (토글 가능) -->
	{#if showControls}
		<div class="controls-panel">
			<div class="control-section">
				<h3>페이지</h3>
				<div class="nav-buttons">
					<a
						href="/setup?workDir={encodeURIComponent(workDir)}&entitySetName={encodeURIComponent(entitySetName)}"
						class="nav-btn setup-btn"
					>
						설정
					</a>
					<a
						href="/preview?workDir={encodeURIComponent(workDir)}&entitySetName={encodeURIComponent(entitySetName)}"
						class="nav-btn preview-btn"
					>
						미리보기
					</a>
					<a
						href="/generate?workDir={encodeURIComponent(workDir)}&entitySetName={encodeURIComponent(entitySetName)}"
						class="nav-btn generate-btn"
					>
						배경생성
					</a>
				</div>
			</div>

			<div class="control-section">
				<h3>씬 선택</h3>
				<div class="scene-buttons">
					{#if availableScenes.length > 0}
						{#each availableScenes as scene}
							<button
								class="scene-btn"
								class:active={currentSceneId === scene}
								on:click={() => changeScene(scene)}
							>
								Scene {scene}
							</button>
						{/each}
					{:else}
						<p class="no-scenes">매핑을 로드하면 씬 목록이 표시됩니다</p>
					{/if}
				</div>
			</div>

			<div class="control-section">
				<h3>행동 시뮬레이션</h3>

				<!-- 웨어러블 센서 액션 -->
				<div class="action-group">
					<h4 class="group-title">웨어러블 센서</h4>
					<div class="action-buttons">
						{#each actionGroups.wearable as actionId}
							{@const action = actions.find(a => a.id === actionId)}
							<button
								class="action-btn"
								style="background-color: {action.color}"
								on:click={() => simulateAction(action.id)}
							>
								{action.label}
							</button>
						{/each}
					</div>
				</div>

				<!-- 키넥트 자세 액션 -->
				<div class="action-group">
					<h4 class="group-title">키넥트 자세</h4>
					<div class="action-buttons">
						{#each actionGroups.kinect as actionId}
							{@const action = actions.find(a => a.id === actionId)}
							<button
								class="action-btn"
								style="background-color: {action.color}"
								on:click={() => simulateAction(action.id)}
							>
								{action.label}
							</button>
						{/each}
					</div>
				</div>
			</div>

			<div class="control-section">
				<h3>재생 설정</h3>
				<div class="playback-settings">
					<label class="setting-label">
						<span>최소 재생 시간: {(minPlayDuration / 1000).toFixed(1)}초</span>
						<input
							type="range"
							min="0"
							max="10000"
							step="500"
							bind:value={minPlayDuration}
							class="slider"
						/>
					</label>
				</div>
			</div>
		</div>
	{/if}

	<!-- 센서 디스플레이 -->
	<SensorDisplay events={sensorEvents} />
</div>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		overflow: hidden;
	}

	.main-container {
		width: 100vw;
		height: 100vh;
		background-color: #000;
		display: flex;
		flex-direction: column;
	}

	.status-bar {
		background-color: rgba(0, 0, 0, 0.9);
		color: #fff;
		padding: 10px 20px;
		display: flex;
		gap: 20px;
		align-items: center;
		border-bottom: 1px solid #333;
		z-index: 100;
	}

	.status-item {
		display: flex;
		gap: 8px;
		align-items: center;
	}

	.status-item.project-info {
		padding-right: 16px;
		margin-right: 16px;
		border-right: 1px solid #444;
	}

	.label {
		font-weight: bold;
		color: #aaa;
	}

	.value {
		color: #fff;
	}

	.path {
		color: #888;
		font-size: 12px;
	}

	.value.connected {
		color: #4caf50;
	}

	.value.active {
		color: #4caf50;
		font-weight: bold;
	}

	.value.inactive {
		color: #f44336;
	}

	.control-toggle {
		margin-left: auto;
		padding: 6px 12px;
		background-color: #333;
		color: #fff;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		font-size: 12px;
	}

	.control-toggle:hover {
		background-color: #444;
	}

	.player-container {
		flex: 1;
		position: relative;
	}

	.no-video {
		width: 100%;
		height: 100%;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		color: #aaa;
		padding: 40px;
		text-align: center;
	}

	.no-video h2 {
		margin: 0 0 16px 0;
		color: #fff;
		font-size: 24px;
	}

	.no-video p {
		margin: 0 0 24px 0;
		font-size: 16px;
	}

	.action-buttons {
		display: flex;
		gap: 16px;
		margin-bottom: 32px;
	}

	.btn-primary,
	.btn-secondary {
		padding: 12px 24px;
		border-radius: 6px;
		text-decoration: none;
		font-weight: bold;
		font-size: 14px;
		transition: all 0.2s;
	}

	.btn-primary {
		background-color: #2196f3;
		color: #fff;
	}

	.btn-primary:hover {
		background-color: #1976d2;
	}

	.btn-secondary {
		background-color: #555;
		color: #fff;
	}

	.btn-secondary:hover {
		background-color: #666;
	}

	.help-text {
		max-width: 500px;
		background-color: rgba(255, 255, 255, 0.05);
		padding: 20px;
		border-radius: 8px;
		border: 1px solid #333;
	}

	.help-text p {
		margin: 0 0 12px 0;
		color: #ddd;
	}

	.help-text ol {
		text-align: left;
		margin: 0;
		padding-left: 24px;
	}

	.help-text li {
		margin-bottom: 8px;
		color: #aaa;
	}

	.controls-panel {
		position: absolute;
		top: 60px;
		left: 20px;
		background-color: rgba(0, 0, 0, 0.8);
		border: 1px solid #444;
		border-radius: 8px;
		padding: 20px;
		color: #fff;
		max-width: 400px;
		z-index: 50;
	}

	.control-section {
		margin-bottom: 20px;
	}

	.control-section:last-child {
		margin-bottom: 0;
	}

	.control-section h3 {
		margin: 0 0 10px 0;
		font-size: 14px;
		color: #aaa;
	}

	.nav-buttons {
		display: flex;
		flex-direction: row;
		gap: 8px;
	}

	.nav-btn {
		flex: 1;
		padding: 10px 12px;
		border-radius: 4px;
		text-decoration: none;
		font-size: 12px;
		font-weight: 500;
		color: #fff;
		text-align: center;
		transition: all 0.2s;
		border: 1px solid transparent;
		white-space: nowrap;
	}

	.nav-btn.setup-btn {
		background-color: #2196f3;
		border-color: #1976d2;
	}

	.nav-btn.setup-btn:hover {
		background-color: #1976d2;
		border-color: #1565c0;
	}

	.nav-btn.preview-btn {
		background-color: #9c27b0;
		border-color: #7b1fa2;
	}

	.nav-btn.preview-btn:hover {
		background-color: #7b1fa2;
		border-color: #6a1b9a;
	}

	.nav-btn.generate-btn {
		background-color: #4caf50;
		border-color: #388e3c;
	}

	.nav-btn.generate-btn:hover {
		background-color: #388e3c;
		border-color: #2e7d32;
	}

	.action-group {
		margin-bottom: 20px;
	}

	.group-title {
		font-size: 13px;
		color: #aaa;
		margin: 0 0 8px 0;
		font-weight: normal;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.scene-buttons,
	.action-buttons {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}

	.scene-btn,
	.action-btn {
		padding: 8px 16px;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		font-size: 12px;
		color: #fff;
		transition: opacity 0.2s;
	}

	.scene-btn {
		background-color: #333;
	}

	.scene-btn.active {
		background-color: #2196f3;
	}

	.scene-btn:hover,
	.action-btn:hover {
		opacity: 0.8;
	}

	.no-scenes {
		color: #888;
		font-size: 12px;
		margin: 0;
		padding: 8px;
	}

	.playback-settings {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.setting-label {
		display: flex;
		flex-direction: column;
		gap: 8px;
		font-size: 12px;
		color: #ddd;
		cursor: pointer;
	}

	.setting-label span {
		font-weight: 500;
	}

	.slider {
		width: 100%;
		height: 6px;
		border-radius: 3px;
		background: #444;
		outline: none;
		-webkit-appearance: none;
	}

	.slider::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 16px;
		height: 16px;
		border-radius: 50%;
		background: #2196f3;
		cursor: pointer;
		transition: background 0.2s;
	}

	.slider::-webkit-slider-thumb:hover {
		background: #1976d2;
	}

	.slider::-moz-range-thumb {
		width: 16px;
		height: 16px;
		border-radius: 50%;
		background: #2196f3;
		cursor: pointer;
		border: none;
		transition: background 0.2s;
	}

	.slider::-moz-range-thumb:hover {
		background: #1976d2;
	}
</style>
