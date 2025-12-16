<script lang="ts">
	/**
	 * 크로스디졸브 효과를 지원하는 비디오 플레이어
	 * 2개의 비디오 레이어를 번갈아 사용하여 부드러운 전환 구현
	 */

	import { onMount, onDestroy } from 'svelte';

	export let videoUrl = '';
	export let transitionDuration = 1000; // ms
	export let minPlayDuration = 0; // 최소 재생 시간 (ms)

	let video1;
	let video2;
	let currentLayer = 0;
	let isTransitioning = false;
	let mounted = false;
	let currentVideoUrl = ''; // 현재 재생 중인 URL 추적
	let lastTransitionTime = 0; // 마지막 전환 시간
	let pendingVideoUrl = ''; // 전환 대기 중인 URL
	let pendingTimer = null; // pending 전환 타이머

	onMount(() => {
		console.log('[VideoPlayer] Component mounted');
		mounted = true;
		// 마운트 후 초기 비디오가 있으면 로드
		if (videoUrl) {
			console.log('[VideoPlayer] Initial video URL:', videoUrl);
			crossFadeTo(videoUrl);
		}
	});

	onDestroy(() => {
		// 타이머 정리
		if (pendingTimer) {
			clearTimeout(pendingTimer);
			pendingTimer = null;
		}
	});

	// 비디오 URL이 변경되면 전환 (실제로 다른 URL일 때만)
	$: if (mounted && videoUrl) {
		// URL에서 파일명 추출 (쿼리 파라미터 제외)
		const newFilename = videoUrl.split('?')[0];
		const currentFilename = currentVideoUrl.split('?')[0];

		if (newFilename !== currentFilename) {
			console.log('[VideoPlayer] 🎬 Video URL changed:', videoUrl);
			console.log('[VideoPlayer] Previous URL:', currentVideoUrl);
			crossFadeTo(videoUrl);
		}
	}

	function crossFadeTo(newVideoUrl) {
		console.log('[VideoPlayer] crossFadeTo called with:', newVideoUrl);

		if (!video1 || !video2) {
			console.error('[VideoPlayer] ❌ Video elements not ready!', { video1, video2 });
			return;
		}

		// URL에서 파일명 추출하여 비교 (캐시 방지 파라미터 무시)
		const newFilename = newVideoUrl.split('?')[0];
		const currentFilename = currentVideoUrl.split('?')[0];

		if (newFilename === currentFilename) {
			console.log('[VideoPlayer] ⏭️ Same video file, skipping transition');
			pendingVideoUrl = ''; // pending 취소
			if (pendingTimer) {
				clearTimeout(pendingTimer);
				pendingTimer = null;
			}
			return;
		}

		// 이미 전환 중이면 pending으로 저장하고 대기
		if (isTransitioning) {
			console.log('[VideoPlayer] ⏸️ Already transitioning, queuing for later');
			pendingVideoUrl = newVideoUrl;
			return;
		}

		// 최소 재생 시간 체크
		const now = Date.now();
		const timeSinceLastTransition = now - lastTransitionTime;

		if (minPlayDuration > 0 && lastTransitionTime > 0 && timeSinceLastTransition < minPlayDuration) {
			const remainingTime = minPlayDuration - timeSinceLastTransition;
			console.log(`[VideoPlayer] ⏸️ Minimum play duration not met. Wait ${Math.ceil(remainingTime / 1000)}s more.`);
			pendingVideoUrl = newVideoUrl; // 나중에 전환하도록 저장

			// 기존 타이머가 있으면 취소
			if (pendingTimer) {
				clearTimeout(pendingTimer);
			}

			// 남은 시간 후 자동 전환
			pendingTimer = setTimeout(() => {
				console.log('[VideoPlayer] ⏰ Minimum duration elapsed, processing pending URL');
				if (pendingVideoUrl) {
					const urlToPlay = pendingVideoUrl;
					pendingVideoUrl = '';
					pendingTimer = null;
					crossFadeTo(urlToPlay);
				}
			}, remainingTime);

			return;
		}

		pendingVideoUrl = ''; // pending 초기화
		if (pendingTimer) {
			clearTimeout(pendingTimer);
			pendingTimer = null;
		}
		isTransitioning = true;
		lastTransitionTime = now;

		// 다음 레이어 결정
		const nextLayer = currentLayer === 0 ? 1 : 0;
		const nextVideo = nextLayer === 0 ? video1 : video2;
		const currentVideo = currentLayer === 0 ? video1 : video2;

		console.log('[VideoPlayer] Layer info:', {
			currentLayer,
			nextLayer,
			currentVideoSrc: currentVideo.src,
			nextVideoSrc: nextVideo.src
		});

		// 다음 비디오 로드
		nextVideo.src = newVideoUrl;
		console.log('[VideoPlayer] 📥 Loading video:', newVideoUrl);
		nextVideo.load();

		nextVideo.onloadeddata = () => {
			console.log('[VideoPlayer] ✅ Video loaded successfully');

			// 현재 URL 업데이트
			currentVideoUrl = newVideoUrl;

			// 재생 시작
			nextVideo.play()
				.then(() => {
					console.log('[VideoPlayer] ▶️ Video playing');
				})
				.catch((error) => {
					console.error('[VideoPlayer] ❌ Video play error:', error);
				});

			// 레이어 전환 (CSS transition으로 페이드 효과)
			setTimeout(() => {
				console.log('[VideoPlayer] 🔄 Switching layer to:', nextLayer);
				currentLayer = nextLayer;

				// 전환 완료 후 이전 비디오 일시정지
				setTimeout(() => {
					currentVideo.pause();
					isTransitioning = false;
					console.log('[VideoPlayer] ✅ Transition complete');

					// pending URL이 있으면 즉시 전환
					if (pendingVideoUrl) {
						console.log('[VideoPlayer] 🚀 Processing pending URL:', pendingVideoUrl);
						const urlToPlay = pendingVideoUrl;
						pendingVideoUrl = '';
						if (pendingTimer) {
							clearTimeout(pendingTimer);
							pendingTimer = null;
						}
						crossFadeTo(urlToPlay);
					}
				}, transitionDuration);
			}, 100);
		};

		nextVideo.onerror = (error) => {
			console.error('[VideoPlayer] ❌ Video load error:', error);
			console.error('[VideoPlayer] Failed URL:', newVideoUrl);
			console.error('[VideoPlayer] Video element:', nextVideo);
			isTransitioning = false;
		};
	}

	function handleVideoEnded(event) {
		console.log('[VideoPlayer] 🔄 Video ended, looping with crossfade...');

		if (isTransitioning) {
			console.log('[VideoPlayer] Already transitioning, skip loop transition');
			return;
		}

		// pending URL이 있으면 루프하지 않고 바로 전환
		if (pendingVideoUrl) {
			console.log('[VideoPlayer] 🚀 Pending URL exists, transitioning instead of looping');
			const urlToPlay = pendingVideoUrl;
			pendingVideoUrl = '';
			if (pendingTimer) {
				clearTimeout(pendingTimer);
				pendingTimer = null;
			}
			crossFadeTo(urlToPlay);
			return;
		}

		const video = event.target;

		// 크로스디졸브로 루프 (다른 레이어에 같은 비디오 로드)
		isTransitioning = true;

		// 다음 레이어 결정
		const nextLayer = currentLayer === 0 ? 1 : 0;
		const nextVideo = nextLayer === 0 ? video1 : video2;
		const currentVideo = video; // 끝난 비디오

		console.log('[VideoPlayer] Loop transition:', {
			endedLayer: currentLayer,
			nextLayer: nextLayer,
			videoUrl: currentVideoUrl
		});

		// 다음 레이어에 같은 비디오를 처음부터 로드
		nextVideo.src = currentVideoUrl;
		nextVideo.load();

		nextVideo.onloadeddata = () => {
			console.log('[VideoPlayer] ✅ Loop video loaded');

			// 처음부터 재생
			nextVideo.currentTime = 0;
			nextVideo.play()
				.then(() => {
					console.log('[VideoPlayer] ▶️ Loop video playing');
				})
				.catch((error) => {
					console.error('[VideoPlayer] ❌ Loop video play error:', error);
				});

			// 레이어 전환 (CSS transition으로 페이드 효과)
			setTimeout(() => {
				console.log('[VideoPlayer] 🔄 Switching layer for loop to:', nextLayer);
				currentLayer = nextLayer;

				// 전환 완료 후 이전 비디오 리셋
				setTimeout(() => {
					currentVideo.pause();
					currentVideo.currentTime = 0;
					isTransitioning = false;
					console.log('[VideoPlayer] ✅ Loop transition complete');

				// pending URL이 있으면 즉시 전환
				if (pendingVideoUrl) {
					console.log('[VideoPlayer] 🚀 Processing pending URL after loop:', pendingVideoUrl);
					const urlToPlay = pendingVideoUrl;
					pendingVideoUrl = '';
					if (pendingTimer) {
						clearTimeout(pendingTimer);
						pendingTimer = null;
					}
					crossFadeTo(urlToPlay);
				}
				}, transitionDuration);
			}, 100);
		};

		nextVideo.onerror = (error) => {
			console.error('[VideoPlayer] ❌ Loop video load error:', error);
			// 에러 시 기본 루프 방식으로 폴백
			currentVideo.currentTime = 0;
			currentVideo.play();
			isTransitioning = false;
		};
	}
</script>

<div class="video-container">
	<video
		bind:this={video1}
		class="video-layer"
		class:active={currentLayer === 0}
		muted
		playsinline
		on:ended={handleVideoEnded}
	>
		<track kind="captions" />
	</video>

	<video
		bind:this={video2}
		class="video-layer"
		class:active={currentLayer === 1}
		muted
		playsinline
		on:ended={handleVideoEnded}
	>
		<track kind="captions" />
	</video>
</div>

<style>
	.video-container {
		position: relative;
		width: 100%;
		height: 100%;
		background-color: #000;
		overflow: hidden;
	}

	.video-layer {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		object-fit: contain;
		opacity: 0;
		transition: opacity var(--transition-duration, 1s) ease-in-out;
	}

	.video-layer.active {
		opacity: 1;
	}
</style>
