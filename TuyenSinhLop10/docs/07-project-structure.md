# Project Structure

## Monorepo De Xuat

```text
tuyen-sinh-lop10/
  apps/
    web/
      app/
      components/
      features/
      lib/
      public/
    api/
      src/
        modules/
          auth/
          content/
          questions/
          exams/
          attempts/
          analytics/
          tutor/
          study-plans/
          gamification/
        common/
        main.ts
  packages/
    config/
    database/
      prisma/
      seed/
    shared/
      src/types/
      src/schemas/
    prompts/
  data/
    questions/
    exam-templates/
  docs/
  tools/
    import-questions.ts
    validate-questions.ts
```

## Neu Lam Full-stack Next.js Truoc

```text
app/
  (auth)/
  (student)/dashboard/
  (student)/practice/
  (student)/exams/
  (student)/tutor/
  api/
components/
features/
lib/
server/
  db/
  services/
  ai/
data/
docs/
```

## Khuyen Nghi

- MVP co the bat dau bang full-stack Next.js de nhanh ra san pham.
- Khi API phuc tap, tach NestJS thanh `apps/api`.
- Prompt AI nen dat trong package rieng `packages/prompts` de versioning.
- Shared schema dung Zod de dong bo frontend/backend.
