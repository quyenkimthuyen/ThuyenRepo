import { Card } from "@/components/ui/card";

export function StatCard({ label, value, detail }: { label: string; value: string | number; detail: string }) {
  return (
    <Card className="flex flex-col gap-2">
      <span className="text-sm font-bold text-[var(--muted-foreground)]">{label}</span>
      <strong className="text-3xl font-black">{value}</strong>
      <span className="text-sm text-[var(--muted-foreground)]">{detail}</span>
    </Card>
  );
}
