# B 담당 glossary 제안

범위: H31110-72–H31332-75, 49문항·49분석. 실제 `parts`를 이어 붙인 표면형을 `forms`로 정리했습니다. 토큰을 여러 조각으로 참조한 경우 형태를 합친 문자열이며, pattern은 일반적인 배열입니다. 이 제안에서 role termIds 외에 쓰는 `measure`·`adverb`는 통합 계약의 추가 공통 용어입니다.

```json
[
  {
    "id": "a-exclamation",
    "hanzi": "啊",
    "pinyin": "a",
    "meaning": "말 끝에서 감탄하는 느낌을 더하는 말",
    "pattern": "평가 + 啊",
    "termIds": [
      "particle"
    ],
    "forms": [
      "啊"
    ],
    "caution": "의미 있는 명사나 동작을 뜻하지 않습니다."
  },
  {
    "id": "action-subject",
    "hanzi": "동사구 주어",
    "pinyin": "",
    "meaning": "행동 전체를 설명의 대상으로 삼기",
    "pattern": "행동 + 是 + 어떤 일",
    "termIds": [
      "subject",
      "verb"
    ],
    "forms": [
      "帮助别人"
    ],
    "caution": "사람 이름만 주어가 되는 것은 아닙니다."
  },
  {
    "id": "ba-disposal",
    "hanzi": "把",
    "pinyin": "bǎ",
    "meaning": "어떤 대상을 어떻게 처리하는지 말하도록 대상을 앞에 꺼내는 말",
    "pattern": "주어 + 把 + 대상 + 동사 + 결과·상태",
    "termIds": [
      "preposition",
      "object"
    ],
    "forms": [
      "把信",
      "把房子",
      "把教室",
      "把菜单"
    ],
    "caution": "把 뒤에는 처리할 대상이 오며 동사 뒤에서 결과나 처리 내용을 분명히 합니다."
  },
  {
    "id": "bei-passive",
    "hanzi": "被",
    "pinyin": "bèi",
    "meaning": "앞의 대상이 다른 힘이나 사람의 행동을 받았음을 나타내는 말",
    "pattern": "영향받는 대상 + 被 + (행위자) + 동사",
    "termIds": [
      "preposition",
      "subject"
    ],
    "forms": [
      "被",
      "被风"
    ],
    "caution": "被 뒤의 행위자는 생략할 수 있습니다."
  },
  {
    "id": "bi-comparison",
    "hanzi": "比",
    "pinyin": "bǐ",
    "meaning": "무엇과 비교하는지 기준을 연결하는 말",
    "pattern": "주어 + 比 + 기준 + 상태",
    "termIds": [
      "preposition"
    ],
    "forms": [
      "比去年"
    ],
    "caution": "比较의 比를 이 용법으로 분리하지 않습니다."
  },
  {
    "id": "bu-negation",
    "hanzi": "不",
    "pinyin": "bù",
    "meaning": "바로 뒤의 행동·판단·상태를 아니라고 하는 말",
    "pattern": "不 + 부정할 말",
    "termIds": [
      "adverbial"
    ],
    "forms": [
      "不喜欢"
    ],
    "caution": "어느 말 앞에 놓느냐에 따라 부정하는 범위가 달라집니다."
  },
  {
    "id": "classifier",
    "hanzi": "양사",
    "pinyin": "",
    "meaning": "사람·물건·종류 등을 세거나 가리킬 때 쓰는 단위",
    "pattern": "수·지시어 + 양사 + 명사",
    "termIds": [
      "measure",
      "attribute"
    ],
    "forms": [
      "件",
      "位",
      "只",
      "条",
      "种"
    ],
    "caution": "대상마다 알맞은 단위가 다릅니다. 种은 종류를 셉니다."
  },
  {
    "id": "clause-object",
    "hanzi": "절 목적어",
    "pinyin": "",
    "meaning": "주어와 술어가 있는 문장 전체를 생각·믿음 등의 내용으로 쓰기",
    "pattern": "생각·믿음 동사 + [주어 + 술어]",
    "termIds": [
      "object",
      "subject",
      "predicate"
    ],
    "forms": [
      "觉得熊猫更可爱",
      "那是真的"
    ],
    "caution": "절 안에도 별도의 주어가 있을 수 있습니다."
  },
  {
    "id": "comparison-difference",
    "hanzi": "차이 수량",
    "pinyin": "",
    "meaning": "비교한 결과의 차이가 얼마나 큰지 나타내는 양",
    "pattern": "比 + 기준 + 상태 + 차이 수량",
    "termIds": [
      "quantity"
    ],
    "forms": [
      "10公斤"
    ],
    "caution": "비교 기준과 차이의 양은 다릅니다."
  },
  {
    "id": "de-adverbial",
    "hanzi": "地",
    "pinyin": "de",
    "meaning": "앞의 꾸밈말이 뒤의 행동을 어떻게 하는지 알려 주도록 잇는 말",
    "pattern": "꾸밈말 + 地 + 동사",
    "termIds": [
      "particle",
      "adverbial"
    ],
    "forms": [
      "地"
    ],
    "caution": "的는 명사를 꾸미고 得는 동사·상태 뒤의 설명을 잇습니다."
  },
  {
    "id": "de-attributive",
    "hanzi": "的",
    "pinyin": "de",
    "meaning": "앞의 꾸밈말을 뒤의 사람·물건 등에 연결하는 말",
    "pattern": "꾸밈말 + 的 + 명사",
    "termIds": [
      "particle",
      "attribute"
    ],
    "forms": [
      "的"
    ],
    "caution": "소유뿐 아니라 시간·장소·행동으로도 명사를 꾸밀 수 있습니다."
  },
  {
    "id": "de-complement",
    "hanzi": "得",
    "pinyin": "de",
    "meaning": "행동이나 상태 뒤에서 그 정도·양상·반응을 설명하도록 잇는 말",
    "pattern": "동사·상태 + 得 + 설명",
    "termIds": [
      "particle",
      "complement"
    ],
    "forms": [
      "得"
    ],
    "caution": "觉得는 한 동사이므로 그 안의 得를 보어 표지로 떼지 않습니다."
  },
  {
    "id": "de-nominal",
    "hanzi": "的",
    "pinyin": "de",
    "meaning": "앞의 설명을 ‘그런 것’처럼 명사로 쓰게 하는 말",
    "pattern": "꾸밈말 + 的",
    "termIds": [
      "particle",
      "object"
    ],
    "forms": [
      "的"
    ],
    "caution": "뒤의 명사가 문맥상 생략될 수 있으며 是…的 강조 구문과 구별해야 합니다."
  },
  {
    "id": "degree-adverb",
    "hanzi": "정도부사",
    "pinyin": "",
    "meaning": "상태의 정도가 얼마나 큰지 앞에서 알려 주는 말",
    "pattern": "정도부사 + 형용사",
    "termIds": [
      "adverbial",
      "adverb"
    ],
    "forms": [
      "特别",
      "非常"
    ],
    "caution": "보어는 보통 동사나 상태 뒤에서 설명한다는 점이 다릅니다."
  },
  {
    "id": "direction-complement",
    "hanzi": "방향보어",
    "pinyin": "",
    "meaning": "동작 뒤에 붙어 움직이는 방향을 알려 주는 말",
    "pattern": "동사 + 방향",
    "termIds": [
      "complement"
    ],
    "forms": [
      "放进"
    ],
    "caution": "방향보어가 모두 글자 그대로의 공간 이동만 나타내는 것은 아닙니다."
  },
  {
    "id": "dou-scope",
    "hanzi": "都",
    "pinyin": "dōu",
    "meaning": "앞에서 말한 대상 전체가 해당함을 나타내는 말",
    "pattern": "여러 대상 + 都 + 술어",
    "termIds": [
      "adverbial"
    ],
    "forms": [
      "都"
    ],
    "caution": "무엇을 모두 포함하는지 앞의 대상을 확인합니다."
  },
  {
    "id": "dui-target",
    "hanzi": "对",
    "pinyin": "duì",
    "meaning": "태도나 감정이 향하는 대상을 연결하는 말",
    "pattern": "주어 + 对 + 대상 + 태도·평가",
    "termIds": [
      "preposition"
    ],
    "forms": [
      "对人",
      "对你的回答"
    ],
    "caution": "对 자체가 ‘만족하다’나 ‘친절하다’를 뜻하지는 않습니다."
  },
  {
    "id": "exclamation-duome-a",
    "hanzi": "多么…啊",
    "pinyin": "duōme … a",
    "meaning": "어떤 상태의 정도에 감탄하는 표현",
    "pattern": "多么 + 형용사 + 啊",
    "termIds": [
      "adverbial",
      "particle"
    ],
    "forms": [
      "多么啊"
    ],
    "caution": "보통 정보를 묻는 질문보다 감탄을 나타냅니다."
  },
  {
    "id": "existence-location",
    "hanzi": "존현문",
    "pinyin": "",
    "meaning": "장소를 먼저 말한 뒤 그곳에 무엇이 어떤 상태로 있는지 소개하기",
    "pattern": "장소 + 동사 + 着 + 존재하는 대상",
    "termIds": [
      "location",
      "verb",
      "subject"
    ],
    "forms": [
      "黑板上写着她的名字"
    ],
    "caution": "뒤의 존재 대상을 동작을 한 사람으로 읽지 않습니다."
  },
  {
    "id": "gan-courage",
    "hanzi": "敢",
    "pinyin": "gǎn",
    "meaning": "어떤 행동을 할 용기가 있거나 감히 함을 나타내는 말",
    "pattern": "敢 + 동사 / 不敢 + 동사",
    "termIds": [
      "modal"
    ],
    "forms": [
      "不敢"
    ],
    "caution": "불가능한 능력과 심리적으로 엄두가 안 남은 다릅니다."
  },
  {
    "id": "gei-recipient",
    "hanzi": "给",
    "pinyin": "gěi",
    "meaning": "물건이나 행동을 받는 상대를 연결하는 말",
    "pattern": "전달 동사 + 给 + 받는 사람",
    "termIds": [
      "preposition",
      "object"
    ],
    "forms": [
      "给我"
    ],
    "caution": "이 용법에서는 给가 전달 동사 뒤에 옵니다. 항상 동사 앞으로 옮기지 않습니다."
  },
  {
    "id": "geng-comparison",
    "hanzi": "更",
    "pinyin": "gèng",
    "meaning": "다른 대상이나 이전 상태보다 정도가 더 큼을 나타내는 말",
    "pattern": "更 + 상태",
    "termIds": [
      "adverbial"
    ],
    "forms": [
      "更"
    ],
    "caution": "비교 기준은 문맥에 생략될 수 있습니다."
  },
  {
    "id": "genju-basis",
    "hanzi": "根据",
    "pinyin": "gēnjù",
    "meaning": "무엇에 따라 행동하는지 기준을 연결하는 말",
    "pattern": "根据 + 기준 + 행동",
    "termIds": [
      "preposition"
    ],
    "forms": [
      "根据要求"
    ],
    "caution": "행동의 대상이 아니라 행동할 때 따르는 기준입니다."
  },
  {
    "id": "hai-mei-not-yet",
    "hanzi": "还没(有)",
    "pinyin": "hái méi(yǒu)",
    "meaning": "어떤 일이 아직 이루어지지 않았음을 나타내는 말",
    "pattern": "还没(有) + 동사·결과 (+ 呢)",
    "termIds": [
      "adverbial",
      "particle"
    ],
    "forms": [
      "还没",
      "还没有呢"
    ],
    "caution": "呢는 현재도 이어지는 상황의 느낌을 더할 수 있습니다."
  },
  {
    "id": "hen-adjective",
    "hanzi": "很",
    "pinyin": "hěn",
    "meaning": "상태를 형용사로 설명하며 정도를 나타내는 말",
    "pattern": "주어 + 很 + 형용사",
    "termIds": [
      "adverbial",
      "predicate"
    ],
    "forms": [
      "很"
    ],
    "caution": "항상 한국어의 강한 ‘매우’로 번역하지는 않습니다."
  },
  {
    "id": "hui-ability",
    "hanzi": "会",
    "pinyin": "huì",
    "meaning": "배워서 어떤 행동을 할 줄 아는 능력을 나타내는 말",
    "pattern": "会 + 행동 / 不会 + 행동",
    "termIds": [
      "modal"
    ],
    "forms": [
      "不会"
    ],
    "caution": "문맥에 따라 미래 추측의 会도 있으나 여기서는 배운 능력입니다."
  },
  {
    "id": "jile-degree",
    "hanzi": "极了",
    "pinyin": "jí le",
    "meaning": "상태 뒤에서 그 정도가 매우 크다고 강조하는 말",
    "pattern": "상태 + 极了",
    "termIds": [
      "complement"
    ],
    "forms": [
      "极了"
    ],
    "caution": "여기의 了를 과거형으로 떼어 해석하지 않습니다."
  },
  {
    "id": "jiuyao-le-imminent",
    "hanzi": "就要…了",
    "pinyin": "jiù yào … le",
    "meaning": "곧 일이 일어날 상황임을 나타내는 표현",
    "pattern": "就要 + 동사 + 了",
    "termIds": [
      "modal",
      "particle"
    ],
    "forms": [
      "就要了"
    ],
    "caution": "일이 이미 끝났다는 뜻이 아닙니다."
  },
  {
    "id": "le-change",
    "hanzi": "了",
    "pinyin": "le",
    "meaning": "앞서와 달라진 새 상태나 현재에 이른 상황을 나타내는 말",
    "pattern": "새 상태·상황 + 了",
    "termIds": [
      "particle"
    ],
    "forms": [
      "了"
    ],
    "caution": "과거 시제 표시와 같지 않습니다."
  },
  {
    "id": "le-completed",
    "hanzi": "了",
    "pinyin": "le",
    "meaning": "동작이나 일이 이루어졌음을 나타내는 말",
    "pattern": "동사 (+ 결과) + 了",
    "termIds": [
      "particle"
    ],
    "forms": [
      "了"
    ],
    "caution": "모든 了가 과거형인 것은 아니며 질문·부정·다른 절 안의 맥락도 봐야 합니다."
  },
  {
    "id": "le-disposal-plan",
    "hanzi": "了",
    "pinyin": "le",
    "meaning": "처리 행동을 마무리하여 대상의 처분을 나타내는 말",
    "pattern": "决定 + 把 + 대상 + 동사 + 了",
    "termIds": [
      "particle"
    ],
    "forms": [
      "了"
    ],
    "caution": "决定의 내용 안에 쓰이면 실제 처리가 벌써 이루어졌다고 단정하지 않습니다."
  },
  {
    "id": "ma-question",
    "hanzi": "吗",
    "pinyin": "ma",
    "meaning": "그렇다·아니다로 답할 수 있는 질문을 만드는 말",
    "pattern": "진술 내용 + 吗",
    "termIds": [
      "question",
      "particle"
    ],
    "forms": [
      "吗"
    ],
    "caution": "의문사가 이미 있는 질문에는 보통 이 방식으로 吗를 더하지 않습니다."
  },
  {
    "id": "nominal-predicate",
    "hanzi": "명사·수량 술어",
    "pinyin": "",
    "meaning": "금액이나 나이 같은 말이 직접 설명을 맡는 표현",
    "pattern": "대상 + (합계·이미 등) + 금액·나이",
    "termIds": [
      "predicate",
      "quantity"
    ],
    "forms": [
      "107岁",
      "18块"
    ],
    "caution": "이런 문장은 是 없이도 성립하지만 모든 명사를 이렇게 쓸 수 있는 것은 아닙니다."
  },
  {
    "id": "qilai-onset",
    "hanzi": "起来",
    "pinyin": "qǐlái",
    "meaning": "동작 뒤에서 그 행동이 시작됨을 나타내는 말",
    "pattern": "동사 + (了) + 起来",
    "termIds": [
      "complement"
    ],
    "forms": [
      "哭起来"
    ],
    "caution": "여기서는 위로 움직이는 공간 방향이 아닙니다."
  },
  {
    "id": "qing-request",
    "hanzi": "请",
    "pinyin": "qǐng",
    "meaning": "뒤의 행동을 공손하게 부탁하는 말",
    "pattern": "请 + 행동",
    "termIds": [
      "modal"
    ],
    "forms": [
      "请"
    ],
    "caution": "부탁하는 행동의 내용은 뒤에서 말합니다."
  },
  {
    "id": "quantity-duo",
    "hanzi": "多",
    "pinyin": "duō",
    "meaning": "수 뒤에서 그 수보다 조금 더 많음을 나타내는 말",
    "pattern": "큰 수 + 多 + 단위",
    "termIds": [
      "quantity"
    ],
    "forms": [
      "多"
    ],
    "caution": "여기의 多는 별도 술어 ‘많다’가 아니라 대략적인 초과 수량입니다."
  },
  {
    "id": "question-in-place",
    "hanzi": "의문사 제자리",
    "pinyin": "",
    "meaning": "묻는 내용을 원래 문장 성분 자리에 놓아 질문하기",
    "pattern": "대상 + 多少钱 / 동사 + 哪种 + 명사",
    "termIds": [
      "question",
      "object"
    ],
    "forms": [
      "哪种",
      "多少钱"
    ],
    "caution": "한국어처럼 의문 표현을 문장 맨 앞으로 무조건 옮기지 않습니다."
  },
  {
    "id": "result-complement",
    "hanzi": "결과보어",
    "pinyin": "",
    "meaning": "동작 뒤에서 그 행동으로 어떤 결과가 났는지 알려 주는 말",
    "pattern": "동사 + 결과",
    "termIds": [
      "complement"
    ],
    "forms": [
      "刮跑",
      "学会",
      "打扫干净",
      "洗干净",
      "画好"
    ],
    "caution": "会가 学 뒤에 오는 学会에서는 배워 할 수 있게 된 결과이며 앞에 오는 능원동사 会와 다릅니다."
  },
  {
    "id": "shi-de-assertion",
    "hanzi": "是…的",
    "pinyin": "shì … de",
    "meaning": "어떤 판단이 분명히 그렇다고 강조하는 표현",
    "pattern": "주어 + 是 + 판단 + 的",
    "termIds": [
      "verb",
      "particle"
    ],
    "forms": [
      "是的"
    ],
    "caution": "과거 사건의 시간·장소·방식을 강조하는 是…的와 구별합니다."
  },
  {
    "id": "tai-le-degree",
    "hanzi": "太…了",
    "pinyin": "tài … le",
    "meaning": "상태의 정도가 매우 높거나 지나치다고 평가하는 표현",
    "pattern": "太 + 형용사 + 了",
    "termIds": [
      "adverbial",
      "particle"
    ],
    "forms": [
      "太了"
    ],
    "caution": "이 了는 상태가 변한 과거나 동작의 완료를 뜻하지 않습니다."
  },
  {
    "id": "topic-object",
    "hanzi": "대상 화제",
    "pinyin": "",
    "meaning": "동작의 대상을 앞에 꺼내 그것에 대해 설명하기",
    "pattern": "대상 + 그 대상에 대한 설명",
    "termIds": [
      "topic",
      "object"
    ],
    "forms": [
      "你的作业",
      "你的脸"
    ],
    "caution": "앞에 온 명사가 반드시 행동하는 사람인 것은 아닙니다."
  },
  {
    "id": "xiang-desire",
    "hanzi": "想",
    "pinyin": "xiǎng",
    "meaning": "뒤의 행동을 하고 싶은 마음을 나타내는 말",
    "pattern": "想 + 행동",
    "termIds": [
      "modal"
    ],
    "forms": [
      "想"
    ],
    "caution": "실제 행동이 이미 일어났다는 뜻은 아닙니다."
  },
  {
    "id": "yinggai-obligation",
    "hanzi": "应该",
    "pinyin": "yīnggāi",
    "meaning": "어떤 행동을 해야 한다는 당위를 나타내는 말",
    "pattern": "应该 + 행동 / 不应该 + 행동",
    "termIds": [
      "modal"
    ],
    "forms": [
      "不应该"
    ],
    "caution": "不应该는 여기서 ‘해서는 안 된다’라는 판단입니다."
  },
  {
    "id": "you-again",
    "hanzi": "又",
    "pinyin": "yòu",
    "meaning": "전에 있었던 일이 다시 일어남을 나타내는 말",
    "pattern": "又 + 일어난 일",
    "termIds": [
      "adverbial"
    ],
    "forms": [
      "又"
    ],
    "caution": "又…又…로 두 특징을 나열하는 용법과 다릅니다."
  },
  {
    "id": "you-you-parallel",
    "hanzi": "又…又…",
    "pinyin": "yòu … yòu …",
    "meaning": "두 가지 특징이 함께 있음을 나란히 말하는 표현",
    "pattern": "又 + 특징1 + 又 + 특징2",
    "termIds": [
      "connective",
      "predicate"
    ],
    "forms": [
      "又又"
    ],
    "caution": "여기서는 사건이 다시 발생했다는 뜻이 아닙니다."
  },
  {
    "id": "yuelaiyue-change",
    "hanzi": "越来越",
    "pinyin": "yuè lái yuè",
    "meaning": "시간이 갈수록 어떤 정도가 점점 커짐을 나타내는 말",
    "pattern": "越来越 + 상태",
    "termIds": [
      "adverbial"
    ],
    "forms": [
      "越来越"
    ],
    "caution": "단순히 매우 그러하다는 뜻보다 변화의 흐름이 있습니다."
  },
  {
    "id": "zai-location",
    "hanzi": "在",
    "pinyin": "zài",
    "meaning": "행동이 일어나는 장소를 연결하는 말",
    "pattern": "在 + 장소 + 동사",
    "termIds": [
      "preposition",
      "location"
    ],
    "forms": [
      "在大学"
    ],
    "caution": "现在의 在와 구별하며, 在+동사로 진행을 나타내는 경우와도 구별합니다."
  },
  {
    "id": "zhe-state",
    "hanzi": "着",
    "pinyin": "zhe",
    "meaning": "동작 뒤에서 그 결과 상태가 이어짐을 나타내는 말",
    "pattern": "동사 + 着 + 존재하는 대상",
    "termIds": [
      "particle"
    ],
    "forms": [
      "着"
    ],
    "caution": "이 예문의 写着는 쓰는 중이 아니라 적혀 있는 상태입니다."
  },
  {
    "id": "zui-superlative",
    "hanzi": "最",
    "pinyin": "zuì",
    "meaning": "비교 범위 안에서 정도가 가장 큼을 나타내는 말",
    "pattern": "最 + 상태",
    "termIds": [
      "adverbial"
    ],
    "forms": [
      "最"
    ],
    "caution": "비교 범위는 문맥으로 주어질 수 있습니다."
  }
]
```
