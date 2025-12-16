<script>
	/**
	 * VP 초기 설정 페이지
	 */

	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	const API_BASE = 'http://localhost:8001';

	let workDir = '/Users/khh/Projects/consistent-ai-video-generator/test/demo-file';
	let entitySetName = 'test_project';
	let loading = false;
	let message = '';
	let error = '';

	onMount(() => {
		// URL 파라미터에서 기본값 읽기
		const params = new URLSearchParams(window.location.search);
		const urlWorkDir = params.get('workDir');
		const urlEntitySetName = params.get('entitySetName');

		if (urlWorkDir) workDir = urlWorkDir;
		if (urlEntitySetName) entitySetName = urlEntitySetName;
	});

	async function loadMapping() {
		loading = true;
		error = '';
		message = '';

		try {
			const response = await fetch(
				`${API_BASE}/vp/load-mapping?work_dir=${encodeURIComponent(workDir)}&entity_set_name=${encodeURIComponent(entitySetName)}`
			);

			const data = await response.json();

			if (data.mapping) {
				message = '매핑 로드 완료! 플레이어로 이동합니다...';
				setTimeout(() => {
					// URL 파라미터로 설정 전달
					const params = new URLSearchParams({
						workDir: workDir,
						entitySetName: entitySetName
					});
					goto(`/?${params.toString()}`);
				}, 1500);
			} else {
				error = '매핑 파일을 찾을 수 없습니다. 먼저 배경 영상을 생성해주세요.';
			}
		} catch (err) {
			error = `매핑 로드 실패: ${err.message}`;
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>VP 초기 설정</title>
</svelte:head>

<div class="container">
	<div class="card">
		<h1>Virtual Production 초기 설정</h1>
		<p class="subtitle">배경 영상 매핑을 로드하여 시스템을 시작합니다.</p>

		<form on:submit|preventDefault={loadMapping}>
			<div class="form-group">
				<label for="workDir">Work Directory</label>
				<input
					id="workDir"
					type="text"
					bind:value={workDir}
					placeholder="/path/to/work/directory"
					required
				/>
				<small>consistentvideo 작업 디렉토리 경로</small>
			</div>

			<div class="form-group">
				<label for="entitySetName">Entity Set Name</label>
				<input
					id="entitySetName"
					type="text"
					bind:value={entitySetName}
					placeholder="project_name"
					required
				/>
				<small>프로젝트 이름 (폴더명)</small>
			</div>

			{#if message}
				<div class="message success">{message}</div>
			{/if}

			{#if error}
				<div class="message error">{error}</div>
			{/if}

			<button type="submit" disabled={loading}>
				{loading ? '로딩 중...' : '매핑 로드'}
			</button>
		</form>

		<div class="info-box">
			<h3>ℹ️ 배경 영상이 없나요?</h3>
			<p>웹 인터페이스에서 간편하게 배경 영상을 생성할 수 있습니다:</p>
			<div class="action-buttons">
				<a
					href="/generate?workDir={encodeURIComponent(workDir)}&entitySetName={encodeURIComponent(entitySetName)}"
					class="btn-generate"
				>
					배경 생성 페이지로 이동
				</a>
			</div>
			<p style="margin-top: 20px; font-size: 13px; color: #888;">
				또는 Python API를 사용할 수도 있습니다 (고급 사용자용)
			</p>
		</div>

		<div class="links">
			<a href="/?workDir={encodeURIComponent(workDir)}&entitySetName={encodeURIComponent(entitySetName)}">
				메인 플레이어
			</a>
			<span>|</span>
			<a href="/generate?workDir={encodeURIComponent(workDir)}&entitySetName={encodeURIComponent(entitySetName)}">
				배경 생성
			</a>
			<span>|</span>
			<a href="/preview?workDir={encodeURIComponent(workDir)}&entitySetName={encodeURIComponent(entitySetName)}">
				미리보기
			</a>
		</div>
	</div>
</div>

<style>
	:global(body) {
		margin: 0;
		background-color: #1a1a1a;
		color: #fff;
		font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
	}

	.container {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 20px;
	}

	.card {
		background-color: #2a2a2a;
		border-radius: 12px;
		padding: 40px;
		max-width: 600px;
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

	.form-group {
		margin-bottom: 20px;
	}

	label {
		display: block;
		margin-bottom: 8px;
		font-weight: bold;
		color: #ddd;
	}

	input {
		width: 100%;
		padding: 12px;
		background-color: #1a1a1a;
		border: 1px solid #444;
		border-radius: 6px;
		color: #fff;
		font-size: 14px;
		box-sizing: border-box;
	}

	input:focus {
		outline: none;
		border-color: #2196f3;
	}

	small {
		display: block;
		margin-top: 6px;
		color: #888;
		font-size: 12px;
	}

	button {
		width: 100%;
		padding: 14px;
		background-color: #2196f3;
		color: #fff;
		border: none;
		border-radius: 6px;
		font-size: 16px;
		font-weight: bold;
		cursor: pointer;
		transition: background-color 0.2s;
	}

	button:hover:not(:disabled) {
		background-color: #1976d2;
	}

	button:disabled {
		background-color: #555;
		cursor: not-allowed;
	}

	.message {
		padding: 12px;
		border-radius: 6px;
		margin-bottom: 16px;
	}

	.message.success {
		background-color: rgba(76, 175, 80, 0.2);
		border: 1px solid #4caf50;
		color: #4caf50;
	}

	.message.error {
		background-color: rgba(244, 67, 54, 0.2);
		border: 1px solid #f44336;
		color: #f44336;
	}

	.info-box {
		margin-top: 30px;
		padding: 20px;
		background-color: rgba(33, 150, 243, 0.1);
		border: 1px solid rgba(33, 150, 243, 0.3);
		border-radius: 8px;
	}

	.info-box h3 {
		margin: 0 0 12px 0;
		font-size: 16px;
		color: #2196f3;
	}

	.info-box p {
		margin: 0 0 12px 0;
		color: #aaa;
		font-size: 14px;
	}

	pre {
		background-color: #1a1a1a;
		border: 1px solid #444;
		border-radius: 6px;
		padding: 12px;
		overflow-x: auto;
		margin: 0;
	}

	code {
		color: #4caf50;
		font-family: 'Courier New', monospace;
		font-size: 12px;
	}

	.links {
		margin-top: 20px;
		text-align: center;
	}

	.links a {
		color: #2196f3;
		text-decoration: none;
		font-size: 14px;
	}

	.links a:hover {
		text-decoration: underline;
	}

	.links span {
		color: #555;
		margin: 0 8px;
	}

	.action-buttons {
		margin: 20px 0;
	}

	.btn-generate {
		display: inline-block;
		padding: 12px 24px;
		background-color: #4caf50;
		color: #fff;
		text-decoration: none;
		border-radius: 6px;
		font-weight: bold;
		font-size: 14px;
		transition: background-color 0.2s;
	}

	.btn-generate:hover {
		background-color: #45a049;
	}
</style>
