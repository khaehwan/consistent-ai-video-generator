<script lang="ts">
	/**
	 * 배경 영상 미리보기 페이지
	 */

	import { onMount } from 'svelte';

	type PreviewItem = {
		scene_id: number;
		action: string;
		video_filename: string;
		video_url: string;
	};

	const API_BASE = 'http://localhost:8001';

	let previews: PreviewItem[] = [];
	let loading = true;
	let workDir = '';
	let entitySetName = '';
	let selectedVideo: string | null = null;

	onMount(async () => {
		console.log('[Preview] onMount called');

		// URL 파라미터에서 workDir, entitySetName 가져오기
		const params = new URLSearchParams(window.location.search);
		workDir = params.get('workDir') || '';
		entitySetName = params.get('entitySetName') || '';

		console.log('[Preview] URL params:', { workDir, entitySetName });

		if (workDir && entitySetName) {
			await loadPreviews();
		} else {
			console.warn('[Preview] ⚠️ Missing workDir or entitySetName');
			loading = false;
		}
	});

	async function loadPreviews(): Promise<void> {
		console.log('[Preview] 📥 Loading previews...');

		try {
			const url = `${API_BASE}/vp/preview?work_dir=${encodeURIComponent(workDir)}&entity_set_name=${encodeURIComponent(entitySetName)}`;
			console.log('[Preview] Fetching:', url);

			const response = await fetch(url);
			console.log('[Preview] Response status:', response.status);

			if (!response.ok) {
				console.error('[Preview] ❌ Response not OK:', response.statusText);
				const errorText = await response.text();
				console.error('[Preview] Error response:', errorText);
				return;
			}

			const data = await response.json();
			console.log('[Preview] 📦 Response data:', data);

			previews = data.previews || [];
			console.log('[Preview] ✅ Loaded', previews.length, 'preview items');

			if (previews.length === 0) {
				console.warn('[Preview] ⚠️ No previews found. Check if videos exist.');
			} else {
				console.log('[Preview] Preview items:', previews);
			}
		} catch (error) {
			console.error('[Preview] ❌ Failed to load previews:', error);
			console.error('[Preview] Error details:', {
				message: error.message,
				stack: error.stack
			});
		} finally {
			loading = false;
		}
	}

	function playVideo(videoUrl: string): void {
		const fullUrl = `${API_BASE}${videoUrl}`;
		console.log('[Preview] 🎬 Playing video:', fullUrl);
		selectedVideo = fullUrl;
	}

	function groupByScene(items: PreviewItem[]): Map<number, PreviewItem[]> {
		const groups = new Map<number, PreviewItem[]>();
		items.forEach((item) => {
			if (!groups.has(item.scene_id)) {
				groups.set(item.scene_id, []);
			}
			groups.get(item.scene_id)!.push(item);
		});
		return groups;
	}

	$: sceneGroups = groupByScene(previews);
</script>

<svelte:head>
	<title>배경 영상 미리보기</title>
</svelte:head>

<div class="container">
	<header>
		<h1>배경 영상 미리보기</h1>
		<a href="/" class="back-link">← 플레이어로 돌아가기</a>
	</header>

	{#if loading}
		<div class="loading">로딩 중...</div>
	{:else if previews.length === 0}
		<div class="empty">
			<p>생성된 배경 영상이 없습니다.</p>
			<p class="hint">workDir와 entitySetName을 URL 파라미터로 지정해주세요.</p>
		</div>
	{:else}
		<div class="content">
			<!-- 비디오 플레이어 -->
			{#if selectedVideo}
				<div class="player-section">
					<video src={selectedVideo} controls autoplay loop>
						<track kind="captions" />
					</video>
				</div>
			{/if}

			<!-- 씬별 그리드 -->
			<div class="scenes-grid">
				{#each Array.from(sceneGroups.entries()) as [sceneId, items]}
					<div class="scene-group">
						<h2>Scene {sceneId}</h2>
						<div class="video-grid">
							{#each items as item}
								<div
									class="video-card"
									on:click={() => playVideo(item.video_url)}
									on:keydown={() => playVideo(item.video_url)}
									role="button"
									tabindex="0"
								>
									<div class="thumbnail">
										<video src="{API_BASE}{item.video_url}" muted>
											<track kind="captions" />
										</video>
									</div>
									<div class="info">
										<span class="action">{item.action}</span>
										<span class="filename">{item.video_filename}</span>
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}
</div>

<style>
	.container {
		min-height: 100vh;
		background-color: #1a1a1a;
		color: #fff;
		padding: 20px;
	}

	header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 30px;
	}

	h1 {
		margin: 0;
		font-size: 24px;
	}

	.back-link {
		color: #2196f3;
		text-decoration: none;
	}

	.back-link:hover {
		text-decoration: underline;
	}

	.loading,
	.empty {
		text-align: center;
		padding: 60px 20px;
		color: #888;
	}

	.hint {
		font-size: 12px;
		color: #666;
	}

	.content {
		display: flex;
		flex-direction: column;
		gap: 30px;
	}

	.player-section {
		background-color: #000;
		border-radius: 8px;
		overflow: hidden;
	}

	.player-section video {
		width: 100%;
		max-height: 500px;
		object-fit: contain;
	}

	.scenes-grid {
		display: flex;
		flex-direction: column;
		gap: 30px;
	}

	.scene-group h2 {
		margin: 0 0 15px 0;
		font-size: 18px;
		color: #aaa;
	}

	.video-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 15px;
	}

	.video-card {
		background-color: #2a2a2a;
		border-radius: 8px;
		overflow: hidden;
		cursor: pointer;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.video-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
	}

	.thumbnail {
		width: 100%;
		height: 120px;
		background-color: #000;
		overflow: hidden;
	}

	.thumbnail video {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.info {
		padding: 10px;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.action {
		font-weight: bold;
		color: #4caf50;
	}

	.filename {
		font-size: 11px;
		color: #888;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
