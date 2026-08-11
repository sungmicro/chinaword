import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Pause, Play, Volume2 } from 'lucide-react';
import script from './data/intro-script.json';
import { speakChinese, stopSpeaking } from './speech';

// 따라 말하기용 화면. 한 줄 재생이 끝나면 그 줄을 말한 시간만큼 쉬었다가 다음 줄로 넘어갑니다.
// 쉬는 동안 사용자가 같은 문장을 따라 말합니다.

const PREF_KEY = 'sungmi-vocab-memorize-v1';
const SLOW_RATE = 0.6;
const NORMAL_RATE = 0.85;
const MIN_GAP_MS = 700;
const EXTRA_GAP_MS = 350;

function loadPrefs() {
  try {
    const saved = localStorage.getItem(PREF_KEY);
    const parsed = saved ? JSON.parse(saved) : null;
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function savePrefs(prefs) {
  try {
    localStorage.setItem(PREF_KEY, JSON.stringify(prefs));
  } catch {
    // 저장 실패가 학습을 막을 이유는 없습니다.
  }
}

// 선택한 구간의 줄들을 원문 순서 그대로 펼칩니다.
function flattenLines(sectionId) {
  const sections =
    sectionId === '전체' ? script.sections : script.sections.filter((s) => s.id === sectionId);

  return sections.flatMap((section) =>
    section.lines.map((line, index) => ({
      ...line,
      key: `${section.id}-${index}`,
      sectionTitle: section.title
    }))
  );
}

export default function MemorizeScript({ canSpeak }) {
  const initial = loadPrefs();
  const [sectionId, setSectionId] = useState(initial.sectionId ?? '전체');
  const [showPinyin, setShowPinyin] = useState(initial.showPinyin ?? true);
  const [showKo, setShowKo] = useState(initial.showKo ?? true);
  const [slow, setSlow] = useState(initial.slow ?? false);
  const [activeKey, setActiveKey] = useState(null);
  const [playing, setPlaying] = useState(false);

  const lines = useMemo(() => flattenLines(sectionId), [sectionId]);

  const playingRef = useRef(false);
  const timerRef = useRef(null);
  const linesRef = useRef(lines);
  linesRef.current = lines;

  useEffect(() => {
    savePrefs({ sectionId, showPinyin, showKo, slow });
  }, [sectionId, showPinyin, showKo, slow]);

  const stop = useCallback(() => {
    playingRef.current = false;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
    stopSpeaking();
    setPlaying(false);
    setActiveKey(null);
  }, []);

  // 화면을 벗어나거나 구간을 바꾸면 재생을 멈춥니다.
  useEffect(() => stop, [stop]);
  useEffect(() => {
    stop();
  }, [sectionId, stop]);

  const rate = slow ? SLOW_RATE : NORMAL_RATE;

  const playFrom = useCallback(
    (index) => {
      const list = linesRef.current;
      if (!playingRef.current) return;
      if (index >= list.length) {
        stop();
        return;
      }

      const line = list[index];
      setActiveKey(line.key);
      const startedAt = Date.now();

      speakChinese(line.hanzi, {
        rate,
        onEnd: () => {
          if (!playingRef.current) return;
          // 말하는 데 걸린 만큼 쉬어서 따라 말할 시간을 줍니다.
          const spokenMs = Date.now() - startedAt;
          const gap = Math.max(MIN_GAP_MS, spokenMs + EXTRA_GAP_MS);
          timerRef.current = setTimeout(() => playFrom(index + 1), gap);
        }
      });
    },
    [rate, stop]
  );

  function togglePlay() {
    if (playing) {
      stop();
      return;
    }
    playingRef.current = true;
    setPlaying(true);
    playFrom(0);
  }

  function speakOne(line) {
    stop();
    setActiveKey(line.key);
    speakChinese(line.hanzi, { rate, onEnd: () => setActiveKey(null) });
  }

  const chips = ['전체', ...script.sections.map((section) => section.id)];
  const chipLabel = (id) =>
    id === '전체' ? '전체' : script.sections.find((section) => section.id === id)?.label ?? id;

  return (
    <section className="memoPanel" aria-label="자기소개 암기">
      <div className="memoControls">
        <div className="lessonChips" aria-label="구간 선택">
          {chips.map((id) => (
            <button
              key={id}
              type="button"
              className={`lessonChip ${sectionId === id ? 'active' : ''}`}
              onClick={() => setSectionId(id)}
            >
              {chipLabel(id)}
            </button>
          ))}
        </div>

        <div className="memoToolbar">
          {canSpeak ? (
            <button
              type="button"
              className={`memoPlay ${playing ? 'active' : ''}`}
              onClick={togglePlay}
            >
              {playing ? <Pause size={16} /> : <Play size={16} />}
              {playing ? '정지' : '이어서 재생'}
            </button>
          ) : null}

          <div className="memoToggles">
            {canSpeak ? (
              <button
                type="button"
                className={`memoToggle ${slow ? 'active' : ''}`}
                onClick={() => setSlow(!slow)}
              >
                느리게
              </button>
            ) : null}
            <button
              type="button"
              className={`memoToggle ${showPinyin ? 'active' : ''}`}
              onClick={() => setShowPinyin(!showPinyin)}
            >
              병음
            </button>
            <button
              type="button"
              className={`memoToggle ${showKo ? 'active' : ''}`}
              onClick={() => setShowKo(!showKo)}
            >
              뜻
            </button>
          </div>
        </div>
      </div>

      <div className="memoBody">
        <ol className="memoList">
          {lines.map((line) => {
            const active = activeKey === line.key;
            const content = (
              <div className="memoTexts">
                <p className="memoHanzi">{line.hanzi}</p>
                {showPinyin ? <p className="memoPinyin">{line.pinyin}</p> : null}
                {showKo ? <p className="memoKo">{line.ko}</p> : null}
              </div>
            );

            return (
              <li key={line.key}>
                {canSpeak ? (
                  <button
                    type="button"
                    className={`memoRow ${active ? 'speaking' : ''}`}
                    onClick={() => speakOne(line)}
                    aria-label={`${line.hanzi} 발음 듣기`}
                  >
                    {content}
                    <Volume2 className="memoSpeakIcon" size={18} />
                  </button>
                ) : (
                  <div className="memoRow">{content}</div>
                )}
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
