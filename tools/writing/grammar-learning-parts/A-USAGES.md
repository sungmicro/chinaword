# 문법 학습 A: 공통 용법 사전 제안

범위: `H31001-71` ~ `H31110-71` (46문항, 49분석, 105 points).

`a.json`은 `version: 1` + `items` 형식입니다. `parts`는 기존 토큰 인덱스와 반열린 문자 구간 `[start, end)`이며, 문맥을 수작업 판정한 후 원래 group의 명시적 구간 또는 직접 지정한 구간을 사용했습니다. 글자 검색으로 기능어를 붙이지 않았습니다. `termIds`는 기존 role ID를 사용하며, 원래 group 안에 합쳐진 的 등의 개념도 추가했습니다.

아래 JSON을 통합 glossary의 usages 정본화에 사용할 수 있습니다. `forms`는 실제 points.parts를 이어 붙인 표면형 전부입니다. 不到의 到, 现在의 在, 离开的 离, 比较의 比는 해당 글자의 개사/보어 용법으로 분류하지 않았습니다. 得가 없는 学习很努力와 做事情特别认真은 화제·설명 구조로 보았습니다. 공식답·grammar·study는 변경하지 않았습니다.

주의할 문항: H31001-75의 `很大提高`, H31008-75의 `放厨房里`는 공식답을 그대로 두고 설명했습니다. H31006-74는 `看到这个句子` 전체의 주어 역할과 내부 `看到`의 결과보어를 구분했습니다. H31004-75·H31005-72·H31006-75의 복수 답은 서로 다른 분석마다 따로 설명했습니다.

