import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BookOpen, CheckCircle2, Eye, EyeOff, RotateCcw, Search, Shuffle, Star, XCircle } from 'lucide-react';
import vocabData from './data/vocab.json';
import './styles.css';

const STORAGE_KEY = 'sungmi-vocab-progress-v1';

function uniqueValues(items, key) {
  return [...new Set(items.map((item) => item[key]).filter(Boolean))];
}

function loadProgress() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) ?? {};
  } catch {
    return {};
  }
}

function saveProgress(progress) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
}

function normalize(text) {
  return String(text ?? '').toLowerCase().trim();
}

function VocabCard({ card, progress, onMark }) {
  const [flipped, setFlipped] = useState(false);
  const status = progress[card.id];

  return (
    <article className={`card ${flipped ? 'is-flipped' : ''}`} onClick={() => setFlipped((value) => !value)}>
      <div className="cardTop">
        <span className="pill">{card.level}</span>
        <span className="pill muted">{card.lesson}</span>
        <span className="pill muted">{card.partOfSpeech}</span>
      </div>

      <div className="cardBody">
        {!flipped ? (
          <>
            <p className="hanzi">{card.hanzi}</p>
            <p className="pinyin">{card.pinyin}</p>
            <p className="hint">카드를 누르면 뜻과 예문이 열립니다</p>
          </>
        ) : (
          <>
            <p className="meaning">{card.meaningKo}</p>
            <div className="exampleBox">
              <p className="exampleZh">{card.exampleZh}</p>
              <p className="examplePinyin">{card.examplePinyin}</p>
              <p className="exampleKo">{card.exampleKo}</p>
            </div>
          </>
        )}
      </div>

      <div className="cardActions" onClick={(event) => event.stopPropagation()}>
        <button
          className={`miniButton ${status === 'known' ? 'activeKnown' : ''}`}
          onClick={() => onMark(card.id, status === 'known' ? null : 'known')}
          aria-label="아는 단어로 표시"
        >
          <CheckCircle2 size={16} /> 알아요
        </button>
        <button
          className={`miniButton ${status === 'review' ? 'activeReview' : ''}`}
          onClick={() => onMark(card.id, status === 'review' ? null : 'review')}
          aria-label="복습 필요 단어로 표시"
        >
          <Star size={16} /> 복습
        </button>
      </div>
    </article>
  );
}

function App() {
  const [query, setQuery] = useState('');
  const [level, setLevel] = useState('전체');
  const [lesson, setLesson] = useState('전체');
  const [statusFilter, setStatusFilter] = useState('전체');
  const [isRandom, setIsRandom] = useState(false);
  const [progress, setProgress] = useState(loadProgress);

  useEffect(() => {
    saveProgress(progress);
  }, [progress]);

  const levels = useMemo(() => ['전체', ...uniqueValues(vocabData, 'level')], []);
  const lessons = useMemo(() => ['전체', ...uniqueValues(vocabData, 'lesson')], []);

  const stats = useMemo(() => {
    const known = Object.values(progress).filter((value) => value === 'known').length;
    const review = Object.values(progress).filter((value) => value === 'review').length;
    return { total: vocabData.length, known, review };
  }, [progress]);

  const filteredCards = useMemo(() => {
    const q = normalize(query);
    const base = vocabData.filter((card) => {
      const matchesQuery = !q || [
        card.hanzi,
        card.pinyin,
        card.meaningKo,
        card.exampleZh,
        card.examplePinyin,
        card.exampleKo,
        card.category,
        card.partOfSpeech,
        ...(card.tags ?? [])
      ].some((value) => normalize(value).includes(q));

      const matchesLevel = level === '전체' || card.level === level;
      const matchesLesson = lesson === '전체' || card.lesson === lesson;
      const matchesStatus = statusFilter === '전체' || progress[card.id] === statusFilter;
      return matchesQuery && matchesLevel && matchesLesson && matchesStatus;
    });

    if (!isRandom) return base;

    return [...base].sort(() => Math.random() - 0.5);
  }, [query, level, lesson, statusFilter, progress, isRandom]);

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
  }

  return (
    <main className="appShell">
      <section className="hero">
        <div>
          <p className="eyebrow">Sungmi Chinese Vocabulary</p>
          <h1>성미 중국어 카드 단어장</h1>
          <p className="heroText">
            한자와 병음을 먼저 보고, 카드를 눌러 뜻과 예문을 확인하는 개인용 중국어 단어장입니다.
          </p>
        </div>
        <div className="heroBadge">
          <BookOpen size={26} />
          <strong>{stats.total}</strong>
          <span>cards</span>
        </div>
      </section>

      <section className="statsGrid" aria-label="학습 현황">
        <div className="statCard">
          <span>전체 단어</span>
          <strong>{stats.total}</strong>
        </div>
        <div className="statCard">
          <span>알아요</span>
          <strong>{stats.known}</strong>
        </div>
        <div className="statCard">
          <span>복습 필요</span>
          <strong>{stats.review}</strong>
        </div>
      </section>

      <section className="toolbar" aria-label="검색 및 필터">
        <label className="searchBox">
          <Search size={18} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="한자, 병음, 뜻, 예문 검색"
          />
        </label>

        <select value={level} onChange={(event) => setLevel(event.target.value)}>
          {levels.map((item) => <option key={item}>{item}</option>)}
        </select>

        <select value={lesson} onChange={(event) => setLesson(event.target.value)}>
          {lessons.map((item) => <option key={item}>{item}</option>)}
        </select>

        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="전체">전체 상태</option>
          <option value="known">알아요</option>
          <option value="review">복습 필요</option>
        </select>

        <button className="toolButton" onClick={() => setIsRandom((value) => !value)}>
          <Shuffle size={16} /> {isRandom ? '랜덤 해제' : '랜덤'}
        </button>

        <button className="toolButton secondary" onClick={resetProgress}>
          <RotateCcw size={16} /> 학습표시 초기화
        </button>
      </section>

      <section className="resultInfo">
        <span>{filteredCards.length}개 카드 표시 중</span>
        <span className="clickGuide"><Eye size={16} /> 카드 클릭 → 뜻 보기</span>
      </section>

      {filteredCards.length > 0 ? (
        <section className="cardGrid">
          {filteredCards.map((card) => (
            <VocabCard key={card.id} card={card} progress={progress} onMark={markCard} />
          ))}
        </section>
      ) : (
        <section className="emptyState">
          <XCircle size={32} />
          <h2>표시할 단어가 없습니다</h2>
          <p>검색어 또는 필터를 바꿔보세요.</p>
        </section>
      )}

      <footer className="footerNote">
        <EyeOff size={15} /> 단어 데이터는 <code>src/data/vocab.json</code> 파일에서 수정합니다.
      </footer>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
