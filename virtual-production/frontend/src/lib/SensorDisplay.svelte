<script lang="ts">
	/**
	 * 센서 이벤트 디스플레이
	 * 최근 센서 이벤트를 작은 패널에 표시
	 */

	import { getActionMetadata } from './constants';

	export let events = [];
	export let maxEvents = 10;
	export let collapsed = false;

	// 최근 이벤트만 유지
	$: recentEvents = events.slice(-maxEvents);

	function toggleCollapse() {
		collapsed = !collapsed;
	}

	function formatTimestamp(timestamp) {
		const date = new Date(timestamp);
		return date.toLocaleTimeString('ko-KR');
	}

	function getBehaviorLabel(behavior) {
		const metadata = getActionMetadata(behavior);
		return metadata.label;
	}

	function getBehaviorColor(behavior) {
		const metadata = getActionMetadata(behavior);
		return metadata.color;
	}
</script>

<div class="sensor-display" class:collapsed>
	<div class="header" on:click={toggleCollapse} on:keydown={toggleCollapse} role="button" tabindex="0">
		<span class="title">센서 이벤트</span>
		<span class="toggle">{collapsed ? '▲' : '▼'}</span>
	</div>

	{#if !collapsed}
		<div class="events-list">
			{#if recentEvents.length === 0}
				<div class="no-events">이벤트 없음</div>
			{:else}
				{#each recentEvents as event (event.timestamp)}
					<div class="event-item">
						<span class="timestamp">{formatTimestamp(event.timestamp)}</span>
						<span class="behavior" style="background-color: {getBehaviorColor(event.behavior)}">
							{getBehaviorLabel(event.behavior)}
						</span>
						{#if event.metadata}
							<span class="metadata">{JSON.stringify(event.metadata)}</span>
						{/if}
					</div>
				{/each}
			{/if}
		</div>
	{/if}
</div>

<style>
	.sensor-display {
		position: fixed;
		bottom: 20px;
		right: 20px;
		width: 300px;
		max-height: 400px;
		background-color: rgba(0, 0, 0, 0.8);
		border: 1px solid #444;
		border-radius: 8px;
		color: #fff;
		font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
		font-size: 12px;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
		transition: max-height 0.3s ease;
	}

	.sensor-display.collapsed {
		max-height: 40px;
	}

	.header {
		padding: 10px 15px;
		background-color: rgba(255, 255, 255, 0.1);
		cursor: pointer;
		display: flex;
		justify-content: space-between;
		align-items: center;
		user-select: none;
	}

	.header:hover {
		background-color: rgba(255, 255, 255, 0.15);
	}

	.title {
		font-weight: bold;
	}

	.toggle {
		font-size: 10px;
	}

	.events-list {
		padding: 10px;
		max-height: 340px;
		overflow-y: auto;
	}

	.events-list::-webkit-scrollbar {
		width: 6px;
	}

	.events-list::-webkit-scrollbar-track {
		background: rgba(255, 255, 255, 0.05);
	}

	.events-list::-webkit-scrollbar-thumb {
		background: rgba(255, 255, 255, 0.3);
		border-radius: 3px;
	}

	.no-events {
		text-align: center;
		color: #888;
		padding: 20px;
	}

	.event-item {
		padding: 6px 8px;
		margin-bottom: 6px;
		background-color: rgba(255, 255, 255, 0.05);
		border-radius: 4px;
		display: flex;
		align-items: center;
		gap: 8px;
		flex-wrap: wrap;
	}

	.timestamp {
		color: #888;
		font-size: 10px;
	}

	.behavior {
		padding: 2px 8px;
		border-radius: 12px;
		font-weight: bold;
		color: #fff;
		font-size: 11px;
	}

	.metadata {
		color: #aaa;
		font-size: 10px;
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
