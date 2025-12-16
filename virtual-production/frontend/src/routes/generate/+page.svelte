<script>
	/**
	 * VP 배경 생성 페이지
	 */

	import { goto } from '$app/navigation';

	const API_BASE = 'http://localhost:8001';

	// 프로젝트 설정
	let workDir = '/Users/khh/Projects/consistent-ai-video-generator/test/demo-file';
	let entitySetName = 'test_project';
	let storyText = '';

	// 모델 및 옵션
	let textModel = 'gpt-4o';
	let imageModel = 'gpt-image-1';
	let videoModel = 'veo-3.0-fast-generate-preview';
	let style = 'realistic';
	let quality = 'medium';

	// 진행 상태
	let currentStep = 0; // 0: 준비, 1: 씬 분석, 2: 배경 생성, 3: 매핑 생성, 4: 완료
	let loading = false;
	let error = '';
	let logs = [];

	// 결과
	let sceneActions = null;
	let backgroundPlan = null;
	let generatedVideos = null;
	let mapping = null;

	// 모델 옵션
	const textModels = ['gpt-4o', 'gpt-4.1', 'gpt-5'];
	const imageModels = ['gpt-image-1'];
	const videoModels = ['veo-3.0-generate-preview', 'veo-3.0-fast-generate-preview', 'runway', 'sora2'];
	const styles = ['realistic', 'illustration', 'anime', 'watercolor', 'oil_painting', 'comic', 'storybook', 'sketch'];
	const qualities = ['low', 'medium', 'high'];

	function addLog(message, type = 'info') {
		const timestamp = new Date().toLocaleTimeString();
		logs = [...logs, { timestamp, message, type }];
	}

	async function step1_analyzeScenes() {
		if (!storyText.trim()) {
			error = '스토리 텍스트를 입력해주세요.';
			return;
		}

		loading = true;
		error = '';
		currentStep = 1;
		addLog('VP 컷 생성 시작...', 'info');

		try {
			const response = await fetch(`${API_BASE}/vp/generate-vp-cuts`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					work_dir: workDir,
					entity_set_name: entitySetName,
					story_text: storyText,
					model: textModel
				})
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || 'VP 컷 생성 실패');
			}

			// 응답 데이터 검증
			if (data.cuts_generated === undefined || data.scenes_processed === undefined) {
				throw new Error('VP 컷 생성 응답 데이터가 올바르지 않습니다.');
			}

			addLog(`VP 컷 생성 완료! ${data.scenes_processed}개 씬, ${data.cuts_generated}개 컷`, 'success');
			addLog(data.message, 'info');

			// 자동으로 다음 단계
			await step2_generateBackgrounds();
		} catch (err) {
			error = `VP 컷 생성 실패: ${err.message}`;
			addLog(error, 'error');
			currentStep = 0;
		} finally {
			loading = false;
		}
	}

	async function step2_generateBackgrounds() {
		loading = true;
		currentStep = 2;
		addLog('VP 영상 생성 시작... (시간이 오래 걸릴 수 있습니다)', 'info');

		try {
			const response = await fetch(`${API_BASE}/vp/generate-vp-videos`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					work_dir: workDir,
					entity_set_name: entitySetName,
					image_model: imageModel,
					video_model: videoModel,
					style: style,
					quality: quality,
					size: '1024x1024'
				})
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || 'VP 영상 생성 실패');
			}

			// 응답 데이터 검증
			if (data.images_generated === undefined || data.videos_generated === undefined) {
				throw new Error('VP 영상 생성 응답 데이터가 올바르지 않습니다.');
			}

			addLog(`VP 영상 생성 완료! 이미지 ${data.images_generated}개, 비디오 ${data.videos_generated}개`, 'success');
			addLog(data.message, 'info');

			// 자동으로 다음 단계
			await step3_generateMapping();
		} catch (err) {
			error = `VP 영상 생성 실패: ${err.message}`;
			addLog(error, 'error');
			currentStep = 1;
		} finally {
			loading = false;
		}
	}

	async function step3_generateMapping() {
		loading = true;
		currentStep = 3;
		addLog('센서-배경 매핑 생성 중...', 'info');

		try {
			const response = await fetch(`${API_BASE}/vp/generate-mapping`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					work_dir: workDir,
					entity_set_name: entitySetName,
					model: textModel
				})
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || '매핑 생성 실패');
			}

			// 응답 데이터 검증
			if (!data.mapping) {
				throw new Error('매핑 생성 응답 데이터가 올바르지 않습니다.');
			}

			mapping = data.mapping;
			// 매핑 통계 계산
			const sceneCount = Object.keys(data.mapping).filter(key => key !== 'sensor_mapping').length;
			addLog(`매핑 생성 완료! ${sceneCount}개 씬의 센서-배경 매핑 생성됨`, 'success');
			currentStep = 4;

			// 완료 후 3초 뒤 메인 플레이어로 이동
			setTimeout(() => {
				addLog('메인 플레이어로 이동합니다...', 'info');
				setTimeout(() => goto('/'), 1000);
			}, 2000);
		} catch (err) {
			error = `매핑 생성 실패: ${err.message}`;
			addLog(error, 'error');
			currentStep = 2;
		} finally {
			loading = false;
		}
	}

	function reset() {
		currentStep = 0;
		loading = false;
		error = '';
		logs = [];
		sceneActions = null;
		backgroundPlan = null;
		generatedVideos = null;
		mapping = null;
	}

	async function loadStoryFile(event) {
		const file = event.target.files[0];
		if (file) {
			storyText = await file.text();
			addLog(`파일 로드: ${file.name}`, 'info');
		}
	}