```json
{
  "de-manner": {
    "hanzi": "地",
    "pinyin": "de",
    "meaning": "앞말을 ‘~하게’로 만들어 동작의 방식을 꾸밉니다.",
    "pattern": "상태·방식+地+동사",
    "termIds": [
      "particle",
      "adverbial"
    ],
    "forms": [
      "高兴地",
      "满意地"
    ],
    "caution": "동사 뒤에서 보어를 잇는 得, 명사를 꾸미는 的와 구별합니다."
  },
  "le-completed": {
    "hanzi": "了",
    "pinyin": "le",
    "meaning": "동작이나 일이 이루어졌음을 나타냅니다.",
    "pattern": "동사(+결과보어)+了",
    "termIds": [
      "particle",
      "verb"
    ],
    "forms": [
      "笑了",
      "忘了",
      "花了",
      "洗干净了",
      "写错了",
      "拿走了"
    ],
    "caution": "과거 시제를 만드는 어미가 아닙니다. 문장 끝에서 상황 변화를 나타내는 了와 문맥으로 구별합니다."
  },
  "de-attribute": {
    "hanzi": "的",
    "pinyin": "de",
    "meaning": "앞말을 뒤 명사에 연결해 누구의 것인지, 어떤 것인지 밝힙니다.",
    "pattern": "꾸미는 말+的+명사",
    "termIds": [
      "particle",
      "attribute"
    ],
    "forms": [
      "上午的考试",
      "熊猫的眼睛和耳朵",
      "这个城市的春天",
      "叔叔的太阳镜",
      "你脚下的路",
      "你丈夫的鼻子",
      "你的丈夫",
      "李小姐的头发",
      "他们班的学生",
      "自己的腿脚",
      "羊的耳朵和鼻子",
      "中国南方的雨水"
    ],
    "caution": "모든 꾸밈 관계에 的가 필수인 것은 아닙니다."
  },
  "degree-adverb": {
    "hanzi": "比较／特别／很",
    "pinyin": "bǐjiào / tèbié / hěn",
    "meaning": "상태가 어느 정도인지 동사나 형용사 앞에서 알려 줍니다.",
    "pattern": "정도 부사+상태 표현",
    "termIds": [
      "adverbial",
      "predicate"
    ],
    "forms": [
      "比较简单",
      "特别认真",
      "很有兴趣"
    ],
    "caution": "比较는 ‘비교적’이라는 한 단어이며 比를 떼어 비교문으로 읽지 않습니다."
  },
  "de-complement": {
    "hanzi": "得",
    "pinyin": "de",
    "meaning": "동사 뒤에서 동작의 정도·양상이나 변화한 상태를 이어 줍니다.",
    "pattern": "동사+得+상태 설명",
    "termIds": [
      "particle",
      "complement"
    ],
    "forms": [
      "变得越来越好",
      "写得很漂亮"
    ],
    "caution": "觉得 같은 단어 안의 得까지 이 기능으로 설명하지 않습니다. 得 앞 동사와 뒤 보어를 함께 봅니다."
  },
  "increasing-degree": {
    "hanzi": "越来越",
    "pinyin": "yuè lái yuè",
    "meaning": "시간이 흐르며 ‘점점 더 ~하다’는 변화를 나타냅니다.",
    "pattern": "越来越+형용사·상태",
    "termIds": [
      "adverbial",
      "predicate"
    ],
    "forms": [
      "越来越好"
    ],
    "caution": "두 대상이 어느 쪽보다 낫다는 比 비교문과 구별합니다."
  },
  "le-change": {
    "hanzi": "了",
    "pinyin": "le",
    "meaning": "이전과 다른 상황이 생겼거나 지금까지 이어진 새 상황임을 나타냅니다.",
    "pattern": "문장+了",
    "termIds": [
      "particle"
    ],
    "forms": [
      "了",
      "很久没见面了",
      "发烧了"
    ],
    "caution": "很久没…了에서는 만나지 않은 상황을 말하며, 동작이 완료되었다는 뜻이 아닙니다."
  },
  "classifier": {
    "hanzi": "位",
    "pinyin": "wèi",
    "meaning": "사람을 공손하게 셀 때 명사 앞에 쓰는 단위입니다.",
    "pattern": "지시사·수사+位+사람 명사",
    "termIds": [
      "quantity",
      "attribute"
    ],
    "forms": [
      "那位医生",
      "那位邻居"
    ],
    "caution": "位 자체가 ‘의사’나 ‘이웃’의 뜻을 가진 것은 아닙니다."
  },
  "gei-recipient": {
    "hanzi": "给",
    "pinyin": "gěi",
    "meaning": "送 뒤에서 물건을 받는 사람을 소개합니다.",
    "pattern": "送给+받는 사람+물건",
    "termIds": [
      "preposition",
      "verb",
      "object"
    ],
    "forms": [
      "送给他一个礼物",
      "送给弟弟"
    ],
    "caution": "여기서 给는 送 뒤의 수령자 표지입니다. 모든 给 구를 동사 앞으로 옮기지 않습니다."
  },
  "also-adverb": {
    "hanzi": "也",
    "pinyin": "yě",
    "meaning": "앞서 말한 대상과 마찬가지로 ‘~도’임을 덧붙입니다.",
    "pattern": "주어+也+술어",
    "termIds": [
      "adverbial"
    ],
    "forms": [
      "也"
    ],
    "caution": "한국어 ‘~도’처럼 주어 명사에 붙이지 않고 술어 앞에 둡니다."
  },
  "attribute-order": {
    "hanzi": "很大提高",
    "pinyin": "hěn dà tígāo",
    "meaning": "꾸미는 말을 앞에 놓아 향상의 폭을 설명합니다.",
    "pattern": "꾸미는 말+명사",
    "termIds": [
      "attribute",
      "object"
    ],
    "forms": [
      "很大提高"
    ],
    "caution": "이 공식 답안은 很大提高이며 的가 없습니다. 원문에 없는 的를 넣어 parts를 만들지 않습니다."
  },
  "sequence-adverb": {
    "hanzi": "先",
    "pinyin": "xiān",
    "meaning": "여러 행동 중 먼저 하는 행동임을 나타냅니다.",
    "pattern": "先+동사",
    "termIds": [
      "adverbial"
    ],
    "forms": [
      "先"
    ],
    "caution": "先 뒤에 오는 동작이 우선입니다."
  },
  "verb-reduplication": {
    "hanzi": "看看",
    "pinyin": "kànkan",
    "meaning": "같은 동사를 반복해 ‘잠깐, 한번’ 하는 가벼운 동작을 말합니다.",
    "pattern": "동사+같은 동사",
    "termIds": [
      "verb"
    ],
    "forms": [
      "看看"
    ],
    "caution": "같은 동작을 정확히 두 번 했다는 횟수 표현이 아닙니다."
  },
  "verb-object": {
    "hanzi": "동사+목적어",
    "pinyin": "",
    "meaning": "동작 뒤에 그 행동이 향하는 대상을 놓습니다.",
    "pattern": "동사+행동의 대상",
    "termIds": [
      "verb",
      "object"
    ],
    "forms": [
      "带护照",
      "举行会议",
      "吃草",
      "喜欢中国文化",
      "离开东门"
    ],
    "caution": "목적어는 항상 물건인 것은 아닙니다. 동작·상태를 담은 구절도 올 수 있습니다."
  },
  "degree-hen": {
    "hanzi": "很",
    "pinyin": "hěn",
    "meaning": "형용사나 상태 표현 앞에서 정도를 나타냅니다.",
    "pattern": "很+형용사·상태",
    "termIds": [
      "adverbial",
      "predicate"
    ],
    "forms": [
      "很新鲜",
      "很满意",
      "很热情"
    ],
    "caution": "평범한 상태 설명에서는 항상 ‘매우’를 강하게 강조하는 것은 아닙니다."
  },
  "all-adverb": {
    "hanzi": "都",
    "pinyin": "dōu",
    "meaning": "앞에서 말한 여러 대상이 ‘모두’ 해당함을 나타냅니다.",
    "pattern": "여러 대상+都+술어",
    "termIds": [
      "adverbial"
    ],
    "forms": [
      "都"
    ],
    "caution": "어떤 대상 전체를 가리키는지 앞부분에서 확인합니다."
  },
  "de-nominal": {
    "hanzi": "的",
    "pinyin": "de",
    "meaning": "앞의 성질 표현을 명사처럼 쓰게 합니다.",
    "pattern": "是+성질 표현+的",
    "termIds": [
      "particle",
      "predicate"
    ],
    "forms": [
      "黑色的"
    ],
    "caution": "黑色的의 的는 과거 일의 세부를 강조하는 是…的와 역할이 다릅니다."
  },
  "a-not-a-question": {
    "hanzi": "敢不敢",
    "pinyin": "gǎn bu gǎn",
    "meaning": "긍정과 부정을 나란히 놓아 행동할 용기가 있는지 묻습니다.",
    "pattern": "능원동사+不+같은 능원동사",
    "termIds": [
      "modal",
      "question"
    ],
    "forms": [
      "敢不敢"
    ],
    "caution": "단순히 ‘감히 하지 않는다’고 단정하는 표현이 아니라 질문입니다."
  },
  "yong-means": {
    "hanzi": "用",
    "pinyin": "yòng",
    "meaning": "도구나 수단을 소개해 ‘~을 써서’라는 뜻을 냅니다.",
    "pattern": "用+수단+동사",
    "termIds": [
      "preposition",
      "adverbial"
    ],
    "forms": [
      "用冷水",
      "用铅笔"
    ],
    "caution": "이 문맥의 用 구는 수단을 나타내며 본동사 앞에 놓입니다."
  },
  "ba-disposal": {
    "hanzi": "把",
    "pinyin": "bǎ",
    "meaning": "영향을 주거나 처리할 대상을 동사 앞에 먼저 제시합니다.",
    "pattern": "把+대상+동사+처리 내용·결과",
    "termIds": [
      "preposition",
      "object"
    ],
    "forms": [
      "把手机送给弟弟",
      "把碗和筷子洗干净",
      "把冰箱放厨房里"
    ],
    "caution": "把 뒤는 행동하는 사람이 아니라 처리할 대상입니다."
  },
  "mei-negation": {
    "hanzi": "没",
    "pinyin": "méi",
    "meaning": "어떤 일이 일어나지 않았음을 나타냅니다.",
    "pattern": "没+동사",
    "termIds": [
      "adverbial",
      "verb"
    ],
    "forms": [
      "没见面"
    ],
    "caution": "很久没见面了의 了를 보고 만남이 이루어졌다고 해석하지 않습니다."
  },
  "frequency-adverb": {
    "hanzi": "经常",
    "pinyin": "jīngcháng",
    "meaning": "어떤 행동이 자주 일어남을 나타냅니다.",
    "pattern": "经常+동사",
    "termIds": [
      "adverbial"
    ],
    "forms": [
      "经常"
    ],
    "caution": "행동의 빈도를 나타내며 동사 앞에 놓입니다."
  },
  "topic-comment": {
    "hanzi": "화제와 설명",
    "pinyin": "",
    "meaning": "먼저 설명할 대상을 꺼낸 뒤 그 대상에 대한 내용을 말합니다.",
    "pattern": "화제+그에 대한 설명",
    "termIds": [
      "topic",
      "subject",
      "predicate"
    ],
    "forms": [
      "他的汉字",
      "你的丈夫鼻子",
      "会议",
      "学习很努力",
      "她身高",
      "做事情特别认真"
    ],
    "caution": "화제가 항상 뒤 동작을 직접 하는 주어인 것은 아닙니다. 得 없는 활동 평가를 得 구문으로 바꾸지 않습니다."
  },
  "cost-object": {
    "hanzi": "900块钱",
    "pinyin": "jiǔbǎi kuài qián",
    "meaning": "花 뒤에서 비용으로 든 돈의 양을 말합니다.",
    "pattern": "花(+了)+돈의 양",
    "termIds": [
      "object",
      "quantity"
    ],
    "forms": [
      "900块钱"
    ],
    "caution": "이 문항의 돈 액수는 수량 목적어이며 동작 방식의 보어가 아닙니다."
  },
  "zai-location-verb": {
    "hanzi": "在",
    "pinyin": "zài",
    "meaning": "대상이 어느 장소에 ‘있다’고 말하는 동사입니다.",
    "pattern": "대상+在+장소",
    "termIds": [
      "verb",
      "object",
      "location"
    ],
    "forms": [
      "在我的包里"
    ],
    "caution": "동작 앞에서 장소를 소개하는 개사 在와 구별합니다. 现在 안의 在도 이 용법이 아닙니다."
  },
  "localizer": {
    "hanzi": "里",
    "pinyin": "lǐ",
    "meaning": "명사 뒤에 붙어 그 장소의 안쪽을 가리킵니다.",
    "pattern": "장소·물건+里",
    "termIds": [
      "location"
    ],
    "forms": [
      "我的包里",
      "咖啡里"
    ],
    "caution": "里가 붙은 덩어리 전체가 장소입니다."
  },
  "yao-intention": {
    "hanzi": "要",
    "pinyin": "yào",
    "meaning": "앞으로 하려고 하는 행동이나 계획을 나타냅니다.",
    "pattern": "要+앞으로 할 행동",
    "termIds": [
      "modal"
    ],
    "forms": [
      "要"
    ],
    "caution": "要는 문맥에 따라 필요·의무도 나타냅니다. 공항에 가려는 이 문장은 계획입니다."
  },
  "serial-purpose": {
    "hanzi": "去…接…",
    "pinyin": "qù … jiē …",
    "meaning": "어디에 가는지 말한 뒤 그곳에서 할 목적 행동을 이어 말합니다.",
    "pattern": "去+장소+목적 행동",
    "termIds": [
      "verb",
      "object"
    ],
    "forms": [
      "去机场接女朋友"
    ],
    "caution": "去의 뒤 장소와 다음 동작의 대상을 구별합니다."
  },
  "hai-continuing": {
    "hanzi": "还",
    "pinyin": "hái",
    "meaning": "상태가 계속됨을 나타내어 ‘아직, 여전히’라는 뜻을 냅니다.",
    "pattern": "还+상태 표현",
    "termIds": [
      "adverbial"
    ],
    "forms": [
      "还"
    ],
    "caution": "여기서는 물건을 돌려주는 동사 还(huán)이 아닙니다."
  },
  "bu-negation": {
    "hanzi": "不",
    "pinyin": "bù",
    "meaning": "뒤의 동작이나 상태를 부정합니다.",
    "pattern": "不+동사·형용사",
    "termIds": [
      "adverbial"
    ],
    "forms": [
      "不喜欢"
    ],
    "caution": "이 문장의 不喜欢은 좋아하지 않는다는 뜻입니다. 동작 미발생의 没와 구별합니다."
  },
  "zenme-le": {
    "hanzi": "怎么了",
    "pinyin": "zěnme le",
    "meaning": "무슨 일이 생겼는지, 상태가 어떻게 되었는지 묻습니다.",
    "pattern": "대상+怎么了",
    "termIds": [
      "question",
      "particle"
    ],
    "forms": [
      "怎么了"
    ],
    "caution": "여기서는 동작의 방법을 묻는 ‘어떻게 하다’가 아닙니다."
  },
  "question-in-place": {
    "hanzi": "什么时候",
    "pinyin": "shénme shíhou",
    "meaning": "언제인지 물으며 답에 해당하는 시간 자리에 놓입니다.",
    "pattern": "시간 자리의 什么时候+동사",
    "termIds": [
      "time",
      "question"
    ],
    "forms": [
      "什么时候"
    ],
    "caution": "의문사라고 항상 문장 맨 앞으로 옮기지 않습니다."
  },
  "yao-obligation": {
    "hanzi": "要",
    "pinyin": "yào",
    "meaning": "행동을 할 필요가 있거나 ‘해야 한다’고 말합니다.",
    "pattern": "要+해야 할 행동",
    "termIds": [
      "modal"
    ],
    "forms": [
      "要"
    ],
    "caution": "이 문장에서는 노인에게 필요한 돌봄을 말합니다. 모든 要를 의무로 해석하지 않습니다."
  },
  "buyao-prohibition": {
    "hanzi": "不要",
    "pinyin": "bú yào",
    "meaning": "뒤의 행동을 하지 말라고 금지합니다.",
    "pattern": "不要+동사",
    "termIds": [
      "adverbial",
      "modal"
    ],
    "forms": [
      "不要"
    ],
    "caution": "여기서는 ‘원하지 않다’가 아니라 ‘~하지 마라’입니다."
  },
  "result-complement": {
    "hanzi": "干净／错／到",
    "pinyin": "gānjìng / cuò / dào",
    "meaning": "동사 뒤에서 동작이 어떤 결과에 이르렀는지 보충합니다.",
    "pattern": "동사+결과보어",
    "termIds": [
      "verb",
      "complement"
    ],
    "forms": [
      "洗干净",
      "看到",
      "写错"
    ],
    "caution": "看到의 到는 실제로 보게 된 결과이고, 不到一米七의 到는 같은 보어로 분류하지 않습니다."
  },
  "ma-question": {
    "hanzi": "吗",
    "pinyin": "ma",
    "meaning": "문장 끝에서 앞 내용이 맞는지 확인 질문을 만듭니다.",
    "pattern": "평서 내용+吗",
    "termIds": [
      "question",
      "particle"
    ],
    "forms": [
      "吗"
    ],
    "caution": "문장 끝에 붙는 표지이며 ‘무엇’이라는 의문사가 아닙니다."
  },
  "sudden-adverb": {
    "hanzi": "突然",
    "pinyin": "tūrán",
    "meaning": "일이 갑자기 일어남을 나타냅니다.",
    "pattern": "突然+동사",
    "termIds": [
      "adverbial"
    ],
    "forms": [
      "突然"
    ],
    "caution": "갑작스러운 발생을 말하며 동사 앞에 옵니다."
  },
  "clause-subject": {
    "hanzi": "看到这个句子",
    "pinyin": "kàndào zhège jùzi",
    "meaning": "행동을 담은 덩어리 전체를 문장의 설명 대상으로 삼습니다.",
    "pattern": "행동 구절+술어",
    "termIds": [
      "subject",
      "verb"
    ],
    "forms": [
      "看到这个句子"
    ],
    "caution": "주어가 반드시 사람·사물 명사 하나일 필요는 없습니다."
  },
  "clause-object": {
    "hanzi": "游戏结束",
    "pinyin": "yóuxì jiéshù",
    "meaning": "작은 문장 전체가 동사 뒤에서 그 내용을 말합니다.",
    "pattern": "表示+내용 문장",
    "termIds": [
      "object",
      "subject",
      "predicate"
    ],
    "forms": [
      "游戏结束"
    ],
    "caution": "游戏와 结束를 따로 동급 목적어로 나누지 않습니다."
  },
  "dui-target": {
    "hanzi": "对",
    "pinyin": "duì",
    "meaning": "감정이나 평가가 향하는 대상을 ‘~에 대해’로 소개합니다.",
    "pattern": "对+대상+평가·감정",
    "termIds": [
      "preposition",
      "adverbial"
    ],
    "forms": [
      "对这条绿裤子",
      "对表演"
    ],
    "caution": "对 구는 술어 앞 또는 화제를 먼저 내세우는 문장 앞에 놓일 수 있습니다."
  },
  "bei-passive": {
    "hanzi": "被",
    "pinyin": "bèi",
    "meaning": "주어가 다른 사람의 행동을 받거나 당했음을 나타냅니다.",
    "pattern": "행동받는 대상+被(+행동한 사람)+동사",
    "termIds": [
      "preposition",
      "subject"
    ],
    "forms": [
      "他的姓名被写错",
      "菜单被服务员拿"
    ],
    "caution": "被 뒤의 행위자는 생략될 수도 있습니다. 주어를 행동한 사람으로 읽지 않습니다."
  },
  "quantity-below": {
    "hanzi": "不到",
    "pinyin": "bú dào",
    "meaning": "수량 앞에서 그 기준에 미치지 못함을 나타냅니다.",
    "pattern": "不到+기준 수량",
    "termIds": [
      "predicate",
      "quantity"
    ],
    "forms": [
      "不到一米七"
    ],
    "caution": "不到一米七에서 到는 방향·결과보어가 아닙니다."
  },
  "time-position": {
    "hanzi": "现在",
    "pinyin": "xiànzài",
    "meaning": "행동이 일어나는 ‘지금’이라는 때를 나타냅니다.",
    "pattern": "시간 표현+동작",
    "termIds": [
      "time"
    ],
    "forms": [
      "现在"
    ],
    "caution": "现在는 한 단어입니다. 在를 떼어 장소 개사로 설명하지 않습니다."
  },
  "if-then": {
    "hanzi": "如果…就…",
    "pinyin": "rúguǒ … jiù …",
    "meaning": "조건을 먼저 말하고 그 조건일 때의 결과를 연결합니다.",
    "pattern": "如果+조건+就+결과",
    "termIds": [
      "connective",
      "adverbial"
    ],
    "forms": [
      "如果就"
    ],
    "caution": "조건 부분과 결과 부분이 어디인지 함께 봅니다."
  },
  "geng-degree": {
    "hanzi": "更",
    "pinyin": "gèng",
    "meaning": "현재나 기준보다 ‘더’ 그런 상태임을 나타냅니다.",
    "pattern": "更+형용사·상태",
    "termIds": [
      "adverbial",
      "predicate"
    ],
    "forms": [
      "更好"
    ],
    "caution": "여기서는 국수가 있으면 지금보다 더 좋겠다는 뜻입니다."
  },
  "le-hypothetical-state": {
    "hanzi": "了",
    "pinyin": "le",
    "meaning": "가정한 조건에서 성립할 새 상태를 나타냅니다.",
    "pattern": "如果+조건+就+상태+了",
    "termIds": [
      "particle",
      "connective"
    ],
    "forms": [
      "好了"
    ],
    "caution": "가정문 속 了를 과거형으로 해석하지 않습니다."
  },
  "total-adverb": {
    "hanzi": "一共",
    "pinyin": "yígòng",
    "meaning": "전체를 합한 총수량임을 나타냅니다.",
    "pattern": "一共+수량",
    "termIds": [
      "adverbial",
      "quantity"
    ],
    "forms": [
      "一共三层"
    ],
    "caution": "뒤 수량 전체가 총합입니다."
  },
  "direction-complement": {
    "hanzi": "走",
    "pinyin": "zǒu",
    "meaning": "拿 뒤에서 물건이 원래 있던 곳을 떠나는 방향을 보충합니다.",
    "pattern": "拿+走",
    "termIds": [
      "verb",
      "complement"
    ],
    "forms": [
      "拿走"
    ],
    "caution": "走는 이 문장에서 혼자 ‘걷다’라는 본동사가 아닙니다."
  },
  "bi-comparison": {
    "hanzi": "比",
    "pinyin": "bǐ",
    "meaning": "비교의 기준을 ‘~보다’로 소개합니다.",
    "pattern": "A+比+B+차이를 나타내는 상태",
    "termIds": [
      "preposition",
      "predicate"
    ],
    "forms": [
      "中国南方的雨水比北方多"
    ],
    "caution": "比较의 比와 구별합니다. 比 뒤 B는 비교 기준입니다."
  },
  "location-complement": {
    "hanzi": "厨房里",
    "pinyin": "chúfáng lǐ",
    "meaning": "동사 뒤에서 물건을 놓을 도착 장소를 보충합니다.",
    "pattern": "放+도착 장소",
    "termIds": [
      "verb",
      "complement",
      "location"
    ],
    "forms": [
      "放厨房里"
    ],
    "caution": "이 답안에는 在가 없으며 없는 글자를 parts에 넣지 않습니다."
  },
  "ba-suggestion": {
    "hanzi": "吧",
    "pinyin": "ba",
    "meaning": "문장 끝에서 제안이나 권유를 부드럽게 합니다.",
    "pattern": "제안 내용+吧",
    "termIds": [
      "particle"
    ],
    "forms": [
      "吧"
    ],
    "caution": "처리 대상을 소개하는 把(bǎ)와 다른 글자·역할입니다."
  },
  "wish-construction": {
    "hanzi": "祝",
    "pinyin": "zhù",
    "meaning": "누구에게 어떤 좋은 상태를 바라는지 말합니다.",
    "pattern": "祝+사람+바라는 상태",
    "termIds": [
      "verb",
      "object",
      "subject",
      "predicate"
    ],
    "forms": [
      "祝大家身体健康"
    ],
    "caution": "뒤의 사람은 축원받는 대상이고, 신체 상태 설명이 이어집니다."
  },
  "shi-de-emphasis": {
    "hanzi": "是…的",
    "pinyin": "shì … de",
    "meaning": "이미 일어난 일의 시간·장소 같은 세부를 강조합니다.",
    "pattern": "주어+是+강조할 정보+동사+的",
    "termIds": [
      "particle",
      "time"
    ],
    "forms": [
      "是8点半离开东门的"
    ],
    "caution": "是黑色的 같은 성질 판단 문장을 모두 이 강조 구문으로 분류하지 않습니다."
  }
}
```
