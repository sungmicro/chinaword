import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Eye, Shuffle, Sparkles, Volume2 } from 'lucide-react';
import vocabData from './data/vocab.json';
import { speakChinese, stopSpeaking, useChineseVoice } from './speech';
import './styles.css';

const PROMPT_TYPES = ['hanzi', 'pinyin', 'meaningKo'];

const PROMPT_LABELS = {
  hanzi: '중국어',
  pinyin: '한어병음',
  meaningKo: '한글 뜻'
};

const MODE_OPTIONS = [
  { key: 'random', label: '랜덤' },
  { key: 'hanzi', label: '한자만' },
  { key: 'pinyin', label: '병음만' },
  { key: 'meaningKo', label: '뜻만' }
];

function loadJson(key, fallback) {
  try {
    const saved = localStorage.getItem(key);
    return saved ? JSON.parse(saved) : fallback;
  } catch {
    return fallback;
  }
}

function saveJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function studyDayKey(date = new Date()) {
  // 성미님 기준: 하루는 새벽 5시에 시작합니다.
  const shifted = new Date(date.getTime() - 5 * 60 * 60 * 1000);
  const year = shifted.getFullYear();
  const month = String(shifted.getMonth() + 1).padStart(2, '0');
  const day = String(shifted.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function inferItemType(card) {
  const values = [card.itemType, card.category, card.partOfSpeech].filter(Boolean).join(' ');
  if (/문장|sentence/i.test(values)) return '문장';
  if (/패턴|문법|grammar|pattern/i.test(values)) return '패턴';
  if (/표현|phrase|expression|인사/i.test(values)) return '표현';
  return '단어';
}

function buildStudyItems(rawData) {
  return rawData
    .map((card, index) => ({
      ...card,
      id: String(card.id ?? index + 1),
      itemType: card.itemType ?? inferItemType(card),
      hanzi: card.hanzi ?? card.zh ?? card.chinese ?? '',
      pinyin: card.pinyin ?? '',
      meaningKo: card.meaningKo ?? card.meaning ?? card.korean ?? ''
    }))
    .filter((card) => card.hanzi || card.pinyin || card.meaningKo);
}

function randomIndex(length, previousIndex = -1) {
  if (length <= 1) return 0;
  let nextIndex = Math.floor(Math.random() * length);
  while (nextIndex === previousIndex) {
    nextIndex = Math.floor(Math.random() * length);
  }
  return nextIndex;
}

function availablePromptTypes(card) {
  return PROMPT_TYPES.filter((type) => String(card?.[type] ?? '').trim());
}

function randomPromptType(card) {
  const availableTypes = availablePromptTypes(card);
  const types = availableTypes.length ? availableTypes : PROMPT_TYPES;
  return types[Math.floor(Math.random() * types.length)];
}

function resolvePromptType(card, mode) {
  if (mode === 'random') return randomPromptType(card);
  if (String(card?.[mode] ?? '').trim()) return mode;
  return randomPromptType(card);
}

function typeBreakdown(items) {
  const counts = items.reduce((acc, item) => {
    acc[item.itemType] = (acc[item.itemType] ?? 0) + 1;
    return acc;
  }, {});

  return ['단어', '표현', '문장', '패턴']
    .filter((type) => counts[type])
    .map((type) => `${type} ${counts[type]}개`)
    .join(' · ');
}

function lengthClass(text) {
  const size = String(text ?? '').length;
  if (size > 40) return 'textLong';
  if (size > 18) return 'textMedium';
  return 'textShort';
}

function HiddenAnswer({ card, promptType, canSpeak, speaking, onSpeak }) {
  const answerRows = PROMPT_TYPES
    .filter((type) => type !== promptType)
    .map((type) => ({ type, label: PROMPT_LABELS[type], value: card[type] }))
    .filter((row) => String(row.value ?? '').trim());

  return (
    <div className="answerPanel">
      {answerRows.map((row) => {
        const speakable = canSpeak && row.type === 'hanzi';

        if (!speakable) {
          return (
            <div className="answerRow" key={row.label}>
              <span>{row.label}</span>
              <strong className={lengthClass(row.value)}>{row.value}</strong>
            </div>
          );
        }

        return (
          <button
            type="button"
            key={row.label}
            className={`answerRow answerRowSpeak ${speaking ? 'speaking' : ''}`}
            onClick={() => onSpeak(card.hanzi)}
            aria-label={`${row.value} 발음 듣기`}
          >
            <span>
              {row.label} <Volume2 size={12} /> 눌러서 듣기
            </span>
            <strong className={lengthClass(row.value)}>{row.value}</strong>
          </button>
        );
      })}
    </div>
  );
}

function PromptModeButtons({ promptMode, onChange }) {
  return (
    <div className="modeControls" aria-label="출제 모드 선택">
      {MODE_OPTIONS.map((option) => (
        <button
          key={option.key}
          type="button"
          className={`modeButton ${promptMode === option.key ? 'active' : ''}`}
          onClick={() => onChange(option.key)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function StudyCard({ card, promptType, revealed, onReveal, onNext, canSpeak, speaking, onSpeak }) {
  const promptText = card?.[promptType] || '';
  // 뜻만 보고 맞히는 중이면 발음이 정답을 알려주므로, 정답을 연 뒤에만 읽어줍니다.
  const promptSpeakable = canSpeak && promptType !== 'meaningKo';
  const promptClassName = `promptText prompt-${promptType} ${lengthClass(promptText)}`;

  return (
    <section className={`studyCard ${revealed ? 'revealed' : ''}`} aria-label="랜덤 학습 카드">
      <div className="cardMeta">
        <span>{card.itemType}</span>
        <span>출제: {PROMPT_LABELS[promptType]}</span>
      </div>

      <div className="promptArea">
        <p className="promptLabel">먼저 보고 맞혀보세요</p>
        {promptSpeakable ? (
          <button
            type="button"
            className={`${promptClassName} speakablePrompt ${speaking ? 'speaking' : ''}`}
            onClick={() => onSpeak(card.hanzi)}
            aria-label={`${promptText} 발음 듣기`}
          >
            {promptText}
          </button>
        ) : (
          <h2 className={promptClassName}>{promptText}</h2>
        )}
        {promptSpeakable ? (
          <p className="speakHint">
            <Volume2 size={13} /> 눌러서 발음 듣기
          </p>
        ) : null}
      </div>

      {revealed ? (
        <HiddenAnswer
          card={card}
          promptType={promptType}
          canSpeak={canSpeak}
          speaking={speaking}
          onSpeak={onSpeak}
        />
      ) : (
        <div className="hiddenGuide">정답을 떠올린 뒤 버튼을 눌러 확인하세요.</div>
      )}

      <div className="primaryActions">
        {!revealed ? (
          <button className="mainButton" onClick={onReveal}>
            <Eye size={18} /> 정답 보기
          </button>
        ) : (
          <button className="mainButton" onClick={onNext}>
            <Shuffle size={18} /> 다음 카드
          </button>
        )}
      </div>
    </section>
  );
}

function App() {
  const studyItems = useMemo(() => buildStudyItems(vocabData), []);
  const [todayCountState, setTodayCountState] = useState(() =>
    loadJson('sungmi-vocab-daily-count-v4', { day: studyDayKey(), count: 0 })
  );
  const [promptMode, setPromptMode] = useState(() =>
    loadJson('sungmi-vocab-prompt-mode-v1', 'random')
  );
  const [currentIndex, setCurrentIndex] = useState(() => randomIndex(studyItems.length));
  const [promptType, setPromptType] = useState(() =>
    resolvePromptType(studyItems[currentIndex], promptMode)
  );
  const [revealed, setRevealed] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const { supported: speechSupported, checked: voiceChecked, voice: chineseVoice } = useChineseVoice();

  const todayKey = studyDayKey();
  const todayCount = todayCountState.day === todayKey ? todayCountState.count : 0;

  useEffect(() => {
    if (todayCountState.day !== todayKey) {
      setTodayCountState({ day: todayKey, count: 0 });
    }
  }, [todayCountState.day, todayKey]);

  useEffect(() => {
    saveJson('sungmi-vocab-daily-count-v4', todayCountState);
  }, [todayCountState]);

  useEffect(() => {
    saveJson('sungmi-vocab-prompt-mode-v1', promptMode);
  }, [promptMode]);

  const currentCard = studyItems[currentIndex] ?? studyItems[0];
  const canSpeak = Boolean(chineseVoice && String(currentCard?.hanzi ?? '').trim());

  const handleSpeak = useCallback((text) => {
    speakChinese(text, {
      onStart: () => setSpeaking(true),
      onEnd: () => setSpeaking(false)
    });
  }, []);

  // 카드가 바뀌면 이전 카드 음성은 끊습니다.
  useEffect(() => {
    stopSpeaking();
    setSpeaking(false);
  }, [currentIndex]);

  const statsText = useMemo(() => {
    const breakdown = typeBreakdown(studyItems);
    return `전체 ${studyItems.length}개 · ${breakdown} · 오늘 넘긴 카드 ${todayCount}장`;
  }, [studyItems, todayCount]);

  function changePromptMode(nextMode) {
    setPromptMode(nextMode);
    setPromptType(resolvePromptType(currentCard, nextMode));
    setRevealed(false);
  }

  function moveNext() {
    const nextIndex = randomIndex(studyItems.length, currentIndex);
    const nextCard = studyItems[nextIndex];
    setCurrentIndex(nextIndex);
    setPromptType(resolvePromptType(nextCard, promptMode));
    setRevealed(false);
    setTodayCountState((prev) => {
      const normalized = prev.day === todayKey ? prev : { day: todayKey, count: 0 };
      return { ...normalized, count: normalized.count + 1 };
    });
  }

  useEffect(() => {
    function handleKeydown(event) {
      // 버튼에 포커스가 있을 때의 Enter는 그 버튼이 처리하게 둡니다.
      if (event.key === 'Enter' && event.target instanceof HTMLButtonElement) return;

      if (event.key === ' ' || event.key === 'Enter') {
        event.preventDefault();
        if (revealed) moveNext();
        else setRevealed(true);
        return;
      }

      if ((event.key === 's' || event.key === 'S') && canSpeak && (promptType !== 'meaningKo' || revealed)) {
        event.preventDefault();
        handleSpeak(currentCard.hanzi);
      }
    }

    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
  });

  if (!currentCard) {
    return (
      <main className="appShell">
        <section className="emptyState">
          <h1>표시할 단어가 없습니다</h1>
          <p><code>src/data/vocab.json</code> 파일에 단어를 추가해 주세요.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="appShell">
      <header className="hero">
        <div className="topLine">
          <p className="eyebrow">Chinese Drill</p>
          <p className="headerStats"><Sparkles size={14} /> {statsText}</p>
        </div>
        <h1>중국어 단어를 외워보자😆</h1>
        <PromptModeButtons promptMode={promptMode} onChange={changePromptMode} />
        {voiceChecked && !chineseVoice ? (
          <p className="voiceNotice">
            {speechSupported
              ? '이 기기에 중국어 음성이 없어 발음 듣기가 꺼져 있어요. 설정 → 접근성 → 텍스트 음성 변환에서 중국어(간체) 음성을 설치하면 켜집니다.'
              : '이 브라우저는 음성 읽기를 지원하지 않아요. 크롬이나 사파리에서 열어보세요.'}
          </p>
        ) : null}
      </header>

      <StudyCard
        card={currentCard}
        promptType={promptType}
        revealed={revealed}
        onReveal={() => setRevealed(true)}
        onNext={moveNext}
        canSpeak={canSpeak}
        speaking={speaking}
        onSpeak={handleSpeak}
      />

      <p className="keyboardHint">Space 또는 Enter: 정답 보기 / 다음 카드 · S: 발음 듣기</p>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
