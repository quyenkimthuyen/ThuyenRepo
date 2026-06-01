function renderMindMap(container, detail, alphabet, onSpeak, onOpenLetter) {
  const vowels = alphabet.filter((item) => item.type === "vowel");
  const consonants = alphabet.filter((item) => item.type === "consonant");

  container.innerHTML = `
    <div class="mind-center">Bảng chữ cái<br />tiếng Việt</div>
    <section>
      <h3>Nguyên âm</h3>
      <div class="mind-letters">
        ${vowels.map((item) => `<button data-letter="${item.letter}">${item.letter}</button>`).join("")}
      </div>
    </section>
    <section>
      <h3>Phụ âm</h3>
      <div class="mind-letters">
        ${consonants.map((item) => `<button data-letter="${item.letter}">${item.letter}</button>`).join("")}
      </div>
    </section>
  `;

  const showDetail = (letter) => {
    const item = alphabet.find((entry) => entry.letter === letter);
    detail.innerHTML = `
      <div class="detail-visual">${item.visual}</div>
      <div>
        <p class="eyebrow">${item.imageConcept}</p>
        <h3>${item.letter} / ${item.uppercase}</h3>
        <p>${item.shapeNote}</p>
        <p><strong>Phát âm:</strong> ${item.phonics}</p>
        <p><strong>Ví dụ:</strong> ${item.exampleWord}</p>
        <div class="action-row">
          <button class="pill-btn" data-speak>Nghe</button>
          <button class="pill-btn success" data-open>Học chữ này</button>
        </div>
      </div>
    `;
    detail.querySelector("[data-speak]").addEventListener("click", () => onSpeak(`${item.phonics}. ${item.spelling}. ${item.exampleWord}`));
    detail.querySelector("[data-open]").addEventListener("click", () => onOpenLetter(item.letter));
  };

  container.querySelectorAll("[data-letter]").forEach((button) => {
    button.addEventListener("click", () => showDetail(button.dataset.letter));
  });

  showDetail(alphabet[0].letter);
}

window.MindMap = { renderMindMap };
