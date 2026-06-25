const AICoach = {
  questions: [
    'Điều gì khiến bạn chọn phương án này?',
    'Nếu kết quả xấu xảy ra, bạn nghĩ nguyên nhân là gì?',
    'Bạn có thấy mô hình lặp lại nào trong các quyết định gần đây không?',
    'Lựa chọn này phản ánh ưu tiên gì của bạn lúc này?',
    'Bạn đang cân nhắc điều gì nhiều nhất: an toàn, phần thưởng, hay mối quan hệ?'
  ],

  getQuestion(state, choice) {
    const tags = choice.tags || [];
    const recent = state.decisions.slice(-5);

    if (tags.includes('short_term') && recent.filter((d) => d.tags?.includes('short_term')).length >= 3) {
      return 'Bạn có nhận ra mình thường chọn lợi ích ngay lập tức không? Điều gì thúc đẩy điều đó?';
    }

    if (tags.includes('avoidance')) {
      return 'Khi né tránh một tình huống, bạn thường lo lắng điều gì nhất?';
    }

    if (tags.includes('risk_high')) {
      return 'Bạn cảm thấy thế nào khi chấp nhận rủi ro? Điều gì khiến bạn tin vào lựa chọn này?';
    }

    if (tags.includes('relationship')) {
      return 'Mối quan hệ ảnh hưởng thế nào đến quyết định của bạn lần này?';
    }

    if (tags.includes('learning')) {
      return 'Bạn kỳ vọng việc học này sẽ mang lại gì trong tương lai?';
    }

    const idx = state.decisions.length % this.questions.length;
    return this.questions[idx];
  },

  getFollowUp(reflection) {
    if (!reflection || reflection.length < 10) {
      return 'Hãy thử mô tả chi tiết hơn về lý do đằng sau quyết định.';
    }
    if (reflection.includes('vì') || reflection.includes('bởi')) {
      return 'Bạn có thể nhìn lại: liệu lý do đó có lặp lại trong các quyết định khác không?';
    }
    return 'Cảm ơn bạn đã chia sẻ. Hãy tiếp tục quan sát mô hình này trong các tình huống tiếp theo.';
  }
};
