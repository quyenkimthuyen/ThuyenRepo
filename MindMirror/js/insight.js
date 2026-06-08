(function () {
const INSIGHT_QUESTIONS = {
  ROOT: [
    "Vấn đề này bắt đầu từ sự kiện cụ thể nào?",
    "Bạn đang muốn hiểu sự thật hay muốn chứng minh mình đúng?",
    "Nếu nhìn chậm lại, phần nào là sự kiện và phần nào là diễn giải?"
  ],
  FACT: [
    "Đây là điều bạn tận mắt chứng kiến?",
    "Có bằng chứng không?",
    "Có người khác xác nhận không?"
  ],
  INTERPRETATION: [
    "Đây là sự kiện hay suy diễn?",
    "Có cách giải thích khác không?",
    "Nếu người khác gặp tình huống này họ có nghĩ giống bạn không?"
  ],
  BELIEF: [
    "Niềm tin này đến từ đâu?",
    "Nó luôn đúng trong mọi trường hợp không?",
    "Có ngoại lệ không?"
  ],
  EMOTION: [
    "Cảm xúc này bắt nguồn từ điều gì?",
    "Nó có phản ánh đầy đủ sự thật không?"
  ],
  ACTION: [
    "Hành động này giải quyết hay làm trầm trọng vấn đề?",
    "Nếu làm lại bạn có chọn cách khác không?"
  ],
  CONSEQUENCE: [
    "Hậu quả ngắn hạn?",
    "Hậu quả dài hạn?",
    "Ai bị ảnh hưởng?"
  ]
};

const CONVICTION_ITEMS = [
  "Tôi có thể nói: 'Có thể tôi đúng một phần, nhưng chưa chắc đúng toàn bộ.'",
  "Tôi đã ghi sự kiện cụ thể, không chỉ ghi kết luận về người khác.",
  "Tôi đã viết ít nhất một lý do khiến người kia có thể không hoàn toàn sai.",
  "Tôi biết mình sợ mất gì nếu phải đổi quan điểm.",
  "Tôi biết điều kiện cụ thể nào sẽ khiến mình thay đổi.",
  "Tôi có thể giữ giá trị của mình mà không làm người kia mất phẩm giá."
];

const TRUTH_ITEMS = [
  "Tôi biết mình đang bảo vệ giá trị cụ thể nào.",
  "Tôi biết hình ảnh bản thân nào đang bị chạm vào.",
  "Nếu đổi vai, tôi vẫn thấy cách mình làm là chấp nhận được.",
  "Tôi có thể nhận một phần trách nhiệm mà không thấy mình sụp đổ.",
  "Bước tiếp theo của tôi giúp hiểu sự thật rõ hơn, không chỉ giúp tôi thắng.",
  "Tôi có thể nói sự thật mà không hạ thấp người kia."
];

function getInsightQuestions(type) {
  return INSIGHT_QUESTIONS[type] || [];
}

function calculateConvictionScore(answers, convictionState = {}) {
  const choiceScores = {
    reactive: 0,
    aware: 0.55,
    mature: 1
  };
  const choiceKeys = ["evidence", "counterEvidence", "flexibility", "egoAwareness", "respect"];
  const choiceScore = choiceKeys.reduce((score, key) => {
    return score + (choiceScores[convictionState.choices?.[key]] ?? 0);
  }, 0);
  const reflectionScore = CONVICTION_ITEMS.reduce((score, _, index) => {
    return score + (answers[index] ? 1 : 0);
  }, 0);

  const certainty = Number(convictionState.certainty ?? 50);
  const certaintyPenalty = certainty >= 85 && choiceScore < choiceKeys.length ? 10 : 0;
  const conviction = Math.max(0, Math.min(100, Math.round(
    ((choiceScore / choiceKeys.length) * 70) +
    ((reflectionScore / CONVICTION_ITEMS.length) * 30) -
    certaintyPenalty
  )));

  return {
    conviction,
    stubborn: 100 - conviction,
    feedback: getConvictionFeedback(conviction, certainty)
  };
}

function getConvictionFeedback(conviction, certainty) {
  if (conviction >= 75) {
    return "Bạn đang kiên định theo hướng lành mạnh: có quan điểm, có bằng chứng, có phản chứng và có điều kiện để điều chỉnh.";
  }

  if (certainty >= 80 && conviction < 55) {
    return "Dấu hiệu cố chấp cao: mức chắc chắn mạnh hơn khả năng tự kiểm tra. Hãy xem lại các checklist về phản chứng, điều kiện đổi ý và phẩm giá của người kia.";
  }

  if (conviction >= 50) {
    return "Bạn đã bắt đầu tự phản biện. Bước tiếp theo là chọn rõ hơn các mục về ngoại lệ, điều kiện đổi ý và cách giữ giá trị mà không công kích.";
  }

  return "Niềm tin này còn đang ở dạng phản ứng ban đầu. Hãy quay lại cây tư duy để tách sự kiện, diễn giải và niềm tin trước khi kết luận.";
}

function calculateTruthScore(answers, truthState = {}) {
  const choiceScores = {
    reactive: 0,
    aware: 0.55,
    mature: 1
  };
  const choiceKeys = ["value", "selfImage", "mirror", "humility", "truthAction"];
  const choiceScore = choiceKeys.reduce((score, key) => {
    return score + (choiceScores[truthState.choices?.[key]] ?? 0);
  }, 0);
  const reflectionScore = TRUTH_ITEMS.reduce((score, _, index) => {
    return score + (answers[index] ? 1 : 0);
  }, 0);

  const truth = Math.max(0, Math.min(100, Math.round(
    ((choiceScore / choiceKeys.length) * 70) +
    ((reflectionScore / TRUTH_ITEMS.length) * 30)
  )));

  return {
    truth,
    ego: 100 - truth,
    feedback: getTruthFeedback(truth)
  };
}

function getTruthFeedback(truth) {
  if (truth >= 75) {
    return "Bạn đang nghiêng về tìm kiếm sự thật: đã nhìn cả giá trị, cái tôi, đổi vai và chọn hành động làm rõ thực tế.";
  }

  if (truth >= 50) {
    return "Bạn đã bắt đầu tách sự thật khỏi cái tôi. Hãy xem lại các mục về đổi vai, nhận trách nhiệm và hành động làm sự thật rõ hơn.";
  }

  return "Dấu hiệu bảo vệ cái tôi còn mạnh. Hãy bắt đầu bằng đổi vai: nếu người khác làm giống bạn, bạn có chấp nhận không?";
}

window.CognitiveInsight = {
  INSIGHT_QUESTIONS,
  CONVICTION_ITEMS,
  TRUTH_ITEMS,
  getInsightQuestions,
  calculateConvictionScore,
  calculateTruthScore
};
})();
