import { useEffect, useState } from 'react';

// 브라우저 내장 음성합성(Web Speech API)으로 중국어를 읽어줍니다.
// 실제 중국어 TTS 엔진을 쓰기 때문에 한자만 넘겨도 성조가 그대로 살아납니다.

const CHINESE_LANG_PREFIX = 'zh';
const PREFERRED_LANGS = ['zh-cn', 'zh_cn', 'cmn-hans-cn', 'zh-hans', 'zh'];

function getSynth() {
  return typeof window !== 'undefined' ? window.speechSynthesis : null;
}

export function isSpeechSupported() {
  return Boolean(getSynth() && typeof window.SpeechSynthesisUtterance === 'function');
}

function voiceScore(voice) {
  const lang = String(voice.lang ?? '').toLowerCase().replace('_', '-');
  const name = String(voice.name ?? '').toLowerCase();

  let score = 0;
  const preferredIndex = PREFERRED_LANGS.indexOf(lang);
  if (preferredIndex >= 0) score += 100 - preferredIndex * 10;
  else if (lang.startsWith(CHINESE_LANG_PREFIX)) score += 40; // zh-TW, zh-HK 등

  // 기기에 설치된 음성이 네트워크 음성보다 빠르고 안정적입니다.
  if (voice.localService) score += 8;
  if (name.includes('google')) score += 6;
  if (name.includes('ting-ting') || name.includes('tingting')) score += 6;

  return score;
}

export function pickChineseVoice() {
  const synth = getSynth();
  if (!synth) return null;

  const chineseVoices = synth
    .getVoices()
    .filter((voice) => String(voice.lang ?? '').toLowerCase().startsWith(CHINESE_LANG_PREFIX));

  if (!chineseVoices.length) return null;

  return chineseVoices.slice().sort((a, b) => voiceScore(b) - voiceScore(a))[0];
}

export function speakChinese(text, { rate = 0.85, onStart, onEnd } = {}) {
  const synth = getSynth();
  const trimmed = String(text ?? '').trim();
  if (!synth || !trimmed || !isSpeechSupported()) return false;

  // 모바일에서는 반드시 탭 이벤트 안에서 동기적으로 speak()를 호출해야 소리가 납니다.
  synth.cancel();

  const utterance = new SpeechSynthesisUtterance(trimmed);
  const voice = pickChineseVoice();
  if (voice) utterance.voice = voice;
  utterance.lang = voice?.lang || 'zh-CN';
  utterance.rate = rate; // 성조를 구분해 듣기 좋게 살짝 느리게
  utterance.pitch = 1;
  utterance.volume = 1;

  if (onStart) utterance.addEventListener('start', onStart);
  if (onEnd) {
    utterance.addEventListener('end', onEnd);
    utterance.addEventListener('error', onEnd);
  }

  synth.speak(utterance);
  synth.resume(); // 일부 안드로이드 크롬에서 일시정지 상태로 남는 문제 방지
  return true;
}

export function stopSpeaking() {
  getSynth()?.cancel();
}

// 중국어 음성이 기기에 설치돼 있는지 확인합니다.
// 크롬은 음성 목록을 비동기로 채우기 때문에 voiceschanged 이벤트를 기다려야 합니다.
export function useChineseVoice() {
  const [state, setState] = useState(() => ({
    supported: isSpeechSupported(),
    checked: false,
    voice: null
  }));

  useEffect(() => {
    const synth = getSynth();
    if (!synth || !isSpeechSupported()) {
      setState({ supported: false, checked: true, voice: null });
      return undefined;
    }

    let cancelled = false;

    function refresh(markChecked) {
      if (cancelled) return;
      const voice = pickChineseVoice();
      setState((prev) => ({
        supported: true,
        checked: prev.checked || markChecked || Boolean(voice),
        voice
      }));
    }

    function handleVoicesChanged() {
      refresh(true);
    }

    refresh(false);
    synth.addEventListener?.('voiceschanged', handleVoicesChanged);

    // voiceschanged가 아예 안 오는 브라우저를 위한 안전장치
    const timer = setTimeout(() => refresh(true), 1500);

    return () => {
      cancelled = true;
      clearTimeout(timer);
      synth.removeEventListener?.('voiceschanged', handleVoicesChanged);
      synth.cancel();
    };
  }, []);

  return state;
}
