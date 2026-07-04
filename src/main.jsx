import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  BookOpen,
  CheckCircle2,
  Eye,
  EyeOff,
  Filter,
  RotateCcw,
  Search,
  Shuffle,
  Sparkles,
  Star,
  XCircle
} from 'lucide-react';
import vocabData from './data/vocab.json';
import './styles.css';

const PROGRESS_KEY = 'sungmi-vocab-progress-v2';
const SESSION_KEY = 'sungmi-vocab-session-count-v2';
const PROMPT_TYPES = ['hanzi', 'pinyin', 'meaningKo'];

const PROMPT_LABELS = {
  hanzi: '중국어',
  pinyin: '한어병음',
  meaningKo: '한글 뜻'
};

function uniqueValues(items, key) {
  return [...new Set(items.map((item) => item[key]).filter(Boolean))];
}

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

function normalize(text) {
  return String(text ?? '').toLowerCase().replace(/\s+/g, ' ').trim();
}

function inferItemType(card) {
  const category = card.category ?? '';
  const partOfSpeech = card.partOfSpeech ?? '';

  if ([category, partOfSpeech].some((value) => /문장|sentence/i.test(value))) return '문장';
  if ([category, partOfSpeech].some((value) => /표현|인사|phrase|expression/i.test(value))) return '표현';
  if ([category, partOfSpeech].some((value) => /문법|조사|grammar/i.test(value))) return '문법';
  return '단어';
}

function buildStudyItems(rawData) {
  const primaryItems = rawData.map((card) => ({
    ...card,
    id: String(card.id),
    itemType: card.itemType ?? inferItemType(card),
    sourceWord: null
  }));

  const sentenceItems = rawData
    .filter((card) => card.exampleZh && card.examplePinyin && card.exampleKo)
    .map((card) => ({
      id: `${card.id}-sentence`,
      level: card.level,
      lesson: card.lesson,
      category: '예문',
      itemType: '문장',
      hanzi: card.exampleZh,
      pinyin: card.examplePinyin,
      meaningKo: card.exampleKo,
      partOfSpeech: '문장',
      exampleZh: '',
      examplePinyin: '',
      exampleKo: '',
      sourceWord: card.hanzi,
      sourcePinyin: card.pinyin,
      sourceMeaning: card.meaningKo,
      tags: [...(card.tags ?? []), '예문']
    }));

  return [...primaryItems, ...sentenceItems];
}

function randomIndex(length, previousIndex = -1) {
  if (length <= 1) return 0;

  let nextIndex = Math.floor(Math.random() * length);
  while (nextIndex === previousIndex) {
    nextIndex = Math.floor(Math.random() * length);
  }
  return nextIndex;
}

function randomPromptType() {
  return PROMPT_TYPES[Math.floor(Math.random() * PROMPT_TYPES.length)];
}

function getPromptText(card, promptType) {
  return card?.[promptType] || '';
}

function HiddenAnswer({ card, promptType }) {
  const answerRows = PROMPT_TYPES
    .filter((type) => type !== promptType)
    .map((type) => ({ label: PROMPT_LABELS[type], value: card[type] }));

  return (
    <div className="answerPanel">
      <p className="answerTitle">정답 확인</p>
      <div className="answerRows">
        {answerRows.map((row) => (
          <div className="answerRow" key={row.label}>
            <span>{row.label}</span>
            <strong>{row.value}</strong>
          </div>
        ))}
      </div>

      {card.sourceWord && (
        <div className="sourceBox">
          <span>이 문장이 포함한 원 단어</span>
          <strong>{card.sourceWord}</strong>
          <em>{card.sourcePinyin} · {card.sourceMeaning}</em>
        </div>
      )}

      {!card.sourceWord && card.exampleZh && (
        <div className="exampleBox">
          <span>예문</span>
          <p className="exampleZh">{card.exampleZh}</p>
          <p className="examplePinyin">{card.examplePinyin}</p>
          <p className="exampleKo">{card.exampleKo}</p>
        </div>
      )}
    </div>
  );
}

