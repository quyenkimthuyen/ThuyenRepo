class StoryEngine {
  constructor(story, savedProgress = null) {
    this.story = story;
    this.scenes = story.scenes;
    this.sceneMap = {};
    this.scenes.forEach(s => { this.sceneMap[s.id] = s; });

    if (savedProgress) {
      this.currentSceneId = savedProgress.currentSceneId;
      this.sceneIndex = savedProgress.sceneIndex || 0;
      this.choicePath = savedProgress.choicePath || [];
      this.consequenceQueue = savedProgress.consequenceQueue || [];
      this.visitedScenes = savedProgress.visitedScenes || [];
    } else {
      this.currentSceneId = story.startScene || story.scenes[0].id;
      this.sceneIndex = 0;
      this.choicePath = [];
      this.consequenceQueue = createConsequenceQueue();
      this.visitedScenes = [];
    }

    this.isComplete = false;
    this.lastConsequenceMessages = [];
  }

  getCurrentScene() {
    return this.sceneMap[this.currentSceneId];
  }

  getProgress() {
    const total = this.story.totalScenes || this.scenes.length;
    const visited = this.visitedScenes.length;
    return Math.min(100, Math.round((visited / total) * 100));
  }

  makeChoice(choiceIndex) {
    const scene = this.getCurrentScene();
    if (!scene || !scene.choices) return null;

    const choice = scene.choices[choiceIndex];
    if (!choice) return null;

    this.choicePath.push(choice.id);
    this.visitedScenes.push(this.currentSceneId);

    const relChanges = applyImmediateEffects(window.appState, choice);
    scheduleConsequences(this.consequenceQueue, choice, this.sceneIndex);

    this.sceneIndex++;
    const delayed = checkDelayedConsequences(this.consequenceQueue, this.sceneIndex, window.appState);
    this.lastConsequenceMessages = delayed;

    if (choice.nextScene) {
      this.currentSceneId = choice.nextScene;
    } else if (choice.endStory) {
      this.isComplete = true;
    }

    const nextScene = this.getCurrentScene();
    if (!nextScene && !this.isComplete) {
      this.isComplete = true;
    }

    return {
      choice,
      relationshipChanges: relChanges,
      delayedConsequences: delayed,
      nextScene,
    };
  }

  advanceNarrative() {
    const scene = this.getCurrentScene();
    if (scene?.choices) return null;

    this.visitedScenes.push(this.currentSceneId);
    this.sceneIndex++;

    const delayed = checkDelayedConsequences(this.consequenceQueue, this.sceneIndex, window.appState);
    this.lastConsequenceMessages = delayed;

    if (scene.nextScene) {
      this.currentSceneId = scene.nextScene;
    } else {
      this.isComplete = true;
    }

    return { delayedConsequences: delayed, nextScene: this.getCurrentScene() };
  }

  getSaveData() {
    return {
      currentSceneId: this.currentSceneId,
      sceneIndex: this.sceneIndex,
      choicePath: this.choicePath,
      consequenceQueue: this.consequenceQueue,
      visitedScenes: this.visitedScenes,
    };
  }

  getCharacter(charId) {
    return this.story.characters.find(c => c.id === charId);
  }
}
