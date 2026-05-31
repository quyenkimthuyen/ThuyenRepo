import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import {
  IPA_TO_SPELLING_RULES,
  PRONUNCIATION_RULES,
  SPELLING_TO_IPA_RULES
} from "@/data/pronunciation-rules";

export default function RulesPage() {
  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-gradient-to-br from-purple-600 to-blue-700 p-6 text-white sm:p-8">
        <Badge className="bg-white/20 text-white">Quy tắc tổng quát cho tiếng Anh Mỹ</Badge>
        <h1 className="mt-3 max-w-3xl text-4xl font-black tracking-tight sm:text-5xl">
          Hai bảng giúp đoán cách đọc và đoán cách viết.
        </h1>
        <p className="mt-3 max-w-3xl text-lg text-blue-50">
          Đây là quy tắc xác suất cao, không phải luật tuyệt đối. Dùng để đọc từ mới tốt hơn và
          nghe chính tả tốt hơn, sau đó kiểm tra lại bằng IPA/từ điển.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <Card className="space-y-3">
          <Badge>Chiều 1</Badge>
          <CardTitle>English spelling {"->"} IPA</CardTitle>
          <p className="text-[var(--muted-foreground)]">
            Nhìn chữ tiếng Anh rồi đoán âm. Hữu ích khi gặp từ mới chưa từng nghe.
          </p>
        </Card>
        <Card className="space-y-3">
          <Badge>Chiều 2</Badge>
          <CardTitle>IPA / âm nghe được {"->"} spelling</CardTitle>
          <p className="text-[var(--muted-foreground)]">
            Nghe một âm rồi đoán các cách viết có thể có. Hữu ích khi nghe chép chính tả.
          </p>
        </Card>
      </section>

      <section className="space-y-4">
        <div>
          <Badge>Bảng 1</Badge>
          <h2 className="mt-2 text-3xl font-black tracking-tight">
            Từ chữ tiếng Anh đoán IPA để đọc được
          </h2>
        </div>
        <div className="overflow-hidden rounded-3xl border border-[var(--border)] bg-[var(--card)]">
          <div className="hidden grid-cols-[1fr_1fr_1fr_1.6fr_1.2fr] gap-3 border-b border-[var(--border)] bg-[var(--muted)] p-4 text-sm font-black md:grid">
            <span>Chữ/cụm chữ</span>
            <span>Thường đọc IPA</span>
            <span>Gợi ý Việt</span>
            <span>Khi nào hay gặp</span>
            <span>Lưu ý</span>
          </div>
          <div className="divide-y divide-[var(--border)]">
            {SPELLING_TO_IPA_RULES.map((rule) => (
              <div
                key={rule.id}
                className="grid gap-3 p-4 md:grid-cols-[1fr_1fr_1fr_1.6fr_1.2fr]"
              >
                <div>
                  <p className="text-xs font-bold text-[var(--muted-foreground)] md:hidden">
                    Chữ/cụm chữ
                  </p>
                  <p className="font-mono text-lg font-black">{rule.spelling}</p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {rule.examples.slice(0, 4).map((example) => (
                      <span
                        key={example}
                        className="rounded-full bg-[var(--muted)] px-2 py-1 text-xs font-bold"
                      >
                        {example}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-xs font-bold text-[var(--muted-foreground)] md:hidden">
                    Thường đọc IPA
                  </p>
                  <p className="font-mono font-black text-blue-600 dark:text-blue-300">
                    {rule.usuallyIpa}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-bold text-[var(--muted-foreground)] md:hidden">
                    Gợi ý Việt
                  </p>
                  <p className="font-black">{rule.vietnameseHint}</p>
                </div>
                <p className="text-sm text-[var(--muted-foreground)]">{rule.when}</p>
                <p className="rounded-2xl bg-amber-50 p-3 text-sm font-bold text-amber-950 dark:bg-amber-950 dark:text-amber-50">
                  {rule.watchOut}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <Badge>Bảng 2</Badge>
          <h2 className="mt-2 text-3xl font-black tracking-tight">
            Từ IPA hoặc âm nghe được đoán cách viết tiếng Anh
          </h2>
        </div>
        <div className="overflow-hidden rounded-3xl border border-[var(--border)] bg-[var(--card)]">
          <div className="hidden grid-cols-[0.8fr_1.4fr_1fr_1.6fr_1.4fr] gap-3 border-b border-[var(--border)] bg-[var(--muted)] p-4 text-sm font-black md:grid">
            <span>IPA nghe được</span>
            <span>Cách viết hay gặp</span>
            <span>Gợi ý Việt</span>
            <span>Ví dụ</span>
            <span>Mẹo nghe viết</span>
          </div>
          <div className="divide-y divide-[var(--border)]">
            {IPA_TO_SPELLING_RULES.map((rule) => (
              <div
                key={rule.id}
                className="grid gap-3 p-4 md:grid-cols-[0.8fr_1.4fr_1fr_1.6fr_1.4fr]"
              >
                <div>
                  <p className="text-xs font-bold text-[var(--muted-foreground)] md:hidden">
                    IPA nghe được
                  </p>
                  <p className="font-mono text-lg font-black text-blue-600 dark:text-blue-300">
                    {rule.ipa}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-bold text-[var(--muted-foreground)] md:hidden">
                    Cách viết hay gặp
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {rule.commonSpellings.map((spelling) => (
                      <span
                        key={spelling}
                        className="rounded-full bg-[var(--muted)] px-2 py-1 font-mono text-xs font-black"
                      >
                        {spelling}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-xs font-bold text-[var(--muted-foreground)] md:hidden">
                    Gợi ý Việt
                  </p>
                  <p className="font-black">{rule.vietnameseHint}</p>
                </div>
                <div className="flex flex-wrap gap-1">
                  {rule.examples.map((example) => (
                    <span
                      key={example}
                      className="rounded-full bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700 dark:bg-blue-950 dark:text-blue-200"
                    >
                      {example}
                    </span>
                  ))}
                </div>
                <p className="rounded-2xl bg-emerald-50 p-3 text-sm font-bold text-emerald-950 dark:bg-emerald-950 dark:text-emerald-50">
                  {rule.listeningTip}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <Badge>Thẻ học chi tiết</Badge>
          <h2 className="mt-2 text-3xl font-black tracking-tight">Một số quy tắc quan trọng</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
        {PRONUNCIATION_RULES.map((rule) => (
          <Card key={rule.id} className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <Badge>Rule: {rule.pattern}</Badge>
                <CardTitle className="mt-3">{rule.ipa}</CardTitle>
              </div>
              <span className="rounded-2xl bg-blue-100 px-4 py-2 text-xl font-black text-blue-700 dark:bg-blue-950 dark:text-blue-200">
                {rule.vietnameseHint}
              </span>
            </div>
            <p className="text-[var(--muted-foreground)]">{rule.explanation}</p>
            <div className="flex flex-wrap gap-2">
              {rule.examples.map((example) => (
                <span key={example} className="rounded-full bg-[var(--muted)] px-3 py-1 text-sm font-bold">
                  {example}
                </span>
              ))}
            </div>
          </Card>
        ))}
        </div>
      </section>
    </div>
  );
}