function StudyCard({ card, promptType, revealed, progress, onReveal, onNext, onMark }) {
  const status = progress[card.id];
  const promptText = getPromptText(card, promptType);

  return (
    <section className={`studyCard ${revealed ? 'revealed' : ''}`} aria-label="랜덤 학습 카드">
      <div className="cardMeta">
        <span className="pill strong">{card.itemType}</span>
        <span className="pill">{card.level}</span>
        <span className="pill muted">{card.lesson}</span>
        <span className="pill muted">출제: {PROMPT_LABELS[promptType]}</span>
      </div>

      <div className="promptArea">
        <p className="promptLabel">먼저 보고 맞혀보세요</p>
        <h2 className={`promptText prompt-${promptType}`}>{promptText}</h2>
      </div>

      {revealed ? (
        <HiddenAnswer card={card} promptType={promptType} />
      ) : (
        <div className="hiddenGuide">
          <EyeOff size={20} />
          <span>아래 버튼을 누르면 나머지 정보가 열립니다.</span>
        </div>
      )}

      <div className="primaryActions">
        {!revealed ? (
          <button className="mainButton" onClick={onReveal}>
            <Eye size={18} /> 정답 보기
          </button>
        ) : (
          <button className="mainButton" onClick={onNext}>
            <Shuffle size={18} /> 다음 랜덤 카드
          </button>
        )}
      </div>

      <div className="reviewActions">
        <button
          className={`miniButton ${status === 'known' ? 'activeKnown' : ''}`}
          onClick={() => onMark(card.id, status === 'known' ? null : 'known')}
        >
          <CheckCircle2 size={16} /> 알아요
        </button>
        <button
          className={`miniButton ${status === 'review' ? 'activeReview' : ''}`}
          onClick={() => onMark(card.id, status === 'review' ? null : 'review')}
        >
          <Star size={16} /> 복습 필요
        </button>
      </div>
    </section>
  );
}

