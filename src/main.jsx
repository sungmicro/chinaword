import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Eye, Search, Shuffle, Sparkles, Volume2, X } from 'lucide-react';
import vocabData from './data/vocab.json';
import { speakChinese, stopSpeaking, useChineseVoice } from './speech';
import { buildLessonChips, lessonBadge, matchesLessonChip } from './lessons';
import { MINE_LESSON, mineToStudyItems, useMyVocab } from './myVocab';
import Listening from './Listening';
import Reading from './Reading';
import MemorizeScript from './MemorizeScript';
import ToneQuiz from './ToneQuiz';
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

const VIEW_OPTIONS = [
  { key: 'study', label: '랜덤 학습' },
  { key: 'list', label: '단어장' },
  { key: 'memo', label: '암기' },
  { key: 'quiz', label: '시험보기' },
  { key: 'listen', label: '듣기' },
  { key: 'read', label: '독해' }
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

// 성조 부호를 떼서 "ni hao"처럼 검색해도 "nǐ hǎo"가 걸리게 합니다.
function normalizeForSearch(text) {
  return String(text ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\s+/g, '');
}

function lengthClass(text) {
  const size = String(text ?? '').length;
  if (size > 40) return 'textLong';
  if (size > 18) return 'textMedium';
  return 'textShort';
}

// 한자는 한 글자가 정사각형이라 같은 글자 수라도 병음·한글보다 자리를 훨씬 많이 먹습니다.
// 긴 문장이 카드를 넘치지 않도록 한자에만 한 단계 더 작은 구간을 둡니다.
function hanziLengthClass(text) {
  return String(text ?? '').length > 20 ? 'textLong' : lengthClass(text);
}

// 문장(itemType '문장')은 단어보다 글씨를 절반 크기로 표시합니다.
function sentenceModifier(itemType) {
  return itemType === '문장' ? ' sentenceHanzi' : '';
}

// 내 단어장 카드는 담을 때 같이 저장한 용법·설명·예문·출처를 정답과 함께 보여줍니다.
function MineDetails({ card }) {
  if (!card.note && !card.exampleZh && !card.source) return null;
  return (
    <div className="mineDetails">
      {card.note ? <p className="mineNote">{card.note}</p> : null}
      {card.exampleZh ? (
        <div className="mineExample">
          <p className="mineExampleZh">{card.exampleZh}</p>
          {card.examplePinyin ? <p className="vocabPinyin">{card.examplePinyin}</p> : null}
          {card.exampleKo ? <p className="vocabMeaning">{card.exampleKo}</p> : null}
        </div>
      ) : null}
      {card.source ? <p className="mineSource">{card.source}</p> : null}
    </div>
  );
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
        const sizeClass =
          row.type === 'hanzi'
            ? hanziLengthClass(row.value) + sentenceModifier(card.itemType)
            : lengthClass(row.value);

        if (!speakable) {
          return (
            <div className="answerRow" key={row.label}>
              <span>{row.label}</span>
              <strong className={sizeClass}>{row.value}</strong>
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
            <strong className={sizeClass}>{row.value}</strong>
          </button>
        );
      })}
      {card.mineKey ? <MineDetails card={card} /> : null}
    </div>
  );
}

