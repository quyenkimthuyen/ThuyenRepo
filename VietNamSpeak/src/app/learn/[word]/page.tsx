import { notFound } from "next/navigation";

import { WordLearningCard } from "@/components/word-learning-card";
import { WORDS, getNextWordId, getWordById } from "@/data/words";

export function generateStaticParams() {
  return WORDS.map((word) => ({ word: word.id }));
}

export default async function LearnWordPage({ params }: { params: Promise<{ word: string }> }) {
  const { word: wordId } = await params;
  const word = getWordById(wordId);

  if (!word) notFound();

  return <WordLearningCard word={word} nextWordId={getNextWordId(word.id)} />;
}