</script>

<svelte:head>
	<title>배경 생성 - VP</title>
</svelte:head>

<div class="container">
	<div class="card">
		<h1>Virtual Production 배경 생성</h1>
		<p class="subtitle">스토리로부터 배경 영상을 자동 생성합니다</p>

		<!-- 진행 단계 표시 -->
		<div class="progress-steps">
			<div class="step" class:active={currentStep >= 1} class:current={currentStep === 1}>
				<div class="step-number">1</div>
				<div class="step-label">씬 분석</div>
			</div>
			<div class="step-line" class:active={currentStep >= 2}></div>
			<div class="step" class:active={currentStep >= 2} class:current={currentStep === 2}>
				<div class="step-number">2</div>
				<div class="step-label">배경 생성</div>
			</div>
			<div class="step-line" class:active={currentStep >= 3}></div>
			<div class="step" class:active={currentStep >= 3} class:current={currentStep === 3}>
				<div class="step-number">3</div>
				<div class="step-label">매핑 생성</div>
			</div>
			<div class="step-line" class:active={currentStep >= 4}></div>
			<div class="step" class:active={currentStep >= 4} class:current={currentStep === 4}>
				<div class="step-number">✓</div>
				<div class="step-label">완료</div>
			</div>
		</div>

		{#if currentStep === 0}
			<!-- 설정 입력 폼 -->
			<form on:submit|preventDefault={step1_analyzeScenes}>
				<div class="section">
					<h3>프로젝트 설정</h3>
					<div class="form-group">
						<label for="workDir">Work Directory</label>
						<input id="workDir" type="text" bind:value={workDir} required />
						<small>consistentvideo 작업 디렉토리 경로</small>
					</div>

					<div class="form-group">
						<label for="entitySetName">Entity Set Name</label>
						<input id="entitySetName" type="text" bind:value={entitySetName} required />
						<small>프로젝트 이름 (폴더명)</small>
					</div>
				</div>

				<div class="section">
					<h3>스토리 텍스트</h3>
					<div class="form-group">
						<label for="storyText">스토리</label>
						<textarea
							id="storyText"
							bind:value={storyText}
							rows="10"
							placeholder="스토리를 입력하거나 파일을 불러오세요..."
							required
						></textarea>
						<div class="file-upload">
							<input type="file" id="storyFile" accept=".txt" on:change={loadStoryFile} />
							<label for="storyFile" class="file-label">또는 파일 선택</label>
						</div>
					</div>
				</div>

				<div class="section">
					<h3>AI 모델 설정</h3>
					<div class="form-row">
						<div class="form-group">
							<label for="textModel">텍스트 모델</label>
							<select id="textModel" bind:value={textModel}>
								{#each textModels as model}
									<option value={model}>{model}</option>
								{/each}
							</select>
						</div>

						<div class="form-group">
							<label for="imageModel">이미지 모델</label>
							<select id="imageModel" bind:value={imageModel}>
								{#each imageModels as model}
									<option value={model}>{model}</option>
								{/each}
							</select>
						</div>
					</div>

					<div class="form-row">
						<div class="form-group">
							<label for="videoModel">비디오 모델</label>
							<select id="videoModel" bind:value={videoModel}>
								{#each videoModels as model}
									<option value={model}>{model}</option>
								{/each}
							</select>
						</div>

						<div class="form-group">
							<label for="style">화풍</label>
							<select id="style" bind:value={style}>
								{#each styles as s}
									<option value={s}>{s}</option>
								{/each}
							</select>
						</div>
					</div>

					<div class="form-row">
						<div class="form-group">
							<label for="quality">품질</label>
							<select id="quality" bind:value={quality}>
								{#each qualities as q}
									<option value={q}>{q}</option>
								{/each}
							</select>
						</div>
					</div>
				</div>

				{#if error}
					<div class="message error">{error}</div>
				{/if}

				<button type="submit" disabled={loading} class="btn-primary">
					{loading ? '생성 중...' : '배경 생성 시작'}
				</button>
			</form>
		{:else}
			<!-- 진행 중 표시 -->
			<div class="progress-section">
				{#if loading}
					<div class="spinner"></div>
					<p class="loading-text">
						{#if currentStep === 1}
							씬 분석 중...
						{:else if currentStep === 2}
							배경 영상 생성 중... (수 분 소요될 수 있습니다)
						{:else if currentStep === 3}
							센서-배경 매핑 생성 중...
						{/if}
					</p>
				{/if}

				{#if currentStep === 4}
					<div class="success-message">
						<h2>✓ 배경 생성 완료!</h2>
						<p>잠시 후 메인 플레이어로 이동합니다...</p>
						<div class="result-summary">
							<div class="result-item">
								<strong>씬 수:</strong> {Object.keys(sceneActions).length}개
							</div>
							<div class="result-item">
								<strong>생성된 배경:</strong> {Object.keys(generatedVideos).length}개
							</div>
							<div class="result-item">
								<strong>매핑:</strong> {Object.keys(mapping).length}개 씬
							</div>
						</div>
						<div class="action-buttons">
							<a href="/" class="btn-primary">메인 플레이어로 가기</a>
							<a href="/preview" class="btn-secondary">미리보기</a>
						</div>
					</div>
				{/if}

				{#if error}
					<div class="message error">{error}</div>
					<button on:click={reset} class="btn-secondary">다시 시도</button>
				{/if}
			</div>
		{/if}

		<!-- 로그 출력 -->
		{#if logs.length > 0}
			<div class="logs-section">
				<h3>실행 로그</h3>
				<div class="logs">
					{#each logs as log}
						<div class="log-item {log.type}">
							<span class="log-time">[{log.timestamp}]</span>
							<span class="log-message">{log.message}</span>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<div class="links">
			<a href="/">메인 플레이어</a>
			<span>|</span>
			<a href="/setup">초기 설정</a>
			<span>|</span>
			<a href="/preview">미리보기</a>
		</div>
	</div>
</div>

<style>
	:global(body) {
		margin: 0;
		background-color: #1a1a1a;
		color: #fff;
		font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
		overflow-y: auto;
	}

	.container {
		min-height: 100vh;
		display: flex;
		align-items: flex-start;
		justify-content: center;
		padding: 40px 20px;
	}

	.card {
		background-color: #2a2a2a;
		border-radius: 12px;
		padding: 40px;
		max-width: 800px;
		width: 100%;
		box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
	}

	h1 {
		margin: 0 0 10px 0;
		font-size: 28px;
		color: #fff;
	}

	.subtitle {
		margin: 0 0 30px 0;
		color: #aaa;
		font-size: 14px;
	}

	h3 {
		margin: 0 0 15px 0;
		font-size: 18px;
		color: #ddd;
	}

	.progress-steps {
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 40px;
		padding: 20px 0;
	}

	.step {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 8px;
	}

	.step-number {
		width: 40px;
		height: 40px;
		border-radius: 50%;
		background-color: #444;
		color: #888;
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: bold;
		transition: all 0.3s;
	}

	.step.active .step-number {
		background-color: #2196f3;
		color: #fff;
	}

	.step.current .step-number {
		background-color: #4caf50;
		animation: pulse 2s infinite;
	}

	@keyframes pulse {
		0%, 100% {
			transform: scale(1);
		}
		50% {
			transform: scale(1.1);
		}
	}

	.step-label {
		font-size: 12px;
		color: #888;
	}

	.step.active .step-label {
		color: #ddd;
	}

	.step-line {
		width: 60px;
		height: 2px;
		background-color: #444;
		transition: all 0.3s;
	}

	.step-line.active {
		background-color: #2196f3;
	}

	.section {
		margin-bottom: 30px;
		padding: 20px;
		background-color: rgba(255, 255, 255, 0.03);
		border-radius: 8px;
	}

	.form-group {
		margin-bottom: 20px;
	}

	.form-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 15px;
	}

	label {
		display: block;
		margin-bottom: 8px;
		font-weight: bold;
		color: #ddd;
	}

	input,
	textarea,
	select {
		width: 100%;
		padding: 12px;
		background-color: #1a1a1a;
		border: 1px solid #444;
		border-radius: 6px;
		color: #fff;
		font-size: 14px;
		box-sizing: border-box;
		font-family: inherit;
	}

	textarea {
		resize: vertical;
	}

	input:focus,
	textarea:focus,
	select:focus {
		outline: none;
		border-color: #2196f3;
	}

	small {
		display: block;
		margin-top: 6px;
		color: #888;
		font-size: 12px;
	}

	.file-upload {
		margin-top: 10px;
	}

	.file-upload input[type='file'] {
		display: none;
	}

	.file-label {
		display: inline-block;
		padding: 8px 16px;
		background-color: #444;
		color: #fff;
		border-radius: 6px;
		cursor: pointer;
		font-size: 12px;
		transition: background-color 0.2s;
	}

	.file-label:hover {
		background-color: #555;
	}

	button,
	.btn-primary,
	.btn-secondary {
		padding: 14px 24px;
		border: none;
		border-radius: 6px;
		font-size: 16px;
		font-weight: bold;
		cursor: pointer;
		transition: background-color 0.2s;
		text-decoration: none;
		display: inline-block;
		text-align: center;
	}

	button,
	.btn-primary {
		width: 100%;
		background-color: #2196f3;
		color: #fff;
	}

	button:hover:not(:disabled),
	.btn-primary:hover {
		background-color: #1976d2;
	}

	button:disabled {
		background-color: #555;
		cursor: not-allowed;
	}

	.btn-secondary {
		background-color: #555;
		color: #fff;
	}

	.btn-secondary:hover {
		background-color: #666;
	}

	.message {
		padding: 12px;
		border-radius: 6px;
		margin-bottom: 16px;
	}

	.message.error {
		background-color: rgba(244, 67, 54, 0.2);
		border: 1px solid #f44336;
		color: #f44336;
	}

	.progress-section {
		text-align: center;
		padding: 40px 20px;
	}

	.spinner {
		margin: 0 auto 20px;
		width: 50px;
		height: 50px;
		border: 4px solid #444;
		border-top-color: #2196f3;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.loading-text {
		font-size: 16px;
		color: #aaa;
	}

	.success-message {
		padding: 20px;
	}

	.success-message h2 {
		color: #4caf50;
		font-size: 32px;
		margin-bottom: 10px;
	}

	.result-summary {
		margin: 30px 0;
		padding: 20px;
		background-color: rgba(255, 255, 255, 0.05);
		border-radius: 8px;
	}

	.result-item {
		padding: 10px 0;
		border-bottom: 1px solid #444;
		font-size: 14px;
	}

	.result-item:last-child {
		border-bottom: none;
	}

	.action-buttons {
		display: flex;
		gap: 16px;
		justify-content: center;
		margin-top: 20px;
	}

	.logs-section {
		margin-top: 30px;
		padding: 20px;
		background-color: #1a1a1a;
		border-radius: 8px;
		max-height: 400px;
		overflow-y: auto;
	}

	.logs {
		font-family: 'Courier New', monospace;
		font-size: 12px;
	}

	.log-item {
		padding: 6px 0;
		border-bottom: 1px solid #333;
	}

	.log-item:last-child {
		border-bottom: none;
	}

	.log-time {
		color: #888;
		margin-right: 8px;
	}

	.log-message {
		color: #ddd;
	}

	.log-item.success {
		color: #4caf50;
	}

	.log-item.success .log-message {
		color: #4caf50;
	}

	.log-item.error {
		color: #f44336;
	}

	.log-item.error .log-message {
		color: #f44336;
	}

	.links {
		margin-top: 30px;
		text-align: center;
		font-size: 14px;
	}

	.links a {
		color: #2196f3;
		text-decoration: none;
		margin: 0 10px;
	}

	.links a:hover {
		text-decoration: underline;
	}

	.links span {
		color: #555;
	}
</style>
