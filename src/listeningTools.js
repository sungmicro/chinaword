// 듣기 탭 도우미: 풀이 기록, 문항 구간 재생. 독해와 같이 쓰는 부분은 practiceStore.js에 있습니다.
import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchCached, readJson, writeJson } from './practiceStore';

export { UNKNOWN, gradeOf, tally } from './practiceStore';

const ANSWER_KEY = 'sungmi-vocab-listening-v1';
const PREF_KEY = 'sungmi-vocab-listening-prefs-v1';

// { "H31001": { "23": "A", "24": "?" } }
export const loadAnswers = () => readJson(ANSWER_KEY, {});
export const saveAnswers = (answers) => writeJson(ANSWER_KEY, answers);
export const loadPrefs = () => readJson(PREF_KEY, {});
export const savePrefs = (prefs) => writeJson(PREF_KEY, prefs);

// 회차 데이터(대본·해설, 약 85KB)는 그 회차를 고를 때만 받아옵니다.
export const fetchTest = (id) => fetchCached(`/listening/${id}.json`, id);

// 이어 붙인 음원에서 지금 시각이 몇 번 문항인지 찾습니다 (문항 사이 쉼은 앞 문항에 붙입니다).
function itemAt(items, time) {
  let found = null;
  for (const item of items) {
    if (item.start - 0.1 <= time) found = item;
    else break;
  }
  return found?.no ?? null;
}

// 한 문항을 되풀이할 때 다시 처음으로 돌아가기 전 쉬는 시간(초).
// 음원에는 문항마다 뒤에 2초 무음이 붙어 있어서, 그 무음 안에서 쉬고 돌아갑니다.
const REPEAT_PAUSE = 1.2;

// 회차 음원 하나를 두고 한 문항을 멈출 때까지 되풀이하거나(item), 여러 문항을 이어서 재생합니다(run).
// 둘 다 파일을 그냥 흘려보내므로 화면이 꺼져도 끊기지 않습니다.
export function useClipPlayer(src, items) {
  const audioRef = useRef(null);
  const endRef = useRef(null);
  const loopStartRef = useRef(null);
  const itemsRef = useRef(items);
  const [playing, setPlaying] = useState(null); // { mode: 'item' | 'run', no, round }

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
        if (loopStartRef.current !== null) {
          audio.currentTime = loopStartRef.current;
          setPlaying((prev) => (prev ? { ...prev, round: prev.round + 1 } : prev));
          return;
        }
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
      loopStartRef.current = null;
      setPlaying(null);
    };
  }, [src]);

  const playSpan = useCallback((start, end, mode, no, repeat = false) => {
    const audio = audioRef.current;
    if (!audio) return;
    endRef.current = end;
    loopStartRef.current = repeat ? start : null;
    const seek = () => {
      audio.currentTime = start;
    };
    if (audio.readyState >= 1) seek();
    else audio.addEventListener('loadedmetadata', seek, { once: true });
    setPlaying({ mode, no, round: 1 });
    // play()는 버튼을 누른 그 순간에 불러야 아이폰에서도 소리가 납니다.
    audio.play()?.catch(() => setPlaying(null));
  }, []);

  const playItem = useCallback(
    (item) => playSpan(item.start, item.end + REPEAT_PAUSE, 'item', item.no, true),
    [playSpan]
  );

  const playRun = useCallback(
    (list) => {
      if (!list.length) return;
      playSpan(list[0].start, list[list.length - 1].end + 0.05, 'run', list[0].no);
    },
    [playSpan]
  );

  const stop = useCallback(() => {
    endRef.current = null;
    loopStartRef.current = null;
    audioRef.current?.pause();
  }, []);

  return { playing, playItem, playRun, stop };
}
