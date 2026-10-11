// 듣기 탭 도우미: 회차 데이터 불러오기, 풀이 기록, 문항 구간 재생.
import { useCallback, useEffect, useRef, useState } from 'react';

const ANSWER_KEY = 'sungmi-vocab-listening-v1';
const PREF_KEY = 'sungmi-vocab-listening-prefs-v1';

// '모르겠음'은 기록에 '?'로 남깁니다. 틀린 것과 따로 셉니다.
export const UNKNOWN = '?';

function readJson(key, fallback) {
  try {
    const saved = localStorage.getItem(key);
    const parsed = saved ? JSON.parse(saved) : null;
    return parsed && typeof parsed === 'object' ? parsed : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // 저장 실패가 학습을 막을 이유는 없습니다.
  }
}

// { "H31001": { "23": "A", "24": "?" } }
export const loadAnswers = () => readJson(ANSWER_KEY, {});
export const saveAnswers = (answers) => writeJson(ANSWER_KEY, answers);
export const loadPrefs = () => readJson(PREF_KEY, {});
export const savePrefs = (prefs) => writeJson(PREF_KEY, prefs);

export function gradeOf(item, picked) {
  if (!picked) return null;
  if (picked === UNKNOWN) return 'unknown';
  return picked === item.answer ? 'right' : 'wrong';
}

export function tally(items, picks = {}) {
  return items.reduce(
    (acc, item) => {
      const grade = gradeOf(item, picks[item.no]);
      if (grade) acc[grade] += 1;
      return acc;
    },
    { right: 0, wrong: 0, unknown: 0 }
  );
}

const testCache = new Map();

// 회차 데이터(대본·해설, 약 85KB)는 그 회차를 고를 때만 받아옵니다.
export function fetchTest(id) {
  if (!testCache.has(id)) {
    const request = fetch(`/listening/${id}.json`).then((response) => {
      if (!response.ok) throw new Error(`${id} 데이터를 불러오지 못했어요 (${response.status})`);
      return response.json();
    });
    request.catch(() => testCache.delete(id));
    testCache.set(id, request);
  }
  return testCache.get(id);
}

// 이어 붙인 음원에서 지금 시각이 몇 번 문항인지 찾습니다 (문항 사이 쉼은 앞 문항에 붙입니다).
function itemAt(items, time) {
  let found = null;
  for (const item of items) {
    if (item.start - 0.1 <= time) found = item;
    else break;
  }
  return found?.no ?? null;
}

// 회차 음원 하나를 두고 문항 구간만 재생하거나(item), 여러 문항을 이어서 재생합니다(run).
// 이어 듣기는 파일을 그냥 흘려보내므로 화면이 꺼져도 끊기지 않습니다.
export function useClipPlayer(src, items) {
  const audioRef = useRef(null);
  const endRef = useRef(null);
  const itemsRef = useRef(items);
  const [playing, setPlaying] = useState(null); // { mode: 'item' | 'run', no }

  itemsRef.current = items;

  useEffect(() => {
    if (!src) return undefined;
    const audio = new Audio();
    audio.preload = 'auto';
    audio.src = src;
    audioRef.current = audio;
    let frame = 0;

    function check() {
      const end = endRef.current;
      if (end !== null && audio.currentTime >= end) {
        endRef.current = null;
        audio.pause();
        return;
      }
      setPlaying((prev) => {
        if (!prev || prev.mode !== 'run') return prev;
        const no = itemAt(itemsRef.current, audio.currentTime);
        return no && no !== prev.no ? { ...prev, no } : prev;
      });
    }

    // 구간 끝에서 정확히 멈추려고 화면이 켜져 있을 때는 프레임마다 확인합니다.
    // 화면이 꺼지면 프레임이 멈추므로 timeupdate가 대신 확인합니다.
    function tick() {
      check();
      if (!audio.paused) frame = requestAnimationFrame(tick);
    }
    const onPlaying = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(tick);
    };
    const onStopped = () => {
      cancelAnimationFrame(frame);
      setPlaying(null);
    };

    audio.addEventListener('playing', onPlaying);
    audio.addEventListener('timeupdate', check);
    audio.addEventListener('pause', onStopped);
    audio.addEventListener('ended', onStopped);

    return () => {
      cancelAnimationFrame(frame);
      audio.removeEventListener('playing', onPlaying);
      audio.removeEventListener('timeupdate', check);
      audio.removeEventListener('pause', onStopped);
      audio.removeEventListener('ended', onStopped);
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
      audioRef.current = null;
      endRef.current = null;
      setPlaying(null);
    };
  }, [src]);

  const playSpan = useCallback((start, end, mode, no) => {
    const audio = audioRef.current;
    if (!audio) return;
    endRef.current = end;
    const seek = () => {
      audio.currentTime = start;
    };
    if (audio.readyState >= 1) seek();
    else audio.addEventListener('loadedmetadata', seek, { once: true });
    setPlaying({ mode, no });
    // play()는 버튼을 누른 그 순간에 불러야 아이폰에서도 소리가 납니다.
    audio.play()?.catch(() => setPlaying(null));
  }, []);

  const playItem = useCallback((item) => playSpan(item.start, item.end + 0.05, 'item', item.no), [playSpan]);

  const playRun = useCallback(
    (list) => {
      if (!list.length) return;
      playSpan(list[0].start, list[list.length - 1].end + 0.05, 'run', list[0].no);
    },
    [playSpan]
  );

  const stop = useCallback(() => {
    endRef.current = null;
    audioRef.current?.pause();
  }, []);

  return { playing, playItem, playRun, stop };
}
