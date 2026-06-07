# API Specification

Base URL: `/api/v1`

## Auth

### POST `/auth/session`

Tao hoac lay session hien tai.

Response:

```json
{ "user": { "id": "uuid", "email": "student@example.com", "role": "student" } }
```

## Onboarding

### POST `/students/profile`

Body:

```json
{
  "currentScores": { "toan": 5.5, "nguVan": 6, "tiengAnh": 5 },
  "targetScores": { "toan": 8, "nguVan": 8, "tiengAnh": 8 },
  "targetSchool": "THPT Nguyen Thuong Hien",
  "examDate": "2026-06-06",
  "dailyStudyMinutes": 90
}
```

### POST `/diagnostics/start`

Tao bai kiem tra dau vao theo mon hoac tong hop.

## Content

### GET `/subjects`

Tra ve 3 mon va thoi gian thi.

### GET `/subjects/{subjectId}/topics`

Loc topic theo mon.

### GET `/topics/{topicId}/lessons`

Lay bai hoc, cong thuc, vi du, sai lam.

## Question Bank

### GET `/questions`

Query params: `subjectId`, `topicId`, `difficulty`, `sourceYear`, `tags`, `status`, `limit`, `cursor`.

### POST `/questions/import`

Admin import JSONL. Response gom so dong thanh cong, loi schema, trung ID.

### POST `/questions/{id}/favorite`

Danh dau yeu thich.

## Practice

### POST `/practice/sessions`

Body:

```json
{ "subjectId": "toan", "topicIds": ["ham-so-bac-hai"], "difficulty": ["NhanBiet", "ThongHieu"], "count": 10, "mode": "practice" }
```

### POST `/practice/answers`

Body:

```json
{ "sessionId": "uuid", "questionId": "math-001", "answer": "...", "timeSpentSeconds": 90 }
```

Response:

```json
{ "isCorrect": true, "score": 1, "solution": "...", "nextReviewAt": null }
```

## Exams

### GET `/exam-templates`

Tra ve template theo mon va nam cau truc.

### POST `/exams/generate`

Body:

```json
{ "subjectId": "toan", "templateId": "hcm-2026-toan", "mode": "mock" }
```

### POST `/attempts/{attemptId}/submit`

Nop bai va cham diem.

## Analytics

### GET `/analytics/dashboard`

Tra ve diem trung binh, ty le dung, streak, topic heatmap, du doan diem.

### GET `/analytics/topics/{topicId}`

Chi tiet mastery, loi sai lap lai, cau nen on.

## AI Tutor

### POST `/tutor/chat`

Body:

```json
{
  "mode": "teacher|practice|exam",
  "subjectId": "toan",
  "questionId": "math-001",
  "message": "Em khong hieu buoc nay",
  "studentContext": { "targetScore": 8, "recentMistakes": ["HinhHocPhang"] }
}
```

Response:

```json
{ "message": "...", "hintsUsed": 1, "blocked": false, "usage": { "inputTokens": 1200, "outputTokens": 300 } }
```

### POST `/tutor/grade-essay`

Body gom de bai, bai viet, rubric type. Response gom diem thanh phan, nhan xet, loi uu tien, goi y sua.

## Study Plans

### POST `/study-plans/generate`

Tao ke hoach 30/60/90 ngay.

### PATCH `/study-plan-days/{id}`

Danh dau hoan thanh, doi lich.

## Gamification

### GET `/gamification/profile`

XP, level, streak, badges.

### POST `/xp-events`

Chi backend/internal goi sau khi hoc sinh hoan thanh hanh dong.