function VocabList({ items, mineItems, onRemoveMine, canSpeak, speakingText, onSpeak }) {
  const [query, setQuery] = useState('');
  const [lesson, setLesson] = useState('전체');

  const lessons = useMemo(() => buildLessonChips(items), [items]);
  // «내 단어장»은 단원이 아니라 내가 담은 목록이라 «전체» 바로 뒤에 따로 둡니다.
  const chips = useMemo(() => [lessons[0], MINE_LESSON, ...lessons.slice(1)], [lessons]);
  const showingMine = lesson === MINE_LESSON;

  const visibleItems = useMemo(() => {
    const needle = normalizeForSearch(query);
    const pool = showingMine ? mineItems : items;

    return pool.filter((item) => {
      if (!showingMine && !matchesLessonChip(item, lesson)) return false;
      if (!needle) return true;
      return (
        normalizeForSearch(item.hanzi).includes(needle) ||
        normalizeForSearch(item.pinyin).includes(needle) ||
        normalizeForSearch(item.meaningKo).includes(needle)
      );
    });
  }, [items, mineItems, showingMine, lesson, query]);

  return (
    <section className="listPanel" aria-label="단어장">
      <div className="listControls">
        <label className="searchBox">
          <Search size={16} />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="한자 · 병음 · 뜻으로 검색 (예: 你好, ni hao, 안녕)"
            aria-label="단어 검색"
          />
        </label>

        <div className="lessonChips" aria-label="단원 선택">
          {chips.map((option) => (
            <button
              key={option}
              type="button"
              className={`lessonChip ${lesson === option ? 'active' : ''}`}
              onClick={() => setLesson(option)}
            >
              {option === MINE_LESSON ? `${MINE_LESSON} ${mineItems.length}` : option}
            </button>
          ))}
        </div>

        <p className="listCount">{visibleItems.length}개</p>
      </div>

      <div className="listBody">
        {visibleItems.length ? (
          <ul className="vocabList">
            {visibleItems.map((item) => {
              const speakable = canSpeak && String(item.hanzi ?? '').trim();
              const badge = lessonBadge(item.lesson);

              const body = (
                <>
                  <div className="vocabTexts">
                    <p className={`vocabHanzi ${hanziLengthClass(item.hanzi)}${sentenceModifier(item.itemType)}`}>{item.hanzi}</p>
                    {item.pinyin ? <p className="vocabPinyin">{item.pinyin}</p> : null}
                    {item.meaningKo ? <p className="vocabMeaning">{item.meaningKo}</p> : null}
                    {item.mineKey && item.note ? <p className="mineNote">{item.note}</p> : null}
                    {item.mineKey && item.exampleZh ? (
                      <p className="mineExampleZh">
                        {item.exampleZh} <span>{item.exampleKo}</span>
                      </p>
                    ) : null}
                    {item.mineKey && item.source ? <p className="mineSource">{item.source}</p> : null}
                  </div>

                  <div className="vocabSide">
                    {badge ? <span className="vocabTag vocabLessonTag">{badge}</span> : null}
                    <span className="vocabTag">{item.itemType}</span>
                    {speakable ? <Volume2 className="vocabSpeakIcon" size={20} /> : null}
                  </div>
                </>
              );

              return (
                <li key={item.id} className={item.mineKey ? 'mineRow' : undefined}>
                  {speakable ? (
                    <button
                      type="button"
                      className={`vocabRow vocabRowSpeak ${speakingText === item.hanzi ? 'speaking' : ''}`}
                      onClick={() => onSpeak(item.hanzi)}
                      aria-label={`${item.hanzi} 발음 듣기`}
                    >
                      {body}
                    </button>
                  ) : (
                    <div className="vocabRow">{body}</div>
                  )}
                  {item.mineKey ? (
                    <button
                      type="button"
                      className="mineRemove"
                      onClick={() => onRemoveMine(item.mineKey)}
                      aria-label={`${item.hanzi} 내 단어장에서 빼기`}
                    >
                      <X size={14} /> 빼기
                    </button>
                  ) : null}
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="listEmpty">
            {showingMine && !mineItems.length ? '해설에서 ＋ 담기를 누르면 여기에 모여요.' : '검색 결과가 없어요.'}
          </p>
        )}
      </div>
    </section>
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

function StudyCard({ card, promptType, revealed, onReveal, onNext, canSpeak, speaking, onSpeak, mineToggle }) {
  const promptText = card?.[promptType] || '';
  // 뜻만 보고 맞히는 중이면 발음이 정답을 알려주므로, 정답을 연 뒤에만 읽어줍니다.
  const promptSpeakable = canSpeak && promptType !== 'meaningKo';
  const promptClassName = `promptText prompt-${promptType} ${
    promptType === 'hanzi'
      ? hanziLengthClass(promptText) + sentenceModifier(card?.itemType)
      : lengthClass(promptText)
  }`;

  return (
    <section className={`studyCard ${revealed ? 'revealed' : ''}`} aria-label="랜덤 학습 카드">
      <div className="cardMeta">
        <span>{card.itemType}</span>
        {mineToggle}
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
  const mine = useMyVocab();
  const mineItems = useMemo(() => mineToStudyItems(mine.items), [mine.items]);
  const [mineOnly, setMineOnly] = useState(() => loadJson('sungmi-vocab-study-mine-v1', false) === true);
  // 담은 것이 없으면 «내 단어장만»은 켜지지 않습니다. 켜 둔 채 마지막 항목을 빼면 꺼집니다.
  const studyMine = mineOnly && mineItems.length > 0;
  const pool = studyMine ? mineItems : studyItems;
  const [todayCountState, setTodayCountState] = useState(() =>
    loadJson('sungmi-vocab-daily-count-v4', { day: studyDayKey(), count: 0 })
  );
  const [promptMode, setPromptMode] = useState(() =>
    loadJson('sungmi-vocab-prompt-mode-v1', 'random')
  );
  const [currentIndex, setCurrentIndex] = useState(() => randomIndex(pool.length));
  const [promptType, setPromptType] = useState(() => resolvePromptType(pool[currentIndex], promptMode));
  const [revealed, setRevealed] = useState(false);
  const [speakingText, setSpeakingText] = useState(null);
  const [view, setView] = useState(() => loadJson('sungmi-vocab-view-v1', 'study'));
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

  useEffect(() => {
    saveJson('sungmi-vocab-view-v1', view);
  }, [view]);

  useEffect(() => {
    if (mineOnly && !mineItems.length) setMineOnly(false);
  }, [mineOnly, mineItems.length]);

  useEffect(() => {
    saveJson('sungmi-vocab-study-mine-v1', mineOnly);
  }, [mineOnly]);

  const currentCard = pool[currentIndex] ?? pool[0];
  // 카드가 바뀌었는데(예: 내 단어장에서 뺌) 출제 칸이 비어 있으면 있는 칸으로 보여줍니다.
  const cardPrompts = availablePromptTypes(currentCard);
  const shownPrompt = cardPrompts.includes(promptType) ? promptType : cardPrompts[0] ?? 'hanzi';
  const hasChineseVoice = Boolean(chineseVoice);
  const canSpeak = hasChineseVoice && Boolean(String(currentCard?.hanzi ?? '').trim());

  const handleSpeak = useCallback((text) => {
    speakChinese(text, {
      onStart: () => setSpeakingText(text),
      onEnd: () => setSpeakingText(null)
    });
  }, []);

  // 카드를 넘기거나 탭을 옮기면 이전 음성은 끊습니다.
  useEffect(() => {
    stopSpeaking();
    setSpeakingText(null);
  }, [currentIndex, view]);

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
    const nextIndex = randomIndex(pool.length, currentIndex);
    const nextCard = pool[nextIndex];
    setCurrentIndex(nextIndex);
    setPromptType(resolvePromptType(nextCard, promptMode));
    setRevealed(false);
    setTodayCountState((prev) => {
      const normalized = prev.day === todayKey ? prev : { day: todayKey, count: 0 };
      return { ...normalized, count: normalized.count + 1 };
    });
  }

  function toggleMineOnly() {
    const next = !studyMine;
    const nextPool = next ? mineItems : studyItems;
    const nextIndex = randomIndex(nextPool.length);
    setMineOnly(next);
    setCurrentIndex(nextIndex);
    setPromptType(resolvePromptType(nextPool[nextIndex], promptMode));
    setRevealed(false);
  }

  useEffect(() => {
    function handleKeydown(event) {
      // 단어장 탭에서는 검색 입력을 방해하지 않도록 단축키를 끕니다.
      if (view !== 'study') return;
      // 버튼에 포커스가 있을 때의 Enter는 그 버튼이 처리하게 둡니다.
      if (event.key === 'Enter' && event.target instanceof HTMLButtonElement) return;

      if (event.key === ' ' || event.key === 'Enter') {
        event.preventDefault();
        if (revealed) moveNext();
        else setRevealed(true);
        return;
      }

      if ((event.key === 's' || event.key === 'S') && canSpeak && (shownPrompt !== 'meaningKo' || revealed)) {
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

        <div className="viewTabs" role="tablist" aria-label="화면 선택">
          {VIEW_OPTIONS.map((option) => (
            <button
              key={option.key}
              type="button"
              role="tab"
              aria-selected={view === option.key}
              className={`viewTab ${view === option.key ? 'active' : ''}`}
              onClick={() => setView(option.key)}
            >
              {option.label}
            </button>
          ))}
        </div>

        {view === 'study' ? (
          <PromptModeButtons promptMode={promptMode} onChange={changePromptMode} />
        ) : null}

        {voiceChecked && !chineseVoice ? (
          <p className="voiceNotice">
            {speechSupported
              ? '이 기기에 중국어 음성이 없어 발음 듣기가 꺼져 있어요. 설정 → 접근성 → 텍스트 음성 변환에서 중국어(간체) 음성을 설치하면 켜집니다.'
              : '이 브라우저는 음성 읽기를 지원하지 않아요. 크롬이나 사파리에서 열어보세요.'}
          </p>
        ) : null}
      </header>

      {view === 'study' ? (
        <StudyCard
          card={currentCard}
          promptType={shownPrompt}
          revealed={revealed}
          onReveal={() => setRevealed(true)}
          onNext={moveNext}
          canSpeak={canSpeak}
          speaking={Boolean(speakingText)}
          onSpeak={handleSpeak}
          mineToggle={
            <button
              type="button"
              className={`mineOnlyToggle${studyMine ? ' active' : ''}`}
              onClick={toggleMineOnly}
              disabled={!mineItems.length}
              aria-pressed={studyMine}
            >
              내 단어장만 {mineItems.length}
            </button>
          }
        />
      ) : view === 'list' ? (
        <VocabList
          items={studyItems}
          mineItems={mineItems}
          onRemoveMine={mine.remove}
          canSpeak={hasChineseVoice}
          speakingText={speakingText}
          onSpeak={handleSpeak}
        />
      ) : view === 'memo' ? (
        <MemorizeScript canSpeak={hasChineseVoice} />
      ) : view === 'listen' ? (
        <Listening />
      ) : view === 'read' ? (
        <Reading />
      ) : (
        <ToneQuiz items={studyItems} canSpeak={hasChineseVoice} onSpeak={handleSpeak} />
      )}

      <p className="keyboardHint">
        {view === 'study'
          ? 'Space 또는 Enter: 정답 보기 / 다음 카드 · S: 발음 듣기'
          : view === 'list'
            ? '단어를 누르면 발음이 재생됩니다'
            : view === 'memo'
              ? '문장을 누르면 재생됩니다 · 이어서 재생하면 한 줄씩 쉬어가며 들려줍니다'
              : view === 'listen'
                ? '문제 듣기는 멈춤을 누를 때까지 되풀이합니다 · 이어 듣기는 화면을 꺼도 계속 재생됩니다'
                : view === 'read'
                  ? '답을 고르면 정답 근거·끊어 읽기·단어·문법이 열립니다 · ＋ 담기로 내 단어장에 모아요'
                  : '한자를 보고 들으면서 성조가 맞는 병음을 고르세요'}
      </p>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