function App() {
  const studyItems = useMemo(() => buildStudyItems(vocabData), []);
  const [query, setQuery] = useState('');
  const [level, setLevel] = useState('전체');
  const [lesson, setLesson] = useState('전체');
  const [itemType, setItemType] = useState('전체');
  const [statusFilter, setStatusFilter] = useState('전체');
  const [progress, setProgress] = useState(() => loadJson(PROGRESS_KEY, {}));
  const [sessionCount, setSessionCount] = useState(() => loadJson(SESSION_KEY, 0));
  const [currentIndex, setCurrentIndex] = useState(0);
  const [promptType, setPromptType] = useState(randomPromptType);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    saveJson(PROGRESS_KEY, progress);
  }, [progress]);

  useEffect(() => {
    saveJson(SESSION_KEY, sessionCount);
  }, [sessionCount]);

  const levels = useMemo(() => ['전체', ...uniqueValues(studyItems, 'level')], [studyItems]);
  const lessons = useMemo(() => ['전체', ...uniqueValues(studyItems, 'lesson')], [studyItems]);
  const itemTypes = useMemo(() => ['전체', ...uniqueValues(studyItems, 'itemType')], [studyItems]);

  const filteredItems = useMemo(() => {
    const q = normalize(query);

    return studyItems.filter((card) => {
      const matchesQuery = !q || [
        card.hanzi,
        card.pinyin,
        card.meaningKo,
        card.exampleZh,
        card.examplePinyin,
        card.exampleKo,
        card.category,
        card.itemType,
        card.partOfSpeech,
        card.sourceWord,
        card.sourcePinyin,
        card.sourceMeaning,
        ...(card.tags ?? [])
      ].some((value) => normalize(value).includes(q));

      const matchesLevel = level === '전체' || card.level === level;
      const matchesLesson = lesson === '전체' || card.lesson === lesson;
      const matchesType = itemType === '전체' || card.itemType === itemType;
      const matchesStatus = statusFilter === '전체' || progress[card.id] === statusFilter;

      return matchesQuery && matchesLevel && matchesLesson && matchesType && matchesStatus;
    });
  }, [studyItems, query, level, lesson, itemType, statusFilter, progress]);

  const currentCard = filteredItems[currentIndex] ?? filteredItems[0];

  useEffect(() => {
    if (currentIndex >= filteredItems.length) {
      setCurrentIndex(0);
      setRevealed(false);
      setPromptType(randomPromptType());
    }
  }, [filteredItems.length, currentIndex]);

  useEffect(() => {
    function handleKeydown(event) {
      if (event.key === ' ' || event.key === 'Enter') {
        event.preventDefault();
        if (revealed) moveNext();
        else setRevealed(true);
      }
    }

    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
  });

  const stats = useMemo(() => {
    const known = Object.values(progress).filter((value) => value === 'known').length;
    const review = Object.values(progress).filter((value) => value === 'review').length;
    const words = studyItems.filter((card) => card.itemType === '단어').length;
    const sentences = studyItems.filter((card) => card.itemType === '문장').length;
    return { total: studyItems.length, words, sentences, known, review };
  }, [progress, studyItems]);

  function moveNext() {
    setCurrentIndex((prev) => randomIndex(filteredItems.length, prev));
    setPromptType(randomPromptType());
    setRevealed(false);
    setSessionCount((prev) => prev + 1);
  }

  function markCard(id, value) {
    setProgress((prev) => {
      const next = { ...prev };
      if (!value) delete next[id];
      else next[id] = value;
      return next;
    });
  }

  function resetProgress() {
    setProgress({});
    setSessionCount(0);
  }

  function resetFilters() {
    setQuery('');
    setLevel('전체');
    setLesson('전체');
    setItemType('전체');
    setStatusFilter('전체');
    setCurrentIndex(0);
    setRevealed(false);
    setPromptType(randomPromptType());
  }

  return (
    <main className="appShell">
      <section className="hero">
        <div>
          <p className="eyebrow">Sungmi Chinese Random Drill</p>
          <h1>성미 중국어 랜덤 카드</h1>
          <p className="heroText">
            한자, 한어병음, 한글 뜻 중 하나가 무작위로 먼저 나오고, 정답 보기를 누르면 나머지 정보가 열립니다.
            단어와 예문 문장이 함께 랜덤 출제됩니다.
          </p>
        </div>
        <div className="heroBadge">
          <BookOpen size={26} />
          <strong>{stats.total}</strong>
          <span>items</span>
        </div>
      </section>

      <section className="statsGrid" aria-label="학습 현황">
        <div className="statCard">
          <span>전체 항목</span>
          <strong>{stats.total}</strong>
        </div>
        <div className="statCard">
          <span>단어 / 표현</span>
          <strong>{stats.words}</strong>
        </div>
        <div className="statCard">
          <span>문장</span>
          <strong>{stats.sentences}</strong>
        </div>
        <div className="statCard">
          <span>오늘 넘긴 카드</span>
          <strong>{sessionCount}</strong>
        </div>
      </section>

      <section className="toolbar" aria-label="검색 및 필터">
        <label className="searchBox">
          <Search size={18} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="한자, 병음, 뜻, 문장 검색"
          />
        </label>

        <select value={level} onChange={(event) => setLevel(event.target.value)}>
          {levels.map((item) => <option key={item}>{item}</option>)}
        </select>

        <select value={lesson} onChange={(event) => setLesson(event.target.value)}>
          {lessons.map((item) => <option key={item}>{item}</option>)}
        </select>

        <select value={itemType} onChange={(event) => setItemType(event.target.value)}>
          {itemTypes.map((item) => <option key={item}>{item === '전체' ? '전체 유형' : item}</option>)}
        </select>

        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="전체">전체 상태</option>
          <option value="known">알아요</option>
          <option value="review">복습 필요</option>
        </select>

        <button className="toolButton secondary" onClick={resetFilters}>
          <Filter size={16} /> 필터 초기화
        </button>

        <button className="toolButton secondary" onClick={resetProgress}>
          <RotateCcw size={16} /> 기록 초기화
        </button>
      </section>

      <section className="resultInfo">
        <span>{filteredItems.length}개 항목에서 무작위 출제 중</span>
        <span className="clickGuide"><Sparkles size={16} /> Space 또는 Enter로 정답/다음 카드</span>
      </section>

      {currentCard ? (
        <StudyCard
          card={currentCard}
          promptType={promptType}
          revealed={revealed}
          progress={progress}
          onReveal={() => setRevealed(true)}
          onNext={moveNext}
          onMark={markCard}
        />
      ) : (
        <section className="emptyState">
          <XCircle size={32} />
          <h2>표시할 항목이 없습니다</h2>
          <p>검색어 또는 필터를 바꿔보세요.</p>
        </section>
      )}

      <footer className="footerNote">
        <EyeOff size={15} /> 단어·문장 데이터는 <code>src/data/vocab.json</code> 파일에서 수정합니다.
      </footer>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
