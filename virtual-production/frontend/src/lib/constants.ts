/**
 * Virtual Production - Action Constants
 * 센서 액션 메타데이터 정의
 */

export interface ActionMetadata {
	label: string;
	color: string;
	category: 'wearable' | 'kinect';
}

/**
 * 모든 센서 액션의 메타데이터
 */
export const ACTION_METADATA: Record<string, ActionMetadata> = {
	// 웨어러블 센서 액션 (8개)
	stop: { label: '정지', color: '#888888', category: 'wearable' },
	walk: { label: '걷기', color: '#4CAF50', category: 'wearable' },
	run: { label: '달리기', color: '#FF9800', category: 'wearable' },
	fall: { label: '낙상', color: '#F44336', category: 'wearable' },
	turn: { label: '뒤돌아보기', color: '#2196F3', category: 'wearable' },
	shout: { label: '소리지름', color: '#9C27B0', category: 'wearable' },
	dark: { label: '어두움', color: '#424242', category: 'wearable' },
	bright: { label: '밝음', color: '#FFEB3B', category: 'wearable' },

	// 키넥트 자세 액션 (5개)
	standing: { label: '서있음', color: '#00BCD4', category: 'kinect' },
	sitting: { label: '앉음', color: '#3F51B5', category: 'kinect' },
	lying: { label: '누움', color: '#9E9E9E', category: 'kinect' },
	left_arm_up: { label: '왼팔 들기', color: '#FF5722', category: 'kinect' },
	right_arm_up: { label: '오른팔 들기', color: '#E91E63', category: 'kinect' }
};

/**
 * 액션 ID 목록 (백엔드와 동일한 순서)
 */
export const ALL_ACTIONS = [
	// Wearable sensor actions
	'stop',
	'walk',
	'run',
	'fall',
	'turn',
	'shout',
	'dark',
	'bright',
	// Kinect posture actions
	'standing',
	'sitting',
	'lying',
	'left_arm_up',
	'right_arm_up'
] as const;

export type ActionId = (typeof ALL_ACTIONS)[number];

/**
 * 액션 ID를 받아 메타데이터 반환
 */
export function getActionMetadata(actionId: string): ActionMetadata {
	return (
		ACTION_METADATA[actionId] || {
			label: actionId,
			color: '#888888',
			category: 'wearable'
		}
	);
}

/**
 * 카테고리별로 액션 그룹화
 */
export function getActionsByCategory() {
	const wearable = ALL_ACTIONS.filter((id) => ACTION_METADATA[id].category === 'wearable');
	const kinect = ALL_ACTIONS.filter((id) => ACTION_METADATA[id].category === 'kinect');

	return { wearable, kinect };
}
